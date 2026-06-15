import argparse
import importlib
import sys
from typing import List, Optional

from automation_runner import WorkflowRunner
from examples.damai_android import run_smoke_workflow as run_damai_android_smoke
from examples.damai_web import run_smoke_workflow as run_damai_web_smoke


WORKFLOWS = {
    "damai-web-smoke": run_damai_web_smoke,
    "damai-android-smoke": run_damai_android_smoke,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="automation-runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    examples = subparsers.add_parser("examples", help="list example workflows")
    examples.add_argument("--dry-run", action="store_true", help="list only")

    run = subparsers.add_parser("run", help="run an example workflow")
    run.add_argument("workflow", choices=sorted(WORKFLOWS))
    run.add_argument("--live", action="store_true", help="allow live execution")
    run.add_argument("--factory", help="session factory import path")
    run.add_argument("--url", help="URL for web workflows")
    run.add_argument("--app-id", help="app ID for Android workflows")
    return parser


def load_object(import_path: str):
    module_name, separator, object_path = import_path.partition(":")
    if not separator or not module_name or not object_path:
        raise ValueError("import path must use module:object")

    target = importlib.import_module(module_name)
    for part in object_path.split("."):
        target = getattr(target, part)
    return target


def _print_error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "examples":
        for workflow_name in sorted(WORKFLOWS):
            print(workflow_name)
        if args.dry_run:
            print("dry-run: no live browser, Appium, ADB, or device session started")
        return 0

    if args.command == "run":
        if not args.live:
            return _print_error("--live is required to run workflows")
        if not args.factory:
            return _print_error("--factory is required for live workflows")
        if args.workflow == "damai-web-smoke":
            if not args.url:
                return _print_error("--url is required for damai-web-smoke")
            session_factory = load_object(args.factory)
            workflow = WORKFLOWS[args.workflow]
            runner = WorkflowRunner(
                session_factory=session_factory,
                workflow=lambda session: workflow(session, url=args.url),
            )
        else:
            if not args.app_id:
                return _print_error("--app-id is required for damai-android-smoke")
            session_factory = load_object(args.factory)
            workflow = WORKFLOWS[args.workflow]
            runner = WorkflowRunner(
                session_factory=session_factory,
                workflow=lambda session: workflow(session, app_id=args.app_id),
            )

        result = runner.run()
        print(f"{args.workflow} success={result.success}")
        return 0

    return 1
