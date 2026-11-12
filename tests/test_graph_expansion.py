import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import networkx as nx

from graph.builder import Builder
from graph.candidates import CandidateBuilder
from graph.data_loader import GraphDataLoader
from graph.ranker import GraphRanker, PageRankRanker
from graph.seeds import SeedExpander


class _ExpansionDatabase:
    def __init__(self):
        self.queries = []

    def fetch_all(self, query, params):
        self.queries.append((query, params))
        if "FROM pr_files" in query:
            return [
                {"pr_id": 2, "file_id": 10, "additions": 1, "deletions": 0},
                {"pr_id": 2, "file_id": 11, "additions": 2, "deletions": 0},
                {"pr_id": 4, "file_id": 11, "additions": 3, "deletions": 0},
            ]
        return [
            {"issue_id": 1, "pr_id": 4},
            {"issue_id": 1, "pr_id": 2},
            {"issue_id": 3, "pr_id": 5},
        ]


class _SeedLoader:
    def __init__(self):
        self.closing_call = None
        self.files_call = None

    def get_closing_prs(self, repo_id, issue_ids, as_of, exclude_item_ids):
        self.closing_call = (repo_id, set(issue_ids), as_of, set(exclude_item_ids))
        return {1: [4, 2], 3: [5]}

    def get_pr_files(self, pr_ids):
        self.files_call = set(pr_ids)
        return {
            2: [(10, 1, 0), (11, 2, 0)],
            4: [(11, 3, 0)],
            5: [(12, 1, 0)],
        }


class GraphExpansionTests(unittest.TestCase):
    def test_graph_loader_file_and_closing_pr_helpers(self):
        db = _ExpansionDatabase()
        loader = GraphDataLoader(db)

        files = loader.get_pr_files([4, 2])
        as_of = datetime(2021, 1, 1, tzinfo=timezone.utc)
        closing = loader.get_closing_prs(
            repo_id=9,
            issue_ids={1, 3},
            as_of=as_of,
            exclude_item_ids={4},
        )

        self.assertEqual(files[2], [(10, 1, 0), (11, 2, 0)])
        self.assertEqual(closing, {1: [4, 2], 3: [5]})
        query, params = db.queries[1]
        self.assertIn("pr.merged_at < %s", query)
        self.assertIn("NOT (pr.github_id = ANY(%s::bigint[]))", query)
        self.assertEqual(params, (9, [1, 3], as_of, [4]))

    def test_seed_expansion_discounts_issues_caps_seeds_and_normalizes_files(self):
        as_of = datetime(2021, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "item_id": 1,
                "item_kind": "issue",
                "distance": 0.3,
            },
            {
                "item_id": 1,
                "item_kind": "issue",
                "distance": 0.2,
            },
            {
                "item_id": 2,
                "item_kind": "pr",
                "distance": 0.1,
            },
            {
                "item_id": 3,
                "item_kind": "issue",
                "distance": 0.5,
            },
            {
                "item_id": 99,
                "item_kind": "pr",
                "distance": 0.0,
            },
        ]
        loader = _SeedLoader()
        builder = Builder()
        builder.file_idf = {"file_10": 0.5, "file_11": 1.0}

        result = SeedExpander(
            max_seeds=2,
            max_seed_files=2,
            issue_to_pr_discount=0.9,
        ).expand(
            rows,
            builder,
            loader,
            repo_id=9,
            as_of=as_of,
            exclude_item_ids={99},
        )

        self.assertEqual(set(result.seed_prs), {2, 4})
        self.assertAlmostEqual(result.seed_prs[2], 0.9)
        self.assertAlmostEqual(result.seed_prs[4], 0.72)
        self.assertEqual(loader.closing_call, (9, {1, 3}, as_of, {99}))
        self.assertEqual(loader.files_call, {2, 4})
        self.assertLessEqual(len(result.file_weights), 2)
        self.assertAlmostEqual(max(result.file_weights.values()), 1.0)
        self.assertGreater(result.file_weights["file_11"], result.file_weights["file_10"])

    def test_candidate_builder_excludes_semantic_devs_and_ranks_rare_file_affinity(self):
        builder = Builder()
        builder.authored_affinity = {
            "dev_1": {"file_rare": 0.5},
            "dev_3": {"file_popular": 1.0},
            "dev_4": {},
        }
        builder.review_affinity = {
            "dev_2": {"file_rare": 0.5},
        }

        candidate_ids, expansion_ids, affinities = CandidateBuilder().build(
            builder,
            {"file_rare": 0.8, "file_popular": 0.2},
            semantic_dev_ids={2},
            max_expanded=1,
        )

        self.assertEqual(candidate_ids, {1, 2})
        self.assertEqual(expansion_ids, {1})
        self.assertGreater(affinities[1], affinities[3])
        self.assertAlmostEqual(affinities[1], 0.4)
        self.assertEqual(affinities[4], 0.0)

    def test_graph_ranker_accepts_weighted_files_and_file_affinity(self):
        builder = Builder()
        builder.graph = {
            "dev_1": ["pr_10"],
            "pr_10": ["file_rare"],
            "dev_2": ["pr_11"],
            "pr_11": ["file_popular"],
        }
        ranker = GraphRanker(builder)
        semantic_scores = {1: {("item_body", 2): 0.6}}

        set_results = ranker.rank(
            {"file_rare", "file_popular"},
            {1, 2},
            set(),
            semantic_scores,
        )
        dict_results = ranker.rank(
            {"file_rare": 0.9, "file_popular": 0.1},
            {1, 2},
            set(),
            semantic_scores,
        )
        self.assertEqual(
            [row["coverage"] for row in set_results],
            [row["coverage"] for row in dict_results],
        )
        weighted_results = ranker.rank(
            {"file_rare": 0.9, "file_popular": 0.1},
            {1, 2},
            set(),
            semantic_scores,
            file_affinity={1: 0.7, 2: 0.2},
        )
        by_dev = {row["developer_id"]: row for row in weighted_results}
        self.assertEqual(by_dev[1]["coverage"], 0.7)
        self.assertEqual(by_dev[2]["coverage"], 0.2)
        self.assertEqual(by_dev[2]["semantic_relevance"], 0)
        self.assertEqual(by_dev[1]["historical_related_pr_count"], 1)

    def test_pagerank_personalization_splits_mass_between_devs_and_files(self):
        class RankerBuilder:
            weighted = True
            graph = {}
            nx_graph = nx.DiGraph()

            def __init__(self):
                self.nx_graph.add_nodes_from(
                    ("dev_1", "dev_2", "file_10", "file_11")
                )

        captured = {}

        def fake_pagerank(_graph, **kwargs):
            captured.update(kwargs)
            return {node: 0.0 for node in _graph}

        with patch("graph.ranker.nx.pagerank", side_effect=fake_pagerank):
            PageRankRanker(RankerBuilder()).rank(
                relevant_files=set(),
                developer_ids={1, 2},
                retrieved_pr_ids=set(),
                semantic_scores={
                    1: {("item_body", 1): 0.8},
                    2: {("item_body", 2): 0.4},
                },
                file_weights={"file_10": 1.0, "file_11": 3.0},
                seed_mix=0.5,
            )

        personalization = captured["personalization"]
        self.assertAlmostEqual(sum(personalization.values()), 1.0)
        self.assertAlmostEqual(personalization["dev_1"], 1 / 3)
        self.assertAlmostEqual(personalization["dev_2"], 1 / 6)
        self.assertAlmostEqual(personalization["file_10"], 0.125)
        self.assertAlmostEqual(personalization["file_11"], 0.375)
        self.assertEqual(captured["weight"], "weight")


if __name__ == "__main__":
    unittest.main()
