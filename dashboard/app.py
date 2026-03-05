from __future__ import annotations

import base64
from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from tiktok_ai_analytics.db import get_engine
from tiktok_ai_analytics.kpis import engagement_rate

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI TikTok Growth System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand palette ─────────────────────────────────────────────────────────────
PINK   = "#FF2D6B"
BLUE   = "#0095F6"
TEAL   = "#00C6C6"
ORANGE = "#FF6B35"
DARK   = "#0D0D0D"
CARD   = "#161616"
BORDER = "#2A2A2A"
MUTED  = "#888888"
WHITE  = "#F0F0F0"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
      background-color: {DARK};
      color: {WHITE};
      font-family: 'Inter', 'Segoe UI', sans-serif;
  }}
  [data-testid="stSidebar"] {{
      background-color: #0A0A0A;
      border-right: 1px solid {BORDER};
  }}
  [data-testid="stSidebar"] * {{ color: {WHITE} !important; }}
  #MainMenu, footer, header {{ visibility: hidden; }}
  h1, h2, h3 {{ color: {WHITE} !important; font-weight: 700 !important; letter-spacing: -0.5px; }}
  [data-testid="metric-container"] {{
      background: {CARD};
      border: 1px solid {BORDER};
      border-radius: 16px;
      padding: 20px 24px !important;
  }}
  [data-testid="metric-container"] label {{
      color: {MUTED} !important;
      font-size: 0.75rem !important;
      text-transform: uppercase;
      letter-spacing: 1px;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
      color: {WHITE} !important;
      font-size: 2rem !important;
      font-weight: 800 !important;
  }}
  [data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
  hr {{ border-color: {BORDER}; }}
  .section-label {{
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 2px;
      color: {MUTED};
      margin-bottom: 4px;
  }}
  .gradient-title {{
      background: linear-gradient(90deg, {PINK}, {BLUE}, {TEAL});
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      font-size: 1.8rem;
      font-weight: 900;
      letter-spacing: -1px;
  }}
  .pill {{
      display: inline-block;
      padding: 2px 10px;
      border-radius: 20px;
      font-size: 0.72rem;
      font-weight: 600;
  }}
  .pill-pink  {{ background: {PINK}22; color: {PINK}; border: 1px solid {PINK}44; }}
  .pill-blue  {{ background: {BLUE}22; color: {BLUE}; border: 1px solid {BLUE}44; }}
  .pill-teal  {{ background: {TEAL}22; color: {TEAL}; border: 1px solid {TEAL}44; }}
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: {DARK}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}

  /* Period button row */
  div[data-testid="stHorizontalBlock"] button {{
      background: {CARD} !important;
      border: 1px solid {BORDER} !important;
      color: {WHITE} !important;
      border-radius: 8px !important;
      font-size: 0.78rem !important;
  }}
</style>
""", unsafe_allow_html=True)

# ── Plotly base layout (no 'legend' key — set per-chart as needed) ────────────
PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=WHITE, family="Inter, Segoe UI, sans-serif"),
    margin=dict(l=0, r=0, t=32, b=0),
)

AXIS = dict(gridcolor=BORDER, zerolinecolor=BORDER)


def _logo_b64() -> str:
    p = PROJECT_ROOT / "images" / "ChatGPT Image Mar 4, 2026, 05_47_11 PM.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    logo_b64 = _logo_b64()
    if logo_b64:
        st.markdown(
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="width:100%;max-width:220px;margin:0 auto 24px;display:block;">',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="section-label">Time Period</p>', unsafe_allow_html=True)
    period = st.radio(
        "period",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
        index=3,
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown('<p class="section-label">Rank posts by</p>', unsafe_allow_html=True)
    sort_metric = st.selectbox(
        "sort",
        ["Views", "Engagement Rate", "Share Rate", "Likes", "Comments"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown('<p class="section-label">Chart — top N posts</p>', unsafe_allow_html=True)
    top_n = st.slider("Show top N posts", min_value=5, max_value=50, value=10, step=5,
                      label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<p class="section-label">Export</p>', unsafe_allow_html=True)
    export_placeholder = st.empty()

    st.markdown("---")
    st.markdown(
        f'<p style="font-size:0.7rem;color:{MUTED}">Auto-refreshes daily at 09:00 · '
        f'Powered by <span style="color:{PINK}">AI</span></p>',
        unsafe_allow_html=True,
    )

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        return pd.read_sql(
            text("""
                SELECT m.post_id, m.snapshot_date,
                       m.views, m.likes, m.comments, m.shares, m.saves,
                       m.avg_watch_time_seconds, m.completion_rate,
                       p.duration_seconds, p.caption, p.hashtags,
                       p.hook_text, p.format_type, p.cta_type, p.posted_at
                FROM post_metrics_daily m
                JOIN posts p ON p.post_id = m.post_id
                ORDER BY m.snapshot_date DESC, m.views DESC
            """),
            conn,
        )


try:
    df = load_data()
except Exception as exc:
    st.error(f"Database error: {exc}")
    st.info("Make sure PostgreSQL is running and `run-daily` has been executed.")
    st.stop()

if df.empty:
    st.info("No data yet — run `python -m tiktok_ai_analytics.cli run-daily` first.")
    st.stop()

df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
df["posted_at"] = pd.to_datetime(df["posted_at"], utc=True, errors="coerce")

# ── Period filter ─────────────────────────────────────────────────────────────
today = date.today()
PERIOD_MAP = {
    "Last 7 days":  today - timedelta(days=7),
    "Last 30 days": today - timedelta(days=30),
    "Last 90 days": today - timedelta(days=90),
    "All time":     df["snapshot_date"].min().date(),
}
cutoff = PERIOD_MAP[period]
filtered = df[df["snapshot_date"].dt.date >= cutoff].copy()

if filtered.empty:
    st.warning(f"No data in the selected period ({period}). Showing all data.")
    filtered = df.copy()

# ── Aggregate per post ────────────────────────────────────────────────────────
summary = filtered.groupby("post_id", as_index=False).agg(
    total_views=("views", "max"),
    total_likes=("likes", "max"),
    total_comments=("comments", "max"),
    total_shares=("shares", "max"),
    total_saves=("saves", "max"),
    avg_completion=("completion_rate", "mean"),
    caption=("caption", "first"),
    hashtags=("hashtags", "first"),
    hook_text=("hook_text", "first"),
    format_type=("format_type", "first"),
    cta_type=("cta_type", "first"),
    duration_seconds=("duration_seconds", "first"),
    posted_at=("posted_at", "first"),
)
summary["total_saves"] = summary["total_saves"].fillna(0).astype(int)
summary["engagement_rate"] = summary.apply(
    lambda r: engagement_rate(
        likes=int(r.total_likes), comments=int(r.total_comments),
        shares=int(r.total_shares), saves=int(r.total_saves),
        views=int(r.total_views),
    ), axis=1,
)
summary["share_rate"] = (
    summary["total_shares"] / summary["total_views"].replace(0, pd.NA)
).fillna(0)

SORT_COLS = {
    "Views": "total_views",
    "Engagement Rate": "engagement_rate",
    "Share Rate": "share_rate",
    "Likes": "total_likes",
    "Comments": "total_comments",
}
summary = summary.sort_values(SORT_COLS[sort_metric], ascending=False).reset_index(drop=True)

# ── KPI totals ────────────────────────────────────────────────────────────────
total_views    = int(summary["total_views"].sum())
total_likes    = int(summary["total_likes"].sum())
total_shares   = int(summary["total_shares"].sum())
total_comments = int(summary["total_comments"].sum())
avg_eng        = summary["engagement_rate"].mean()
post_count     = summary["post_id"].nunique()
best_views     = int(summary["total_views"].max())

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<p class="gradient-title">AI TikTok Growth System</p>'
    f'<p style="color:{MUTED};font-size:0.85rem;margin-top:-8px;">'
    f'Content analytics & performance intelligence · {period} · {post_count} posts tracked</p>',
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Top KPI cards ─────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Tracked Posts",   f"{post_count}")
c2.metric("Total Views",     f"{total_views:,}")
c3.metric("Total Likes",     f"{total_likes:,}")
c4.metric("Total Shares",    f"{total_shares:,}")
c5.metric("Avg Engagement",  f"{avg_eng:.2%}")
c6.metric("Best Post Views", f"{best_views:,}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Views trend + Engagement bar ──────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.markdown('<p class="section-label">Views Over Time</p>', unsafe_allow_html=True)
    trend = (
        filtered.groupby("snapshot_date", as_index=False)
        .agg(total_views=("views", "sum"))
    )
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend["snapshot_date"], y=trend["total_views"],
        mode="lines+markers",
        line=dict(color=PINK, width=3),
        marker=dict(size=7, color=PINK, line=dict(color=DARK, width=2)),
        fill="tozeroy",
        fillcolor="rgba(255,45,107,0.09)",
        name="Views",
    ))
    fig_trend.update_layout(
        **PLOTLY_BASE,
        height=260,
        xaxis={**AXIS, "tickformat": "%b %d"},
        yaxis=AXIS,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["zoom2d","pan2d","select2d","lasso2d","resetScale2d","autoScale2d","zoomIn2d","zoomOut2d"]})

with col_right:
    st.markdown(
        f'<p class="section-label">Engagement by Post — Top {top_n}</p>',
        unsafe_allow_html=True,
    )
    top_eng = summary.head(top_n).copy()
    top_eng["label"] = top_eng["hook_text"].fillna(top_eng["post_id"]).str[:30] + "…"
    fig_eng = go.Figure(go.Bar(
        x=top_eng["engagement_rate"] * 100,
        y=top_eng["label"],
        orientation="h",
        marker=dict(
            color=top_eng["engagement_rate"],
            colorscale=[[0, BLUE], [0.5, TEAL], [1, PINK]],
            showscale=False,
        ),
        text=[f"{v:.1f}%" for v in top_eng["engagement_rate"] * 100],
        textposition="outside",
        textfont=dict(color=WHITE, size=11),
    ))
    fig_eng.update_layout(
        **PLOTLY_BASE,
        height=260,
        xaxis={**AXIS, "title": "Engagement %"},
        yaxis={**AXIS, "autorange": "reversed"},
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_eng, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["zoom2d","pan2d","select2d","lasso2d","resetScale2d","autoScale2d","zoomIn2d","zoomOut2d"]})

# ── Row 2: Scatter + Format breakdown ────────────────────────────────────────
col_a, col_b = st.columns([2, 1], gap="large")

with col_a:
    st.markdown('<p class="section-label">Views vs Engagement (bubble = shares)</p>', unsafe_allow_html=True)
    sc = summary.head(max(top_n, 20)).copy()
    sc["label"] = sc["hook_text"].fillna(sc["post_id"]).str[:30]
    sc["bubble"] = (sc["total_shares"] + 1) * 8
    fig_scatter = go.Figure(go.Scatter(
        x=sc["total_views"],
        y=sc["engagement_rate"] * 100,
        mode="markers+text",
        marker=dict(
            size=sc["bubble"].clip(upper=60),
            color=sc["engagement_rate"],
            colorscale=[[0, BLUE], [0.5, TEAL], [1, PINK]],
            showscale=True,
            colorbar=dict(title="Eng%", thickness=10, tickfont=dict(color=WHITE)),
            line=dict(color=DARK, width=1),
        ),
        text=sc["label"],
        textposition="top center",
        textfont=dict(size=9, color=MUTED),
        hovertemplate="<b>%{text}</b><br>Views: %{x:,}<br>Engagement: %{y:.2f}%<extra></extra>",
    ))
    fig_scatter.update_layout(
        **PLOTLY_BASE,
        height=300,
        xaxis={**AXIS, "title": "Views"},
        yaxis={**AXIS, "title": "Engagement %"},
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_scatter, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["zoom2d","pan2d","select2d","lasso2d","resetScale2d","autoScale2d","zoomIn2d","zoomOut2d"]})

with col_b:
    st.markdown('<p class="section-label">Content Format Mix</p>', unsafe_allow_html=True)
    fmt_counts = summary["format_type"].fillna("standard").value_counts().reset_index()
    fmt_counts.columns = ["format", "count"]
    fig_pie = go.Figure(go.Pie(
        labels=fmt_counts["format"],
        values=fmt_counts["count"],
        hole=0.55,
        marker=dict(colors=[PINK, BLUE, TEAL, ORANGE, "#9B59B6"]),
        textfont=dict(color=WHITE, size=12),
        hovertemplate="%{label}: %{value} posts<extra></extra>",
    ))
    fig_pie.add_annotation(
        text=f"<b>{post_count}</b><br><span style='font-size:10px'>posts</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(color=WHITE, size=14),
    )
    fig_pie.update_layout(
        **PLOTLY_BASE,
        height=300,
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="v", x=1.0, y=0.5),
    )
    st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["zoom2d","pan2d","select2d","lasso2d","resetScale2d","autoScale2d","zoomIn2d","zoomOut2d"]})

# ── Row 3: Top posts leaderboard ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<p class="section-label">Content Performance Leaderboard — Top {top_n} by {sort_metric}</p>',
    unsafe_allow_html=True,
)

MEDAL = {0: "🥇", 1: "🥈", 2: "🥉"}

for i, row in summary.head(top_n).iterrows():
    medal = MEDAL.get(i, f"#{i+1}")
    eng_pct = f"{row['engagement_rate']:.1%}"
    hook = (row["hook_text"] or row["caption"] or row["post_id"])[:80]
    fmt = row["format_type"] or "standard"
    cta = row["cta_type"] or "—"
    duration = f"{row['duration_seconds']}s" if row["duration_seconds"] else "—"
    bar_width = min(int(row["engagement_rate"] * 800), 100)
    bar_color = PINK if i == 0 else (BLUE if i == 1 else TEAL)

    st.markdown(f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-radius:14px;
                padding:16px 20px;margin-bottom:10px;">
      <div style="display:flex;align-items:flex-start;gap:16px;">
        <div style="font-size:1.5rem;min-width:36px;text-align:center;">{medal}</div>
        <div style="flex:1;min-width:0;">
          <p style="margin:0 0 4px 0;font-weight:700;font-size:0.95rem;color:{WHITE};
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{hook}</p>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
            <span class="pill pill-pink">eng {eng_pct}</span>
            <span class="pill pill-blue">shares {row['total_shares']:,}</span>
            <span class="pill pill-teal">{fmt}</span>
            <span class="pill pill-pink">cta: {cta}</span>
            <span class="pill pill-blue">{duration}</span>
          </div>
          <div style="display:flex;gap:32px;">
            <span style="color:{MUTED};font-size:0.8rem;">👁 <b style="color:{WHITE}">{row['total_views']:,}</b></span>
            <span style="color:{MUTED};font-size:0.8rem;">❤️ <b style="color:{WHITE}">{row['total_likes']:,}</b></span>
            <span style="color:{MUTED};font-size:0.8rem;">💬 <b style="color:{WHITE}">{row['total_comments']:,}</b></span>
            <span style="color:{MUTED};font-size:0.8rem;">🔁 <b style="color:{WHITE}">{row['total_shares']:,}</b></span>
          </div>
        </div>
        <div style="text-align:right;min-width:80px;">
          <p style="margin:0;font-size:1.6rem;font-weight:900;color:{bar_color}">{row['total_views']:,}</p>
          <p style="margin:0;font-size:0.7rem;color:{MUTED}">views</p>
          <div style="height:4px;background:{BORDER};border-radius:2px;margin-top:6px;">
            <div style="height:4px;width:{bar_width}%;background:linear-gradient(90deg,{bar_color},{PINK});
                        border-radius:2px;"></div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Row 4: Hashtag analysis + Daily metrics ───────────────────────────────────
st.markdown("---")
col_hash, col_daily = st.columns([1, 2], gap="large")

with col_hash:
    st.markdown('<p class="section-label">Top Hashtags</p>', unsafe_allow_html=True)
    all_tags = []
    for tags in summary["hashtags"].dropna():
        all_tags.extend([t.strip() for t in tags.split() if t.startswith("#")])
    if all_tags:
        tag_series = pd.Series(all_tags).value_counts().head(12).reset_index()
        tag_series.columns = ["hashtag", "count"]
        fig_hash = go.Figure(go.Bar(
            x=tag_series["count"],
            y=tag_series["hashtag"],
            orientation="h",
            marker=dict(color=TEAL, opacity=0.85),
            text=tag_series["count"],
            textposition="outside",
            textfont=dict(color=WHITE),
        ))
        fig_hash.update_layout(
            **PLOTLY_BASE,
            height=320,
            xaxis=AXIS,
            yaxis={**AXIS, "autorange": "reversed"},
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_hash, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["zoom2d","pan2d","select2d","lasso2d","resetScale2d","autoScale2d","zoomIn2d","zoomOut2d"]})
    else:
        st.info("No hashtag data yet.")

with col_daily:
    st.markdown('<p class="section-label">Daily Metrics Breakdown</p>', unsafe_allow_html=True)
    daily = (
        filtered.groupby("snapshot_date", as_index=False)
        .agg(views=("views", "sum"), likes=("likes", "sum"),
             comments=("comments", "sum"), shares=("shares", "sum"))
    )
    fig_daily = go.Figure()
    for col_name, color in [("views", PINK), ("likes", BLUE), ("shares", TEAL), ("comments", ORANGE)]:
        fig_daily.add_trace(go.Scatter(
            x=daily["snapshot_date"], y=daily[col_name],
            name=col_name.capitalize(),
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
        ))
    fig_daily.update_layout(
        **PLOTLY_BASE,
        height=320,
        xaxis={**AXIS, "tickformat": "%b %d"},
        yaxis=AXIS,
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.2),
    )
    st.plotly_chart(fig_daily, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["zoom2d","pan2d","select2d","lasso2d","resetScale2d","autoScale2d","zoomIn2d","zoomOut2d"]})

# ── Sidebar exports (filled after data is ready) ─────────────────────────────
def _build_html_report(summary: pd.DataFrame, period: str, total_views: int,
                       total_likes: int, total_shares: int, avg_eng: float) -> str:
    rows = ""
    for i, r in summary.head(10).iterrows():
        hook = (r["hook_text"] or r["caption"] or r["post_id"])[:60]
        rows += f"""
        <tr>
          <td>#{i+1}</td>
          <td>{hook}</td>
          <td>{r['total_views']:,}</td>
          <td>{r['total_likes']:,}</td>
          <td>{r['total_shares']:,}</td>
          <td>{r['engagement_rate']:.2%}</td>
        </tr>"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>AI TikTok Growth System — Performance Report</title>
<style>
  body {{ font-family: Inter, sans-serif; background: #0D0D0D; color: #F0F0F0; padding: 40px; }}
  h1 {{ background: linear-gradient(90deg,#FF2D6B,#0095F6,#00C6C6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2rem; margin-bottom: 4px; }}
  .sub {{ color: #888; font-size: 0.85rem; margin-bottom: 32px; }}
  .kpis {{ display: flex; gap: 20px; margin-bottom: 32px; flex-wrap: wrap; }}
  .kpi {{ background: #161616; border: 1px solid #2A2A2A; border-radius: 12px;
           padding: 16px 24px; min-width: 140px; }}
  .kpi-label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #888; }}
  .kpi-value {{ font-size: 1.8rem; font-weight: 900; color: #F0F0F0; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th {{ text-align: left; padding: 10px 12px; background: #161616;
        color: #888; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #2A2A2A; font-size: 0.85rem; }}
  tr:hover td {{ background: #1a1a1a; }}
  .footer {{ margin-top: 40px; color: #555; font-size: 0.75rem; text-align: center; }}
</style></head><body>
<h1>AI TikTok Growth System</h1>
<p class="sub">Performance Report · {period} · Generated {date.today()}</p>
<div class="kpis">
  <div class="kpi"><div class="kpi-label">Total Views</div><div class="kpi-value">{total_views:,}</div></div>
  <div class="kpi"><div class="kpi-label">Total Likes</div><div class="kpi-value">{total_likes:,}</div></div>
  <div class="kpi"><div class="kpi-label">Total Shares</div><div class="kpi-value">{total_shares:,}</div></div>
  <div class="kpi"><div class="kpi-label">Avg Engagement</div><div class="kpi-value">{avg_eng:.2%}</div></div>
  <div class="kpi"><div class="kpi-label">Posts Tracked</div><div class="kpi-value">{len(summary)}</div></div>
</div>
<h2 style="font-size:1rem;color:#888;text-transform:uppercase;letter-spacing:2px;">Top 10 Posts</h2>
<table>
  <thead><tr><th>#</th><th>Hook / Caption</th><th>Views</th><th>Likes</th><th>Shares</th><th>Engagement</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<div class="footer">AI TikTok Growth System · Data as of {date.today()}</div>
</body></html>"""

csv_bytes = summary[[
    "post_id", "caption", "total_views", "total_likes", "total_comments",
    "total_shares", "engagement_rate", "format_type", "posted_at"
]].to_csv(index=False).encode("utf-8")

html_report = _build_html_report(
    summary, period, total_views, total_likes, total_shares, avg_eng
).encode("utf-8")

with export_placeholder:
    st.download_button(
        "⬇ Download CSV",
        data=csv_bytes,
        file_name=f"tiktok_analytics_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True,
    )
st.sidebar.download_button(
    "⬇ Download Report (HTML)",
    data=html_report,
    file_name=f"tiktok_report_{date.today()}.html",
    mime="text/html",
    use_container_width=True,
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<p style="text-align:center;color:{MUTED};font-size:0.75rem;">'
    f'AI TikTok Growth System · Data refreshes daily at 09:00 · '
    f'<span style="color:{PINK}">{post_count} posts tracked</span></p>',
    unsafe_allow_html=True,
)
