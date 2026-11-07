from embeddings.db import Database
from embeddings.search import SemanticSearch
from graph.builder import Builder
from graph.ranker import GraphRanker
from graph.data_loader import GraphDataLoader


def main():
    db = Database()

    try:
        db.open()

        # -----------------------------------------
        # 1. Semantic search
        # -----------------------------------------
        query = "Redis connection pooling"

        searcher = SemanticSearch(db)
        results = searcher.search(query, limit=100)

        pr_results = [
            row for row in results
            if row["item_kind"] == "pr"
        ]

        pr_ids = {
            row["item_id"]
            for row in pr_results
        }

        print(f"\nSearch query: {query}")
        print(f"Retrieved PRs: {len(pr_ids)}")

        # -----------------------------------------
        # 2. Inspect semantic relevance
        # -----------------------------------------
        print("\n" + "=" * 70)
        print("SEMANTICALLY RETRIEVED PULL REQUESTS")
        print("=" * 70)

        # Multiple chunks can belong to the same PR.
        # Keep the best (lowest distance) result per PR.
        best_pr_results = {}

        for row in pr_results:
            pr_id = row["item_id"]

            if (
                pr_id not in best_pr_results
                or row["distance"] < best_pr_results[pr_id]["distance"]
            ):
                best_pr_results[pr_id] = row

        sorted_pr_results = sorted(
            best_pr_results.values(),
            key=lambda row: row["distance"]
        )

        semantic_scores = {}

        for pr_id, row in best_pr_results.items():
            developer_id = row["author_id"]
            distance = row["distance"]

            if developer_id not in semantic_scores:
                semantic_scores[developer_id] = []

            semantic_scores[developer_id].append(distance)

        print("\nSemantic scores by developer:")

        for developer_id, distances in semantic_scores.items():
            print(
                f"Developer {developer_id}: "
                f"PRs={len(distances)}, "
                f"Best distance={min(distances):.4f}"
            )

        for position, row in enumerate(sorted_pr_results, start=1):
            print(f"\nPR #{position}")
            print(f"Developer: {row['developer_login']} (ID: {row['author_id']})")
            print(f"PR Number: {row['item_number']}")
            print(f"Title: {row['item_title']}")
            print(f"Semantic Distance: {row['distance']:.4f}")
            print(f"GitHub URL: {row['github_url']}")

        # -----------------------------------------
        # 3. Load graph data
        # -----------------------------------------
        loader = GraphDataLoader(db)
        graph_rows = loader.get_graph_data()

        builder = Builder()
        builder.build_graph(graph_rows)

        print("\n" + "=" * 70)
        print("GRAPH STATISTICS")
        print("=" * 70)
        print(f"Graph relationships: {len(graph_rows)}")
        print(f"Graph nodes: {len(builder.graph)}")

        direct_developers = builder.get_devs_for_prs(pr_ids)

        print(f"Direct PR authors: {len(direct_developers)}")

        # -----------------------------------------
        # 4. Graph ranking
        # -----------------------------------------
        ranker = GraphRanker(builder)
        ranked = ranker.rank_from_prs(pr_ids, semantic_scores)

        print("\n" + "=" * 70)
        print("DEVELOPER RANKINGS")
        print("=" * 70)

        for position, developer in enumerate(ranked[:10], start=1):
            print(f"\nRANK #{position}")
            print(f"Developer ID: {developer['developer_id']}")
            print(f"Score: {developer['score']:.4f}")
            print(f"Direct PRs: {developer['direct_pr_count']}")
            print(
                "Historical related PRs: "
                f"{developer['historical_related_pr_count']}"
            )
            print(f"Total files: {developer['total_files']}")
            print(f"Covered files: {developer['covered_files']}")
            print(f"Coverage: {developer['coverage']:.4f}")
            print(f"Semantic PRs: {developer['semantic_pr_count']}")
            print(f"Semantic relevance: {developer['semantic_relevance']:.4f}")
            print(f"Historical depth: {developer['historical_depth']:.4f}")

    finally:
        db.close()


if __name__ == "__main__":
    main()