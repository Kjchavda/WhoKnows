import unittest
from datetime import datetime, timezone

from scripts.eval_common import (
    bootstrap_ci,
    fetch_evaluation_dataset,
    paired_bootstrap_ci,
    score_query,
    split_dataset,
)


class _EvaluationDatabase:
    def __init__(self):
        self.queries = []

    def fetch_all(self, query, params):
        self.queries.append((query, params))
        if "FROM reviews rv" in query:
            return [{"pr_id": 101, "reviewer_id": 4}]
        return [
            {
                "issue_github_id": 10,
                "issue_number": 1,
                "issue_title": "Fix issue",
                "issue_body": "Body",
                "issue_ts": datetime(2020, 1, 1, tzinfo=timezone.utc),
                "closing_pr_id": 101,
                "pr_author_id": 2,
                "pr_author_type": "User",
            },
            {
                "issue_github_id": 10,
                "issue_number": 1,
                "issue_title": "Fix issue",
                "issue_body": "Body",
                "issue_ts": datetime(2020, 1, 1, tzinfo=timezone.utc),
                "closing_pr_id": 102,
                "pr_author_id": 3,
                "pr_author_type": "Bot",
            },
        ]


class EvaluationMetricsTests(unittest.TestCase):
    def test_metrics_and_bootstrap_are_deterministic(self):
        result = score_query(
            issue_number=12,
            ranked_ids=[4, 8, 9, 7],
            candidate_ids={4, 8},
            ground_truth={7},
            answerable=True,
            split="test",
        )

        self.assertEqual(result["first_hit_rank"], 4)
        self.assertEqual(result["mrr"], 0.25)
        self.assertFalse(result["hit_at_3"])
        self.assertTrue(result["hit_at_5"])
        self.assertFalse(result["candidate_hit"])

        values = [0.0, 0.5, 1.0]
        self.assertEqual(
            bootstrap_ci(values, resamples=100, seed=7),
            bootstrap_ci(values, resamples=100, seed=7),
        )
        self.assertEqual(
            paired_bootstrap_ci(values, values, resamples=100, seed=7),
            (0.0, 0.0),
        )

    def test_split_keeps_oldest_queries_in_train(self):
        issues = [
            {
                "issue_number": number,
                "issue_github_id": number,
                "issue_ts": datetime(2020, 1, number, tzinfo=timezone.utc),
            }
            for number in (4, 1, 3, 2)
        ]

        train, test = split_dataset(issues, holdout=0.25)

        self.assertEqual([row["issue_number"] for row in train], [1, 2, 3])
        self.assertEqual([row["issue_number"] for row in test], [4])

    def test_dataset_groups_closing_prs_and_queries_reviewers_once(self):
        db = _EvaluationDatabase()

        dataset = fetch_evaluation_dataset(db, repo_id=9, limit=20)

        self.assertEqual(len(dataset), 1)
        issue = dataset[0]
        self.assertEqual(issue["closing_pr_ids"], [101, 102])
        self.assertEqual(issue["ground_truth"], {2, 4})
        self.assertEqual(issue["query"], "Fix issue\nBody")
        self.assertEqual(len(db.queries), 2)
        self.assertIn("COALESCE(LOWER(d.type), '') <> 'bot'", db.queries[1][0])


if __name__ == "__main__":
    unittest.main()
