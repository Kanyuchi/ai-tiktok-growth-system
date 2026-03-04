from tiktok_ai_analytics.kpis import (
    comment_rate,
    engagement_rate,
    follower_conversion,
    retention_proxy,
    share_rate,
)


def test_engagement_rate() -> None:
    assert engagement_rate(10, 5, 2, 3, 100) == 0.2


def test_zero_division_protection() -> None:
    assert share_rate(1, 0) == 0.0
    assert comment_rate(1, 0) == 0.0
    assert retention_proxy(5.0, 0) == 0.0
    assert follower_conversion(5, 0) == 0.0
