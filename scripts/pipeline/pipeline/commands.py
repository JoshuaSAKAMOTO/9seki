import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from pipeline import statcast
from pipeline.clients import D1Client, R2Client
from pipeline.config import load_config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def seed_players() -> None:
    """Insert/update the curated Japanese MLB player master in D1."""
    cfg = load_config()
    d1 = D1Client(cfg.cloudflare_account_id, cfg.d1_database_id, cfg.cloudflare_api_token)

    players = json.loads((DATA_DIR / "players.json").read_text(encoding="utf-8"))
    now = _now_iso()
    for p in players:
        d1.query(
            """
            INSERT INTO players
              (mlbam_id, name_en, name_ja, name_ja_kana, team_code, primary_role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mlbam_id) DO UPDATE SET
              name_en = excluded.name_en,
              name_ja = excluded.name_ja,
              name_ja_kana = excluded.name_ja_kana,
              team_code = excluded.team_code,
              primary_role = excluded.primary_role,
              updated_at = excluded.updated_at
            """,
            [
                p["mlbam_id"],
                p["name_en"],
                p["name_ja"],
                p["name_ja_kana"],
                p["team_code"],
                p["primary_role"],
                now,
                now,
            ],
        )
    print(f"Seeded {len(players)} players")


def _parquet_key(target: date) -> str:
    return (
        f"statcast/year={target.year:04d}/"
        f"month={target.month:02d}/"
        f"day={target.day:02d}/pitches.parquet"
    )


def _write_game_logs(
    d1: D1Client, df: pd.DataFrame, tracked_ids: set[int]
) -> int:
    """Aggregate per-player-per-game stats into player_game_logs."""
    rows_written = 0

    # Pitchers
    pitcher_ids = set(df["pitcher"].dropna().astype(int).unique()) & tracked_ids
    for pid in pitcher_ids:
        df_p = df[df["pitcher"] == pid]
        for game_pk, df_game in df_p.groupby("game_pk"):
            stats = statcast.aggregate_pitcher_game(df_game)
            d1.query(
                """
                INSERT INTO player_game_logs (mlbam_id, game_date, game_pk, role, stats)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mlbam_id, game_pk, role) DO UPDATE SET stats = excluded.stats
                """,
                [
                    int(pid),
                    str(df_game["game_date"].iloc[0]),
                    int(game_pk),
                    "pitcher",
                    json.dumps(stats, ensure_ascii=False),
                ],
            )
            rows_written += 1

    # Batters
    batter_ids = set(df["batter"].dropna().astype(int).unique()) & tracked_ids
    for bid in batter_ids:
        df_b = df[df["batter"] == bid]
        for game_pk, df_game in df_b.groupby("game_pk"):
            stats = statcast.aggregate_batter_game(df_game)
            d1.query(
                """
                INSERT INTO player_game_logs (mlbam_id, game_date, game_pk, role, stats)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mlbam_id, game_pk, role) DO UPDATE SET stats = excluded.stats
                """,
                [
                    int(bid),
                    str(df_game["game_date"].iloc[0]),
                    int(game_pk),
                    "batter",
                    json.dumps(stats, ensure_ascii=False),
                ],
            )
            rows_written += 1

    return rows_written


def daily_batch(target_date: date | None = None) -> None:
    """Fetch Statcast for the target date, upload raw parquet to R2,
    and update game logs in D1 for tracked players."""
    cfg = load_config()
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    d1 = D1Client(cfg.cloudflare_account_id, cfg.d1_database_id, cfg.cloudflare_api_token)
    r2 = R2Client(
        cfg.cloudflare_account_id,
        cfg.r2_access_key_id,
        cfg.r2_secret_access_key,
        cfg.r2_bucket,
    )

    tracked = d1.rows("SELECT mlbam_id FROM players")
    tracked_ids = {int(row["mlbam_id"]) for row in tracked}
    if not tracked_ids:
        print("No players tracked; run `seed-players` first.")
        return
    print(f"Tracking {len(tracked_ids)} players")

    print(f"Fetching Statcast data for {target_date.isoformat()}")
    df = statcast.fetch_day(target_date)
    if df.empty:
        print("No Statcast data returned for this date.")
        return
    print(f"Fetched {len(df)} total pitches")

    df_tracked = statcast.filter_tracked(df, tracked_ids)
    if df_tracked.empty:
        print("No tracked players appeared in this date's games.")
        return
    print(f"Filtered to {len(df_tracked)} pitches involving tracked players")

    key = _parquet_key(target_date)
    r2.upload_dataframe(df_tracked, key)
    print(f"Uploaded raw parquet to r2://{cfg.r2_bucket}/{key}")

    written = _write_game_logs(d1, df_tracked, tracked_ids)
    print(f"Wrote {written} game log rows to D1")

    if written > 0:
        _trigger_pages_rebuild()


def _trigger_pages_rebuild() -> None:
    """日次データが入ったら Cloudflare Pages の再ビルドを要求する。
    PAGES_DEPLOY_HOOK_URL 未設定なら黙ってスキップ、エラー時もパイプライン全体は失敗させない。"""
    import os

    import httpx

    url = os.environ.get("PAGES_DEPLOY_HOOK_URL")
    if not url:
        print("PAGES_DEPLOY_HOOK_URL not set; skipping rebuild trigger.")
        return
    try:
        r = httpx.post(url, timeout=10.0)
        r.raise_for_status()
        print(f"Triggered Pages rebuild (status {r.status_code})")
    except Exception as e:
        print(f"Pages rebuild trigger failed (non-fatal): {e}")
