CREATE TABLE IF NOT EXISTS posts (
  post_id TEXT PRIMARY KEY,
  posted_at TIMESTAMPTZ,
  caption TEXT,
  hashtags TEXT,
  audio_name TEXT,
  duration_seconds INT,
  category TEXT,
  format_type TEXT,
  hook_text TEXT,
  cta_type TEXT,
  visual_style TEXT
);

CREATE TABLE IF NOT EXISTS post_metrics_daily (
  post_id TEXT NOT NULL,
  snapshot_date DATE NOT NULL,
  views INT,
  likes INT,
  comments INT,
  shares INT,
  saves INT,
  avg_watch_time_seconds FLOAT,
  completion_rate FLOAT,
  PRIMARY KEY (post_id, snapshot_date),
  CONSTRAINT fk_post FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

CREATE INDEX IF NOT EXISTS idx_post_metrics_daily_snapshot_date
  ON post_metrics_daily (snapshot_date);

CREATE TABLE IF NOT EXISTS experiments (
  experiment_id TEXT PRIMARY KEY,
  hypothesis TEXT,
  variant_a_definition TEXT,
  variant_b_definition TEXT,
  start_date DATE,
  end_date DATE,
  winner_metric TEXT
);

CREATE TABLE IF NOT EXISTS content_ideas (
  idea_id TEXT PRIMARY KEY,
  theme TEXT,
  hook TEXT,
  script TEXT,
  caption TEXT,
  hashtags TEXT,
  recommended_length INT,
  recommended_post_time TEXT,
  score FLOAT
);
