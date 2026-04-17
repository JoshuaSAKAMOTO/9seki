"""Claude Sonnet step: generate the Japanese MDX draft with prompt caching."""

from anthropic import Anthropic

from writing.config import Config
from writing.prompts import build_system_blocks, build_user_prompt

WRITING_MODEL = "claude-sonnet-4-6"


def write_draft(
    cfg: Config,
    topic: str,
    player: dict,
    role: str,
    start_date: str,
    end_date: str,
    stats_json: str,
    findings: str,
) -> tuple[str, dict]:
    """
    Generate an MDX draft.
    Returns (mdx_text, usage_dict).
    """
    client = Anthropic(api_key=cfg.anthropic_api_key)

    system_blocks = build_system_blocks()
    user_prompt = build_user_prompt(
        topic=topic,
        player=player,
        role=role,
        start_date=start_date,
        end_date=end_date,
        stats_json=stats_json,
        findings=findings,
    )

    response = client.messages.create(
        model=WRITING_MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=system_blocks,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_parts = [b.text for b in response.content if b.type == "text"]
    mdx = "".join(text_parts).strip()

    # user_promptの「出力は以下のMDXから始めること」でプロンプト末尾に
    # `---\ntitle: "..."\n` を誘導しているが、モデルが頭の `---` を
    # 省略する場合がある。なければ補って整える。
    if not mdx.startswith("---"):
        mdx = "---\n" + mdx

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(
            response.usage, "cache_creation_input_tokens", 0
        ),
        "cache_read_input_tokens": getattr(
            response.usage, "cache_read_input_tokens", 0
        ),
    }
    return mdx, usage
