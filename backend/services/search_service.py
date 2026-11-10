
from embeddings.search import SemanticSearch
from graph.builder import Builder
from graph.data_loader import GraphDataLoader
from graph.ranker import GraphRanker


class SearchService:
    """Coordinate semantic retrieval and graph-based developer ranking."""

    def __init__(self, db, embedder):
        self.db = db

        self.semantic_search = SemanticSearch(db, embedder=embedder)
        self.graph_loader = GraphDataLoader(db)

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

        # 1. Semantic retrieval
        semantic_results = self.semantic_search.search(
            query=query,
            repo_id=repo_id,
            limit=limit,
        )

        if not semantic_results:
            return []

        # 2. Deduplicate contributions and calculate semantic scores
        developer_contributions = {}
        developer_evidence = {}

        for row in semantic_results:
            developer_id = row["author_id"]

            if developer_id is None:
                continue

            contribution_id = self._get_contribution_id(row)
            contribution_key = (row["source"], contribution_id)

            similarity = 1 - float(row["distance"])

            if developer_id not in developer_contributions:
                developer_contributions[developer_id] = {}

            if developer_id not in developer_evidence:
                developer_evidence[developer_id] = {}

            existing_score = developer_contributions[developer_id].get(
                contribution_key
            )

            # Keep the best chunk for each contribution.
            if existing_score is None or similarity > existing_score:
                developer_contributions[developer_id][contribution_key] = (
                    similarity
                )

                developer_evidence[developer_id][contribution_key] = {
                    **row,
                    "similarity": similarity,
                }

        if not developer_contributions:
            return []

        # GraphRanker expects semantic scores grouped by developer.
        semantic_scores = {
            developer_id: list(contributions.values())
            for developer_id, contributions in developer_contributions.items()
        }

        developer_ids = set(semantic_scores.keys())

        # 3. Identify PRs retrieved by semantic search
        retrieved_pr_ids = {
            row["item_id"]
            for row in semantic_results
            if row["item_kind"] == "pr"
        }

        # 4. Build the repository-specific implementation graph
        graph_rows = self.graph_loader.get_graph_data(repo_id)

        builder = Builder()
        builder.build_graph(graph_rows)

        # 5. Collect files associated with retrieved PRs
        relevant_files = set()

        for pr_id in retrieved_pr_ids:
            relevant_files.update(
                builder.graph.get("pr_" + str(pr_id), [])
            )

        # 6. Rank developers using the existing graph ranker
        ranker = GraphRanker(builder)

        ranked_developers = ranker.rank(
            relevant_files=relevant_files,
            developer_ids=developer_ids,
            retrieved_pr_ids=retrieved_pr_ids,
            semantic_scores=semantic_scores,
        )

        # 7. Attach evidence to each ranked developer
        results = []

        for developer in ranked_developers:
            developer_id = developer["developer_id"]

            evidence = list(
                developer_evidence.get(developer_id, {}).values()
            )

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
