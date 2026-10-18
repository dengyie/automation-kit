"""对「已安装的 automation-kit」做冒烟：只验证装进来的那一份，不碰工作区源码。

为什么单独一个脚本、而不是丢进 pytest：测试套件与仓库绑定——要读 `pyproject.toml`、
`CHANGELOG.md` 和 `docs/` 下的 schema 副本，装成 wheel 之后这些文件并不存在。而发布
制品矩阵要验证的恰恰是**装进来的那一份**能不能用，所以这里只做「安装件自证」：

* 导入的 `automation_core` / `automation_runner` 确实来自 site-packages——否则在源码
  树里跑会假绿，这个脚本就失去了意义；
* 安装元数据里的版本与代码里的 `__version__` 一致，且与调用方给的期望版本一致；
* 打包资源齐全：report schema v1/v2、flow schema v1、viewer 模板；
* console script 入口点 `automation-runner` 随元数据装进来了，并且**真能跑**——入口
  点存在不等于命令可用（`[tool.poetry.scripts]` 指向的可调用对象写错时，包装脚本照样
  装得上，只在运行时报错），而用户敲的就是这条命令；
* `yaml` extra 活到了安装元数据里，而且**真能解析 YAML**（app 仓 CI 装的就是
  `automation-kit[yaml]`）；
* CLI 可用：`python -m automation_runner --version`、`report-schema --version 1/2`；
* flow 校验器可用：能加载内置 schema、接受一份最小合法流，并且**拒绝非法流**——只会
  接受好消息的检查等于没检查。

用法：`python scripts/smoke_installed_package.py [期望版本]`。**CI 必须传期望版本**：
不传就跳过版本比对，那道门禁等于不存在（脚本会打印 notice 说明）。本脚本按
`automation-kit[yaml]` 的形态验收，缺 PyYAML 会明确失败而不是静默跳过。

失败打印 `FAIL: ...` 并返回非 0，可直接当 CI 门禁。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from importlib.metadata import PackageNotFoundError, distribution

DIST_NAME = "automation-kit"
CONSOLE_SCRIPT = "automation-runner"
# 必须是 site-packages 里那一份：core 是内核，runner 是下面所有 CLI / schema / flow
# 检查真正依赖的代码。两个都查——从仓库根跑时 `python -m` 会把 cwd 塞进 sys.path，
# 只查 core 会漏掉「runner 被源码遮住」这种情况。
INSTALLED_PACKAGES = ("automation_core", "automation_runner")
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
MINIMAL_FLOW_YAML = """\
workflow: installed-package-smoke
steps:
  - action: open
    url: https://example.test
"""


def _fail(message: str) -> int:
    # 先刷 stdout：CI 里两条流都进管道，stdout 是块缓冲、stderr 不是，不刷的话 FAIL 会
    # 排在这一轮的 ok 之前，日志读起来像「先失败后成功」。
    sys.stdout.flush()
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
    for package in INSTALLED_PACKAGES:
        spec = importlib.util.find_spec(package)
        if spec is None or not spec.origin:
            return _fail(f"{package} 定位不到源文件，安装不完整")
        path = pathlib.Path(spec.origin).resolve()
        if not any(part in ("site-packages", "dist-packages") for part in path.parts):
            return _fail(
                f"{package} 来自 {path}，不是 site-packages —— "
                "工作区源码把它遮住了，这次冒烟不能证明安装件可用"
            )
    print(f"ok: {'、'.join(INSTALLED_PACKAGES)} 均来自 site-packages")
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


def _in_foreign_cwd(args: list) -> subprocess.CompletedProcess:
    """在仓库外的 cwd 里跑子进程。

    `python -m` 会把**当前目录**放进 `sys.path`：从仓库根运行本脚本时，子进程会导入
    工作区源码而不是安装件，CLI 检查随变成假绿。固定 cwd 到临时目录，把「必须从仓库
    外运行」从文档约定变成脚本强制。
    """
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        cwd=tempfile.gettempdir(),
    )


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return _in_foreign_cwd([sys.executable, "-m", "automation_runner", *args])


def _console_script_path() -> pathlib.Path | None:
    found = shutil.which(CONSOLE_SCRIPT)
    if found:
        return pathlib.Path(found)
    scripts_dir = pathlib.Path(sysconfig.get_path("scripts"))
    for candidate in (
        scripts_dir / CONSOLE_SCRIPT,
        scripts_dir / f"{CONSOLE_SCRIPT}.exe",
    ):
        if candidate.is_file():
            return candidate
    return None


def check_console_script(expected: str | None) -> int:
    try:
        entry_points = distribution(DIST_NAME).entry_points
    except PackageNotFoundError:
        return _fail(f"元数据里找不到 {DIST_NAME}")
    names = {entry.name for entry in entry_points if entry.group == "console_scripts"}
    if CONSOLE_SCRIPT not in names:
        return _fail(f"console script {CONSOLE_SCRIPT} 不在入口点里：{sorted(names)}")

    script = _console_script_path()
    if script is None:
        return _fail(
            f"元数据声明了 {CONSOLE_SCRIPT}，但在 PATH 与 "
            f"{sysconfig.get_path('scripts')} 里都找不到"
        )
    try:
        run = _in_foreign_cwd([str(script), "--version"])
    except OSError as exc:
        return _fail(f"{script} 无法执行：{exc}")
    if run.returncode != 0:
        return _fail(
            f"{script.name} --version 退出码 {run.returncode}：{run.stderr.strip()}"
        )
    reported = run.stdout.strip()
    if not reported:
        return _fail(f"{script.name} --version 没有输出")
    if expected and expected not in reported:
        return _fail(f"{script.name} --version 输出 {reported!r}，不含期望版本 {expected}")
    print(f"ok: console script {CONSOLE_SCRIPT} 可执行（{reported}）")
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


def check_yaml_extra_works() -> int:
    """声明了 extra 不等于 YAML 能用（PyYAML 可能没装上、或 loader 与它不兼容）。

    缺 PyYAML 时 `load_flow` 会抛带安装指引的 `FlowError`，这里原样报出来——静默跳过
    会让这道检查退化成什么都不查。
    """
    try:
        from automation_runner.flow_schema import FlowError
        from automation_runner.yaml_loader import load_flow
    except ImportError as exc:
        return _fail(f"flow loader 不可导入：{exc}")

    with tempfile.TemporaryDirectory() as tmp:
        flow_path = pathlib.Path(tmp) / "flow.yaml"
        flow_path.write_text(MINIMAL_FLOW_YAML, encoding="utf-8")
        try:
            loaded = load_flow(str(flow_path))
        except FlowError as exc:
            return _fail(f"最小 YAML 流解析失败：{exc}")
        except Exception as exc:  # noqa: BLE001 - 任何异常都算这道检查失败
            return _fail(f"最小 YAML 流解析抛了意外异常：{type(exc).__name__}: {exc}")

    if loaded.workflow_name != "installed-package-smoke" or len(loaded.steps) != 1:
        return _fail(
            f"YAML 流解析结果异常：name={loaded.workflow_name!r} "
            f"steps={len(loaded.steps)}"
        )
    print("ok: yaml extra 可用（最小 YAML 流解析通过）")
    return 0


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
    from automation_runner.flow_schema import (
        FlowError,
        load_flow_schema,
        validate_flow_document,
    )

    schema = load_flow_schema()
    if not isinstance(schema, dict) or not schema:
        return _fail("内置 flow schema 为空")
    validate_flow_document(MINIMAL_FLOW)

    # 反向对照：校验器必须真的会拒绝坏文档。少了这一半，哪天 validate 退化成空函数，
    # 「接受最小合法流」照样通过，这道检查就成了摆设。
    try:
        validate_flow_document({"workflow": "", "steps": []})
    except FlowError:
        pass
    else:
        return _fail("flow 校验器接受了非法流（workflow 空 + steps 空），这道检查形同虚设")

    print("ok: flow schema 可加载、接受最小合法流、并拒绝非法流")
    return 0


def main(argv: list) -> int:
    expected = argv[1] if len(argv) > 1 else None
    if not expected:
        print(
            "notice: 未给期望版本，跳过版本比对（仅本地便利用）；"
            "CI 必须传版本，否则这道门禁等于不存在",
            file=sys.stderr,
        )
    checks = (
        check_import_source,
        lambda: check_version(expected),
        check_resources,
        lambda: check_console_script(expected),
        check_yaml_extra_declared,
        check_yaml_extra_works,
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
