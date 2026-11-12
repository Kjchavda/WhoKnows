import math
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import networkx as nx
from graph.builder import Builder, edge_weight
from graph.config import GraphConfig
from graph.data_loader import GraphDataLoader
from graph.ranker import PageRankRanker


class _GraphDatabase:
    def __init__(self):
        self.queries = []

    def fetch_all(self, query, params):
        self.queries.append((query, params))
        if "'authored' AS relation" in query:
            return [{
                "developer_id": 1,
                "pr_id": 10,
                "file_id": 100,
                "additions": 1,
                "deletions": 0,
                "created_at": None,
                "merged_at": None,
                "event_at": None,
                "files_in_pr": 1,
                "relation": "authored",
            }]
        if "WITH reviewers AS" in query:
            return [{
                "developer_id": 2,
                "pr_id": 10,
                "file_id": 100,
                "additions": 1,
                "deletions": 0,
                "created_at": None,
                "merged_at": None,
                "event_at": None,
                "files_in_pr": 1,
                "relation": "reviewed",
            }]
        return [{
            "developer_id": 3,
            "pr_id": 10,
            "file_id": 100,
            "additions": 0,
            "deletions": 0,
            "created_at": None,
            "merged_at": None,
            "event_at": None,
            "files_in_pr": 1,
            "relation": "review_comment",
        }]


class GraphBuilderV2Tests(unittest.TestCase):
    def test_legacy_rows_preserve_graph_adjacency_and_ignore_filters(self):
        rows = [
            {"developer_id": 1, "pr_id": 10, "file_id": 100},
            {"developer_id": 2, "pr_id": 11, "file_id": 101},
        ]
        builder = Builder()
        builder.build_graph(
            rows,
            config=GraphConfig(),
            as_of=datetime(2020, 1, 1, tzinfo=timezone.utc),
            exclude_item_ids={10, 11},
        )

        self.assertEqual(
            builder.graph,
            {
                "dev_1": ["pr_10"],
                "pr_10": ["file_100"],
                "file_100": [],
                "dev_2": ["pr_11"],
                "pr_11": ["file_101"],
                "file_101": [],
            },
        )
        self.assertEqual(
            builder.reverse_graph,
            {
                "dev_1": [],
                "pr_10": ["dev_1"],
                "file_100": ["pr_10"],
                "dev_2": [],
                "pr_11": ["dev_2"],
                "file_101": ["pr_11"],
            },
        )
        self.assertEqual(
            set(builder.nx_graph.edges()),
            {
                ("dev_1", "pr_10"),
                ("pr_10", "dev_1"),
                ("pr_10", "file_100"),
                ("file_100", "pr_10"),
                ("dev_2", "pr_11"),
                ("pr_11", "dev_2"),
                ("pr_11", "file_101"),
                ("file_101", "pr_11"),
            },
        )

    def test_filters_by_relation_time_and_excluded_prs(self):
        as_of = datetime(2021, 1, 1, tzinfo=timezone.utc)
        before = as_of - timedelta(days=1)
        after = as_of + timedelta(days=1)
        rows = [
            {
                "developer_id": 1, "pr_id": 10, "file_id": 100,
                "relation": "authored", "created_at": before,
                "merged_at": before, "event_at": None,
                "additions": 1000, "deletions": 0, "files_in_pr": 1,
            },
            {
                "developer_id": 1, "pr_id": 11, "file_id": 101,
                "relation": "authored", "created_at": before,
                "merged_at": after, "event_at": None,
                "additions": 20, "deletions": 10, "files_in_pr": 1,
            },
            {
                "developer_id": 1, "pr_id": 12, "file_id": 102,
                "relation": "authored", "created_at": before,
                "merged_at": before, "event_at": None,
                "additions": 20, "deletions": 10, "files_in_pr": 1,
            },
            {
                "developer_id": 1, "pr_id": 13, "file_id": 103,
                "relation": "authored", "created_at": before,
                "merged_at": None, "event_at": None,
                "additions": 20, "deletions": 10, "files_in_pr": 1,
            },
            {
                "developer_id": 2, "pr_id": 10, "file_id": 100,
                "relation": "reviewed", "created_at": before,
                "merged_at": before, "event_at": before,
                "additions": 1000, "deletions": 0, "files_in_pr": 1,
            },
            {
                "developer_id": 3, "pr_id": 10, "file_id": 100,
                "relation": "reviewed", "created_at": before,
                "merged_at": before, "event_at": as_of,
                "additions": 20, "deletions": 10, "files_in_pr": 1,
            },
            {
                "developer_id": 4, "pr_id": 10, "file_id": 104,
                "relation": "review_comment", "created_at": before,
                "merged_at": before, "event_at": before,
                "additions": 0, "deletions": 0, "files_in_pr": 1,
            },
        ]

        builder = Builder()
        builder.build_graph(
            rows,
            config=GraphConfig(half_life_days=None),
            as_of=as_of,
            exclude_item_ids={12},
        )

        self.assertEqual(builder.graph["dev_1"], ["pr_10"])
        self.assertNotIn("pr_11", builder.graph)
        self.assertNotIn("pr_12", builder.graph)
        self.assertNotIn("pr_13", builder.graph)
        self.assertNotIn("dev_2", builder.graph)
        self.assertNotIn("dev_3", builder.graph)
        self.assertNotIn("dev_4", builder.graph)
        self.assertIn(("dev_2", "pr_10"), builder.nx_graph.edges())
        self.assertIn(("dev_4", "pr_10"), builder.nx_graph.edges())
        self.assertEqual(builder.authored_affinity["dev_1"]["file_100"], 1.0)
        self.assertEqual(builder.review_affinity["dev_2"]["file_100"], 0.4)
        self.assertEqual(builder.review_affinity["dev_4"]["file_104"], 0.7)

    def test_edge_weight_churn_breadth_and_one_year_decay(self):
        as_of = datetime(2021, 1, 1, tzinfo=timezone.utc)
        config = GraphConfig(half_life_days=None)
        churn_row = {
            "relation": "authored",
            "additions": 9,
            "deletions": 0,
            "files_in_pr": 1,
            "created_at": as_of,
            "merged_at": as_of,
        }
        self.assertTrue(math.isclose(
            edge_weight(churn_row, config, as_of),
            math.log1p(9) / math.log1p(config.max_churn),
        ))

        breadth_row = {
            **churn_row,
            "additions": config.max_churn,
            "files_in_pr": 4,
        }
        self.assertTrue(math.isclose(
            edge_weight(breadth_row, config, as_of),
            1.0 / (1.0 + math.log(4)),
        ))

        year_old = {
            **churn_row,
            "additions": config.max_churn,
            "merged_at": as_of - timedelta(days=365),
            "files_in_pr": 1,
        }
        self.assertTrue(math.isclose(
            edge_weight(year_old, GraphConfig(), as_of),
            0.5,
        ))

    def test_file_idf_penalizes_files_in_every_pr(self):
        rows = []
        for pr_id, file_ids in ((1, (100, 101)), (2, (100,)), (3, (100,))):
            for file_id in file_ids:
                rows.append({
                    "developer_id": pr_id,
                    "pr_id": pr_id,
                    "file_id": file_id,
                    "relation": "authored",
                    "created_at": None,
                    "merged_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
                    "event_at": None,
                    "additions": 1,
                    "deletions": 0,
                    "files_in_pr": len(file_ids),
                })

        builder = Builder()
        builder.build_graph(rows, config=GraphConfig(half_life_days=None))

        self.assertLess(builder.file_idf["file_100"], builder.file_idf["file_101"])
        self.assertTrue(all(0 < value <= 1 for value in builder.file_idf.values()))

    def test_loader_includes_review_rows_and_conditionally_filters_bots(self):
        db = _GraphDatabase()
        rows = GraphDataLoader(db).get_graph_rows(9, GraphConfig())

        self.assertEqual(
            [row["relation"] for row in rows],
            ["authored", "reviewed", "review_comment"],
        )
        self.assertIn("LOWER(d.type) <> 'bot'", db.queries[0][0])
        self.assertIn("WHERE LOWER(d.type) <> 'bot'", db.queries[1][0])
        self.assertIn("AND LOWER(d.type) <> 'bot'", db.queries[2][0])

        no_bot_filter_db = _GraphDatabase()
        GraphDataLoader(no_bot_filter_db).get_graph_rows(
            9,
            GraphConfig(exclude_bots=False, include_reviews=False),
        )
        self.assertEqual(len(no_bot_filter_db.queries), 1)
        self.assertNotIn("LOWER(d.type)", no_bot_filter_db.queries[0][0])

    def test_pagerank_uses_weights_and_retries_failed_convergence(self):
        class RankerBuilder:
            weighted = True
            graph = {"dev_1": ["pr_10"], "pr_10": ["file_100"]}
            nx_graph = nx.DiGraph()

            def __init__(self):
                self.nx_graph.add_edge("dev_1", "pr_10", weight=0.5)

        calls = []

        def pagerank(_graph, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise nx.PowerIterationFailedConvergence(100)
            return {"dev_1": 1.0, "pr_10": 0.0}

        with patch("graph.ranker.nx.pagerank", side_effect=pagerank):
            result = PageRankRanker(RankerBuilder()).rank(
                relevant_files=set(),
                developer_ids={1},
                retrieved_pr_ids=set(),
                semantic_scores={1: {("item_body", 2): 0.7}},
            )

        self.assertEqual(result[0]["developer_id"], 1)
        self.assertEqual(calls[0]["weight"], "weight")
        self.assertNotIn("max_iter", calls[0])
        self.assertEqual(calls[1]["weight"], "weight")
        self.assertEqual(calls[1]["max_iter"], 500)


if __name__ == "__main__":
    unittest.main()
