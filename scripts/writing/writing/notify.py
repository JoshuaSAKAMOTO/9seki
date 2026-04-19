"""LINE Messaging API 経由でドラフト完成を通知する。"""

import os
import re
from pathlib import Path

import httpx


def _extract_title(mdx: str) -> str:
    """frontmatterから title を抽出する。見つからなければプレースホルダを返す。"""
    m = re.search(r'^title:\s*"([^"]+)"', mdx, re.MULTILINE)
    return m.group(1) if m else "(タイトル不明)"


def _count_components(mdx: str) -> dict[str, int]:
    """MDXソース中のカスタムコンポーネント出現数を数える。"""
    return {
        "StatCard": len(re.findall(r"<StatCard\b", mdx)),
        "HBarChart": len(re.findall(r"<HBarChart\b", mdx)),
        "Advanced": len(re.findall(r"<Advanced\b", mdx)),
        "Metric": len(re.findall(r"<Metric\b", mdx)),
    }


def _body_char_count(mdx: str) -> int:
    """frontmatter以外の本文文字数を概算（JSXタグや空白を除いた日本語文字ベース）。"""
    body = re.sub(r"^---\n.*?\n---\n", "", mdx, count=1, flags=re.DOTALL)
    body = re.sub(r"<[^>]+>", "", body)  # JSXタグ除去
    body = re.sub(r"\{[^}]+\}", "", body)  # JSX式除去
    body = re.sub(r"\s+", "", body)  # 空白・改行除去
    return len(body)


def notify_draft(
    output_path: Path,
    mdx: str,
    topic: str,
    player_name: str,
) -> None:
    """ドラフト完成をLINEに通知する。環境変数が揃っていなければ静かにスキップ。"""
    token = os.environ.get("LINE_CHANNEL_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        return

    title = _extract_title(mdx)
    comps = _count_components(mdx)
    chars = _body_char_count(mdx)

    comp_str = (
        ", ".join(f"{name}×{n}" for name, n in comps.items() if n > 0) or "なし"
    )

    message = (
        f"球析 ドラフト完成\n"
        f"「{title}」\n\n"
        f"対象: {player_name}\n"
        f"題材: {topic}\n\n"
        f"要素: {comp_str}\n"
        f"本文: 約{chars:,}字\n\n"
        f"{output_path}"
    )

    try:
        r = httpx.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "to": user_id,
                "messages": [{"type": "text", "text": message}],
            },
            timeout=10.0,
        )
        r.raise_for_status()
        print("Sent LINE notification.")
    except Exception as e:
        print(f"LINE notify failed (non-fatal): {e}")
