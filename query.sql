SELECT i.author_id, COUNT(*) AS pr_count
FROM pr_files pf
JOIN files f ON f.id = pf.file_id
JOIN items i ON i.github_id = pf.item_id
WHERE f.repo_id = 363150
  AND f.path = 'redis/connection.py'
GROUP BY i.author_id
ORDER BY pr_count DESC
LIMIT 10;
-- Lists the 10 authors with the most pull requests that changed redis/connection.py    
-- in the specified repository, ordered by pull request count.