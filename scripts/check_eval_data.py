import argparse

from backend.db import Database


def check_eval_data(db: Database, repo_id: int) -> dict[str, int]:
    query = """
        SELECT
            (
                SELECT COUNT(*)
                FROM chunks c
                JOIN items i ON i.github_id = c.item_id
                WHERE i.repo_id = %s
                    AND c.source = 'item_body'
                    AND c.created_at <> i.created_at
            ) AS item_body_mismatches,
            (
                SELECT COUNT(*)
                FROM chunks c
                JOIN comments cm ON cm.github_id = c.source_id
                JOIN items i ON i.github_id = cm.item_id
                WHERE i.repo_id = %s
                    AND c.source IN ('issue_comment', 'review_comment')
                    AND c.created_at <> cm.created_at
            ) AS comment_mismatches,
            (
                SELECT COUNT(*)
                FROM chunks c
                JOIN reviews rv ON rv.github_id = c.source_id
                JOIN items i ON i.github_id = rv.item_id
                WHERE i.repo_id = %s
                    AND c.source = 'review'
                    AND c.created_at <> rv.submitted_at
            ) AS review_mismatches;
    """
    row = db.fetch_one(query, (repo_id, repo_id, repo_id))
    if row is None:
        raise RuntimeError("Timestamp preflight query returned no result.")
    return row


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check embedding chunk timestamps against GitHub source timestamps."
    )
    parser.add_argument("--repo-id", type=int, required=True)
    args = parser.parse_args()

    db = Database()
    try:
        db.open()
        counts = check_eval_data(db, args.repo_id)
    finally:
        db.close()

    for label, key in (
        ("item_body", "item_body_mismatches"),
        ("issue_comment/review_comment", "comment_mismatches"),
        ("review", "review_mismatches"),
    ):
        print(f"{label} timestamp mismatches: {counts[key]}")

    if any(count > 0 for count in counts.values()):
        print("re-run the embedding pipeline for this repo")
        return 1

    print("Timestamp preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
