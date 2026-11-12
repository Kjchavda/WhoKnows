import os
import argparse
import numpy as np

from typing import List, Dict, Any

from backend.db import Database
from embeddings.embedder import Embedder

from graph.builder import Builder
from graph.ranker import GraphRanker
from graph.data_loader import GraphDataLoader


def get_db():
    db = Database()
    db.open()
    return db


def fetch_evaluation_dataset(db: Database, repo_id: int, limit: int = 200) -> List[Dict[str, Any]]:
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

    for issue in issues:
        reviewers = db.fetch_all(
            "SELECT reviewer_id FROM reviews WHERE item_id = %s", 
            (issue['pr_id'],)
        )
        reviewer_ids = [r['reviewer_id'] for r in reviewers if r['reviewer_id']]
        
        truth = set(reviewer_ids)
        if issue['pr_author_id']:
            truth.add(issue['pr_author_id'])
        issue['ground_truth_devs'] = truth

    return issues


def graph_search(db: Database, embedder: Embedder, repo_id: int, query_text: str, max_timestamp, exclude_pr_id: int) -> List[int]:
    """
    Graph Search: Retrieves chunks strictly before the issue creation, 
    builds the NetworkX graph, and ranks developers using Personalized PageRank.
    """
    query_embedding = embedder.model.encode([query_text], show_progress_bar=False)[0].tolist()
    vector_literal = str(query_embedding).replace(' ', '')

    # 1. Time-Constrained Semantic Search
    query = """
        SELECT c.item_id, i.kind as item_kind, c.source, c.source_id, c.author_id,
               (c.embedding <=> %s::vector) as distance
        FROM chunks c
        JOIN items i ON c.item_id = i.github_id
        WHERE i.repo_id = %s
          AND c.created_at < %s
          AND c.item_id != %s
          AND c.author_id IS NOT NULL
        ORDER BY distance ASC
        LIMIT 100;
    """
    results = db.fetch_all(query, (vector_literal, repo_id, max_timestamp, exclude_pr_id))

    if not results:
        return []

    # 2. Group Semantic Contributions
    semantic_contributions = {}
    for row in results:
        developer_id = row["author_id"]
        
        if row["source"] == "item_body":
            contribution_id = row["item_id"]
        else:
            contribution_id = row["source_id"]

        if not contribution_id:
            continue

        contribution_key = (row["source"], contribution_id)
        similarity = 1.0 - float(row["distance"])

        developer_contributions = semantic_contributions.setdefault(developer_id, {})
        existing = developer_contributions.get(contribution_key)

        if existing is None or similarity > existing["similarity"]:
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
    retrieved_pr_ids = {row["item_id"] for row in results if row["item_kind"] == "pr"}

    # 3. Build Implementation Graph (Time-Constrained)
    loader = GraphDataLoader(db)
    
    # CRITICAL: We pass the time-travel parameters into the data loader
    graph_rows = loader.get_graph_data(
        repo_id, 
        max_timestamp=max_timestamp, 
        exclude_pr_id=exclude_pr_id
    )

    builder = Builder()
    builder.build_graph(graph_rows)

    # 4. Find files modified by retrieved PRs
    relevant_files = set()
    for pr_id in retrieved_pr_ids:
        pr_node = "pr_" + str(pr_id)
        relevant_files.update(builder.graph.get(pr_node, []))

    # 5. Combined Developer Ranking
    ranker = GraphRanker(builder)
    ranked = ranker.rank(
        relevant_files=relevant_files,
        developer_ids=semantic_developers,
        retrieved_pr_ids=retrieved_pr_ids,
        semantic_scores=semantic_scores
    )

    return [dev["developer_id"] for dev in ranked]


def calculate_mrr(predictions: list, ground_truth: set):
    for rank, dev_id in enumerate(predictions, start=1):
        if dev_id in ground_truth:
            return 1.0 / rank
    return 0.0


def calculate_hit_at_k(predictions: list, ground_truth: set, k: int):
    top_k = set(predictions[:k])
    return 1 if top_k.intersection(ground_truth) else 0


def main():
    parser = argparse.ArgumentParser(description="Evaluate Graph Ranker")
    parser.add_argument("--repo-id", type=int, required=True, help="GitHub Repo ID to evaluate")
    args = parser.parse_args()

    db = get_db()
    embedder = Embedder()
    
    try:
        print(f"Fetching evaluation dataset for repo {args.repo_id}...")
        dataset = fetch_evaluation_dataset(db, args.repo_id)
        
        if not dataset:
            print("No dataset found.")
            return

        # Test on the exact same 70% training split used for the baseline
        split_idx = int(len(dataset) * 0.7)
        train_set = dataset[:split_idx]
        
        print(f"Evaluating Graph Ranker on {len(train_set)} issues...")

        mrr_scores = []
        hit_at_3 = []
        hit_at_5 = []

        for idx, issue in enumerate(train_set, 1):
            if not issue['ground_truth_devs']:
                continue

            query_text = f"{issue['issue_title']}\n{issue['issue_body'] or ''}"

            predicted_devs = graph_search(
                db=db, 
                embedder=embedder,
                repo_id=args.repo_id, 
                query_text=query_text, 
                max_timestamp=issue['issue_timestamp'],
                exclude_pr_id=issue['pr_id']
            )

            mrr = calculate_mrr(predicted_devs, issue['ground_truth_devs'])
            h3 = calculate_hit_at_k(predicted_devs, issue['ground_truth_devs'], 3)
            h5 = calculate_hit_at_k(predicted_devs, issue['ground_truth_devs'], 5)

            mrr_scores.append(mrr)
            hit_at_3.append(h3)
            hit_at_5.append(h5)

            print(f"[{idx}/{len(train_set)}] Issue #{issue['issue_id']} | MRR: {mrr:.2f} | Hit@3: {h3}")

        print("\n" + "="*40)
        print("PHASE 2 METRICS (Graph Ranker)")
        print("="*40)
        print(f"Mean Reciprocal Rank (MRR): {np.mean(mrr_scores):.4f}")
        print(f"Hit Rate @ 3:               {np.mean(hit_at_3):.2%}")
        print(f"Hit Rate @ 5:               {np.mean(hit_at_5):.2%}")
        print("="*40)

    finally:
        db.close()

if __name__ == "__main__":
    main()