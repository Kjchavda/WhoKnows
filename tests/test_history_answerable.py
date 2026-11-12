import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from graph.pipeline import PipelineResult, RankingPipeline
from scripts.evaluate_rankers import main


def _row(
    developer_id,
    pr_id,
    relation,
    created_at,
    merged_at=None,
    event_at=None,
):
    return {
        "developer_id": developer_id,
        "pr_id": pr_id,
        "file_id": pr_id + 100,
        "additions": 1,
        "deletions": 0,
        "created_at": created_at,
        "merged_at": merged_at,
        "event_at": event_at,
        "files_in_pr": 1,
        "relation": relation,
    }


class _HistoryDatabase:
    def fetch_all(self, query, _params=None):
        if "'authored' AS relation" in query:
            return [
                _row(
                    1,
                    10,
                    "authored",
                    datetime(2020, 1, 1, tzinfo=timezone.utc),
                ),
                _row(
                    3,
                    30,
                    "authored",
                    datetime(2020, 1, 4, tzinfo=timezone.utc),
                ),
            ]
        if "'reviewed' AS relation" in query:
            return [
                _row(
                    2,
                    20,
                    "reviewed",
                    datetime(2020, 1, 1, tzinfo=timezone.utc),
                    event_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
                ),
                _row(
                    4,
                    40,
                    "reviewed",
                    datetime(2020, 1, 1, tzinfo=timezone.utc),
                    event_at=datetime(2020, 1, 4, tzinfo=timezone.utc),
                ),
            ]
        return []


class HistoryAnswerableTests(unittest.TestCase):
    def test_history_includes_reviewers_and_unmerged_authors_before_as_of(self):
        pipeline = RankingPipeline(_HistoryDatabase(), embedder=object())

        developers = pipeline.history_developers(
            repo_id=9,
            as_of=datetime(2020, 1, 3, tzinfo=timezone.utc),
            exclude_item_ids={99},
        )

        self.assertEqual(developers, {1, 2})

    def test_evaluator_computes_answerable_once_and_shares_it_across_presets(self):
        issue = {
            "issue_github_id": 50,
            "issue_number": 1,
            "issue_ts": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "closing_pr_ids": [90],
            "ground_truth": {1},
            "query": "topic",
        }
        semantic_rows = [{"author_id": 1}]

        class FakeDatabase:
            def open(self):
                pass

            def close(self):
                pass

        class FakePipeline:
            def __init__(self):
                self.semantic_search = self
                self.history_calls = []

            def search(self, **_kwargs):
                return semantic_rows

            def history_developers(self, *args):
                self.history_calls.append(args)
                return set()

            def run(self, **kwargs):
                return PipelineResult(
                    ranked=[],
                    candidate_ids=set(),
                    semantic_rows=kwargs["semantic_rows"],
                    builder=None,
                    evidence={},
                )

        database = FakeDatabase()
        pipeline = FakePipeline()
        captured = {}

        def capture_outputs(_out_dir, _summary, query_results):
            captured.update(query_results)
            return Path("unused")

        with (
            patch("scripts.evaluate_rankers.Database", return_value=database),
            patch("scripts.evaluate_rankers.Embedder", return_value=object()),
            patch("scripts.evaluate_rankers.RankingPipeline", return_value=pipeline),
            patch(
                "scripts.evaluate_rankers.fetch_evaluation_dataset",
                return_value=[issue],
            ),
            patch("scripts.evaluate_rankers._write_outputs", side_effect=capture_outputs),
            patch("scripts.evaluate_rankers._print_table"),
        ):
            result = main([
                "--repo-id",
                "9",
                "--presets",
                "semantic",
            ])

        self.assertEqual(result, 0)
        self.assertEqual(len(pipeline.history_calls), 1)
        answerable_flags = {
            preset: rows[0]["answerable"]
            for preset, rows in captured.items()
        }
        self.assertEqual(answerable_flags, {
            "semantic": True,
            "legacy-graph": True,
        })


if __name__ == "__main__":
    unittest.main()
