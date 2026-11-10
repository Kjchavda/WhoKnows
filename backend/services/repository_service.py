
from crawler.crawler import (
    GitHub,
    crawl_repository,
)
from embeddings.pipeline import Pipeline


class RepositoryService:
    def __init__(self, db, embedder):
        self.db = db
        self.embedder = embedder
        self.github = GitHub()
        self.pipeline = Pipeline(db, embedder=embedder)

    def list_repositories(self):
        return self.db.fetch_all(
            """
            SELECT github_id, owner, name
            FROM repositories
            ORDER BY owner, name
            """
        )

    def get_repository(self, repo_id: int):
        if repo_id <= 0:
            raise ValueError("Invalid repository ID")

        return self.db.fetch_one(
            """
            SELECT github_id, owner, name
            FROM repositories
            WHERE github_id = %s
            """,
            (repo_id,),
        )

    def index_repository(self, full_name: str):
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

        # Extract, chunk, embed, and store contributions
        # belonging to this repository.
        self.pipeline.run(
            repo_id=repo_id,
            dry_run=False,
        )

        return self.get_repository(repo_id)
