from datetime import date

import pandas as pd


def fetch_day(target: date) -> pd.DataFrame:
    """Fetch all Statcast pitch data for the given date via pybaseball."""
    from pybaseball import statcast

    iso = target.isoformat()
    df = statcast(start_dt=iso, end_dt=iso)
    if df is None:
        return pd.DataFrame()
    return df


def filter_tracked(df: pd.DataFrame, tracked_ids: set[int]) -> pd.DataFrame:
    """Keep only pitches involving tracked players (as pitcher or batter)."""
    if df.empty:
        return df
    mask = df["pitcher"].isin(tracked_ids) | df["batter"].isin(tracked_ids)
    return df[mask].copy()


_SWING_DESCRIPTIONS = {
    "swinging_strike",
    "swinging_strike_blocked",
    "foul",
    "foul_tip",
    "hit_into_play",
}
_WHIFF_DESCRIPTIONS = {"swinging_strike", "swinging_strike_blocked"}


def aggregate_pitcher_game(df_player: pd.DataFrame) -> dict:
    """Summarise one pitcher's appearance in one game."""
    pitches = len(df_player)
    swings = df_player["description"].isin(_SWING_DESCRIPTIONS).sum()
    whiffs = df_player["description"].isin(_WHIFF_DESCRIPTIONS).sum()
    called_strikes = (df_player["description"] == "called_strike").sum()
    batters_faced = df_player["batter"].nunique()

    pitch_types = (
        df_player["pitch_type"].value_counts(dropna=True).to_dict()
        if "pitch_type" in df_player.columns
        else {}
    )

    velo = df_player["release_speed"].dropna()

    return {
        "pitches": int(pitches),
        "swings": int(swings),
        "whiffs": int(whiffs),
        "called_strikes": int(called_strikes),
        "batters_faced": int(batters_faced),
        "whiff_rate": round(float(whiffs) / float(swings), 3) if swings else None,
        "csw_rate": (
            round(float(whiffs + called_strikes) / float(pitches), 3) if pitches else None
        ),
        "avg_velocity_mph": round(float(velo.mean()), 1) if len(velo) else None,
        "max_velocity_mph": round(float(velo.max()), 1) if len(velo) else None,
        "pitch_types": {str(k): int(v) for k, v in pitch_types.items()},
    }


def aggregate_batter_game(df_player: pd.DataFrame) -> dict:
    """Summarise one batter's plate appearances in one game."""
    pa = df_player[df_player["events"].notna()]
    events = pa["events"].value_counts().to_dict()

    hits = int(pa["events"].isin(["single", "double", "triple", "home_run"]).sum())
    home_runs = int((pa["events"] == "home_run").sum())
    walks = int((pa["events"] == "walk").sum())
    strikeouts = int((pa["events"] == "strikeout").sum())
    ab = int(
        pa["events"].isin(
            [
                "single",
                "double",
                "triple",
                "home_run",
                "strikeout",
                "field_out",
                "grounded_into_double_play",
                "force_out",
                "double_play",
                "triple_play",
                "field_error",
                "fielders_choice",
                "fielders_choice_out",
            ]
        ).sum()
    )

    launch = df_player["launch_speed"].dropna()
    hard_hit = int((launch >= 95.0).sum())
    bip = len(launch)

    return {
        "pa": int(len(pa)),
        "ab": ab,
        "hits": hits,
        "home_runs": home_runs,
        "walks": walks,
        "strikeouts": strikeouts,
        "avg": round(hits / ab, 3) if ab else None,
        "hard_hit_rate": round(hard_hit / bip, 3) if bip else None,
        "events": {str(k): int(v) for k, v in events.items()},
    }
