"""
Reinforcement Learning Module — Thompson Sampling for Content Optimisation
==========================================================================
Learns from the video watch matrix (extracted from TikTok Studio analytics)
and feeds optimised feature weights into the content engine.

Approach: Multi-Armed Bandit with Thompson Sampling
- Each "arm" is a content feature (theme, hook_style, demographic_target)
- Rewards are composite scores from views, watch time, completion, followers
- Beta distributions are updated with each new observation
- The module persists learned priors to data/rl_state.json
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
WATCH_MATRIX_PATH = DATA_DIR / "video_watch_matrix.json"
RL_STATE_PATH = DATA_DIR / "rl_state.json"


@dataclass
class ArmState:
    """Beta distribution parameters for a single arm."""
    alpha: float = 1.0  # successes + prior
    beta: float = 1.0   # failures + prior
    pulls: int = 0
    total_reward: float = 0.0

    def sample(self) -> float:
        return float(np.random.beta(self.alpha, self.beta))

    def update(self, reward: float) -> None:
        """Update with a reward in [0, 1]."""
        self.pulls += 1
        self.total_reward += reward
        self.alpha += reward
        self.beta += (1.0 - reward)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


@dataclass
class ContentRL:
    """Multi-Armed Bandit for content feature selection."""

    # Arms grouped by feature type
    theme_arms: dict[str, ArmState] = field(default_factory=dict)
    hook_style_arms: dict[str, ArmState] = field(default_factory=dict)
    mood_arms: dict[str, ArmState] = field(default_factory=dict)

    # Learned benchmarks from data
    benchmarks: dict[str, float] = field(default_factory=dict)
    audience_profile: dict[str, Any] = field(default_factory=dict)
    retention_insights: dict[str, Any] = field(default_factory=dict)

    # Feature interaction weights (theme × hook_style)
    interaction_rewards: dict[str, float] = field(default_factory=dict)

    THEMES = ["luxury", "mindset", "motivation", "softlife", "pov",
              "relationship", "success", "aesthetic", "feminine_energy"]
    HOOK_STYLES = ["question", "third_person_narrative", "direct_address",
                   "reframe_statement", "pov_statement", "bold_claim"]
    MOODS = ["empowering", "calm", "bold", "mysterious", "serene",
             "aspirational", "confident", "reflective"]

    def __post_init__(self) -> None:
        for theme in self.THEMES:
            self.theme_arms.setdefault(theme, ArmState())
        for hook in self.HOOK_STYLES:
            self.hook_style_arms.setdefault(hook, ArmState())
        for mood in self.MOODS:
            self.mood_arms.setdefault(mood, ArmState())

    # ── Core RL Methods ───────────────────────────────────────────────────

    def select_best_features(self) -> dict[str, str]:
        """Thompson Sampling: sample from each arm's posterior, pick highest."""
        best_theme = max(self.theme_arms, key=lambda k: self.theme_arms[k].sample())
        best_hook = max(self.hook_style_arms, key=lambda k: self.hook_style_arms[k].sample())
        best_mood = max(self.mood_arms, key=lambda k: self.mood_arms[k].sample())

        return {
            "theme": best_theme,
            "hook_style": best_hook,
            "mood": best_mood,
        }

    def get_feature_rankings(self) -> dict[str, list[tuple[str, float]]]:
        """Return all features ranked by posterior mean (exploitation view)."""
        return {
            "themes": sorted(
                [(k, v.mean) for k, v in self.theme_arms.items()],
                key=lambda x: x[1], reverse=True,
            ),
            "hook_styles": sorted(
                [(k, v.mean) for k, v in self.hook_style_arms.items()],
                key=lambda x: x[1], reverse=True,
            ),
            "moods": sorted(
                [(k, v.mean) for k, v in self.mood_arms.items()],
                key=lambda x: x[1], reverse=True,
            ),
        }

    def compute_content_score(self, theme: str, hook_style: str, mood: str) -> float:
        """Score a content combination using posterior means + interaction bonus."""
        theme_score = self.theme_arms.get(theme, ArmState()).mean
        hook_score = self.hook_style_arms.get(hook_style, ArmState()).mean
        mood_score = self.mood_arms.get(mood, ArmState()).mean

        # Interaction bonus
        interaction_key = f"{theme}:{hook_style}"
        interaction_bonus = self.interaction_rewards.get(interaction_key, 0.0)

        return (theme_score * 0.4 + hook_score * 0.3 +
                mood_score * 0.2 + interaction_bonus * 0.1)

    # ── Learning from Watch Matrix ────────────────────────────────────────

    def learn_from_watch_matrix(self, matrix_path: Path | None = None) -> dict[str, Any]:
        """Ingest the video watch matrix and update all arm distributions."""
        path = matrix_path or WATCH_MATRIX_PATH
        with open(path) as f:
            data = json.load(f)

        videos = data["videos"]
        aggregate = data.get("aggregate_insights", {})

        # Store aggregate insights
        self.audience_profile = aggregate.get("audience_profile", {})
        self.retention_insights = aggregate.get("retention_crisis", {})

        # Compute rewards for each video
        # Normalise each metric to [0, 1] using min-max across the dataset
        views = [v["overview"]["views"] for v in videos]
        watch_times = [v["overview"]["avg_watch_time_seconds"] for v in videos]
        completions = [v["overview"]["watched_full_video_pct"] for v in videos]
        followers = [v["overview"]["new_followers"] for v in videos]

        def normalise(values: list[float]) -> list[float]:
            lo, hi = min(values), max(values)
            if hi == lo:
                return [0.5] * len(values)
            return [(v - lo) / (hi - lo) for v in values]

        norm_views = normalise(views)
        norm_watch = normalise(watch_times)
        norm_comp = normalise(completions)
        norm_follow = normalise(followers)

        # Composite reward: weighted combination
        # Views matter (reach), but watch time + completion are engagement quality
        WEIGHTS = {
            "views": 0.20,
            "watch_time": 0.30,
            "completion": 0.35,
            "followers": 0.15,
        }

        rewards = []
        for i in range(len(videos)):
            r = (WEIGHTS["views"] * norm_views[i] +
                 WEIGHTS["watch_time"] * norm_watch[i] +
                 WEIGHTS["completion"] * norm_comp[i] +
                 WEIGHTS["followers"] * norm_follow[i])
            rewards.append(r)

        # Update arms
        learned = []
        for video, reward in zip(videos, rewards):
            theme = video.get("theme", "")
            hook_style = video.get("hook_style", "")

            if theme in self.theme_arms:
                self.theme_arms[theme].update(reward)
            if hook_style in self.hook_style_arms:
                self.hook_style_arms[hook_style].update(reward)

            # Track interaction
            interaction_key = f"{theme}:{hook_style}"
            self.interaction_rewards[interaction_key] = reward

            learned.append({
                "video_id": video["video_id"],
                "theme": theme,
                "hook_style": hook_style,
                "reward": round(reward, 4),
            })

        # Compute benchmarks
        self.benchmarks = {
            "avg_views": sum(views) / len(views),
            "avg_watch_time": sum(watch_times) / len(watch_times),
            "avg_completion_pct": sum(completions) / len(completions),
            "avg_followers_per_video": sum(followers) / len(followers),
            "total_videos_analysed": len(videos),
            "best_composite_video": max(learned, key=lambda x: x["reward"])["video_id"],
        }

        return {
            "videos_processed": len(videos),
            "rewards": learned,
            "benchmarks": self.benchmarks,
            "top_features": self.select_best_features(),
            "rankings": self.get_feature_rankings(),
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, path: Path | None = None) -> None:
        path = path or RL_STATE_PATH
        state = {
            "theme_arms": {k: asdict(v) for k, v in self.theme_arms.items()},
            "hook_style_arms": {k: asdict(v) for k, v in self.hook_style_arms.items()},
            "mood_arms": {k: asdict(v) for k, v in self.mood_arms.items()},
            "benchmarks": self.benchmarks,
            "audience_profile": self.audience_profile,
            "retention_insights": self.retention_insights,
            "interaction_rewards": self.interaction_rewards,
        }
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | None = None) -> "ContentRL":
        path = path or RL_STATE_PATH
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        rl = cls()
        for k, v in raw.get("theme_arms", {}).items():
            rl.theme_arms[k] = ArmState(**v)
        for k, v in raw.get("hook_style_arms", {}).items():
            rl.hook_style_arms[k] = ArmState(**v)
        for k, v in raw.get("mood_arms", {}).items():
            rl.mood_arms[k] = ArmState(**v)
        rl.benchmarks = raw.get("benchmarks", {})
        rl.audience_profile = raw.get("audience_profile", {})
        rl.retention_insights = raw.get("retention_insights", {})
        rl.interaction_rewards = raw.get("interaction_rewards", {})
        return rl

    # ── Content Engine Integration ────────────────────────────────────────

    def get_scoring_weights(self) -> dict[str, float]:
        """Return theme weights for ContentEngine._pick_best() to use."""
        rankings = self.get_feature_rankings()
        # Normalise theme scores to weights
        theme_weights = {}
        themes = rankings["themes"]
        if themes:
            max_score = themes[0][1]
            for name, score in themes:
                theme_weights[name] = round(score / max(max_score, 0.01), 3)
        return theme_weights

    def get_caption_guidance(self) -> str:
        """Generate RL-informed guidance for caption generation prompts."""
        rankings = self.get_feature_rankings()
        top_themes = [t[0] for t in rankings["themes"][:3]]
        top_hooks = [h[0] for h in rankings["hook_styles"][:3]]

        audience = self.audience_profile
        retention = self.retention_insights

        lines = [
            "REINFORCEMENT LEARNING INSIGHTS (data-driven, prioritise these):",
            f"- Best performing themes: {', '.join(top_themes)}",
            f"- Best hook styles: {', '.join(top_hooks)}",
        ]
        if audience:
            gender = audience.get("gender_avg", {})
            lines.append(
                f"- Core audience: {gender.get('female', 82)}% female, "
                f"ages {audience.get('core_age_bracket', '25-34')} "
                f"({audience.get('core_age_pct', 47)}%)"
            )
            countries = audience.get("top_countries", [])
            if countries:
                lines.append(f"- Top markets: {', '.join(countries[:3])}")

        if retention:
            drop_off = retention.get("universal_drop_off_second", 2)
            lines.append(
                f"- CRITICAL: Viewers drop off at second {drop_off}. "
                "Hook MUST create curiosity/identity-match in first 2 seconds."
            )

        if self.benchmarks:
            lines.append(
                f"- Benchmarks: {self.benchmarks.get('avg_watch_time', 0):.1f}s avg watch, "
                f"{self.benchmarks.get('avg_completion_pct', 0):.1f}% completion"
            )

        return "\n".join(lines)

    def score_candidate(self, theme: str, mood: str = "",
                        hook_style: str = "") -> float:
        """Score a candidate page for ContentEngine._pick_best()."""
        theme_score = self.theme_arms.get(theme, ArmState()).mean
        hook_score = self.hook_style_arms.get(hook_style, ArmState()).mean if hook_style else 0.5
        mood_score = self.mood_arms.get(mood, ArmState()).mean if mood else 0.5

        interaction_key = f"{theme}:{hook_style}" if hook_style else ""
        interaction_bonus = self.interaction_rewards.get(interaction_key, 0.0)

        return (theme_score * 0.4 + hook_score * 0.3 +
                mood_score * 0.2 + interaction_bonus * 0.1)


def initialise_rl() -> dict[str, Any]:
    """One-shot: load watch matrix, train RL, persist state. Returns summary."""
    rl = ContentRL.load()
    result = rl.learn_from_watch_matrix()
    rl.save()
    return result
