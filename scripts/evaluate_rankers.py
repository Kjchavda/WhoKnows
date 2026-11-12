import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db import Database
from embeddings.embedder import Embedder
from graph.pipeline import PRESETS, RankingPipeline
from scripts.eval_common import (
    fetch_evaluation_dataset,
    paired_bootstrap_ci,
    render_eval_report,
    score_query,
    split_dataset,
    summarize_queries,
)


def _commit_hash() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _selected_presets(value: str | None, baseline: str) -> list[str]:
    if value is None or value.strip().lower() == "all":
        requested = list(PRESETS)
    else:
        requested = [name.strip() for name in value.split(",") if name.strip()]

    unknown = sorted(set(requested) - PRESETS.keys())
    if unknown:
        raise ValueError(f"Unknown ranking presets: {', '.join(unknown)}")
    if baseline not in PRESETS:
        raise ValueError(f"Unknown baseline preset: {baseline}")
    if baseline not in requested:
        requested.append(baseline)
    return list(dict.fromkeys(requested))


def _history_developers(semantic_rows, builder) -> set[int]:
    developers = {
        row["author_id"]
        for row in semantic_rows
        if row["author_id"] is not None
    }
    if builder is not None:
        developers.update(
            int(node.removeprefix("dev_"))
            for node in builder.graph
            if node.startswith("dev_")
        )
    return developers


def _summary_for_split(
    query_results: dict[str, list[dict[str, Any]]],
    split: str,
    baseline: str,
    resamples: int = 1000,
) -> dict[str, Any]:
    summaries = {}
    baseline_rows = query_results[baseline]

    for preset, rows in query_results.items():
        split_rows = [row for row in rows if row["split"] == split]
        baseline_split = [row for row in baseline_rows if row["split"] == split]
        metrics = {}
        for key, predicate in (
            ("overall", lambda row: True),
            ("answerable_only", lambda row: row["answerable"]),
        ):
            selected = [row for row in split_rows if predicate(row)]
            paired_baseline = {
                row["issue_number"]: row["mrr"]
                for row in baseline_split
                if predicate(row)
            }
            paired_rows = [
                row for row in selected
                if row["issue_number"] in paired_baseline
            ]
            summary = summarize_queries(selected, resamples=resamples)
            summary["paired_mrr_difference_ci_95"] = paired_bootstrap_ci(
                [row["mrr"] for row in paired_rows],
                [
                    paired_baseline[row["issue_number"]]
                    for row in paired_rows
                ],
                resamples=resamples,
            )
            metrics[key] = summary
        summaries[preset] = metrics

    return summaries


def _format_ci(value: tuple[float, float] | None) -> str:
    return "n/a" if value is None else f"[{value[0]:.3f}, {value[1]:.3f}]"


def _print_table(
    summaries: dict[str, dict[str, dict[str, Any]]],
    slice_name: str,
) -> None:
    metric_names = (
        ("mrr", "MRR"),
        ("mrr_ci_95", "MRR 95% CI"),
        ("paired_mrr_difference_ci_95", "Paired delta 95% CI"),
        ("hit_at_1", "Hit@1"),
        ("hit_at_3", "Hit@3"),
        ("hit_at_5", "Hit@5"),
        ("hit_at_10", "Hit@10"),
        ("candidate_recall", "Candidate recall"),
        ("mean_candidate_count", "Mean candidates"),
    )
    headers = ["preset"]
    for split in ("train", "test"):
        headers.extend(f"{split} {label}" for _, label in metric_names)

    print(f"\n{slice_name.replace('_', ' ').title()} metrics")
    print(" | ".join(headers))
    for preset in summaries["train"]:
        values = [preset]
        for split in ("train", "test"):
            metrics = summaries[split][preset][slice_name]
            for key, _ in metric_names:
                value = metrics[key]
                if key.endswith("_ci_95"):
                    values.append(_format_ci(value))
                else:
                    values.append(f"{value:.4f}")
        print(" | ".join(values))


def _write_outputs(
    out_dir: Path,
    summary: dict[str, Any],
    query_results: dict[str, list[dict[str, Any]]],
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)

    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = Path("docs") / "EVAL_RESULTS.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_eval_report(summary), encoding="utf-8")

    csv_path = run_dir / "per_query.csv"
    fieldnames = (
        "issue_number",
        "preset",
        "first_hit_rank",
        "n_candidates",
        "truth_size",
        "candidate_hit",
        "answerable",
        "split",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for preset, rows in query_results.items():
            for row in rows:
                writer.writerow({
                    "issue_number": row["issue_number"],
                    "preset": preset,
                    "first_hit_rank": row["first_hit_rank"] or "",
                    "n_candidates": row["n_candidates"],
                    "truth_size": row["truth_size"],
                    "candidate_hit": row["candidate_hit"],
                    "answerable": row["answerable"],
                    "split": row["split"],
                })
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the registered ranking presets."
    )
    parser.add_argument("--repo-id", type=int, required=True)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--holdout", type=float, default=0.3)
    parser.add_argument("--presets", default=None, help="Comma-separated list or all")
    parser.add_argument("--baseline", default="legacy-graph")
    parser.add_argument("--out", type=Path, default=Path("eval_results"))
    args = parser.parse_args(argv)

    if args.limit <= 0:
        parser.error("--limit must be positive")
    try:
        presets = _selected_presets(args.presets, args.baseline)
        split_dataset([], args.holdout)
    except ValueError as exc:
        parser.error(str(exc))

    db = Database()
    try:
        db.open()
        dataset = fetch_evaluation_dataset(db, args.repo_id, args.limit)
        train_set, test_set = split_dataset(dataset, args.holdout)
        if not dataset:
            print("No eligible merged-PR issue data found.")
            return 1

        embedder = Embedder()
        pipeline = RankingPipeline(db, embedder)
        query_results: dict[str, list[dict[str, Any]]] = {
            preset: [] for preset in presets
        }

        for split_name, issues in (("train", train_set), ("test", test_set)):
            for issue in issues:
                exclude_item_ids = {
                    issue["issue_github_id"],
                    *issue["closing_pr_ids"],
                }
                semantic_rows = pipeline.semantic_search.search(
                    query=issue["query"],
                    repo_id=args.repo_id,
                    limit=max(
                        PRESETS[name].semantic_limit for name in presets
                    ),
                    as_of=issue["issue_ts"],
                    exclude_item_ids=exclude_item_ids,
                )

                for preset in presets:
                    config = PRESETS[preset]
                    result = pipeline.run(
                        repo_id=args.repo_id,
                        query=issue["query"],
                        as_of=issue["issue_ts"],
                        exclude_item_ids=exclude_item_ids,
                        config=config,
                        semantic_rows=semantic_rows,
                        limit=config.semantic_limit,
                    )
                    truth = issue["ground_truth"]
                    history_developers = _history_developers(
                        semantic_rows,
                        result.builder,
                    )
                    query_results[preset].append(
                        score_query(
                            issue_number=issue["issue_number"],
                            ranked_ids=[
                                row["developer_id"] for row in result.ranked
                            ],
                            candidate_ids=result.candidate_ids,
                            ground_truth=truth,
                            answerable=bool(truth.intersection(history_developers)),
                            split=split_name,
                        )
                    )
    finally:
        db.close()

    metrics = {}
    for split_name in ("train", "test"):
        metrics[split_name] = _summary_for_split(
            query_results,
            split_name,
            args.baseline,
        )

    generated_at = datetime.now(timezone.utc)
    summary = {
        "repo_id": args.repo_id,
        "generated_at": generated_at.isoformat(),
        "commit": _commit_hash(),
        "holdout": args.holdout,
        "baseline": args.baseline,
        "presets": presets,
        "metrics": metrics,
    }

    run_dir = _write_outputs(args.out, summary, query_results)
    print(f"Evaluation artifacts: {run_dir}")
    _print_table(metrics, "overall")
    _print_table(metrics, "answerable_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
