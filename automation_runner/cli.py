import argparse
import importlib
import json
from pathlib import Path
import sys
import time
from typing import List, Optional

from automation_runner import WorkflowRunner
from automation_runner.reports import build_report
from examples.damai_android import create_workflow as create_damai_android_workflow
from examples.damai_web import create_workflow as create_damai_web_workflow


WORKFLOWS = {
    "damai-web-smoke": create_damai_web_workflow,
    "damai-android-smoke": create_damai_android_workflow,
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
    run.add_argument("--json", action="store_true", help="emit JSON report")
    run.add_argument("--report-file", help="write JSON report to file")
    return parser


def load_object(import_path: str):
    module_name, separator, object_path = import_path.partition(":")
    if not separator or not module_name or not object_path:
        raise ValueError("import path must use module:object")

    try:
        target = importlib.import_module(module_name)
        for part in object_path.split("."):
            target = getattr(target, part)
    except (ImportError, AttributeError) as exc:
        raise ValueError(f"could not load factory: {import_path}") from exc
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
        else:
            if not args.app_id:
                return _print_error("--app-id is required for damai-android-smoke")
        try:
            session_factory = load_object(args.factory)
        except ValueError as exc:
            return _print_error(str(exc))
        if args.workflow == "damai-web-smoke":
            create_workflow = WORKFLOWS[args.workflow]
            runner = WorkflowRunner(
                session_factory=lambda: create_workflow(
                    session_factory=session_factory,
                    url=args.url,
                ),
                workflow=lambda workflow: workflow.run(),
            )
        else:
            create_workflow = WORKFLOWS[args.workflow]
            runner = WorkflowRunner(
                session_factory=lambda: create_workflow(
                    session_factory=session_factory,
                    app_id=args.app_id,
                ),
                workflow=lambda workflow: workflow.run(),
            )

        started_at = time.monotonic()
        result = runner.run()
        elapsed_seconds = time.monotonic() - started_at
        if args.json:
            report = build_report(
                args.workflow,
                result,
                live=args.live,
                workflow_factory=args.factory,
                elapsed_seconds=elapsed_seconds,
            )
            payload = json.dumps(report.to_dict(), sort_keys=True)
            print(payload)
            if args.report_file:
                report_path = Path(args.report_file)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(payload, encoding="utf-8")
            return 0 if result.success else 1
        else:
            if args.report_file:
                return _print_error("--report-file requires --json")
            print(f"{args.workflow} success={result.success}")
        return 0 if result.success else 1

    return 1
