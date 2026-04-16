-- 球析 (9seki) D1 Schema
-- 動的データのみ。記事コンテンツはMDX (Content Collections) で管理。

-- 選手マスタ
CREATE TABLE players (
  mlbam_id       INTEGER PRIMARY KEY,
  name_en        TEXT NOT NULL,           -- Shohei Ohtani
  name_ja        TEXT NOT NULL,           -- 大谷翔平
  name_ja_kana   TEXT,                    -- オオタニショウヘイ
  team_code      TEXT NOT NULL,           -- LAD
  primary_role   TEXT NOT NULL CHECK (primary_role IN ('pitcher', 'batter', 'two_way')),
  jersey_number  INTEGER,
  debut_date     TEXT,
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- 指標マスタ
CREATE TABLE metrics (
  id              TEXT PRIMARY KEY,       -- "stuff-plus"
  name_en         TEXT NOT NULL,          -- "Stuff+"
  name_ja         TEXT NOT NULL,          -- "Stuff+"
  short_desc      TEXT NOT NULL,
  level           TEXT NOT NULL CHECK (level IN ('basic', 'intermediate', 'advanced')),
  source          TEXT NOT NULL,          -- "Statcast", "FanGraphs", etc.
  unit            TEXT,
  league_average  REAL,
  percentile_90   REAL,
  related_metrics TEXT NOT NULL DEFAULT '[]' -- JSON array of metric IDs
);

-- 選手の最新スタッツ（集計キャッシュ）
CREATE TABLE player_latest_stats (
  mlbam_id       INTEGER PRIMARY KEY REFERENCES players(mlbam_id),
  as_of_date     TEXT NOT NULL,
  pitching_stats TEXT,                    -- JSON
  batting_stats  TEXT,                    -- JSON
  last_game_date TEXT,
  updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- 試合ログ
CREATE TABLE player_game_logs (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  mlbam_id       INTEGER NOT NULL REFERENCES players(mlbam_id),
  game_date      TEXT NOT NULL,
  game_pk        INTEGER NOT NULL,
  role           TEXT NOT NULL CHECK (role IN ('pitcher', 'batter')),
  stats          TEXT NOT NULL,           -- JSON
  UNIQUE(mlbam_id, game_pk, role)
);

CREATE INDEX idx_game_logs_player_date ON player_game_logs(mlbam_id, game_date DESC);
CREATE INDEX idx_game_logs_date ON player_game_logs(game_date DESC);
