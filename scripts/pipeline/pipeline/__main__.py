import argparse
from datetime import date

from pipeline import commands


def _date_arg(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("seed-players", help="Insert/update player master from data/players.json")

    daily = sub.add_parser("daily", help="Run the daily Statcast batch")
    daily.add_argument(
        "--date",
        type=_date_arg,
        default=None,
        help="Target date (YYYY-MM-DD). Defaults to yesterday UTC.",
    )

    args = parser.parse_args()

    if args.cmd == "seed-players":
        commands.seed_players()
    elif args.cmd == "daily":
        commands.daily_batch(args.date)


if __name__ == "__main__":
    main()
