from ranker import DeveloperRanker
from db import Database
from embedder import Embedder


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
                c.embedding <=> %s::vector AS distance
            FROM chunks AS c
            WHERE c.embedding IS NOT NULL
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

        for rank, result in enumerate(results, start=1):
            print(f"\n--- Result {rank} ---")
            print(f"Item ID: {result['item_id']}")
            print(f"Source: {result['source']}")
            print(f"Author ID: {result['author_id']}")
            print(f"Cosine distance: {result['distance']:.4f}")
            print(f"Text: {result['text'][:500]}")

        for position, developer in enumerate(ranked, start=1):
            print(f"\nRank: {position}")
            print(f"Developer ID: {developer['author_id']}")
            print(f"Score: {developer['score']:.4f}")
            print(f"Average similarity: {developer['average_similarity']:.4f}")
            print(f"Contributions: {developer['contribution_count']}")

            print("Best evidence:")
            for evidence in developer["evidence"]:
                print("-", evidence["text"][:200])

    finally:
        db.close()
