"""Gemini Flash step: English-language analysis of raw stats."""

from google import genai

from writing.config import Config

ANALYSIS_MODEL = "gemini-2.5-flash"


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
    client = genai.Client(api_key=cfg.google_api_key)

    prompt = f"""You are a sabermetric analyst. Produce a concise bulleted analysis in English
that a Japanese writer will use to draft an article.

Topic: {topic}
Player: {player['name_en']} (MLBAM {player['mlbam_id']}), {player['team_code']}, {role}
Period: {start_date} to {end_date}

Stats summary (JSON from DuckDB aggregation of Statcast data):
```json
{stats_json}
```

Output guidelines:
- 6 to 12 bullet points
- Focus strictly on what is visible in the data and relevant to the topic
- Include specific numbers (always) and league-average comparisons where you can reason about them
- Call out pitch-type or situational patterns (e.g. two-strike usage, pitch mix shift)
- Do NOT speculate beyond the data
- If the data is too thin (e.g. only one game), say so explicitly in one bullet
- No prose — bullets only
- English only. The Japanese writer will handle localization.
"""
    response = client.models.generate_content(
        model=ANALYSIS_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()
