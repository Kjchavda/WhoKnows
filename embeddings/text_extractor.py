from backend.db import Database
class TextExtractor:
    def __init__(self, db: Database):
        self.db = db

    def extract_item_bodies(self, repo_id, limit=100, offset=0):
        query = """
            SELECT
                github_id AS item_id,
                author_id,
                CONCAT_WS(
                    E'\\n',
                    NULLIF(TRIM(title), ''),
                    NULLIF(TRIM(body), '')
                ) AS text
            FROM items
            WHERE repo_id = %s
                AND (
                    NULLIF(TRIM(title), '') IS NOT NULL
                    OR NULLIF(TRIM(body), '') IS NOT NULL
                )
            ORDER BY github_id
            LIMIT %s OFFSET %s;
        """

        rows = self.db.fetch_all(query, (repo_id, limit, offset))

        return [
            {
                "item_id": row["item_id"],
                "source": "item_body",
                "source_id": None,
                "author_id": row["author_id"],
                "text": row["text"],
            }
            for row in rows
        ]

    def extract_comments(self, repo_id, limit=100, offset=0):
        query = """
            SELECT
                c.github_id,
                c.kind,
                c.author_id,
                c.item_id,
                NULLIF(TRIM(c.body), '') AS body
            FROM comments c
            JOIN items i
                ON i.github_id = c.item_id
            WHERE i.repo_id = %s
                AND NULLIF(TRIM(c.body), '') IS NOT NULL
            ORDER BY c.github_id
            LIMIT %s OFFSET %s;
        """

        rows = self.db.fetch_all(query, (repo_id, limit, offset))

        transformed_rows = []

        for row in rows:
            new_row = {
                "item_id": row["item_id"],
                "source": row["kind"],
                "source_id": row["github_id"],
                "author_id": row["author_id"],
                "text": row["body"]
            }

            transformed_rows.append(new_row)

        return transformed_rows

    def extract_reviews(self, repo_id, limit=100, offset=0):
        query = """
            SELECT
                rv.github_id,
                rv.item_id,
                rv.reviewer_id,
                NULLIF(TRIM(rv.body), '') AS body
            FROM reviews rv
            JOIN items i
                ON i.github_id = rv.item_id
            WHERE i.repo_id = %s
                AND NULLIF(TRIM(rv.body), '') IS NOT NULL
            ORDER BY rv.github_id
            LIMIT %s OFFSET %s;
        """

        rows = self.db.fetch_all(query, (repo_id, limit, offset))

        transformed_rows = []

        for row in rows:
            new_row = {
                "item_id": row["item_id"],
                "source": "review",
                "source_id": row["github_id"],
                "author_id": row["reviewer_id"],
                "text": row["body"]
            }

            transformed_rows.append(new_row)

        return transformed_rows