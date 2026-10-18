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
