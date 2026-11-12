from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from backend.db import Database
from embeddings.embedder import Embedder
from embeddings.ranker import SemanticRankerAdapter
from embeddings.search import SemanticSearch
from graph.builder import Builder
from graph.candidates import CandidateBuilder
from graph.config import GraphConfig
from graph.data_loader import GraphDataLoader
from graph.ranker import GraphRanker, PageRankRanker, PopularityRanker
from graph.seeds import SeedExpander, SeedResult


@dataclass(frozen=True)
class PipelineConfig:
    name: str
    ranker: Literal["semantic", "graph", "pagerank", "popularity"]
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
    popularity_top_n: int = 100

    def __post_init__(self) -> None:
        if self.candidate_expansion and not self.seed_expansion:
            raise ValueError("candidate_expansion requires seed_expansion.")


@dataclass
class PipelineResult:
    ranked: list[dict[str, Any]]
    candidate_ids: set[int]
    semantic_rows: list[dict[str, Any]]
    builder: Builder | None
    evidence: dict[int, dict[tuple[str, int], dict[str, Any]]]
    expansion_ids: set[int] = field(default_factory=set)
    file_weights: dict[str, float] = field(default_factory=dict)
    file_affinity: dict[int, float] = field(default_factory=dict)


DEFAULT_PRESET = "legacy-graph"

PRESETS: dict[str, PipelineConfig] = {
    "semantic": PipelineConfig(
        name="semantic",
        ranker="semantic",
        graph=GraphConfig.legacy(),
    ),
    "popularity-all": PipelineConfig(
        name="popularity-all",
        ranker="popularity",
        graph=GraphConfig(weighted=False, half_life_days=None),
    ),
    "popularity-recent": PipelineConfig(
        name="popularity-recent",
        ranker="popularity",
        graph=GraphConfig(),
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
    "v2-graph": PipelineConfig(
        name="v2-graph",
        ranker="graph",
        graph=GraphConfig(),
    ),
    "v2-pagerank": PipelineConfig(
        name="v2-pagerank",
        ranker="pagerank",
        graph=GraphConfig(),
    ),
    "v2-seeds": PipelineConfig(
        name="v2-seeds",
        ranker="graph",
        graph=GraphConfig(),
        seed_expansion=True,
    ),
    "v2-seeds-cand": PipelineConfig(
        name="v2-seeds-cand",
        ranker="graph",
        graph=GraphConfig(),
        seed_expansion=True,
        candidate_expansion=True,
    ),
    "v2-pagerank-seeds-cand": PipelineConfig(
        name="v2-pagerank-seeds-cand",
        ranker="pagerank",
        graph=GraphConfig(),
        seed_expansion=True,
        candidate_expansion=True,
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
            list[dict[str, Any]],
        ] = {}
        self._seed_results_cache: dict[tuple[Any, ...], SeedResult] = {}

    def _get_graph_rows(
        self,
        repo_id: int,
        graph_config: GraphConfig,
    ) -> list[dict[str, Any]]:
        key = (repo_id, graph_config)
        cached = self._graph_rows_cache.get(key)
        if cached is None:
            rows = self.graph_loader.get_graph_rows(repo_id, graph_config)
            self._graph_rows_cache[key] = rows
            return rows
        return cached

    def _expand_seeds(
        self,
        semantic_rows: list[dict[str, Any]],
        builder: Builder,
        repo_id: int,
        as_of: datetime | None,
        excluded_ids: tuple[int, ...],
        config: PipelineConfig,
    ) -> SeedResult:
        expander = SeedExpander(
            max_seeds=config.max_seeds,
            max_seed_files=config.max_seed_files,
            issue_to_pr_discount=config.issue_to_pr_discount,
        )
        if as_of is None:
            return expander.expand(
                semantic_rows,
                builder,
                self.graph_loader,
                repo_id,
                as_of,
                excluded_ids,
            )

        semantic_key = tuple(
            (
                row["item_id"],
                row["item_kind"],
                float(row["distance"]),
            )
            for row in semantic_rows
        )
        cache_key = (
            repo_id,
            config.graph,
            as_of,
            excluded_ids,
            config.max_seeds,
            config.max_seed_files,
            config.issue_to_pr_discount,
            semantic_key,
        )
        cached = self._seed_results_cache.get(cache_key)
        if cached is None:
            cached = expander.expand(
                semantic_rows,
                builder,
                self.graph_loader,
                repo_id,
                as_of,
                excluded_ids,
            )
            self._seed_results_cache[cache_key] = cached
        return cached

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
        excluded_ids = tuple(sorted(set(exclude_item_ids)))
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

        graph_rows = self._get_graph_rows(repo_id, config.graph)

        builder = Builder()
        builder.build_graph(
            graph_rows,
            config=config.graph,
            as_of=as_of,
            exclude_item_ids=excluded_ids,
        )

        if config.ranker == "popularity":
            ranked = PopularityRanker(builder).rank(config.popularity_top_n)
            candidate_ids = {
                row["developer_id"]
                for row in ranked
            }
            return PipelineResult(
                ranked,
                candidate_ids,
                semantic_rows,
                builder,
                evidence,
            )

        retrieved_pr_ids = {
            row["item_id"]
            for row in semantic_rows
            if row["item_kind"] == "pr"
        }
        legacy_relevant_files = {
            file_node
            for pr_id in retrieved_pr_ids
            for file_node in builder.graph.get(f"pr_{pr_id}", [])
        }

        file_weights: dict[str, float] = {}
        expansion_ids: set[int] = set()
        file_affinity: dict[int, float] = {}
        relevant_files = legacy_relevant_files
        if config.seed_expansion:
            seed_result = self._expand_seeds(
                semantic_rows,
                builder,
                repo_id,
                as_of,
                excluded_ids,
                config,
            )
            file_weights = seed_result.file_weights
            relevant_files = file_weights

            if config.candidate_expansion:
                (
                    candidate_ids,
                    expansion_ids,
                    file_affinity,
                ) = CandidateBuilder().build(
                    builder,
                    file_weights,
                    candidate_ids,
                    config.max_expanded_candidates,
                )

        ranker = (
            GraphRanker(builder)
            if config.ranker == "graph"
            else PageRankRanker(builder)
        )
        rank_kwargs = {
            "relevant_files": relevant_files,
            "developer_ids": candidate_ids,
            "retrieved_pr_ids": retrieved_pr_ids,
            "semantic_scores": semantic_scores,
        }
        if config.ranker == "graph":
            if config.candidate_expansion:
                rank_kwargs["file_affinity"] = file_affinity
        else:
            rank_kwargs["file_weights"] = file_weights if config.seed_expansion else None
            rank_kwargs["seed_mix"] = config.seed_mix
        ranked = ranker.rank(**rank_kwargs)
        return PipelineResult(
            ranked,
            candidate_ids,
            semantic_rows,
            builder,
            evidence,
            expansion_ids,
            file_weights,
            file_affinity,
        )


