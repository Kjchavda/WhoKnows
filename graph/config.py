from dataclasses import dataclass


@dataclass(frozen=True)
class GraphConfig:
    exclude_bots: bool = True
    merged_only: bool = True
    include_reviews: bool = True
    weighted: bool = True
    half_life_days: float | None = 365.0
    relation_weights: tuple[tuple[str, float], ...] = (
        ("authored", 1.0),
        ("reviewed", 0.4),
        ("review_comment", 0.7),
    )
    max_churn: int = 1000

    @classmethod
    def legacy(cls) -> "GraphConfig":
        return cls(
            exclude_bots=False,
            merged_only=False,
            include_reviews=False,
            weighted=False,
            half_life_days=None,
        )
