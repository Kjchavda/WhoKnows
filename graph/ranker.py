import networkx as nx

class PageRankRanker:
    def __init__(self, builder):
        self.builder = builder

    def rank(
        self,
        relevant_files,
        developer_ids,
        retrieved_pr_ids,
        semantic_scores
    ):
        # 1. Build the Personalization Vector (Teleportation)
        # We inject the semantic search scores into the PageRank algorithm 
        # so authority naturally flows out from the most semantically relevant devs.
        personalization = {}
        total_injected = 0.0

        for node in self.builder.nx_graph.nodes():
            personalization[node] = 0.0

        for dev_id in developer_ids:
            dev_node = "dev_" + str(dev_id)
            contributions = semantic_scores.get(dev_id, {})
            
            similarities = (
                list(contributions.values())
                if isinstance(contributions, dict)
                else contributions
            )
            
            avg_semantic = sum(similarities) / len(similarities) if similarities else 0.0
            
            if dev_node in personalization:
                personalization[dev_node] = avg_semantic
                total_injected += avg_semantic

        # Fallback if the graph doesn't overlap with semantic results at all
        if total_injected == 0:
            for node in self.builder.nx_graph.nodes():
                personalization[node] = 1.0

        # 2. Run Personalized PageRank
        pr_scores = nx.pagerank(
            self.builder.nx_graph,
            alpha=0.85,
            personalization=personalization
        )

        # 3. Format the output to match the original GraphRanker schema
        # (This allows the evaluate script and main.py to print the same metrics)
        results = []
        retrieved_pr_nodes = {"pr_" + str(pr_id) for pr_id in retrieved_pr_ids}

        for dev_id in developer_ids:
            dev_node = "dev_" + str(dev_id)
            
            # Reconstruct legacy metrics for the UI/evaluator
            contributions = semantic_scores.get(dev_id, {})
            similarities = (list(contributions.values()) if isinstance(contributions, dict) else contributions)
            semantic_relevance = sum(similarities) / len(similarities) if similarities else 0

            prs = self.builder.graph.get(dev_node, [])
            direct_prs = set()
            historical_related_prs = set()
            developer_files = set()
            covered_files = set()

            for pr in prs:
                files = set(self.builder.graph.get(pr, []))
                developer_files.update(files)
                matched_files = files.intersection(relevant_files)

                if pr in retrieved_pr_nodes:
                    direct_prs.add(pr)
                elif matched_files:
                    historical_related_prs.add(pr)

                covered_files.update(matched_files)

            coverage = len(covered_files) / len(relevant_files) if relevant_files else 0

            results.append({
                "developer_id": dev_id,
                "direct_pr_count": len(direct_prs),
                "historical_related_pr_count": len(historical_related_prs),
                "total_files": len(developer_files),
                "covered_files": len(covered_files),
                "coverage": coverage,
                "semantic_contribution_count": len(similarities),
                "semantic_relevance": semantic_relevance,
                # THIS is the actual rank score now
                "score": pr_scores.get(dev_node, 0.0) 
            })

        return sorted(results, key=lambda r: r["score"], reverse=True)