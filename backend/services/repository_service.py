
from crawler.crawler import (
    GitHub,
    crawl_repository,
)
from backend.access import is_platform_admin
from embeddings.pipeline import Pipeline


class RepositoryService:
    def __init__(self, db, embedder):
        self.db = db
        self.embedder = embedder
        self.github = GitHub()
        self.pipeline = Pipeline(db, embedder=embedder)

    def list_repositories(self, user: dict):
        if is_platform_admin(user):
            return self.db.fetch_all(
                """
                SELECT github_id, owner, name, visibility
                FROM repositories
                ORDER BY owner, name
                """
            )

        return self.db.fetch_all(
            """
            SELECT DISTINCT r.github_id, r.owner, r.name, r.visibility
            FROM repositories r
            LEFT JOIN user_repositories ur
              ON ur.repo_id = r.github_id AND ur.user_id = %s
            WHERE r.visibility = 'public' OR ur.user_id IS NOT NULL
            ORDER BY r.owner, r.name
            """,
            (user["id"],),
        )

    def get_repository(self, repo_id: int):
        if repo_id <= 0:
            raise ValueError("Invalid repository ID")

        return self.db.fetch_one(
            """
            SELECT github_id, owner, name, visibility
            FROM repositories
            WHERE github_id = %s
            """,
            (repo_id,),
        )

    def get_repository_stats(self, repo_id: int):
        if repo_id <= 0:
            raise ValueError("Invalid repository ID")

        return self.db.fetch_one(
            """
            WITH repo_items AS (
                SELECT github_id, author_id, repo_id, updated_at
                FROM items
                WHERE repo_id = %s
            ),
            author_counts AS (
                SELECT author_id
                FROM repo_items
                WHERE author_id IS NOT NULL
                UNION
                SELECT c.author_id
                FROM comments c
                JOIN items i ON i.github_id = c.item_id
                WHERE i.repo_id = %s AND c.author_id IS NOT NULL
                UNION
                SELECT r.reviewer_id
                FROM reviews r
                JOIN items i ON i.github_id = r.item_id
                WHERE i.repo_id = %s AND r.reviewer_id IS NOT NULL
                UNION
                SELECT ch.author_id
                FROM chunks ch
                JOIN items i ON i.github_id = ch.item_id
                WHERE i.repo_id = %s AND ch.author_id IS NOT NULL
            )
            SELECT
                (SELECT COUNT(*) FROM items WHERE repo_id = %s AND kind = 'issue') AS issues,
                (SELECT COUNT(*) FROM items WHERE repo_id = %s AND kind = 'pr') AS pull_requests,
                (SELECT COUNT(*) FROM (SELECT DISTINCT author_id FROM author_counts) AS distinct_authors) AS developers,
                (SELECT COUNT(*) FROM chunks ch JOIN items i ON i.github_id = ch.item_id WHERE i.repo_id = %s) AS chunks,
                (SELECT MAX(updated_at) FROM items WHERE repo_id = %s) AS last_indexed_at
            """,
            (repo_id, repo_id, repo_id, repo_id, repo_id, repo_id, repo_id, repo_id),
        )

    def index_repository(
        self,
        full_name: str,
        indexed_by: int | None = None,
        grant_owner: bool = False,
    ):
        if not full_name or "/" not in full_name:
            raise ValueError(
                "Repository must be in OWNER/NAME format"
            )

        # Crawl GitHub data and obtain the database repository ID.
        repo_id = crawl_repository(
            db=self.db,
            gh=self.github,
            full_name=full_name,
        )

        self.db.execute(
            """
            UPDATE repositories
            SET indexed_by = COALESCE(indexed_by, %s)
            WHERE github_id = %s
            """,
            (indexed_by, repo_id),
        )
        if grant_owner and indexed_by is not None:
            self.db.execute(
                """
                INSERT INTO user_repositories (user_id, repo_id, access_role)
                VALUES (%s, %s, 'owner')
                ON CONFLICT (user_id, repo_id) DO NOTHING
                """,
                (indexed_by, repo_id),
            )

        # Extract, chunk, embed, and store contributions
        # belonging to this repository.
        self.pipeline.run(
            repo_id=repo_id,
            dry_run=False,
        )

        return self.get_repository(repo_id)
