import subprocess
import unittest
from unittest.mock import patch

from scripts.eval_common import render_eval_report
from scripts.evaluate_rankers import (
    _commit_hash,
    _summary_for_split,
    main,
)


def _query(issue_number, mrr, answerable=True):
    return {
        "issue_number": issue_number,
        "split": "test",
        "answerable": answerable,
        "mrr": mrr,
        "n_candidates": 1,
        "candidate_hit": True,
        "hit_at_1": True,
        "hit_at_3": True,
        "hit_at_5": True,
        "hit_at_10": True,
    }


def _report_metric(mrr):
    return {
        "query_count": 1,
        "mrr": mrr,
        "mrr_ci_95": (mrr, mrr),
        "paired_mrr_difference_ci_95": (0.1, 0.2),
        "paired_mrr_difference_ci_95_naive": (0.3, 0.4),
        "hit_at_1": 0.5,
        "hit_at_3": 0.8,
        "hit_at_5": 0.9,
        "hit_at_10": 1.0,
        "candidate_recall": 0.9,
        "mean_candidate_count": 2.0,
    }


class EvaluationHygieneTests(unittest.TestCase):
    def test_commit_hash_adds_dirty_marker_but_ignores_eval_artifacts(self):
        responses = [
            subprocess.CompletedProcess([], 0, "abc123\n", ""),
            subprocess.CompletedProcess([], 0, " M graph/pipeline.py\n", ""),
        ]
        with patch(
            "scripts.evaluate_rankers.subprocess.run",
            side_effect=responses,
        ) as run:
            commit = _commit_hash()

        self.assertEqual(commit, "abc123-dirty")
        status_args = run.call_args_list[1].args[0]
        self.assertIn(":(exclude)eval_results/", status_args)

    def test_main_rejects_dirty_tree_without_override(self):
        with (
            patch("scripts.evaluate_rankers._is_dirty", return_value=True),
            self.assertRaises(SystemExit) as raised,
        ):
            main(["--repo-id", "9"])

        self.assertEqual(raised.exception.code, 2)

    def test_allow_dirty_skips_guard(self):
        class FakeDatabase:
            def open(self):
                pass

            def close(self):
                pass

        with (
            patch("scripts.evaluate_rankers._is_dirty") as is_dirty,
            patch("scripts.evaluate_rankers.Database", return_value=FakeDatabase()),
            patch(
                "scripts.evaluate_rankers.fetch_evaluation_dataset",
                return_value=[],
            ),
        ):
            result = main(["--repo-id", "9", "--allow-dirty"])

        self.assertEqual(result, 1)
        is_dirty.assert_not_called()

    def test_summary_computes_paired_ci_against_naive_baseline(self):
        rows = {
            "legacy-graph": [_query(1, 0.2), _query(2, 0.3)],
            "popularity-recent": [_query(1, 0.4), _query(2, 0.5)],
            "v2-seeds-cand": [_query(1, 0.7), _query(2, 0.8)],
        }

        summary = _summary_for_split(
            rows,
            "test",
            "legacy-graph",
            "popularity-recent",
            resamples=100,
        )

        lower, upper = summary["v2-seeds-cand"]["overall"][
            "paired_mrr_difference_ci_95_naive"
        ]
        self.assertAlmostEqual(lower, 0.3)
        self.assertAlmostEqual(upper, 0.3)

    def test_report_prints_naive_baseline_paired_column(self):
        presets = ["legacy-graph", "popularity-recent", "v2-seeds-cand"]
        metrics = {
            split: {
                preset: {
                    slice_name: _report_metric(0.75)
                    for slice_name in ("overall", "answerable_only")
                }
                for preset in presets
            }
            for split in ("train", "test")
        }
        report = render_eval_report({
            "generated_at": "2026-01-01T00:00:00+00:00",
            "repo_id": 363150,
            "commit": "abc123",
            "baseline": "legacy-graph",
            "naive_baseline": "popularity-recent",
            "holdout": 0.3,
            "presets": presets,
            "metrics": metrics,
        })

        self.assertIn(
            "Paired MRR delta vs `popularity-recent` (95% CI)",
            report,
        )
        self.assertIn(
            "| v2-seeds-cand | 0.7500 | 0.8000 | 0.9000 | "
            "[0.100, 0.200] | [0.300, 0.400] |",
            report,
        )
        self.assertIn("`DEFAULT_PRESET` is `legacy-graph`.", report)


if __name__ == "__main__":
    unittest.main()
