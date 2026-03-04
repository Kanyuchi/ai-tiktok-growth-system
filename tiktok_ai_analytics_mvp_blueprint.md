# TikTok AI Analytics System — MVP Blueprint

## Project Overview
This document outlines the Minimum Viable Product (MVP) for an AI-powered analytics system designed to accelerate growth for a faceless luxury TikTok account.

The system will:
1. Automate post-level data collection
2. Store structured performance snapshots
3. Compute key growth KPIs
4. Generate data-driven content recommendations
5. Enable experimentation and optimization

---

# 1. System Architecture

## Data Flow (Daily Automated Job)

1. Refresh OAuth Token
2. Pull Video Inventory (video IDs + metadata)
3. Pull Performance Metrics (views, likes, shares, comments, watch time, completion where available)
4. Store Daily Snapshot in PostgreSQL
5. Compute KPIs
6. Generate Recommendations

Recommended schedule: Daily at 06:00 (Europe/Berlin)

---

# 2. Database Schema (PostgreSQL)

## Table: posts
Stores static post metadata.

- post_id (PRIMARY KEY)
- posted_at (timestamp)
- caption (text)
- hashtags (text)
- audio_name (text)
- duration_seconds (int)
- category (text)
- format_type (text)
- hook_text (text)
- cta_type (text)
- visual_style (text)

## Table: post_metrics_daily
Stores daily performance snapshots.

- post_id (foreign key)
- snapshot_date (date)
- views (int)
- likes (int)
- comments (int)
- shares (int)
- saves (int)
- avg_watch_time_seconds (float)
- completion_rate (float)

PRIMARY KEY (post_id, snapshot_date)

## Table: experiments
Tracks A/B tests.

- experiment_id (PRIMARY KEY)
- hypothesis (text)
- variant_a_definition (text)
- variant_b_definition (text)
- start_date (date)
- end_date (date)
- winner_metric (text)

## Table: content_ideas
AI-generated backlog.

- idea_id (PRIMARY KEY)
- theme (text)
- hook (text)
- script (text)
- caption (text)
- hashtags (text)
- recommended_length (int)
- recommended_post_time (text)
- score (float)

---

# 3. Core KPIs

Primary Growth Metrics:

Engagement Rate = (likes + comments + shares + saves) / views

Share Rate = shares / views

Comment Rate = comments / views

Retention Proxy = avg_watch_time_seconds / duration_seconds

Follower Conversion (if available) = new_followers / views

---

# 4. Automation Components

## A. Token Management
- OAuth v2 authentication
- Automatic token refresh
- Secure credential storage via .env file

## B. ETL Pipeline
- Pull video list
- Pull metrics
- Upsert daily snapshot
- Log missing fields
- Handle rate limits + retries

## C. Scheduler
- Cron job or cloud scheduler
- Daily execution

---

# 5. AI Layer (MVP Version)

## Model 1 — Performance Predictor
Inputs:
- Hook type
- Duration bucket
- Posting time
- Audio type
- Theme
- CTA presence

Output:
- Predicted views
- Predicted share rate

Algorithms:
- Random Forest (baseline)
- Gradient Boosting (improved accuracy)

## Model 2 — Feature Importance Explainer
Purpose:
- Identify which content features drive performance

Outputs examples:
- "7–9 second videos outperform 15–20 second videos"
- "POV hooks have higher share rates"

## Model 3 — Recommendation Engine
Score calculation combines:
- Predicted performance
- Novelty factor
- Brand alignment

Output:
Weekly 14-post content plan

---

# 6. Feature Engineering Framework

## Hook Taxonomy
- POV
- Shock/Contrast
- Instructional
- Aspirational

## Luxury Categories
- Old money aesthetic
- Soft life femininity
- Luxury romance
- High-performance woman
- Travel/jet montage

## Creative Variables
- Text density (low/medium/high)
- Audio style (trending/ambient/voiceover)
- Cut speed (fast/slow)

---

# 7. Dashboard Components (Streamlit)

1. Performance leaderboard
2. Share rate ranking
3. Retention heatmap by posting hour
4. Growth curve visualization
5. Hook performance comparison

---

# 8. Constraints & Design Considerations

- Some playback metrics may have 24–48 hour latency
- Watch-time and completion metrics depend on account access level
- ETL must gracefully handle missing fields
- Avoid scraping; use official APIs

---

# 9. Next Implementation Steps

1. Create PostgreSQL database
2. Register TikTok Business Developer App
3. Implement OAuth token refresh logic
4. Build ETL script
5. Deploy daily scheduler
6. Build Streamlit dashboard
7. Train baseline performance model

---

# MVP Outcome

At completion, the system will:

- Automatically collect performance data
- Identify high-performing content structures
- Recommend what to post next
- Enable systematic experimentation
- Create a scalable content growth engine

---

End of MVP Blueprint

