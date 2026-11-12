from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from backend.db import Database
from embeddings.embedder import Embedder
from embeddings.ranker import SemanticRankerAdapter
from embeddings.search import SemanticSearch
from graph.builder import Builder
from graph.config import GraphConfig
from graph.data_loader import GraphDataLoader
from graph.ranker import GraphRanker, PageRankRanker


@dataclass(frozen=True)
class PipelineConfig:
    name: str
    ranker: Literal["semantic", "graph", "pagerank"]
    graph: GraphConfig
    seed_expansion: bool = False
    candidate_expansion: bool = False
    semantic_limit: int = 100
    max_seeds: int = 30
    max_seed_files: int = 50
    issue_to_pr_discount: float = 0.9
    max_expanded_candidates: int = 30
    seed_mix: float = 0.5
    holdout: float = 0.3
    bootstrap_resamples: int = 1000


@dataclass
class PipelineResult:
    ranked: list[dict[str, Any]]
    candidate_ids: set[int]
    semantic_rows: list[dict[str, Any]]
    builder: Builder | None
    evidence: dict[int, dict[tuple[str, int], dict[str, Any]]]


DEFAULT_PRESET = "legacy-graph"

PRESETS: dict[str, PipelineConfig] = {
    "semantic": PipelineConfig(
        name="semantic",
        ranker="semantic",
        graph=GraphConfig.legacy(),
    ),
    "legacy-graph": PipelineConfig(
        name="legacy-graph",
        ranker="graph",
        graph=GraphConfig.legacy(),
    ),
    "legacy-pagerank": PipelineConfig(
        name="legacy-pagerank",
        ranker="pagerank",
        graph=GraphConfig.legacy(),
    ),
}


def aggregate_contributions(
    rows: Iterable[dict[str, Any]],
) -> tuple[
    dict[int, dict[tuple[str, int], float]],
    dict[int, dict[tuple[str, int], dict[str, Any]]],
]:
    semantic_scores: dict[int, dict[tuple[str, int], float]] = {}
    evidence: dict[int, dict[tuple[str, int], dict[str, Any]]] = {}

    for row in rows:
        developer_id = row["author_id"]
        if developer_id is None:
            continue

        source = row["source"]
        contribution_id = (
            row["item_id"] if source == "item_body" else row["source_id"]
        )
        if contribution_id is None:
            continue

        contribution_key = (source, contribution_id)
        similarity = 1.0 - float(row["distance"])
        developer_scores = semantic_scores.setdefault(developer_id, {})
        current_score = developer_scores.get(contribution_key)
        if current_score is None or similarity > current_score:
            developer_scores[contribution_key] = similarity
            evidence.setdefault(developer_id, {})[contribution_key] = {
                **row,
                "similarity": similarity,
            }

    return semantic_scores, evidence


class RankingPipeline:
    def __init__(self, db: Database, embedder: Embedder):
        self.semantic_search = SemanticSearch(db, embedder=embedder)
        self.graph_loader = GraphDataLoader(db)
        self._graph_rows_cache: dict[
            tuple[int, GraphConfig],
            tuple[datetime, list[dict[str, Any]]],
        ] = {}

    def _get_graph_rows(
        self,
        repo_id: int,
        graph_config: GraphConfig,
        as_of: datetime | None,
    ) -> list[dict[str, Any]]:
        if as_of is None:
            return self.graph_loader.get_graph_data(repo_id)

        key = (repo_id, graph_config)
        cached = self._graph_rows_cache.get(key)
        if cached is None or cached[0] != as_of:
            rows = self.graph_loader.get_graph_data(
                repo_id,
                max_timestamp=as_of,
            )
            self._graph_rows_cache[key] = (as_of, rows)
            return rows
        return cached[1]

    def run(
        self,
        repo_id: int,
        query: str,
        *,
        as_of: datetime | None = None,
        exclude_item_ids: Iterable[int] = (),
        config: PipelineConfig,
        semantic_rows: list[dict[str, Any]] | None = None,
        limit: int = 100,
    ) -> PipelineResult:
        excluded_ids = tuple(exclude_item_ids)
        if semantic_rows is None:
            semantic_rows = self.semantic_search.search(
                query=query,
                repo_id=repo_id,
                limit=min(limit, config.semantic_limit),
                as_of=as_of,
                exclude_item_ids=excluded_ids,
            )

        semantic_scores, evidence = aggregate_contributions(semantic_rows)
        candidate_ids = set(semantic_scores)
        if config.ranker == "semantic":
            if not semantic_rows or not candidate_ids:
                return PipelineResult(
                    [], candidate_ids, semantic_rows, None, evidence
                )
            ranked = SemanticRankerAdapter().rank(semantic_rows)
            return PipelineResult(ranked, candidate_ids, semantic_rows, None, evidence)

        graph_rows = self._get_graph_rows(
            repo_id,
            config.graph,
            as_of,
        )
        excluded_pr_ids = set(excluded_ids)
        graph_rows = [
            row for row in graph_rows if row["pr_id"] not in excluded_pr_ids
        ]

        builder = Builder()
        builder.build_graph(graph_rows)

        retrieved_pr_ids = {
            row["item_id"]
            for row in semantic_rows
            if row["item_kind"] == "pr"
        }
        relevant_files = {
            file_node
            for pr_id in retrieved_pr_ids
            for file_node in builder.graph.get(f"pr_{pr_id}", [])
        }

        ranker = (
            GraphRanker(builder)
            if config.ranker == "graph"
            else PageRankRanker(builder)
        )
        ranked = ranker.rank(
            relevant_files=relevant_files,
            developer_ids=candidate_ids,
            retrieved_pr_ids=retrieved_pr_ids,
            semantic_scores=semantic_scores,
        )
        return PipelineResult(ranked, candidate_ids, semantic_rows, builder, evidence)


