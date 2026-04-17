import argparse
from datetime import date
from pathlib import Path

from writing import commands


def _date_arg(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(prog="writing")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("draft", help="Generate a draft MDX article")
    d.add_argument(
        "--player",
        required=True,
        help='選手のMLBAM ID、日本語名、英語名、またはカナ (例: "山本由伸" or 808967)',
    )
    d.add_argument(
        "--topic",
        required=True,
        help="記事の題材（日本語）",
    )
    d.add_argument(
        "--days",
        type=int,
        default=14,
        help="終了日から遡る日数 (default: 14)",
    )
    d.add_argument(
        "--role",
        choices=["pitcher", "batter"],
        default=None,
        help="役割を明示指定（two_wayの選手で使用）",
    )
    d.add_argument(
        "--end-date",
        type=_date_arg,
        default=None,
        help="期間終端（YYYY-MM-DD）。デフォルト: 昨日",
    )
    d.add_argument(
        "--output",
        type=Path,
        default=None,
        help="出力先MDXパス。デフォルト: src/content/articles/drafts/{slug}.mdx",
    )

    args = parser.parse_args()

    if args.cmd == "draft":
        commands.draft(
            player_identifier=args.player,
            topic=args.topic,
            days=args.days,
            role=args.role,
            end_date=args.end_date,
            output=args.output,
        )


if __name__ == "__main__":
    main()
