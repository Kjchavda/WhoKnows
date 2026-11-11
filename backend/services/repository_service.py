
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
