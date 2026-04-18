"""Prompt construction: load style guide + few-shot examples, build messages."""

from pathlib import Path

# scripts/writing/writing/ → project root = parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STYLE_GUIDE_PATH = PROJECT_ROOT / "docs" / "style-guide.md"
ARTICLES_DIR = PROJECT_ROOT / "src" / "content" / "articles"
METRICS_DIR = PROJECT_ROOT / "src" / "content" / "metrics"

# 順序はキャッシュ安定のため固定
FEW_SHOT_SLUGS = ["yamamoto-splitter-2026"]


def load_style_guide() -> str:
    return STYLE_GUIDE_PATH.read_text(encoding="utf-8")


def list_available_metrics() -> list[str]:
    """src/content/metrics/ 配下の .mdx ファイル名（stem）をslugとして返す。"""
    return sorted(p.stem for p in METRICS_DIR.glob("*.mdx"))


def load_few_shots() -> list[dict]:
    """Return list of {slug, content} for each few-shot article."""
    shots = []
    for slug in FEW_SHOT_SLUGS:
        p = ARTICLES_DIR / f"{slug}.mdx"
        if p.exists():
            shots.append({"slug": slug, "content": p.read_text(encoding="utf-8")})
    return shots


def build_system_blocks() -> list[dict]:
    """
    Static system prompt blocks ordered for maximum cache reuse:
    stable preamble → style guide → few-shots → cache_control marker.
    """
    style_guide = load_style_guide()
    few_shots = load_few_shots()

    preamble = (
        "あなたは「球析 (9seki)」の執筆者である。球析は日本語圏の中上級MLBファン向け、"
        "画像を使わないセイバーメトリクス分析メディア。\n\n"
        "以下のスタイルガイドと模範記事を厳密に守り、依頼された題材について"
        "Astro Content Collections用のMDX記事草稿を生成すること。"
    )

    shots_text = "\n\n".join(
        f"## 模範記事: {s['slug']}\n\n```mdx\n{s['content']}\n```"
        for s in few_shots
    )

    combined = (
        f"{preamble}\n\n"
        f"---\n\n# スタイルガイド\n\n{style_guide}\n\n"
        f"---\n\n# 模範記事（few-shot）\n\n{shots_text}"
    )

    return [
        {
            "type": "text",
            "text": combined,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def build_user_prompt(
    topic: str,
    player: dict,
    role: str,
    start_date: str,
    end_date: str,
    stats_json: str,
    findings: str,
    available_metrics: list[str],
) -> str:
    metrics_csv = ", ".join(available_metrics) if available_metrics else "(なし)"
    return f"""以下の情報をもとに、「球析」のMDX記事草稿を1本生成してください。

# 題材
{topic}

# 対象選手
- 名前: {player['name_ja']} ({player['name_en']})
- MLBAM ID: {player['mlbam_id']}
- チーム: {player['team_code']}
- 主な役割: {role}

# 期間
{start_date} 〜 {end_date}

# 英語での分析 (Gemini Flashが抽出したキーファインディング)
{findings}

# 生データサマリ (DuckDBで集計したJSON)
```json
{stats_json}
```

# 利用可能な指標

`<Metric id="...">` タグで使える id は以下のslugのみ:
{metrics_csv}

このリストにない指標を本文で言及する場合は、`<Metric>` タグを使わず、日本語名と英語名の併記で普通に書くこと（例: 「CSW%（Called + Swinging Strike 率）」）。

frontmatter の `metrics` 配列にも、上記リストに含まれるslugのみを入れること。リストにない指標はfrontmatterから除外する。

# 出力形式

以下の形式で、MDXファイルの中身を **frontmatterから本文終端まで** 1つのMDXブロックとして出力してください。
MDX以外の説明文や前置きは一切書かないこと。出力はそのままファイルに保存される。

必須:
- frontmatterの `status` は必ず `draft` にする
- `publishedAt` は `{end_date}` を使う
- `players` に対象選手のMLBAM IDを含める
- `metrics` に言及した指標のslug配列を入れる（上記「利用可能な指標」リストのslugのみ）
- 本文は5〜10段落
- 単位はkm/h, m, cm, %で統一
- 初出の主要指標には `<Metric id="...">` を使う（ただし利用可能なslugのみ）
- キーとなる数字は `<StatCard>` で強調（1〜3個）
- 必要なら `<HBarChart>` で比較可視化を1つ入れる
- 技術的補足は `<Advanced>` で折りたたむ
- 「〜だ。」「〜である。」調で統一

出力は以下のMDXから始めること（コードフェンス不要）:

---
title: "..."
"""
