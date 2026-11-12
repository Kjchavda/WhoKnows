import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from backend.services.search_service import SearchService
from graph.pipeline import PRESETS, RankingPipeline, aggregate_contributions
from graph.pipeline import PipelineResult


class _FakeDatabase:
    def fetch_all(self, _query, _params=None):
        return []


class _GraphPipelineDatabase:
    def __init__(self):
        self.queries = []

    def fetch_all(self, query, _params=None):
        self.queries.append(query)
        if "FROM pr_files" in query:
            return [{
                "pr_id": 2,
                "file_id": 10,
                "additions": 1000,
                "deletions": 0,
            }]
        if "'authored' AS relation" in query:
            timestamp = datetime(2019, 1, 1, tzinfo=timezone.utc)
            return [
                {
                    "developer_id": 1,
                    "pr_id": 2,
                    "file_id": 10,
                    "additions": 1000,
                    "deletions": 0,
                    "created_at": timestamp,
                    "merged_at": timestamp,
                    "event_at": None,
                    "files_in_pr": 1,
                    "relation": "authored",
                },
                {
                    "developer_id": 2,
                    "pr_id": 3,
                    "file_id": 10,
                    "additions": 1000,
                    "deletions": 0,
                    "created_at": timestamp,
                    "merged_at": timestamp,
                    "event_at": None,
                    "files_in_pr": 1,
                    "relation": "authored",
                },
            ]
        return []


class PipelineAggregateTests(unittest.TestCase):
    def test_aggregate_keeps_best_chunk_per_author_and_contribution(self):
        rows = [
            {
                "author_id": 1,
                "source": "item_body",
                "item_id": 10,
                "source_id": None,
                "distance": 0.4,
                "text": "lower score",
            },
            {
                "author_id": 1,
                "source": "item_body",
                "item_id": 10,
                "source_id": None,
                "distance": 0.1,
                "text": "best item chunk",
            },
            {
                "author_id": 1,
                "source": "issue_comment",
                "item_id": 10,
                "source_id": 20,
                "distance": 0.2,
                "text": "best comment chunk",
            },
            {
                "author_id": 2,
                "source": "issue_comment",
                "item_id": 10,
                "source_id": 20,
                "distance": 0.3,
                "text": "other author",
            },
        ]

        scores, evidence = aggregate_contributions(rows)

        self.assertEqual(
            scores[1],
            {
                ("item_body", 10): 0.9,
                ("issue_comment", 20): 0.8,
            },
        )
        self.assertEqual(evidence[1][("item_body", 10)]["text"], "best item chunk")
        self.assertEqual(
            evidence[1][("issue_comment", 20)]["text"],
            "best comment chunk",
        )
        self.assertEqual(scores[2][("issue_comment", 20)], 0.7)

    def test_semantic_pipeline_adapter_adds_developer_id(self):
        rows = [{
            "author_id": 5,
            "source": "item_body",
            "item_id": 10,
            "source_id": None,
            "distance": 0.1,
        }]
        pipeline = RankingPipeline(_FakeDatabase(), embedder=object())

        result = pipeline.run(
            repo_id=1,
            query="query",
            config=PRESETS["semantic"],
            semantic_rows=rows,
        )

        self.assertEqual(result.candidate_ids, {5})
        self.assertEqual(result.ranked[0]["developer_id"], 5)
        self.assertIsNone(result.builder)

    def test_seed_candidate_preset_expands_from_retrieved_pr_files(self):
        db = _GraphPipelineDatabase()
        pipeline = RankingPipeline(db, embedder=object())
        timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
        rows = [{
            "author_id": 1,
            "source": "item_body",
            "source_id": None,
            "item_id": 2,
            "item_kind": "pr",
            "distance": 0.1,
        }]

        result = pipeline.run(
            repo_id=9,
            query="query",
            as_of=timestamp,
            exclude_item_ids={99},
            config=PRESETS["v2-seeds-cand"],
            semantic_rows=rows,
        )

        self.assertEqual(result.candidate_ids, {1, 2})
        self.assertEqual(result.expansion_ids, {2})
        self.assertEqual(result.file_weights, {"file_10": 1.0})
        self.assertEqual(
            sum("FROM items i" in query for query in db.queries),
            1,
        )

    def test_graph_rows_are_loaded_once_for_equal_configs(self):
        db = _GraphPipelineDatabase()
        pipeline = RankingPipeline(db, embedder=object())
        timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
        rows = [{
            "author_id": 1,
            "source": "item_body",
            "source_id": None,
            "item_id": 2,
            "item_kind": "pr",
            "distance": 0.1,
        }]

        for preset in ("v2-graph", "v2-pagerank"):
            pipeline.run(
                repo_id=9,
                query="query",
                as_of=timestamp,
                config=PRESETS[preset],
                semantic_rows=rows,
            )

        self.assertEqual(
            sum("'authored' AS relation" in query for query in db.queries),
            1,
        )

    def test_search_service_adds_expansion_signals_and_resolves_login_once(self):
        class Database:
            def __init__(self):
                self.queries = []

            def fetch_all(self, query, params):
                self.queries.append((query, params))
                return [{"github_id": 7, "login": "expanded-dev"}]

        class RankingPipelineStub:
            def run(self, **_kwargs):
                return PipelineResult(
                    ranked=[{
                        "developer_id": 7,
                        "score": 0.4,
                        "semantic_relevance": 0.0,
                        "coverage": 0.8,
                        "historical_depth": 0.2,
                    }],
                    candidate_ids={7},
                    semantic_rows=[],
                    builder=None,
                    evidence={},
                    expansion_ids={7},
                )

        db = Database()
        service = SearchService.__new__(SearchService)
        service.db = db
        service.ranking_pipeline = RankingPipelineStub()

        with patch.dict("os.environ", {"RANKING_PRESET": "v2-seeds-cand"}):
            results = service.search(repo_id=9, query="query")

        self.assertEqual(len(db.queries), 1)
        self.assertEqual(results[0]["developer_login"], "expanded-dev")
        self.assertEqual(results[0]["evidence"], [])
        self.assertEqual(
            results[0]["signals"],
            {
                "semantic_relevance": 0.0,
                "coverage": 0.8,
                "historical_depth": 0.2,
                "origin": "graph_expansion",
            },
        )


if __name__ == "__main__":
    unittest.main()
