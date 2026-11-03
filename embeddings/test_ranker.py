
import math

from ranker import DeveloperRanker


def make_result(author_id, item_id, source, source_id, distance):
    return {
        "author_id": author_id,
        "item_id": item_id,
        "source": source,
        "source_id": source_id,
        "distance": distance,
        "text": f"Sample contribution by developer {author_id}",
    }


def test_ranker():

    search_results = [
        # Developer 1: 5 distinct contributions across 1 PR.
        make_result(1, 100, "item_body", None, 0.2),
        make_result(1, 100, "issue_comment", 101, 0.3),
        make_result(1, 100, "issue_comment", 102, 0.25),
        make_result(1, 100, "review", 103, 0.2),
        make_result(1, 100, "review_comment", 104, 0.15),

        # An additional chunk from the same review.
        # Should NOT increase contribution count.
        make_result(1, 100, "review", 103, 0.1),

        # Developer 2: 4 distinct contributions across 4 PRs.
        make_result(2, 201, "item_body", None, 0.2),
        make_result(2, 202, "item_body", None, 0.2),
        make_result(2, 203, "item_body", None, 0.2),
        make_result(2, 204, "item_body", None, 0.2),
    ]

    ranker = DeveloperRanker()
    ranked = ranker.rank(search_results)

    for developer in ranked:
        print("\nDeveloper:", developer["author_id"])
        print("Score:", round(developer["score"], 4))
        print("Average relevance:", round(developer["average_relevance"], 4))
        print("Contribution count:", developer["contribution_count"])
        print("Breadth count:", developer["breadth_count"])

    # Find developers by ID.
    results = {
        developer["author_id"]: developer
        for developer in ranked
    }

    dev1 = results[1]
    dev2 = results[2]

    # Verify contribution deduplication.
    assert dev1["contribution_count"] == 5

    # Five contributions, but only one parent PR.
    assert dev1["breadth_count"] == 1

    # Four contributions across four parent PRs.
    assert dev2["contribution_count"] == 4
    assert dev2["breadth_count"] == 4

    # Verify scoring formula.
    expected_volume = 0.5 * (
        math.log1p(5) + math.log1p(1)
    )

    expected_score = dev1["average_relevance"] * expected_volume

    assert math.isclose(
        dev1["score"],
        expected_score,
        rel_tol=1e-9,
    )

    print("\nAll tests passed!")


if __name__ == "__main__":
    test_ranker()
