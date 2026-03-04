from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RecommendationInput:
    predicted_views: float
    predicted_share_rate: float
    novelty_factor: float
    brand_alignment: float


def score_idea(item: RecommendationInput) -> float:
    """Weighted MVP score.

    You can calibrate these weights later from historical outcomes.
    """
    return (
        0.45 * item.predicted_views
        + 0.25 * item.predicted_share_rate
        + 0.15 * item.novelty_factor
        + 0.15 * item.brand_alignment
    )
