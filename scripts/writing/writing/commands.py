"""Orchestration: data → Claude findings → Claude draft → write MDX file."""

from datetime import date, datetime, timedelta
from pathlib import Path

from slugify import slugify

from writing import analyze, data, prompts, write
from writing.config import load_config

DRAFTS_DIR = prompts.ARTICLES_DIR / "drafts"


def draft(
    player_identifier: str,
    topic: str,
    days: int = 14,
    role: str | None = None,
    end_date: date | None = None,
    output: Path | None = None,
) -> Path:
    """
    Build a draft article about `topic` for the given player.

    Returns the path the draft was written to.
    """
    cfg = load_config()

    end = end_date or (date.today() - timedelta(days=1))
    start = end - timedelta(days=days - 1)

    player = data.lookup_player(cfg, player_identifier)
    inferred_role = role or (
        "pitcher" if player["primary_role"] in ("pitcher", "two_way") else "batter"
    )

    print(
        f"Drafting: {player['name_ja']} ({player['name_en']}) "
        f"{inferred_role} {start} → {end}"
    )
    print(f"Topic: {topic}")

    print("Fetching pitches from R2...")
    df = data.fetch_player_pitches(cfg, int(player["mlbam_id"]), start, end, inferred_role)
    print(f"  {len(df)} pitches")
    if df.empty:
        raise RuntimeError(
            "No pitches found for this player in the given window. "
            "Make sure the daily pipeline has ingested data for this period."
        )

    summary = data.summarise(df, inferred_role)
    stats_json = data.summary_as_json(summary)

    print("Running Claude Sonnet analysis...")
    findings = analyze.analyze_findings(
        cfg=cfg,
        topic=topic,
        player=player,
        role=inferred_role,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        stats_json=stats_json,
    )
    print("  findings ready")

    print("Running Claude Sonnet draft...")
    mdx, usage = write.write_draft(
        cfg=cfg,
        topic=topic,
        player=player,
        role=inferred_role,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        stats_json=stats_json,
        findings=findings,
    )

    print(
        f"  usage: input={usage['input_tokens']} "
        f"output={usage['output_tokens']} "
        f"cache_write={usage['cache_creation_input_tokens']} "
        f"cache_read={usage['cache_read_input_tokens']}"
    )

    if output is None:
        # 日本語topicはslugify互換性が悪いのでファイル名には使わない。
        # 題材は記事のtitle/frontmatter側に残る。
        ts = datetime.now().strftime("%H%M")
        slug_base = f"{slugify(player['name_en'])}-{end.isoformat()}-{ts}"
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        output = DRAFTS_DIR / f"{slug_base}.mdx"

    output.write_text(mdx, encoding="utf-8")
    print(f"Wrote draft: {output}")
    return output
