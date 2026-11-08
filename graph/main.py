
from collections import Counter

from embeddings.db import Database
from embeddings.search import SemanticSearch

from graph.builder import Builder
from graph.ranker import GraphRanker
from graph.data_loader import GraphDataLoader


SOURCE_NAMES = {
    "item_body": "PR/Issue description",
    "issue_comment": "Issue comment",
    "review_comment": "Review comment",
    "review": "PR review",
}


def main(repo_id):
    db = Database()

    try:
        db.open()

        # 1. Semantic search
        query = input("\nSearch GitHub knowledge: ").strip()

        if not query:
            print("Search query cannot be empty.")
            return

        searcher = SemanticSearch(db)
        results = searcher.search(query, repo_id=repo_id, limit=100)

        if not results:
            print("No relevant contributions found.")
            return

        print(f"\nSearch query: {query}")
        print(f"Retrieved semantic chunks: {len(results)}")

        # 2. Inspect contribution source distribution
        source_counts = Counter(
            row["source"] for row in results
        )

        print("\nContribution source breakdown:")

        for source, count in source_counts.items():
            print(f"{SOURCE_NAMES.get(source, source)}: {count}")

        # 3. Group semantic contributions by their actual author.
        # Keep only the best matching chunk per original contribution.

        semantic_contributions = {}

        for row in results:
            developer_id = row["author_id"]

            if developer_id is None:
                continue

            if row["source"] == "item_body":
                contribution_id = row["item_id"]
            else:
                contribution_id = row["source_id"]

            if contribution_id is None:
                continue

            contribution_key = (
                row["source"],
                contribution_id
            )

            similarity = 1 - float(row["distance"])

            developer_contributions = semantic_contributions.setdefault(
                developer_id, {}
            )

            existing = developer_contributions.get(contribution_key)

            if (
                existing is None
                or similarity > existing["similarity"]
            ):
                developer_contributions[contribution_key] = {
                    "similarity": similarity,
                    "row": row
                }

        semantic_scores = {
            developer_id: {
                key: contribution["similarity"]
                for key, contribution in contributions.items()
            }
            for developer_id, contributions in semantic_contributions.items()
        }

        semantic_developers = set(semantic_scores.keys())

        # 4. Identify PRs retrieved by semantic search.
        retrieved_pr_ids = {
            row["item_id"]
            for row in results
            if row["item_kind"] == "pr"
        }

        print(f"\nSemantic developers: {len(semantic_developers)}")
        print(f"Retrieved PRs: {len(retrieved_pr_ids)}")

        # 5. Build implementation graph.
        loader = GraphDataLoader(db)
        graph_rows = loader.get_graph_data(repo_id)

        builder = Builder()
        builder.build_graph(graph_rows)

        # 6. Find files modified by retrieved PRs.
        relevant_files = set()

        for pr_id in retrieved_pr_ids:
            pr_node = "pr_" + str(pr_id)

            relevant_files.update(
                builder.graph.get(pr_node, [])
            )

        print(f"Relevant files: {len(relevant_files)}")

        # 7. Combined developer ranking.
        ranker = GraphRanker(builder)

        ranked = ranker.rank(
            relevant_files=relevant_files,
            developer_ids=semantic_developers,
            retrieved_pr_ids=retrieved_pr_ids,
            semantic_scores=semantic_scores
        )

        # 8. Display final results with usernames and evidence.
        print("\n" + "=" * 90)
        print("WHO KNOWS: " + query)
        print("=" * 90)

        for position, developer in enumerate(ranked[:10], start=1):
            developer_id = developer["developer_id"]

            contributions = semantic_contributions.get(
                developer_id, {}
            )

            evidence = sorted(
                contributions.values(),
                key=lambda item: item["similarity"],
                reverse=True
            )

            # Retrieve username from the actual contribution record.
            username = None

            if evidence:
                username = evidence[0]["row"]["developer_login"]

            print("\n" + "-" * 90)
            print(f"RANK #{position}")
            print("-" * 90)

            print(
                f"Developer: @{username}"
                if username
                else f"Developer ID: {developer_id}"
            )

            print(f"GitHub ID: {developer_id}")
            print(f"Final score: {developer['score']:.4f}")
            print(
                f"Semantic relevance: "
                f"{developer['semantic_relevance']:.4f}"
            )
            print(
                f"Semantic contributions: "
                f"{developer['semantic_contribution_count']}"
            )
            print(
                f"Direct PRs: {developer['direct_pr_count']}"
            )
            print(
                f"Historical related PRs: "
                f"{developer['historical_related_pr_count']}"
            )
            print(
                f"File coverage: "
                f"{developer['covered_files']}/"
                f"{len(relevant_files)} "
                f"({developer['coverage']:.2%})"
            )

            print("\nTOP CONTRIBUTION EVIDENCE")

            for index, contribution in enumerate(evidence[:3], start=1):
                row = contribution["row"]

                source_name = SOURCE_NAMES.get(
                    row["source"],
                    row["source"]
                )

                print(f"\n  Evidence #{index}")
                print(f"  Type: {source_name}")

                print(
                    f"  Parent: {row['item_kind'].upper()} "
                    f"#{row['item_number']}"
                )

                print(f"  Title: {row['item_title']}")
                print(
                    f"  Similarity: "
                    f"{contribution['similarity']:.4f}"
                )
                print(f"  GitHub: {row['github_url']}")

                text = row["text"] or ""
                print(f"  Text: {text[:500]}")

                if len(text) > 500:
                    print("  ...")

    finally:
        db.close()


if __name__ == "__main__":
    try:
        repo_id = int(input("Enter repository GitHub ID: ").strip())

        if repo_id <= 0:
            raise ValueError

    except ValueError:
        print("Invalid repository ID.")
    else:
        main(repo_id)
