import math

class GraphRanker:

    def __init__(self, builder):
        self.builder = builder

    def get_developer_metrics(self, developer_id, relevant_files, retrieved_pr_ids):
        dev_node = "dev_" + str(developer_id)

        prs = self.builder.graph.get(dev_node, [])

        direct_prs = set()
        historical_related_prs = set()
        developer_files = set()
        covered_files = set()

        for pr in prs:
            files = set(self.builder.graph[pr])

            developer_files.update(files)

            matched_files = files.intersection(relevant_files)

            # PR was directly retrieved by semantic search
            if pr in {"pr_" + str(pr_id) for pr_id in retrieved_pr_ids}:
                direct_prs.add(pr)

            # Historical PR touching at least one relevant file
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

    def rank(self, relevant_files, developer_ids, retrieved_pr_ids, semantic_scores):

        metrics = [
            self.get_developer_metrics(
                dev_id,
                relevant_files,
                retrieved_pr_ids
            )
            for dev_id in developer_ids
        ]

        # Add semantic relevance
        for m in metrics:
            distances = semantic_scores.get(m["developer_id"], [])

            m["semantic_pr_count"] = len(distances)

            m["semantic_relevance"] = (
                sum(1 - distance for distance in distances) / len(distances)
                if distances else 0
            )

        max_historical_prs = max(
            (m["historical_related_pr_count"] for m in metrics),
            default=0
        )

        results = []

        for m in metrics:

            historical_depth = (
                math.log1p(m["historical_related_pr_count"])
                / math.log1p(max_historical_prs)
                if max_historical_prs > 0 else 0
            )

            semantic = m["semantic_relevance"]
            coverage = m["coverage"]

            score = (
                0.40 * semantic
                + 0.35 * historical_depth
                + 0.25 * coverage
            )

            results.append({
                **m,
                "historical_depth": historical_depth,
                "score": score
            })

        return sorted(
            results,
            key=lambda x: x["score"],
            reverse=True
        )

    def rank_from_prs(self, pr_ids, semantic_scores):
        developers = self.builder.get_devs_for_prs(pr_ids)

        relevant_files = set()

        for pr_id in pr_ids:
            pr_node = "pr_" + str(pr_id)
            relevant_files.update(
                self.builder.graph.get(pr_node, [])
            )

        developer_ids = [
            int(dev.replace("dev_", ""))
            for dev in developers
        ]

        return self.rank(relevant_files, developer_ids, set(pr_ids), semantic_scores)
