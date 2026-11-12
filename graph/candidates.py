from graph.builder import Builder


class CandidateBuilder:
    def build(
        self,
        builder: Builder,
        file_weights: dict[str, float],
        semantic_dev_ids,
        max_expanded: int,
    ) -> tuple[set[int], set[int], dict[int, float]]:
        semantic_ids = set(semantic_dev_ids)
        total_file_weight = sum(
            weight for weight in file_weights.values() if weight > 0
        )
        developer_nodes = (
            set(builder.authored_affinity)
            | set(builder.review_affinity)
        )
        developer_ids = {
            int(node.removeprefix("dev_"))
            for node in developer_nodes
        } | semantic_ids
        file_affinity: dict[int, float] = {
            developer_id: 0.0 for developer_id in developer_ids
        }

        if total_file_weight > 0:
            for developer_id in developer_ids:
                developer_node = f"dev_{developer_id}"
                authored = builder.authored_affinity.get(developer_node, {})
                reviewed = builder.review_affinity.get(developer_node, {})
                affinity = sum(
                    weight
                    * min(
                        1.0,
                        authored.get(file_node, 0.0)
                        + reviewed.get(file_node, 0.0),
                    )
                    for file_node, weight in file_weights.items()
                    if weight > 0
                ) / total_file_weight
                file_affinity[developer_id] = affinity

        expansions = sorted(
            (
                (developer_id, affinity)
                for developer_id, affinity in file_affinity.items()
                if developer_id not in semantic_ids and affinity > 0
            ),
            key=lambda item: (-item[1], item[0]),
        )[:max(0, max_expanded)]
        expansion_ids = {developer_id for developer_id, _ in expansions}
        return semantic_ids | expansion_ids, expansion_ids, file_affinity
