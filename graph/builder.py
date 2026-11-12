import math
from datetime import datetime, timezone

import networkx as nx

from graph.config import GraphConfig


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Graph timestamps must be timezone-aware.")
    return value.astimezone(timezone.utc)


def edge_weight(
    row: dict,
    cfg: GraphConfig,
    as_of: datetime | None,
) -> float:
    if not cfg.weighted:
        return 1.0

    relation = row["relation"]
    if relation not in ("authored", "reviewed", "review_comment"):
        raise ValueError(f"Unknown graph relation: {relation!r}")

    if relation == "authored":
        churn = min(
            max(int(row.get("additions") or 0) + int(row.get("deletions") or 0), 1),
            max(cfg.max_churn, 1),
        )
        churn_factor = math.log1p(churn) / math.log1p(max(cfg.max_churn, 1))
        breadth = max(int(row.get("files_in_pr") or 1), 1)
        breadth_factor = 1.0 / (1.0 + math.log(breadth))
    elif relation == "reviewed":
        churn = min(
            max(int(row.get("additions") or 0) + int(row.get("deletions") or 0), 1),
            max(cfg.max_churn, 1),
        )
        churn_factor = math.log1p(churn) / math.log1p(max(cfg.max_churn, 1))
        breadth = max(int(row.get("files_in_pr") or 1), 1)
        breadth_factor = 1.0 / (1.0 + math.log(breadth))
    else:
        churn_factor = 1.0
        breadth_factor = 1.0

    relation_weights = dict(cfg.relation_weights)
    relation_weight = relation_weights.get(relation, 1.0)
    half_life_days = cfg.half_life_days
    decay = 1.0
    if half_life_days is not None:
        if half_life_days <= 0:
            raise ValueError("half_life_days must be positive or None.")
        if relation == "authored":
            edge_time = row.get("merged_at") if cfg.merged_only else row.get("created_at")
        else:
            edge_time = row.get("event_at")
        if edge_time is None:
            raise ValueError(f"{relation} rows must have an edge timestamp.")
        reference_time = _as_utc(as_of) if as_of is not None else datetime.now(timezone.utc)
        age_days = max(
            0.0,
            (reference_time - _as_utc(edge_time)).total_seconds() / 86400.0,
        )
        decay = 0.5 ** (age_days / half_life_days)

    return relation_weight * churn_factor * breadth_factor * decay


class Builder:
    def __init__(self) -> None:
        self.graph = {}
        self.reverse_graph = {}
        self.nx_graph = nx.DiGraph()
        self.authored_affinity: dict[str, dict[str, float]] = {}
        self.review_affinity: dict[str, dict[str, float]] = {}
        self.file_df: dict[str, int] = {}
        self.file_idf: dict[str, float] = {}
        self.weighted = False

    def add_edge(self, source, destination, weight: float = 1.0):
        if source not in self.graph:
            self.graph[source] = []
            self.reverse_graph[source] = []

        if destination not in self.graph:
            self.graph[destination] = []
            self.reverse_graph[destination] = []

        if destination not in self.graph[source]:
            self.graph[source].append(destination)
            self.reverse_graph[destination].append(source)

        self.nx_graph.add_edge(source, destination, weight=weight)
        self.nx_graph.add_edge(destination, source, weight=weight)

    def _add_affinity(
        self,
        target: dict[str, dict[str, float]],
        developer_node: str,
        file_node: str,
        weight: float,
    ) -> None:
        developer_affinity = target.setdefault(developer_node, {})
        developer_affinity[file_node] = (
            developer_affinity.get(file_node, 0.0) + weight
        )

    def build_graph(
        self,
        rows,
        config: GraphConfig | None = None,
        as_of: datetime | None = None,
        exclude_item_ids=(),
    ):
        cfg = config or GraphConfig()
        self.weighted = cfg.weighted
        excluded_ids = set(exclude_item_ids)
        authored_prs: set[int] = set()
        file_prs: dict[str, set[int]] = {}
        developer_pr_weights: dict[tuple[str, str], float] = {}
        pr_file_edges: set[tuple[str, str]] = set()

        for row in rows:
            relation = row.get("relation")
            legacy_row = relation is None
            if legacy_row:
                relation = "authored"
                weight = 1.0
            else:
                if relation not in ("authored", "reviewed", "review_comment"):
                    raise ValueError(f"Unknown graph relation: {relation!r}")
                if row["pr_id"] in excluded_ids:
                    continue
                if relation == "authored":
                    if cfg.merged_only and row.get("merged_at") is None:
                        continue
                    edge_time = (
                        row.get("merged_at")
                        if cfg.merged_only
                        else row.get("created_at")
                    )
                else:
                    if not cfg.include_reviews:
                        continue
                    edge_time = row.get("event_at")
                if as_of is not None:
                    if edge_time is None or _as_utc(edge_time) >= _as_utc(as_of):
                        continue
                weight = edge_weight(row, cfg, as_of)

            developer_node = f"dev_{row['developer_id']}"
            pr_node = f"pr_{row['pr_id']}"
            file_node = f"file_{row['file_id']}"
            self.nx_graph.add_nodes_from((developer_node, pr_node, file_node))
            pr_file_edges.add((pr_node, file_node))
            developer_pr_key = (developer_node, pr_node)
            developer_pr_weights[developer_pr_key] = max(
                developer_pr_weights.get(developer_pr_key, 0.0),
                weight,
            )

            if relation == "authored":
                self.add_edge(developer_node, pr_node)
                self.add_edge(pr_node, file_node)
                self._add_affinity(
                    self.authored_affinity,
                    developer_node,
                    file_node,
                    weight,
                )
                authored_prs.add(row["pr_id"])
                file_prs.setdefault(file_node, set()).add(row["pr_id"])
            else:
                self._add_affinity(
                    self.review_affinity,
                    developer_node,
                    file_node,
                    weight,
                )

        for (developer_node, pr_node), weight in developer_pr_weights.items():
            self.nx_graph.add_edge(developer_node, pr_node, weight=weight)
            self.nx_graph.add_edge(pr_node, developer_node, weight=weight)

        for pr_node, file_node in pr_file_edges:
            self.nx_graph.add_edge(pr_node, file_node, weight=1.0)
            self.nx_graph.add_edge(file_node, pr_node, weight=1.0)

        self.file_df = {
            file_node: len(pr_ids)
            for file_node, pr_ids in file_prs.items()
        }
        total_prs = len(authored_prs)
        if self.file_df:
            raw_idf = {
                file_node: math.log((1 + total_prs) / (1 + df)) + 1.0
                for file_node, df in self.file_df.items()
            }
            max_idf = max(raw_idf.values())
            self.file_idf = {
                file_node: idf / max_idf
                for file_node, idf in raw_idf.items()
            }
        else:
            self.file_idf = {}

    def get_devs_for_file(self, file_id):
        file_node = "file_" + str(file_id)
        prs = self.reverse_graph.get(file_node, [])
        devs = set()
        for pr in prs:
            devs.update(self.reverse_graph[pr])
        return list(devs)

    def get_files_for_dev(self, developer_id):
        dev_node = "dev_" + str(developer_id)
        prs = self.graph.get(dev_node, [])
        files = set()
        for pr in prs:
            files.update(self.graph[pr])
        return list(files)

    def get_developer_stats(self, developer_id):
        dev_node = "dev_" + str(developer_id)
        prs = self.graph.get(dev_node, [])
        files = set()
        for pr in prs:
            files.update(self.graph[pr])
        return {
            "developer_id": developer_id,
            "total_prs": len(prs),
            "total_files": len(files)
        }

    def get_devs_for_prs(self, pr_ids):
        developers = set()
        for pr_id in pr_ids:
            pr_node = "pr_" + str(pr_id)
            devs = self.reverse_graph.get(pr_node, [])
            developers.update(devs)
        return developers
