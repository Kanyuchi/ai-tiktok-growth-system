from __future__ import annotations


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0):
        return 0.0
    return float(numerator) / float(denominator)


def engagement_rate(likes: int, comments: int, shares: int, saves: int, views: int) -> float:
    return _safe_div(likes + comments + shares + saves, views)


def share_rate(shares: int, views: int) -> float:
    return _safe_div(shares, views)


def comment_rate(comments: int, views: int) -> float:
    return _safe_div(comments, views)


def retention_proxy(avg_watch_time_seconds: float, duration_seconds: int) -> float:
    return _safe_div(avg_watch_time_seconds, duration_seconds)


def follower_conversion(new_followers: int, views: int) -> float:
    return _safe_div(new_followers, views)
