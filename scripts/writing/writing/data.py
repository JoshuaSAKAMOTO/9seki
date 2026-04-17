"""Data fetching and summarisation from R2 Parquet via DuckDB."""

import json
from datetime import date
from typing import Any

import duckdb
import httpx
import pandas as pd

from writing.config import Config

_SWING = {"swinging_strike", "swinging_strike_blocked", "foul", "foul_tip", "hit_into_play"}
_WHIFF = {"swinging_strike", "swinging_strike_blocked"}


def d1_query(cfg: Config, sql: str, params: list[Any] | None = None) -> list[dict]:
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{cfg.cloudflare_account_id}"
        f"/d1/database/{cfg.d1_database_id}/query"
    )
    r = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {cfg.cloudflare_api_token}",
            "Content-Type": "application/json",
        },
        json={"sql": sql, "params": params or []},
        timeout=30.0,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"D1 query failed: {data.get('errors')}")
    return data["result"][0].get("results", [])


def lookup_player(cfg: Config, identifier: str) -> dict:
    """Find a player by MLBAM ID (numeric string), Japanese name, or English name."""
    if identifier.isdigit():
        rows = d1_query(cfg, "SELECT * FROM players WHERE mlbam_id = ?", [int(identifier)])
    else:
        rows = d1_query(
            cfg,
            "SELECT * FROM players WHERE name_ja = ? OR name_en = ? OR name_ja_kana = ?",
            [identifier, identifier, identifier],
        )
    if not rows:
        raise RuntimeError(f"Player not found: {identifier}")
    return rows[0]


def _duckdb_connection(cfg: Config) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(
        f"""
        CREATE OR REPLACE SECRET r2 (
            TYPE r2,
            KEY_ID '{cfg.r2_access_key_id}',
            SECRET '{cfg.r2_secret_access_key}',
            ACCOUNT_ID '{cfg.cloudflare_account_id}'
        )
        """
    )
    return con


def fetch_player_pitches(
    cfg: Config,
    mlbam_id: int,
    start_date: date,
    end_date: date,
    role: str,
) -> pd.DataFrame:
    """Fetch all pitches for a player in a date range from R2 Parquet."""
    con = _duckdb_connection(cfg)
    path_glob = f"r2://{cfg.r2_bucket}/statcast/year=*/month=*/day=*/pitches.parquet"
    column = "pitcher" if role == "pitcher" else "batter"
    df = con.execute(
        f"""
        SELECT *
        FROM read_parquet('{path_glob}', union_by_name=true)
        WHERE {column} = ?
          AND game_date BETWEEN ? AND ?
        ORDER BY game_date, game_pk, at_bat_number, pitch_number
        """,
        [mlbam_id, start_date.isoformat(), end_date.isoformat()],
    ).df()
    return df


def summarise_pitcher(df: pd.DataFrame) -> dict:
    """Compact numeric summary for an LLM to consume."""
    if df.empty:
        return {"empty": True}

    pitches = len(df)
    swings = df["description"].isin(_SWING).sum()
    whiffs = df["description"].isin(_WHIFF).sum()
    called = (df["description"] == "called_strike").sum()

    games = df["game_pk"].nunique()
    batters_faced = df.groupby("game_pk")["batter"].nunique().sum()

    by_type: dict[str, dict] = {}
    for pt, g in df.groupby("pitch_type", dropna=True):
        s = g["description"].isin(_SWING).sum()
        w = g["description"].isin(_WHIFF).sum()
        velo = g["release_speed"].dropna()
        spin = g["release_spin_rate"].dropna() if "release_spin_rate" in g.columns else pd.Series()
        pfx_z = g["pfx_z"].dropna() if "pfx_z" in g.columns else pd.Series()
        by_type[str(pt)] = {
            "count": int(len(g)),
            "usage_pct": round(len(g) / pitches * 100, 1),
            "avg_velo_mph": round(float(velo.mean()), 1) if len(velo) else None,
            "avg_velo_kmh": round(float(velo.mean()) * 1.609, 1) if len(velo) else None,
            "max_velo_kmh": round(float(velo.max()) * 1.609, 1) if len(velo) else None,
            "swings": int(s),
            "whiffs": int(w),
            "whiff_pct": round(float(w) / float(s) * 100, 1) if s else None,
            "avg_spin_rpm": round(float(spin.mean())) if len(spin) else None,
            "avg_vertical_break_in": round(float(pfx_z.mean()), 2) if len(pfx_z) else None,
        }

    two_strike = df[df["strikes"] == 2] if "strikes" in df.columns else df.iloc[0:0]
    two_strike_usage = (
        {
            str(pt): round(len(g) / len(two_strike) * 100, 1)
            for pt, g in two_strike.groupby("pitch_type", dropna=True)
        }
        if len(two_strike)
        else {}
    )

    return {
        "games": int(games),
        "pitches": int(pitches),
        "batters_faced": int(batters_faced),
        "swings": int(swings),
        "whiffs": int(whiffs),
        "called_strikes": int(called),
        "overall_whiff_pct": round(float(whiffs) / float(swings) * 100, 1) if swings else None,
        "overall_csw_pct": round(float(whiffs + called) / pitches * 100, 1) if pitches else None,
        "by_pitch_type": by_type,
        "two_strike_usage_pct": two_strike_usage,
    }


def summarise_batter(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"empty": True}

    pa = df[df["events"].notna()]
    events = pa["events"].value_counts().to_dict()
    hits = int(pa["events"].isin(["single", "double", "triple", "home_run"]).sum())
    home_runs = int((pa["events"] == "home_run").sum())
    walks = int((pa["events"] == "walk").sum())
    strikeouts = int((pa["events"] == "strikeout").sum())
    ab = int(
        pa["events"].isin(
            [
                "single", "double", "triple", "home_run", "strikeout",
                "field_out", "grounded_into_double_play", "force_out",
                "double_play", "field_error", "fielders_choice", "fielders_choice_out",
            ]
        ).sum()
    )

    launch_speed = df["launch_speed"].dropna()
    launch_angle = df["launch_angle"].dropna()
    hard_hit = int((launch_speed >= 95.0).sum())
    bip = len(launch_speed)

    return {
        "games": int(df["game_pk"].nunique()),
        "plate_appearances": int(len(pa)),
        "at_bats": ab,
        "hits": hits,
        "home_runs": home_runs,
        "walks": walks,
        "strikeouts": strikeouts,
        "avg": round(hits / ab, 3) if ab else None,
        "hard_hit_pct": round(hard_hit / bip * 100, 1) if bip else None,
        "avg_launch_speed_mph": round(float(launch_speed.mean()), 1) if len(launch_speed) else None,
        "avg_launch_speed_kmh": (
            round(float(launch_speed.mean()) * 1.609, 1) if len(launch_speed) else None
        ),
        "avg_launch_angle_deg": round(float(launch_angle.mean()), 1) if len(launch_angle) else None,
        "events": {str(k): int(v) for k, v in events.items()},
    }


def summarise(df: pd.DataFrame, role: str) -> dict:
    if role == "pitcher":
        return summarise_pitcher(df)
    return summarise_batter(df)


def summary_as_json(summary: dict) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2)
