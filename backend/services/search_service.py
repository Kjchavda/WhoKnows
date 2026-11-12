
import os

from graph.pipeline import DEFAULT_PRESET, PRESETS, RankingPipeline


class SearchService:
    """Coordinate semantic retrieval and graph-based developer ranking."""

    def __init__(self, db, embedder):
        self.db = db
        self.ranking_pipeline = RankingPipeline(db, embedder)

    @staticmethod
    def _get_contribution_id(row):
        """
        Return the ID identifying the original contribution.

        Item bodies are identified by item_id.
        Comments and reviews are identified by source_id.
        """
        if row["source"] == "item_body":
            return row["item_id"]

        return row["source_id"]

    def search(self, repo_id: int, query: str, limit: int = 100):
        """
        Search a repository and rank developers based on
        semantic relevance and historical graph relationships.

        The database connection lifecycle is managed externally.
        """

        if not isinstance(repo_id, int) or repo_id <= 0:
            raise ValueError("repo_id must be a positive integer")

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        preset_name = os.getenv("RANKING_PRESET", DEFAULT_PRESET)
        if preset_name not in PRESETS:
            raise ValueError(
                f"Unknown ranking preset {preset_name!r}; "
                f"choose from {', '.join(sorted(PRESETS))}."
            )

        pipeline_result = self.ranking_pipeline.run(
            repo_id=repo_id,
            query=query,
            config=PRESETS[preset_name],
            limit=limit,
        )
        if not pipeline_result.ranked:
            return []

        results = []

        for developer in pipeline_result.ranked:
            developer_id = developer["developer_id"]

            evidence = list(pipeline_result.evidence.get(developer_id, {}).values())

            evidence.sort(
                key=lambda row: row["similarity"],
                reverse=True,
            )

            # Keep the three strongest pieces of evidence.
            top_evidence = [
                {
                    "source": row["source"],
                    "item_kind": row["item_kind"],
                    "item_number": row["item_number"],
                    "item_title": row["item_title"],
                    "similarity": row["similarity"],
                    "github_url": row["github_url"],
                    "text": row["text"],
                }
                for row in evidence[:3]
            ]

            results.append({
                **developer,
                "developer_login": (
                    evidence[0]["developer_login"] if evidence else None
                ),
                "evidence": top_evidence,
            })

        return results
