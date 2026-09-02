import argparse
from dataclasses import replace
import importlib
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from automation_core import __version__ as AUTOMATION_KIT_VERSION
from automation_core.config import ConfigSource, EnvConfigSource
from automation_core.execution import WorkflowResult as ExecutionWorkflowResult
from automation_core.execution import WorkflowStatus
from automation_runner.config import RunnerConfig, load_runner_config
from automation_runner.context import WorkflowContext, WorkflowOptions
from automation_runner.dry_run import DryRunSession
from automation_runner.reports import build_report_v2
from automation_runner.runtime import WorkflowRuntime
from automation_runner.schemas import load_report_schema
from automation_runner.workflows import ComposedWorkflow
from examples.damai_android import build_steps as build_damai_android_steps
from examples.damai_web import build_steps as build_damai_web_steps


def _damai_web_steps(config: RunnerConfig) -> list:
    return build_damai_web_steps(url=config.url)


def _damai_android_steps(config: RunnerConfig) -> list:
    return build_damai_android_steps(app_id=config.app_id)


BUILTIN_WORKFLOWS = {
    "damai-web-smoke": _damai_web_steps,
    "damai-android-smoke": _damai_android_steps,
}

WORKFLOW_METADATA = {
    "damai-android-smoke": {
        "description": "Launch an Android app and capture startup artifacts.",
        "platform": "android",
        "required_options": ["app_id"],
        "supports_dry_run": True,
    },
    "damai-web-smoke": {
        "description": "Open a web URL and capture a screenshot artifact.",
        "platform": "web",
        "required_options": ["url"],
        "supports_dry_run": True,
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="automation-runner")
    parser.add_argument(
        "--version",
        action="version",
        version=f"automation-runner {AUTOMATION_KIT_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    examples = subparsers.add_parser("examples", help="list example workflows")
    examples.add_argument("--dry-run", action="store_true", help="list only")
    examples.add_argument("--json", action="store_true", help="emit JSON workflow list")

    report_schema = subparsers.add_parser(
        "report-schema",
        help="print runner report JSON schema",
    )
    report_schema.add_argument(
        "--version",
        default="2",
        help="runner report schema version",
    )

    run = subparsers.add_parser("run", help="run a workflow")
    run.add_argument("workflow", nargs="?", choices=sorted(BUILTIN_WORKFLOWS))
    run.add_argument("--workflow-factory", help="workflow factory import path")
    run.add_argument("--live", action="store_true", help="allow live execution")
    run.add_argument("--factory", help="session factory import path")
    run.add_argument("--url", help="URL for web workflows")
    run.add_argument("--app-id", help="app ID for Android workflows")
    run.add_argument(
        "--param",
        action="append",
        help="workflow parameter as KEY=VALUE; may be repeated",
    )
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


def _print_run_error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _json_report_payload(report) -> str:
    return json.dumps(report.to_dict(), sort_keys=True) + "\n"


def _write_json_report_file(report_file: str, payload: str) -> None:
    report_path = Path(report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")


def _emit_json_report_payload(payload: str) -> None:
    print(payload, end="")


def _emit_json_report(report) -> None:
    _emit_json_report_payload(_json_report_payload(report))


def _workflow_exit_code(result: ExecutionWorkflowResult) -> int:
    if result.status is WorkflowStatus.CANCELLED:
        return 130
    return 0 if result.success else 1


def _workflow_listing_entry(workflow_name: str) -> Dict[str, object]:
    metadata = WORKFLOW_METADATA[workflow_name]
    return {
        "name": workflow_name,
        "description": metadata["description"],
        "platform": metadata["platform"],
        "required_options": list(metadata["required_options"]),
        "supports_dry_run": metadata["supports_dry_run"],
    }


def _workflow_listing_entries() -> List[Dict[str, object]]:
    missing_metadata = sorted(set(BUILTIN_WORKFLOWS) - set(WORKFLOW_METADATA))
    if missing_metadata:
        raise ValueError(f"missing workflow metadata: {', '.join(missing_metadata)}")
    return [
        _workflow_listing_entry(workflow_name)
        for workflow_name in sorted(BUILTIN_WORKFLOWS)
    ]


def _merge_config(args: argparse.Namespace, config: RunnerConfig) -> RunnerConfig:
    return RunnerConfig(
        live=args.live or config.live,
        emit_json=args.json or config.emit_json,
        factory=args.factory if args.factory is not None else config.factory,
        workflow_factory=(
            args.workflow_factory
            if args.workflow_factory is not None
            else config.workflow_factory
        ),
        url=_merged_optional_cli_string(args.url, config.url),
        app_id=_merged_optional_cli_string(args.app_id, config.app_id),
        parameters=dict(config.parameters),
    )


def _resolve_workflow_selection(
    args: argparse.Namespace,
    config: RunnerConfig,
) -> RunnerConfig:
    if args.workflow and args.workflow_factory:
        raise ValueError("workflow and --workflow-factory are mutually exclusive")
    if args.workflow and config.workflow_factory:
        return replace(config, workflow_factory=None)
    return config


def _workflow_name(args: argparse.Namespace, config: RunnerConfig) -> str:
    if args.workflow:
        return args.workflow
    if config.workflow_factory:
        return config.workflow_factory
    raise ValueError("workflow or --workflow-factory is required")


_OPTION_CONFIG_FIELDS = {
    "url": "url",
    "app_id": "app_id",
}


def _missing_required_option(
    workflow_name: str,
    config: RunnerConfig,
) -> Optional[str]:
    """Validate a built-in workflow's required options against its metadata.

    WORKFLOW_METADATA is the single source of truth for required options, so a
    newly registered builtin cannot silently skip its guard.
    """
    metadata = WORKFLOW_METADATA.get(workflow_name)
    if metadata is None:
        return None
    for option in metadata["required_options"]:
        value = getattr(config, _OPTION_CONFIG_FIELDS[option], None)
        if value is None or not str(value).strip():
            return f"--{option.replace('_', '-')} is required for {workflow_name}"
    return None


def _workflow_context(
    workflow_name: str,
    config: RunnerConfig,
    session_factory_name: Optional[str],
) -> WorkflowContext:
    return WorkflowContext(
        workflow_name=workflow_name,
        live=config.live,
        workflow_factory=config.workflow_factory,
        session_factory=session_factory_name,
    )


def _run_metadata(config: RunnerConfig) -> Dict[str, Any]:
    return {
        "live": config.live,
        "session_factory": config.factory if config.live else None,
        "workflow_factory": config.workflow_factory,
    }


def _workflow_options(config: RunnerConfig, args: argparse.Namespace) -> WorkflowOptions:
    parameters = dict(config.parameters)
    parameters.update(_parse_parameters(args.param))
    return WorkflowOptions(
        url=config.url,
        app_id=config.app_id,
        emit_json=config.emit_json,
        report_file=args.report_file,
        parameters=parameters,
    )


def _optional_cli_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not value.strip():
        return None
    return value


def _merged_optional_cli_string(
    cli_value: Optional[str],
    config_value: Optional[str],
) -> Optional[str]:
    if cli_value is None:
        return config_value
    return _optional_cli_string(cli_value)


def _parse_parameters(values: Optional[List[str]]) -> Dict[str, str]:
    parameters = {}
    for value in values or []:
        key, separator, raw_value = value.partition("=")
        if not separator or not key.strip():
            raise ValueError("--param must use KEY=VALUE")
        parameters[key] = raw_value
    return parameters


def _call_custom_workflow_factory(
    create_workflow,
    session_factory,
    context,
    options,
):
    try:
        signature = inspect.signature(create_workflow)
    except (TypeError, ValueError):
        signature = None
    if signature is not None:
        parameters = signature.parameters
        accepts_keywords = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        if "context" in parameters or "options" in parameters or accepts_keywords:
            return create_workflow(
                session_factory=session_factory,
                context=context,
                options=options,
            )
        return create_workflow(session_factory=session_factory)
    return create_workflow(
        session_factory=session_factory,
        context=context,
        options=options,
    )


def main(
    argv: Optional[List[str]] = None,
    config_source: Optional[ConfigSource] = None,
) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "examples":
        if args.json:
            try:
                workflows = _workflow_listing_entries()
            except ValueError as exc:
                return _print_error(str(exc))
            payload = {
                "dry_run": args.dry_run,
                "workflows": workflows,
            }
            print(json.dumps(payload, sort_keys=True))
            return 0
        for workflow_name in sorted(BUILTIN_WORKFLOWS):
            print(workflow_name)
        if args.dry_run:
            print("dry-run: no live browser, Appium, ADB, or device session started")
        return 0

    if args.command == "report-schema":
        try:
            schema = load_report_schema(args.version)
        except ValueError as exc:
            return _print_error(str(exc))
        print(json.dumps(schema, sort_keys=True))
        return 0

    if args.command == "run":
        source = config_source or EnvConfigSource(os.environ, prefix="AUTOMATION_RUNNER_")
        try:
            config = load_runner_config(source)
        except ValueError as exc:
            return _print_error(str(exc))
        config = _merge_config(args, config)
        try:
            config = _resolve_workflow_selection(args, config)
        except ValueError as exc:
            return _print_error(str(exc))
        try:
            workflow_name = _workflow_name(args, config)
        except ValueError as exc:
            return _print_error(str(exc))
        if args.report_file and not config.emit_json:
            return _print_error("--report-file requires --json")
        if config.live and not config.factory:
            return _print_error("--factory is required for live workflows")
        missing_option = _missing_required_option(workflow_name, config)
        if missing_option is not None:
            return _print_error(missing_option)
        try:
            options = _workflow_options(config, args)
        except ValueError as exc:
            return _print_error(str(exc))
        if config.live:
            try:
                session_factory = load_object(config.factory)
            except ValueError as exc:
                return _print_error(str(exc))
        else:
            session_factory = lambda: DryRunSession(workflow_name)  # noqa: E731

        try:
            workflow = _build_workflow(
                args, config, options, session_factory, workflow_name
            )
        except ValueError as exc:
            return _print_error(str(exc))
        except Exception as exc:
            return _print_run_error(f"{type(exc).__name__}: {exc}")

        try:
            result = workflow.run()
        except Exception as exc:
            return _print_run_error(f"{type(exc).__name__}: {exc}")
        if not isinstance(result, ExecutionWorkflowResult):
            return _print_run_error(
                "workflow factory must return automation_core.execution.WorkflowResult; "
                f"got {type(result).__name__}"
            )

        if config.emit_json:
            report = build_report_v2(result)
            payload = _json_report_payload(report)
            if args.report_file:
                try:
                    _write_json_report_file(args.report_file, payload)
                except OSError as exc:
                    return _print_error(
                        f"could not write report file {args.report_file}: {exc}"
                    )
                _emit_json_report_payload(payload)
            else:
                _emit_json_report(report)
        else:
            print(f"{workflow_name} success={result.success}")
        return _workflow_exit_code(result)

    return 1


def _build_workflow(
    args: argparse.Namespace,
    config: RunnerConfig,
    options,
    session_factory,
    workflow_name: str,
):
    if config.workflow_factory:
        create_workflow = load_object(config.workflow_factory)
        context = _workflow_context(
            workflow_name=workflow_name,
            config=config,
            session_factory_name=config.factory if config.live else None,
        )
        return _call_custom_workflow_factory(
            create_workflow,
            session_factory,
            context,
            options,
        )
    steps = BUILTIN_WORKFLOWS[workflow_name](config)
    runtime = WorkflowRuntime(
        session_factory=session_factory,
        workflow_name=workflow_name,
        metadata=_run_metadata(config),
    )
    return ComposedWorkflow(runtime, steps)
