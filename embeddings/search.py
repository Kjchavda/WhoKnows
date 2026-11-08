from embeddings.ranker import DeveloperRanker
from backend.db import Database
from embeddings.embedder import Embedder


class SemanticSearch:
    def __init__(self, db: Database):
        self.db = db
        self.embedder = Embedder()

    def search(self, query: str, repo_id: int, limit: int = 10):
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
                AND i.repo_id = %s
                

            ORDER BY c.embedding <=> %s::vector

            LIMIT %s;

        """

        rows = self.db.fetch_all(
            sql,
            (query_embedding, repo_id, query_embedding, limit),
        )

        return rows
