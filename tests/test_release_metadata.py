"""发布元数据门禁：版本号、CHANGELOG、发布 tag 与打包资源必须自洽。

版本号在本仓有多个载体（`pyproject.toml`、`automation_core.__version__`、
`CHANGELOG.md` 段头、发布 tag），任何一处漏改都会产出「标签与包内容不符」的制品——
而包源上的版本号不可撤回，也删不掉。这里把一致性做成测试，让它在离线测试和发布
工作流里都能挡住这类错误。

同时校验 `pyproject.toml` 声明的打包资源真实存在：少一个 schema 资源不会让任何
单测失败，只会在用户装完之后才暴露。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

import automation_core

REPO_ROOT = Path(__file__).resolve().parents[1]


def _poetry_version(pyproject_text: str) -> str:
    """取 `[tool.poetry]` 段里的 version。

    本仓构建后端是 poetry-core，版本号在 `[tool.poetry]` 而非 PEP 621 的 `[project]`；
    解析不引第三方（Python 3.8 没有 tomllib），只认该段第一处 `version = "..."`。
    """
    sections = pyproject_text.split("[tool.poetry]", 1)
    assert len(sections) == 2, "pyproject.toml 缺少 [tool.poetry] 段"
    match = re.search(r'^\s*version\s*=\s*"([^"]+)"', sections[1], re.MULTILINE)
    assert match is not None, "[tool.poetry] 段缺少 version"
    return match.group(1)


def _included_paths(pyproject_text: str) -> list:
    """取 `include = [...]` 里声明的打包资源相对路径。"""
    sections = pyproject_text.split("include = [", 1)
    assert len(sections) == 2, "pyproject.toml 缺少 include 列表"
    body = sections[1].split("]", 1)[0]
    return re.findall(r'path\s*=\s*"([^"]+)"', body)


def _tag_mismatch(ref_type: str, ref_name: str, version: str):
    """返回 tag 与包版本不符的说明；不是 tag 构建时返回 None。"""
    if ref_type != "tag" or not ref_name:
        return None
    expected = f"v{version}"
    if ref_name != expected:
        return f"tag {ref_name} 与包版本 {version} 不符（应为 {expected}）"
    return None


def test_pyproject_version_matches_package_version():
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert _poetry_version(text) == automation_core.__version__


def test_changelog_documents_current_version():
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = {line.strip() for line in changelog.splitlines() if line.startswith("## ")}
    assert f"## {automation_core.__version__}" in headings, sorted(headings)


def test_declared_package_resources_exist():
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    paths = _included_paths(text)
    assert paths, "include 列表为空，打包资源无人校验"
    missing = [path for path in paths if not (REPO_ROOT / path).is_file()]
    assert not missing, f"pyproject include 声明的资源不存在：{missing}"


def test_release_tag_matches_version():
    """tag 构建（`push: tags`）时校验 tag 名；分支构建直接跳过。"""
    mismatch = _tag_mismatch(
        os.environ.get("GITHUB_REF_TYPE", ""),
        os.environ.get("GITHUB_REF_NAME", ""),
        automation_core.__version__,
    )
    assert mismatch is None, mismatch


def test_tag_check_rejects_mismatched_tag():
    assert _tag_mismatch("tag", f"v{automation_core.__version__}", automation_core.__version__) is None
    # 非 tag 构建不参与判定
    assert _tag_mismatch("branch", "v0.0.1", automation_core.__version__) is None
    assert _tag_mismatch("tag", "", automation_core.__version__) is None
    # 漏了 v 前缀、或 tag 落后于版本，都必须报错
    assert _tag_mismatch("tag", automation_core.__version__, automation_core.__version__) is not None
    assert _tag_mismatch("tag", "v0.0.1", automation_core.__version__) is not None


def test_release_tag_gate_reads_github_env(monkeypatch):
    """tag 门禁靠 `GITHUB_REF_TYPE` / `GITHUB_REF_NAME` 取上下文。

    变量名或读取方式一旦写错，这道门禁在发布时就是死的（本地永远走「非 tag 构建」
    分支而静默通过）。这里直接驱动 `test_release_tag_matches_version` 本体，证明它
    真的会因错误的 tag 失败、因正确的 tag 通过——否则「发布门禁会检查 tag」只是注释
    里的一句话。
    """
    monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
    monkeypatch.setenv("GITHUB_REF_NAME", f"v{automation_core.__version__}.999")
    with pytest.raises(AssertionError):
        test_release_tag_matches_version()

    monkeypatch.setenv("GITHUB_REF_NAME", f"v{automation_core.__version__}")
    test_release_tag_matches_version()

    monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
    monkeypatch.setenv("GITHUB_REF_NAME", "feat/evolution-m1-m2")
    test_release_tag_matches_version()


def test_verify_job_runs_even_when_one_publish_job_is_skipped():
    """发布后的「从包源装一遍」必须能在 tag 路径上真的跑起来。

    实测语义（2026-10-19 临时探针）：`needs` 里的依赖被 **skip** 时，依赖方 job 会被
    skip——即使它自己的 `if` 条件为真。tag 路径上 `publish-testpypi` 恒被 skip，所以
    `verify-from-index` 的 `if` 必须带 `always()`；少了它，这道最关键的验证会在最需要
    它的时刻静默不执行，而整个 run 仍然显示成功（假绿）。
    """
    yaml = pytest.importorskip("yaml")
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    )
    condition = workflow["jobs"]["verify-from-index"]["if"]
    assert "always()" in condition, condition
    assert "needs.publish-pypi.result == 'success'" in condition, condition
    assert "needs.publish-testpypi.result == 'success'" in condition, condition


def test_ci_always_passes_expected_version_to_smoke():
    """冒烟脚本不传期望版本就跳过版本比对：CI 里漏掉这个参数，版本门禁等于没有。"""
    invocations = []
    for workflow in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if "smoke_installed_package.py" in line:
                invocations.append((workflow.name, line.strip()))
    assert invocations, "没有任何 workflow 调用安装件冒烟，制品矩阵又空了"
    for name, line in invocations:
        tail = line.split("smoke_installed_package.py", 1)[1].strip()
        assert tail, f"{name} 调用冒烟时没传期望版本：{line}"


def test_ci_package_job_installs_both_artifact_kinds():
    """发版同时上传 wheel 和 sdist，两个都得被真的装一遍。

    sdist 不是 wheel 的同义反复：pip 装 wheel 只是解包，装 sdist 要现场调用 build
    backend 构建，产物内容由 `include`/包发现规则决定——一个漏了 `schemas/` 的 sdist
    在 wheel 分支上永远暴露不出来。矩阵只留 wheel 等于给 sdist 免检。
    """
    yaml = pytest.importorskip("yaml")
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["package"]
    kinds = job["strategy"]["matrix"]["artifact"]
    assert set(kinds) == {"wheel", "sdist"}, kinds

    body = yaml.safe_dump(job, allow_unicode=True)
    for suffix in ("*.whl", "*.tar.gz"):
        assert suffix in body, f"package job 没有取 {suffix} 的路径，矩阵里那一支会拿到空值"

    # 构建步骤加了 --wheel 就只产 wheel，sdist 分支会因取不到文件而失败（或更糟：
    # 静默装到上一次构建残留的 tarball）。
    for step in job["steps"]:
        run = step.get("run", "")
        if "python -m build" in run:
            assert "--wheel" not in run, f"构建步骤退化成只产 wheel：{step.get('name')}"


def test_verify_job_installs_published_sdist_too():
    """发布后自证不能只装 wheel：默认安装路径永远命中 wheel，sdist 会全程免检。

    `--no-binary` 是唯一能把 pip 从 wheel 拽回源码构建的开关；少了它，这一步只是把
    上面那步重跑一遍。同时必须换新 venv——同一解释器里 wheel 已装，pip 会判定「已满足」
    而不构建，这一步沦为假绿。
    """
    yaml = pytest.importorskip("yaml")
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["verify-from-index"]["steps"]
    runs = [step.get("run", "") for step in steps]
    sdist_runs = [run for run in runs if "--no-binary" in run]
    assert sdist_runs, "verify-from-index 没有强制源码构建的分支，包源上的 sdist 无人验证"
    sdist_run = sdist_runs[0]
    assert "automation-kit" in sdist_run, sdist_run
    # 必须独立 venv：与 wheel 那步共用解释器时 pip 直接判定已满足，压根不会构建。
    assert "venv" in sdist_run, sdist_run
    # 两种制品都得跑到冒烟上，否则「装了」只是声明。
    assert len([run for run in runs if "smoke_installed_package.py" in run]) >= 2, runs
