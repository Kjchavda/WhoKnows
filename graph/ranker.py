import math
import networkx as nx


class GraphRanker:
    def __init__(self, builder):
        self.builder = builder

    def get_developer_metrics(
        self,
        developer_id,
        relevant_files,
        retrieved_pr_ids
    ):
        dev_node = "dev_" + str(developer_id)

        # Only PRs created by this developer.
        prs = self.builder.graph.get(dev_node, [])

        retrieved_pr_nodes = {
            "pr_" + str(pr_id)
            for pr_id in retrieved_pr_ids
        }

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

        coverage = (
            len(covered_files) / len(relevant_files)
            if relevant_files else 0
        )

        return {
            "developer_id": developer_id,
            "direct_pr_count": len(direct_prs),
            "historical_related_pr_count": len(historical_related_prs),
            "total_files": len(developer_files),
            "covered_files": len(covered_files),
            "coverage": coverage
        }

    def rank(
        self,
        relevant_files,
        developer_ids,
        retrieved_pr_ids,
        semantic_scores
    ):
        metrics = [
            self.get_developer_metrics(
                dev_id,
                relevant_files,
                retrieved_pr_ids
            )
            for dev_id in developer_ids
        ]

        # Semantic scores contain one best similarity per
        # original contribution, grouped by its actual author.
        for metric in metrics:
            contributions = semantic_scores.get(
                metric["developer_id"],
                {}
            )

            similarities = (
                list(contributions.values())
                if isinstance(contributions, dict)
                else contributions
            )

            metric["semantic_contribution_count"] = len(similarities)

            metric["semantic_relevance"] = (
                sum(similarities) / len(similarities)
                if similarities else 0
            )

        max_historical_prs = max(
            (
                metric["historical_related_pr_count"]
                for metric in metrics
            ),
            default=0
        )

        results = []

        for metric in metrics:
            historical_depth = (
                math.log1p(metric["historical_related_pr_count"])
                / math.log1p(max_historical_prs)
                if max_historical_prs > 0 else 0
            )

            semantic = metric["semantic_relevance"]
            coverage = metric["coverage"]

            # Preserve the existing scoring formula.
            score = (
                0.40 * semantic
                + 0.35 * historical_depth
                + 0.25 * coverage
            )

            results.append({
                **metric,
                "historical_depth": historical_depth,
                "score": score
            })

        return sorted(
            results,
            key=lambda result: result["score"],
            reverse=True
        )


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

        if total_injected == 0:
            for node in self.builder.nx_graph.nodes():
                personalization[node] = 1.0

        pr_scores = nx.pagerank(
            self.builder.nx_graph,
            alpha=0.85,
            personalization=personalization
        )

        results = []
        retrieved_pr_nodes = {"pr_" + str(pr_id) for pr_id in retrieved_pr_ids}

        for dev_id in developer_ids:
            dev_node = "dev_" + str(dev_id)
            
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
                "score": pr_scores.get(dev_node, 0.0) 
            })

        return sorted(results, key=lambda r: r["score"], reverse=True)