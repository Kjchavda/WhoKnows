from collections.abc import Iterable
from typing import Any

from graph.config import GraphConfig


class GraphDataLoader:
    def __init__(self, db):
        self.db = db

    def get_graph_data(self, repo_id, max_timestamp=None, exclude_pr_id=None):
        query = """
            SELECT DISTINCT
                i.author_id AS developer_id,
                i.github_id AS pr_id,
                pf.file_id
            FROM items i
            JOIN pr_files pf
                ON pf.item_id = i.github_id
            WHERE i.kind = 'pr'
                AND i.author_id IS NOT NULL
                AND i.repo_id = %s
        """
        
        params = [repo_id]

        # Prevent data leakage during evaluation by hiding future PRs
        if max_timestamp:
            query += " AND i.created_at < %s"
            params.append(max_timestamp)
            
        # Hide the exact PR that fixes the issue being evaluated
        if exclude_pr_id:
            query += " AND i.github_id != %s"
            params.append(exclude_pr_id)

        query += ";"

        return self.db.fetch_all(query, tuple(params))

    def get_graph_rows(
        self,
        repo_id: int,
        config: GraphConfig,
    ) -> list[dict[str, Any]]:
        authored_bot_filter = "AND LOWER(d.type) <> 'bot'" if config.exclude_bots else ""
        authored_query = f"""
            SELECT
                i.author_id AS developer_id,
                i.github_id AS pr_id,
                pf.file_id,
                pf.additions,
                pf.deletions,
                i.created_at,
                i.merged_at,
                NULL::timestamptz AS event_at,
                COUNT(*) OVER (PARTITION BY i.github_id) AS files_in_pr,
                'authored' AS relation
            FROM items i
            JOIN pr_files pf ON pf.item_id = i.github_id
            JOIN developers d ON d.github_id = i.author_id
            WHERE i.repo_id = %s
                AND i.kind = 'pr'
                AND i.author_id IS NOT NULL
                {authored_bot_filter};
        """
        rows = self.db.fetch_all(authored_query, (repo_id,))

        if not config.include_reviews:
            return rows

        reviewer_bot_filter = (
            "WHERE LOWER(d.type) <> 'bot'" if config.exclude_bots else ""
        )
        reviewed_query = f"""
            WITH reviewers AS (
                SELECT
                    rv.reviewer_id,
                    rv.item_id,
                    MIN(rv.submitted_at) AS event_at
                FROM reviews rv
                JOIN items p ON p.github_id = rv.item_id
                WHERE p.repo_id = %s
                    AND p.kind = 'pr'
                    AND rv.reviewer_id IS NOT NULL
                    AND rv.submitted_at IS NOT NULL
                    AND rv.reviewer_id IS DISTINCT FROM p.author_id
                GROUP BY rv.reviewer_id, rv.item_id
            )
            SELECT
                r.reviewer_id AS developer_id,
                r.item_id AS pr_id,
                pf.file_id,
                pf.additions,
                pf.deletions,
                p.created_at,
                p.merged_at,
                r.event_at,
                COUNT(*) OVER (
                    PARTITION BY r.item_id, r.reviewer_id
                ) AS files_in_pr,
                'reviewed' AS relation
            FROM reviewers r
            JOIN items p ON p.github_id = r.item_id
            JOIN pr_files pf ON pf.item_id = r.item_id
            JOIN developers d ON d.github_id = r.reviewer_id
            {reviewer_bot_filter};
        """
        reviewed_rows = self.db.fetch_all(reviewed_query, (repo_id,))

        comment_bot_filter = "AND LOWER(d.type) <> 'bot'" if config.exclude_bots else ""
        review_comment_query = f"""
            SELECT
                c.author_id AS developer_id,
                c.item_id AS pr_id,
                c.file_id,
                0 AS additions,
                0 AS deletions,
                p.created_at,
                p.merged_at,
                MIN(c.created_at) AS event_at,
                1 AS files_in_pr,
                'review_comment' AS relation
            FROM comments c
            JOIN items p ON p.github_id = c.item_id
            JOIN developers d ON d.github_id = c.author_id
            WHERE p.repo_id = %s
                AND p.kind = 'pr'
                AND c.kind = 'review_comment'
                AND c.file_id IS NOT NULL
                AND c.author_id IS NOT NULL
                AND c.author_id IS DISTINCT FROM p.author_id
                {comment_bot_filter}
            GROUP BY
                c.author_id,
                c.item_id,
                c.file_id,
                p.created_at,
                p.merged_at;
        """
        comment_rows = self.db.fetch_all(review_comment_query, (repo_id,))
        return [*rows, *reviewed_rows, *comment_rows]

    def get_pr_files(
        self,
        pr_ids: Iterable[int],
    ) -> dict[int, list[tuple[int, int, int]]]:
        ids = sorted(set(pr_ids))
        if not ids:
            return {}

        rows = self.db.fetch_all(
            """
                SELECT
                    item_id AS pr_id,
                    file_id,
                    additions,
                    deletions
                FROM pr_files
                WHERE item_id = ANY(%s::bigint[])
                ORDER BY item_id, file_id;
            """,
            (ids,),
        )
        files: dict[int, list[tuple[int, int, int]]] = {
            pr_id: [] for pr_id in ids
        }
        for row in rows:
            files[row["pr_id"]].append(
                (row["file_id"], row["additions"], row["deletions"])
            )
        return files

    def get_closing_prs(
        self,
        repo_id: int,
        issue_ids: Iterable[int],
        as_of=None,
        exclude_item_ids: Iterable[int] = (),
    ) -> dict[int, list[int]]:
        ids = sorted(set(issue_ids))
        if not ids:
            return {}

        query = """
            SELECT i.github_id AS issue_id, pci.pr_id
            FROM pr_closes_issue pci
            JOIN items i
                ON i.number = pci.issue_number
                AND i.repo_id = pci.repo_id
            JOIN items pr ON pr.github_id = pci.pr_id
            WHERE pci.repo_id = %s
                AND i.github_id = ANY(%s::bigint[])
                AND pr.kind = 'pr'
                AND pr.merged_at IS NOT NULL
        """
        params: list[Any] = [repo_id, ids]
        if as_of is not None:
            query += " AND pr.merged_at < %s"
            params.append(as_of)

        query += " AND NOT (pr.github_id = ANY(%s::bigint[]))"
        params.append(sorted(set(exclude_item_ids)))
        query += " ORDER BY i.github_id, pci.pr_id;"

        results: dict[int, list[int]] = {issue_id: [] for issue_id in ids}
        for row in self.db.fetch_all(query, tuple(params)):
            results[row["issue_id"]].append(row["pr_id"])
        return results