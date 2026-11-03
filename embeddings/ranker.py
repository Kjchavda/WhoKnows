
import math
from collections import defaultdict


class DeveloperRanker:

    def rank(self, search_results):
        if not search_results:
            return []

        # Group chunks by developer and original contribution.
        developers = defaultdict(dict)

        for result in search_results:
            author_id = result["author_id"]

            if author_id is None:
                continue

            source = result["source"]
            source_id = result["source_id"]

            # Item bodies use item_id because source_id is NULL.
            if source == "item_body":
                contribution_id = result["item_id"]
            else:
                contribution_id = source_id

            if contribution_id is None:
                continue

            contribution_key = (source, contribution_id)

            similarity = 1 - float(result["distance"])

            existing = developers[author_id].get(contribution_key)

            # Keep the most relevant chunk from this contribution.
            if (
                existing is None
                or similarity > existing["similarity"]
            ):
                developers[author_id][contribution_key] = {
                    "similarity": similarity,
                    "result": result,
                }

        ranked_developers = []

        # Calculate one score per developer.
        for author_id, contributions in developers.items():

            contribution_scores = [
                contribution["similarity"]
                for contribution in contributions.values()
            ]

            # Scoring part
            contribution_count = len(contribution_scores)

            breadth = set()

            for contribution in contributions.values():
                breadth.add(contribution["result"]["item_id"])

            breadth_count = len(breadth)

            average_relevance = (
                sum(contribution_scores) / contribution_count
            )

            volume_factor = 0.5*(math.log1p(contribution_count)+math.log1p(breadth_count))

            score = average_relevance * volume_factor

            # Sort distinct contributions by relevance.
            evidence = sorted(
                contributions.values(),
                key=lambda x: x["similarity"],
                reverse=True,
            )

            ranked_developers.append({
                "author_id": author_id,
                "score": score,
                "average_relevance": average_relevance,
                "contribution_count": contribution_count,
                "breadth_count": breadth_count,
                "evidence": [
                    item["result"] for item in evidence[:3]
                ],
            })

        ranked_developers.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return ranked_developers
