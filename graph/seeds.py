import math
from dataclasses import dataclass
from typing import Any

from graph.builder import Builder
from graph.data_loader import GraphDataLoader


@dataclass
class SeedResult:
    file_weights: dict[str, float]
    seed_prs: dict[int, float]


class SeedExpander:
    def __init__(
        self,
        max_seeds: int = 30,
        max_seed_files: int = 50,
        issue_to_pr_discount: float = 0.9,
    ):
        self.max_seeds = max_seeds
        self.max_seed_files = max_seed_files
        self.issue_to_pr_discount = issue_to_pr_discount

    def expand(
        self,
        semantic_rows: list[dict[str, Any]],
        builder: Builder,
        loader: GraphDataLoader,
        repo_id: int,
        as_of,
        exclude_item_ids,
    ) -> SeedResult:
        excluded_ids = set(exclude_item_ids)
        item_scores: dict[int, tuple[str, float]] = {}
        issue_ids = set()

        for row in semantic_rows:
            item_id = row["item_id"]
            if item_id in excluded_ids:
                continue
            similarity = 1.0 - float(row["distance"])
            current = item_scores.get(item_id)
            if current is None or similarity > current[1]:
                item_scores[item_id] = (row["item_kind"], similarity)
            if row["item_kind"] == "issue":
                issue_ids.add(item_id)

        seed_prs: dict[int, float] = {}
        for item_id, (item_kind, similarity) in item_scores.items():
            if item_kind == "pr":
                seed_prs[item_id] = max(seed_prs.get(item_id, float("-inf")), similarity)

        if issue_ids:
            closing_prs = loader.get_closing_prs(
                repo_id,
                issue_ids,
                as_of=as_of,
                exclude_item_ids=excluded_ids,
            )
            for issue_id, (item_kind, similarity) in item_scores.items():
                if item_kind != "issue":
                    continue
                pr_similarity = similarity * self.issue_to_pr_discount
                for pr_id in closing_prs.get(issue_id, []):
                    seed_prs[pr_id] = max(
                        seed_prs.get(pr_id, float("-inf")),
                        pr_similarity,
                    )

        selected_seeds = sorted(
            seed_prs.items(),
            key=lambda item: (-item[1], item[0]),
        )[:max(0, self.max_seeds)]
        seed_prs = dict(selected_seeds)
        if not seed_prs or self.max_seed_files <= 0:
            return SeedResult({}, seed_prs)

        pr_files = loader.get_pr_files(seed_prs)
        file_mass: dict[str, float] = {}
        for pr_id, similarity in seed_prs.items():
            files = pr_files.get(pr_id, [])
            if not files:
                continue
            breadth = 1.0 / (1.0 + math.log(len(files)))
            for file_id, _, _ in files:
                file_node = f"file_{file_id}"
                file_mass[file_node] = (
                    file_mass.get(file_node, 0.0) + similarity * breadth
                )

        weighted_files = {
            file_node: mass * builder.file_idf.get(file_node, 1.0)
            for file_node, mass in file_mass.items()
        }
        selected_files = sorted(
            weighted_files.items(),
            key=lambda item: (-item[1], item[0]),
        )[:self.max_seed_files]
        max_weight = max((weight for _, weight in selected_files), default=0.0)
        if max_weight <= 0:
            return SeedResult({}, seed_prs)

        return SeedResult(
            {
                file_node: weight / max_weight
                for file_node, weight in selected_files
            },
            seed_prs,
        )
