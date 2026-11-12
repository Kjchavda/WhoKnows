import math
import random
from datetime import datetime, timezone
from statistics import fmean
from typing import Any

from backend.db import Database


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def fetch_evaluation_dataset(
    db: Database,
    repo_id: int,
    limit: int = 200,
) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("limit must be positive")

    query = """
        WITH selected_issues AS (
            SELECT
                i.github_id AS issue_github_id,
                i.number AS issue_number,
                i.title AS issue_title,
                i.body AS issue_body,
                i.created_at AS issue_ts
            FROM items i
            WHERE i.repo_id = %s
                AND i.kind = 'issue'
                AND EXISTS (
                    SELECT 1
                    FROM pr_closes_issue pci
                    JOIN items pr ON pr.github_id = pci.pr_id
                    WHERE pci.repo_id = i.repo_id
                        AND pci.issue_number = i.number
                        AND pr.kind = 'pr'
                        AND pr.merged_at IS NOT NULL
                )
            ORDER BY i.created_at DESC, i.github_id
            LIMIT %s
        )
        SELECT
            si.issue_github_id,
            si.issue_number,
            si.issue_title,
            si.issue_body,
            si.issue_ts,
            pr.github_id AS closing_pr_id,
            pr.author_id AS pr_author_id,
            author.type AS pr_author_type
        FROM selected_issues si
        JOIN pr_closes_issue pci
            ON pci.repo_id = %s AND pci.issue_number = si.issue_number
        JOIN items pr
            ON pr.github_id = pci.pr_id
            AND pr.kind = 'pr'
            AND pr.merged_at IS NOT NULL
        LEFT JOIN developers author
            ON author.github_id = pr.author_id
        ORDER BY si.issue_ts DESC, si.issue_github_id, pr.github_id;
    """
    rows = db.fetch_all(query, (repo_id, limit, repo_id))
    grouped: dict[int, dict[str, Any]] = {}
    closing_pr_ids: set[int] = set()

    for row in rows:
        issue_id = row["issue_github_id"]
        issue = grouped.setdefault(
            issue_id,
            {
                "issue_github_id": issue_id,
                "issue_number": row["issue_number"],
                "issue_title": row["issue_title"],
                "issue_body": row["issue_body"],
                "issue_ts": _as_utc(row["issue_ts"]),
                "closing_pr_ids": set(),
                "ground_truth": set(),
            },
        )
        pr_id = row["closing_pr_id"]
        issue["closing_pr_ids"].add(pr_id)
        closing_pr_ids.add(pr_id)

        author_type = (row["pr_author_type"] or "").lower()
        if row["pr_author_id"] is not None and author_type != "bot":
            issue["ground_truth"].add(row["pr_author_id"])

    if closing_pr_ids:
        reviewer_rows = db.fetch_all(
            """
                SELECT rv.item_id AS pr_id, rv.reviewer_id
                FROM reviews rv
                JOIN developers d ON d.github_id = rv.reviewer_id
                WHERE rv.item_id = ANY(%s::bigint[])
                    AND rv.reviewer_id IS NOT NULL
                    AND COALESCE(LOWER(d.type), '') <> 'bot';
            """,
            (sorted(closing_pr_ids),),
        )
        pr_to_issue_ids: dict[int, list[int]] = {}
        for issue_id, issue in grouped.items():
            for pr_id in issue["closing_pr_ids"]:
                pr_to_issue_ids.setdefault(pr_id, []).append(issue_id)

        for row in reviewer_rows:
            for issue_id in pr_to_issue_ids.get(row["pr_id"], []):
                grouped[issue_id]["ground_truth"].add(row["reviewer_id"])

    dataset = []
    for issue in grouped.values():
        issue["closing_pr_ids"] = sorted(issue["closing_pr_ids"])
        issue["ground_truth"] = set(issue["ground_truth"])
        issue["query"] = (
            f'{issue["issue_title"]}\n{issue["issue_body"] or ""}'
        )
        dataset.append(issue)

    return sorted(
        dataset,
        key=lambda issue: (issue["issue_ts"], issue["issue_github_id"]),
    )


def split_dataset(
    dataset: list[dict[str, Any]],
    holdout: float = 0.3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not 0.0 < holdout < 1.0:
        raise ValueError("holdout must be between 0 and 1")

    ordered = sorted(
        dataset,
        key=lambda issue: (issue["issue_ts"], issue["issue_github_id"]),
    )
    split_index = int(len(ordered) * (1.0 - holdout))
    return ordered[:split_index], ordered[split_index:]


def first_hit_rank(ranked_ids: list[int], ground_truth: set[int]) -> int | None:
    return next(
        (
            rank
            for rank, developer_id in enumerate(ranked_ids, start=1)
            if developer_id in ground_truth
        ),
        None,
    )


def score_query(
    issue_number: int,
    ranked_ids: list[int],
    candidate_ids: set[int],
    ground_truth: set[int],
    answerable: bool,
    split: str,
) -> dict[str, Any]:
    hit_rank = first_hit_rank(ranked_ids, ground_truth)
    return {
        "issue_number": issue_number,
        "first_hit_rank": hit_rank,
        "n_candidates": len(candidate_ids),
        "truth_size": len(ground_truth),
        "candidate_hit": bool(candidate_ids.intersection(ground_truth)),
        "answerable": answerable,
        "split": split,
        "mrr": 1.0 / hit_rank if hit_rank is not None else 0.0,
        "hit_at_1": hit_rank is not None and hit_rank <= 1,
        "hit_at_3": hit_rank is not None and hit_rank <= 3,
        "hit_at_5": hit_rank is not None and hit_rank <= 5,
        "hit_at_10": hit_rank is not None and hit_rank <= 10,
    }


def bootstrap_ci(
    values: list[float],
    resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float] | None:
    if not values:
        return None
    if resamples <= 0:
        raise ValueError("resamples must be positive")

    rng = random.Random(seed)
    size = len(values)
    estimates = [
        fmean(values[rng.randrange(size)] for _ in range(size))
        for _ in range(resamples)
    ]
    estimates.sort()
    lower = estimates[math.floor(0.025 * (resamples - 1))]
    upper = estimates[math.ceil(0.975 * (resamples - 1))]
    return lower, upper


def paired_bootstrap_ci(
    values: list[float],
    baseline_values: list[float],
    resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float] | None:
    if len(values) != len(baseline_values):
        raise ValueError("paired samples must have equal lengths")
    if not values:
        return None
    if resamples <= 0:
        raise ValueError("resamples must be positive")

    differences = [
        value - baseline
        for value, baseline in zip(values, baseline_values)
    ]
    rng = random.Random(seed)
    size = len(differences)
    estimates = [
        fmean(differences[rng.randrange(size)] for _ in range(size))
        for _ in range(resamples)
    ]
    estimates.sort()
    lower = estimates[math.floor(0.025 * (resamples - 1))]
    upper = estimates[math.ceil(0.975 * (resamples - 1))]
    return lower, upper


def summarize_queries(
    queries: list[dict[str, Any]],
    resamples: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    mrr_values = [query["mrr"] for query in queries]
    return {
        "query_count": len(queries),
        "mrr": fmean(mrr_values) if mrr_values else 0.0,
        "mrr_ci_95": bootstrap_ci(mrr_values, resamples, seed),
        "hit_at_1": (
            fmean(float(query["hit_at_1"]) for query in queries)
            if queries else 0.0
        ),
        "hit_at_3": (
            fmean(float(query["hit_at_3"]) for query in queries)
            if queries else 0.0
        ),
        "hit_at_5": (
            fmean(float(query["hit_at_5"]) for query in queries)
            if queries else 0.0
        ),
        "hit_at_10": (
            fmean(float(query["hit_at_10"]) for query in queries)
            if queries else 0.0
        ),
        "candidate_recall": (
            fmean(float(query["candidate_hit"]) for query in queries)
            if queries else 0.0
        ),
        "mean_candidate_count": (
            fmean(float(query["n_candidates"]) for query in queries)
            if queries else 0.0
        ),
    }


def render_eval_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Ranking evaluation results",
        "",
        f"- Run date (UTC): {summary['generated_at']}",
        f"- Repository ID: {summary['repo_id']}",
        f"- Commit: `{summary['commit']}`",
        f"- Baseline: `{summary['baseline']}`",
        f"- Holdout: {summary['holdout']:.0%}",
        "",
        "Numbers are **not comparable** to earlier ad-hoc runs because this "
        "harness now matches the production path (bot filter, `ef_search`, "
        "and issue self-exclusion).",
        "",
        "Metrics are macro-averaged per query. MRR confidence intervals use "
        "1000 bootstrap resamples with seed 42. Paired intervals compare each "
        "preset with the baseline on the same queries.",
        "",
    ]

    for slice_name, title in (
        ("overall", "Overall"),
        ("answerable_only", "Answerable only"),
    ):
        lines.extend([
            f"## {title}",
            "",
            "| Preset | Split | Queries | MRR (95% CI) | Paired MRR delta vs baseline (95% CI) | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Candidate recall | Mean candidates |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for preset in summary["presets"]:
            for split in ("train", "test"):
                metrics = summary["metrics"][split][preset][slice_name]
                mrr_ci = metrics["mrr_ci_95"]
                paired_ci = metrics["paired_mrr_difference_ci_95"]
                mrr_interval = (
                    "n/a"
                    if mrr_ci is None
                    else f"[{mrr_ci[0]:.3f}, {mrr_ci[1]:.3f}]"
                )
                paired_interval = (
                    "n/a"
                    if paired_ci is None
                    else f"[{paired_ci[0]:.3f}, {paired_ci[1]:.3f}]"
                )
                lines.append(
                    f"| {preset} | {split} | {metrics['query_count']} | "
                    f"{metrics['mrr']:.4f} {mrr_interval} | "
                    f"{paired_interval} | {metrics['hit_at_1']:.4f} | "
                    f"{metrics['hit_at_3']:.4f} | "
                    f"{metrics['hit_at_5']:.4f} | "
                    f"{metrics['hit_at_10']:.4f} | "
                    f"{metrics['candidate_recall']:.4f} | "
                    f"{metrics['mean_candidate_count']:.2f} |"
                )
        lines.append("")

    phase_two_presets = {
        "v2-seeds",
        "v2-seeds-cand",
        "v2-pagerank-seeds-cand",
    }
    if phase_two_presets.intersection(summary["presets"]):
        lines.extend([
            "## What changed and what moved",
            "",
            "| Preset | Test MRR | Test Hit@3 | Test candidate recall | Paired MRR delta vs baseline (95% CI) |",
            "|---|---:|---:|---:|---:|",
        ])
        positive_ci_presets = []
        for preset in summary["presets"]:
            metrics = summary["metrics"]["test"][preset]["overall"]
            paired_ci = metrics["paired_mrr_difference_ci_95"]
            paired_interval = (
                "n/a"
                if paired_ci is None
                else f"[{paired_ci[0]:.3f}, {paired_ci[1]:.3f}]"
            )
            lines.append(
                f"| {preset} | {metrics['mrr']:.4f} | "
                f"{metrics['hit_at_3']:.4f} | "
                f"{metrics['candidate_recall']:.4f} | {paired_interval} |"
            )
            if paired_ci is not None and paired_ci[0] > 0:
                positive_ci_presets.append(preset)

        candidates = (
            ", ".join(f"`{preset}`" for preset in positive_ci_presets)
            if positive_ci_presets
            else "none"
        )
        lines.extend([
            "",
            f"Test-split presets whose paired MRR-difference interval is entirely "
            f"above zero: {candidates}. These are candidates for owner review, "
            "not automatic promotions; `DEFAULT_PRESET` remains `legacy-graph`.",
            "",
            "Known limitations: `pr_files` reflects each PR's final file set, "
            "and the `developers` table has no time dimension.",
            "",
        ])

    return "\n".join(lines)
