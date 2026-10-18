"""对「已安装的 automation-kit」做冒烟：只验证装进来的那一份，不碰工作区源码。

为什么单独一个脚本、而不是丢进 pytest：测试套件与仓库绑定——要读 `pyproject.toml`、
`CHANGELOG.md` 和 `docs/` 下的 schema 副本，装成 wheel 之后这些文件并不存在。而发布
制品矩阵要验证的恰恰是**装进来的那一份**能不能用，所以这里只做「安装件自证」：

* 导入的 `automation_core` 确实来自 site-packages——否则在源码树里跑会假绿，这条
  检查就失去了意义；
* 安装元数据里的版本与代码里的 `__version__` 一致，且与调用方给的期望版本一致；
* 打包资源齐全：report schema v1/v2、flow schema v1、viewer 模板；
* console script 入口点 `automation-runner` 随元数据装进来了；
* `yaml` extra 活到了安装元数据里（app 仓 CI 装的就是 `automation-kit[yaml]`）；
* CLI 可用：`python -m automation_runner --version`、`report-schema --version 1/2`；
* flow 校验器可用：能加载内置 schema 并接受一份最小合法流。

用法：`python scripts/smoke_installed_package.py [期望版本]`。不传期望版本时跳过版本
比对。失败打印 `FAIL: ...` 并返回非 0，可直接当 CI 门禁。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution

DIST_NAME = "automation-kit"
CONSOLE_SCRIPT = "automation-runner"
REQUIRED_RESOURCES = (
    ("automation_runner.schemas", "report-schema-v1.json"),
    ("automation_runner.schemas", "report-schema-v2.json"),
    ("automation_runner.schemas", "flow-schema-v1.json"),
    ("automation_runner", "viewer-template.html"),
)
MINIMAL_FLOW = {
    "workflow": "installed-package-smoke",
    "steps": [{"action": "open", "url": "https://example.test"}],
}


def _fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def _package_dir(package: str) -> pathlib.Path:
    """定位已安装包的目录；用 find_spec 而不是 importlib.resources.files，
    这样 Python 3.8 也能跑（本仓 requires-python 仍是 ^3.8）。"""
    spec = importlib.util.find_spec(package)
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError(f"{package} 不是可定位的包")
    return pathlib.Path(next(iter(spec.submodule_search_locations)))


def check_import_source() -> int:
    import automation_core

    path = pathlib.Path(automation_core.__file__).resolve()
    if not any(part in ("site-packages", "dist-packages") for part in path.parts):
        return _fail(
            f"automation_core 来自 {path}，不是 site-packages —— "
            "工作区源码把它遮住了，这次冒烟不能证明安装件可用"
        )
    print(f"ok: automation_core 来自 {path}")
    return 0


def check_version(expected: str | None) -> int:
    import automation_core

    try:
        installed = distribution(DIST_NAME).version
    except PackageNotFoundError:
        return _fail(f"元数据里找不到 {DIST_NAME}，安装不完整")

    if installed != automation_core.__version__:
        return _fail(
            f"元数据版本 {installed} 与 automation_core.__version__ "
            f"{automation_core.__version__} 不一致"
        )
    if expected and installed != expected:
        return _fail(f"安装的版本是 {installed}，期望 {expected}")
    print(f"ok: 版本 {installed}")
    return 0


def check_resources() -> int:
    for package, name in REQUIRED_RESOURCES:
        try:
            target = _package_dir(package) / name
        except RuntimeError as exc:
            return _fail(str(exc))
        if not target.is_file():
            return _fail(f"打包资源缺失：{package}/{name}")
        if not target.read_text(encoding="utf-8").strip():
            return _fail(f"打包资源为空：{package}/{name}")
    print(f"ok: {len(REQUIRED_RESOURCES)} 个打包资源齐全")
    return 0


def check_console_script() -> int:
    try:
        entry_points = distribution(DIST_NAME).entry_points
    except PackageNotFoundError:
        return _fail(f"元数据里找不到 {DIST_NAME}")
    names = {
        entry.name for entry in entry_points if entry.group == "console_scripts"
    }
    if CONSOLE_SCRIPT not in names:
        return _fail(f"console script {CONSOLE_SCRIPT} 不在入口点里：{sorted(names)}")
    print(f"ok: console script {CONSOLE_SCRIPT}")
    return 0


def check_yaml_extra_declared() -> int:
    """`yaml` extra 必须活到安装元数据里：app 仓 CI 装的是 `automation-kit[yaml]`。"""
    try:
        requires = distribution(DIST_NAME).requires or []
    except PackageNotFoundError:
        return _fail(f"元数据里找不到 {DIST_NAME}")
    if not any('extra == "yaml"' in req for req in requires):
        return _fail(f"元数据未声明 yaml extra：{list(requires)}")
    print("ok: yaml extra 已声明")
    return 0


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "automation_runner", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def check_cli(expected: str | None) -> int:
    version_run = _run_cli("--version")
    if version_run.returncode != 0:
        return _fail(f"automation-runner --version 退出码 {version_run.returncode}")
    reported = version_run.stdout.strip()
    if not reported:
        return _fail("automation-runner --version 没有输出")
    if expected and expected not in reported:
        return _fail(f"--version 输出 {reported!r}，不含期望版本 {expected}")

    for schema_version in ("1", "2"):
        run = _run_cli("report-schema", "--version", schema_version)
        if run.returncode != 0:
            return _fail(
                f"report-schema --version {schema_version} 退出码 {run.returncode}"
            )
        try:
            payload = json.loads(run.stdout)
        except json.JSONDecodeError as exc:
            return _fail(f"report-schema v{schema_version} 不是合法 JSON：{exc}")
        if not isinstance(payload, dict) or not payload:
            return _fail(f"report-schema v{schema_version} 为空")
    print(f"ok: CLI 可用（{reported}，report-schema v1/v2 可读）")
    return 0


def check_flow_validator() -> int:
    from automation_runner.flow_schema import load_flow_schema, validate_flow_document

    schema = load_flow_schema()
    if not isinstance(schema, dict) or not schema:
        return _fail("内置 flow schema 为空")
    validate_flow_document(MINIMAL_FLOW)
    print("ok: flow schema 可加载且接受最小合法流")
    return 0


def main(argv: list) -> int:
    expected = argv[1] if len(argv) > 1 else None
    checks = (
        check_import_source,
        lambda: check_version(expected),
        check_resources,
        check_console_script,
        check_yaml_extra_declared,
        lambda: check_cli(expected),
        check_flow_validator,
    )
    for check in checks:
        code = check()
        if code:
            return code
    print("PASS: 安装件自证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
