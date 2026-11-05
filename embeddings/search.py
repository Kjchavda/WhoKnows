from embeddings.ranker import DeveloperRanker
from embeddings.db import Database
from embeddings.embedder import Embedder


class SemanticSearch:
    def __init__(self, db: Database):
        self.db = db
        self.embedder = Embedder()

    def search(self, query: str, limit: int = 10):
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        if limit <= 0:
            raise ValueError("Limit must be positive.")

        # Embed the user's search query using the same model
        # used to generate the stored chunk embeddings.
        query_embedding = self.embedder.model.encode(
            query.strip()
        ).tolist()

        sql = """
            SELECT
                c.item_id,
                c.source,
                c.source_id,
                c.author_id,
                c.text,
                c.embedding <=> %s::vector AS distance,

                d.login AS developer_login,

                i.number AS item_number,
                i.kind AS item_kind,
                i.title AS item_title,

                r.full_name AS repository,

                CASE
                    WHEN i.kind = 'pr' THEN
                        'https://github.com/' || r.full_name ||
                        '/pull/' || i.number
                    ELSE
                        'https://github.com/' || r.full_name ||
                        '/issues/' || i.number
                END AS github_url

            FROM chunks AS c

            JOIN items AS i
                ON i.github_id = c.item_id

            JOIN repositories AS r
                ON r.github_id = i.repo_id

            LEFT JOIN developers AS d
                ON d.github_id = c.author_id

            WHERE c.embedding IS NOT NULL
                AND COALESCE(LOWER(d.type), '') <> 'bot'
                

            ORDER BY c.embedding <=> %s::vector

            LIMIT %s;

        """

        rows = self.db.fetch_all(
            sql,
            (query_embedding, query_embedding, limit),
        )

        return rows


if __name__ == "__main__":
    db = Database()

    try:
        db.open()
        searcher = SemanticSearch(db)
        ranker = DeveloperRanker()

        query = input("Search GitHub knowledge: ")
        results = searcher.search(query, limit=100)

        ranked = ranker.rank(results)

        source_names = {
            "item_body": "Issue/PR description",
            "issue_comment": "Issue comment",
            "review_comment": "Review comment",
            "review": "PR review",
        }

        for position, developer in enumerate(ranked[:5], start=1):

            print("\n" + "=" * 80)
            print(f"RANK #{position}")
            print("=" * 80)

            print(f"Developer: @{developer['evidence'][0]['developer_login']}")
            print(f"Developer ID: {developer['author_id']}")
            print(f"Score: {developer['score']:.4f}")
            print(f"Average relevance: {developer['average_relevance']:.4f}")
            print(f"Distinct contributions: {developer['contribution_count']}")
            print(f"Breadth count: {developer['breadth_count']}")

            print("\nTOP EVIDENCE")

            for index, evidence in enumerate(developer["evidence"], start=1):

                contribution_type = source_names.get(
                    evidence["source"],
                    evidence["source"]
                )

                print(f"\n  Evidence #{index}")
                print(f"  Type: {contribution_type}")
                print(
                    f"  Parent: {evidence['item_kind'].upper()} "
                    f"#{evidence['item_number']}"
                )
                print(f"  Title: {evidence['item_title']}")
                print(f"  Author: @{evidence['developer_login']}")
                print(f"  Similarity: {1 - float(evidence['distance']):.4f}")
                print(f"  GitHub: {evidence['github_url']}")
                print(f"  Text: {evidence['text']}")

    finally:
        db.close()
