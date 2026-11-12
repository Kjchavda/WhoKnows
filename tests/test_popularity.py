import unittest
from datetime import datetime, timezone

import networkx as nx

from graph.pipeline import PRESETS, RankingPipeline
from graph.ranker import PopularityRanker


class _GraphDatabase:
    def __init__(self, authored_rows):
        self.authored_rows = authored_rows
        self.queries = []

    def fetch_all(self, query, _params=None):
        self.queries.append(query)
        if "'authored' AS relation" in query:
            if "AND LOWER(d.type) <> 'bot'" in query:
                return [
                    row for row in self.authored_rows
                    if row["developer_type"].lower() != "bot"
                ]
            return self.authored_rows
        return []


def _authored_row(developer_id, pr_id, merged_at, developer_type="User"):
    return {
        "developer_id": developer_id,
        "developer_type": developer_type,
        "pr_id": pr_id,
        "file_id": pr_id + 100,
        "additions": 1,
        "deletions": 0,
        "created_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
        "merged_at": merged_at,
        "event_at": None,
        "files_in_pr": 1,
        "relation": "authored",
    }


class PopularityRankerTests(unittest.TestCase):
    def test_orders_by_activity_then_developer_id_and_truncates(self):
        class Builder:
            nx_graph = nx.DiGraph()

            def __init__(self):
                self.nx_graph.add_edge("dev_3", "pr_30", weight=3.0)
                self.nx_graph.add_edge("dev_2", "pr_20", weight=4.0)
                self.nx_graph.add_edge("dev_1", "pr_10", weight=2.0)
                self.nx_graph.add_edge("dev_1", "pr_11", weight=1.0)

        ranker = PopularityRanker(Builder())

        self.assertEqual(
            ranker.rank(),
            [
                {"developer_id": 2, "score": 4.0},
                {"developer_id": 1, "score": 3.0},
                {"developer_id": 3, "score": 3.0},
            ],
        )
        self.assertEqual(
            ranker.rank(top_n=2),
            [
                {"developer_id": 2, "score": 4.0},
                {"developer_id": 1, "score": 3.0},
            ],
        )

    def test_presets_configure_all_time_and_recent_activity(self):
        all_time = PRESETS["popularity-all"]
        recent = PRESETS["popularity-recent"]

        self.assertFalse(all_time.graph.weighted)
        self.assertIsNone(all_time.graph.half_life_days)
        self.assertEqual(recent.graph.half_life_days, 365.0)

    def test_pipeline_excludes_bots_and_prs_merged_after_as_of(self):
        as_of = datetime(2020, 1, 15, tzinfo=timezone.utc)
        db = _GraphDatabase([
            _authored_row(1, 10, datetime(2020, 1, 10, tzinfo=timezone.utc)),
            _authored_row(2, 20, datetime(2020, 1, 12, tzinfo=timezone.utc), "Bot"),
            _authored_row(3, 30, datetime(2020, 2, 1, tzinfo=timezone.utc)),
        ])
        pipeline = RankingPipeline(db, embedder=object())

        result = pipeline.run(
            repo_id=9,
            query="unused",
            as_of=as_of,
            config=PRESETS["popularity-recent"],
            semantic_rows=[],
        )

        self.assertEqual(result.candidate_ids, {1})
        self.assertEqual(
            [row["developer_id"] for row in result.ranked],
            [1],
        )
        self.assertGreater(result.ranked[0]["score"], 0.0)
        self.assertTrue(any(
            "AND LOWER(d.type) <> 'bot'" in query
            for query in db.queries
        ))


if __name__ == "__main__":
    unittest.main()
