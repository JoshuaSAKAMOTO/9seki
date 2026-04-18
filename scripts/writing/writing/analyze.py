"""Analysis step: Claude Sonnet 4.6 produces English findings from raw stats."""

from anthropic import Anthropic

from writing.config import Config

ANALYSIS_MODEL = "claude-sonnet-4-6"


def analyze_findings(
    cfg: Config,
    topic: str,
    player: dict,
    role: str,
    start_date: str,
    end_date: str,
    stats_json: str,
) -> str:
    """Return a concise English bulleted analysis of the stats, focused on the topic."""
    client = Anthropic(api_key=cfg.anthropic_api_key)

    system = (
        "You are a sharp sabermetric analyst. Given a structured JSON summary of a player's "
        "Statcast data, produce focused bullet-point findings in English. The findings will "
        "be used by a Japanese writer to draft an article for a mid-to-advanced audience "
        "(readers who know FIP, xwOBA, Stuff+, Whiff%, etc. by default).\n\n"
        "Guidelines:\n"
        "- 6 to 12 bullets. No prose, no preamble, no conclusion.\n"
        "- Quote specific numbers from the JSON. Do not invent values.\n"
        "- Call out pitch-type patterns, two-strike / count-based usage, velocity, movement, "
        "whiff distribution, launch quality, event mix — whatever is actually visible.\n"
        "- Add league-average context where you can reason about it (e.g. 'splitter league "
        "Whiff% ~36%, so 42% is ~top-5%'). Mark clearly when you are reasoning vs quoting.\n"
        "- Flag sample-size caveats explicitly when the data is thin.\n"
        "- Do NOT speculate beyond what the data shows.\n"
        "- English only. The writer handles translation and voice."
    )

    user_prompt = f"""Topic: {topic}
Player: {player['name_en']} (MLBAM {player['mlbam_id']}), {player['team_code']}, {role}
Period: {start_date} to {end_date}

Stats summary (DuckDB aggregation of Statcast pitch-level data):
```json
{stats_json}
```

Produce the findings."""

    response = client.messages.create(
        model=ANALYSIS_MODEL,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_parts = [b.text for b in response.content if b.type == "text"]
    return "".join(text_parts).strip()
