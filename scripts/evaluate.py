import argparse
import numpy as np
from embeddings.embedder import Embedder

# Import the existing Database class from your backend
from backend.db import Database

def get_db():
    """
    Connect to Neon/Postgres using the app's standard Database class.
    Ensure the connection pool is opened before returning.
    """
    db = Database()
    db.open()
    return db

def fetch_evaluation_dataset(db: Database, repo_id: int, limit: int = 200):
    """
    Find issues closed by a merged PR. 
    The 'correct' answer is the PR author and its reviewers.
    """
    query = """
        SELECT 
            i.github_id AS issue_id,
            i.title AS issue_title,
            i.body AS issue_body,
            i.created_at AS issue_timestamp,
            pr.github_id AS pr_id,
            pr.author_id AS pr_author_id
        FROM items i
        JOIN pr_closes_issue pci ON i.number = pci.issue_number AND i.repo_id = pci.repo_id
        JOIN items pr ON pci.pr_id = pr.github_id
        WHERE i.repo_id = %s 
          AND i.kind = 'issue' 
          AND pr.kind = 'pr' 
          AND pr.merged_at IS NOT NULL
        ORDER BY i.created_at DESC
        LIMIT %s;
    """
    issues = db.fetch_all(query, (repo_id, limit))

    # Attach reviewers for each PR to form the complete ground truth set
    for issue in issues:
        reviewers = db.fetch_all(
            "SELECT reviewer_id FROM reviews WHERE item_id = %s", 
            (issue['pr_id'],)
        )
        reviewer_ids = [r['reviewer_id'] for r in reviewers if r['reviewer_id']]
        
        # Ground truth is PR author + any reviewers
        truth = set(reviewer_ids)
        if issue['pr_author_id']:
            truth.add(issue['pr_author_id'])
        issue['ground_truth_devs'] = truth

    return issues

def vector_search(db: Database, embedder: Embedder, repo_id: int, query_text: str, max_timestamp, exclude_pr_id: int):
    """
    Baseline Vector Search: Finds top developers based solely on cosine similarity 
    of their historical chunks, strictly BEFORE the issue was created.
    """
    # Use the embedder to encode the query text
    query_embedding = embedder.model.encode([query_text], show_progress_bar=False)[0].tolist()
    
    # Cast the query embedding list to string formatted for pgvector: '[0.1, 0.2, ...]'
    vector_literal = str(query_embedding).replace(' ', '')

    query = """
        SELECT c.author_id, min(c.embedding <=> %s::vector) as best_distance
        FROM chunks c
        JOIN items i ON c.item_id = i.github_id
        WHERE i.repo_id = %s
          AND c.created_at < %s
          AND c.item_id != %s  -- Exclude the fixing PR itself
          AND c.author_id IS NOT NULL
        GROUP BY c.author_id
        ORDER BY best_distance ASC
        LIMIT 20;
    """
    results = db.fetch_all(query, (vector_literal, repo_id, max_timestamp, exclude_pr_id))
    
    return [r['author_id'] for r in results]

def calculate_mrr(predictions: list, ground_truth: set):
    """Calculate Reciprocal Rank. 1/K where K is the rank of the first correct match."""
    for rank, dev_id in enumerate(predictions, start=1):
        if dev_id in ground_truth:
            return 1.0 / rank
    return 0.0

def calculate_hit_at_k(predictions: list, ground_truth: set, k: int):
    """Check if ANY correct developer is in the top K."""
    top_k = set(predictions[:k])
    return 1 if top_k.intersection(ground_truth) else 0

def main():
    parser = argparse.ArgumentParser(description="Evaluate Ranker Baselines")
    parser.add_argument("--repo-id", type=int, required=True, help="GitHub Repo ID to evaluate")
    args = parser.parse_args()

    db = get_db()
    embedder = Embedder()
    
    try:
        print(f"Fetching evaluation dataset for repo {args.repo_id}...")
        dataset = fetch_evaluation_dataset(db, args.repo_id)
        
        if not dataset:
            print("No merged PRs linked to issues found. Run the crawler on a repo with good issue-PR linkage.")
            return

        # Hold out 30% for final validation (Phase 2)
        split_idx = int(len(dataset) * 0.7)
        train_set = dataset[:split_idx]
        
        print(f"Found {len(dataset)} issues. Using {len(train_set)} for baseline measurement.")

        mrr_scores = []
        hit_at_3 = []
        hit_at_5 = []

        for idx, issue in enumerate(train_set, 1):
            if not issue['ground_truth_devs']:
                continue

            # 1. Prepare query text
            query_text = f"{issue['issue_title']}\n{issue['issue_body'] or ''}"

            # 2. Time-travel prediction
            predicted_devs = vector_search(
                db=db, 
                embedder=embedder,
                repo_id=args.repo_id, 
                query_text=query_text, 
                max_timestamp=issue['issue_timestamp'],
                exclude_pr_id=issue['pr_id']
            )

            # 3. Score
            mrr = calculate_mrr(predicted_devs, issue['ground_truth_devs'])
            h3 = calculate_hit_at_k(predicted_devs, issue['ground_truth_devs'], 3)
            h5 = calculate_hit_at_k(predicted_devs, issue['ground_truth_devs'], 5)

            mrr_scores.append(mrr)
            hit_at_3.append(h3)
            hit_at_5.append(h5)

            print(f"[{idx}/{len(train_set)}] Issue #{issue['issue_id']} | MRR: {mrr:.2f} | Hit@3: {h3}")

        print("\n" + "="*40)
        print("BASELINE METRICS (Vector Search Only)")
        print("="*40)
        print(f"Mean Reciprocal Rank (MRR): {np.mean(mrr_scores):.4f}")
        print(f"Hit Rate @ 3:               {np.mean(hit_at_3):.2%}")
        print(f"Hit Rate @ 5:               {np.mean(hit_at_5):.2%}")
        print("="*40)

    finally:
        db.close()

if __name__ == "__main__":
    main()