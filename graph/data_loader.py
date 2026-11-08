class GraphDataLoader:
    def __init__(self, db):
        self.db = db

    def get_graph_data(self, repo_id):
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
                AND i.repo_id = %s;
        """

        return self.db.fetch_all(query, (repo_id,))