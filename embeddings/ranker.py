
import math
from collections import defaultdict


class DeveloperRanker:

    def rank(self, search_results):
        if not search_results:
            return []

        # Group search results by developer
        developers = defaultdict(list)

        for result in search_results:
            author_id = result["author_id"]

            # Ignore contributions without an identified author
            if author_id is None:
                continue

            similarity = 1 - float(result["distance"])

            developers[author_id].append({
                "similarity": similarity,
                "result": result,
            })

        ranked_developers = []

        # Calculate a score for each developer
        for author_id, contributions in developers.items():

            similarities = [
                contribution["similarity"]
                for contribution in contributions
            ]

            contribution_count = len(contributions)

            average_similarity = (
                sum(similarities) / contribution_count
            )

            volume_factor = math.log1p(contribution_count)

            score = average_similarity * volume_factor

            # Keep the strongest matching contributions as evidence
            evidence = sorted(
                contributions,
                key=lambda x: x["similarity"],
                reverse=True,
            )

            ranked_developers.append({
                "author_id": author_id,
                "score": score,
                "average_similarity": average_similarity,
                "contribution_count": contribution_count,
                "evidence": [
                    item["result"] for item in evidence[:3]
                ],
            })

        # Highest score first
        ranked_developers.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return ranked_developers
