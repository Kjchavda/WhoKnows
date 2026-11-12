import unittest

from graph.pipeline import PRESETS, RankingPipeline, aggregate_contributions


class _FakeDatabase:
    def fetch_all(self, _query, _params=None):
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


if __name__ == "__main__":
    unittest.main()
