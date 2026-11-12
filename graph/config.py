from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


def _default_relation_weights() -> Mapping[str, float]:
    return MappingProxyType({
        "authored": 1.0,
        "reviewed": 0.4,
        "review_comment": 0.7,
    })


@dataclass(frozen=True)
class GraphConfig:
    exclude_bots: bool = True
    merged_only: bool = True
    include_reviews: bool = True
    weighted: bool = True
    half_life_days: float | None = 365.0
    relation_weights: Mapping[str, float] = field(
        default_factory=_default_relation_weights,
        hash=False,
    )
    max_churn: int = 1000

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relation_weights",
            MappingProxyType(dict(self.relation_weights)),
        )

    def __hash__(self) -> int:
        return hash((
            self.exclude_bots,
            self.merged_only,
            self.include_reviews,
            self.weighted,
            self.half_life_days,
            tuple(sorted(self.relation_weights.items())),
            self.max_churn,
        ))

    @classmethod
    def legacy(cls) -> "GraphConfig":
        return cls(
            exclude_bots=False,
            merged_only=False,
            include_reviews=False,
            weighted=False,
            half_life_days=None,
        )
