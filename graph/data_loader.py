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