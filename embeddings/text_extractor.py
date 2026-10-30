from db import Database
class TextExtractor:
    def __init__(self, db: Database):
        self.db = db

    def extract_item_bodies(self):
        query = """
            SELECT
                github_id AS item_id,
                author_id,
                CONCAT_WS(
                    E'\n',
                    NULLIF(TRIM(title), ''),
                    NULLIF(TRIM(body), '')
                ) AS text
            FROM items
            WHERE
                NULLIF(TRIM(title), '') IS NOT NULL
                OR NULLIF(TRIM(body), '') IS NOT NULL;
        """

        rows = self.db.fetch_all(query)
        transformed_rows = []

        # TODO: transform each row into the five-field
        # record format, setting source to "item_body"
        # and source_id to None.

        for row in rows:
            new_row = {
                "item_id":row["item_id"],
                "source": "item_body",
                "source_id": None,
                "author_id": row["author_id"],
                "text": row["text"]
            }

            transformed_rows.append(new_row)

        return transformed_rows

    def extract_comments(self):
        query = """
            SELECT 
                github_id,
                kind,
                author_id,
                item_id,
                NULLIF(TRIM(body), '') AS body
            FROM comments
            WHERE 
                NULLIF(TRIM(body),'') IS NOT NULL;
        """

        rows = self.db.fetch_all(query)

        transformed_rows = []

        for row in rows:
            new_row = {
                "item_id":row["item_id"],
                "source": row["kind"],
                "source_id": row["github_id"],
                "author_id": row["author_id"],
                "text": row["body"]
            }

            transformed_rows.append(new_row)

        return transformed_rows

    def extract_reviews(self):
        query = """
            SELECT 
                github_id,
                item_id,
                reviewer_id,
                NULLIF(TRIM(body), '') AS body
            FROM reviews
            WHERE 
                NULLIF(TRIM(body),'') IS NOT NULL;
        """

        rows = self.db.fetch_all(query)

        transformed_rows = []

        for row in rows:
            new_row = {
                "item_id":row["item_id"],
                "source": "review",
                "source_id": row["github_id"],
                "author_id": row["reviewer_id"],
                "text": row["body"]
            }

            transformed_rows.append(new_row)

        return transformed_rows