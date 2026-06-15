import argparse
from typing import List, Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="automation-runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    examples = subparsers.add_parser("examples", help="list example workflows")
    examples.add_argument("--dry-run", action="store_true", help="list only")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "examples":
        print("damai-web-smoke")
        print("damai-android-smoke")
        if args.dry_run:
            print("dry-run: no live browser, Appium, ADB, or device session started")
        return 0

    return 1
