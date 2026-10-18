# Changelog

已发布版本历史。架构与开发规范在 `docs/development.md`，本文件不承担规范职责。

## Unreleased

发布能力与制品验收（见 `docs/development.md` §10.8）。纯发布工具链与测试，运行时行为、
公共接口、report schema v2 与 flow schema v1 均无变化。

- `.github/workflows/publish.yml`：tag `v*` 触发正式发布（PyPI trusted publishing，
  OIDC，无存储 token）；`workflow_dispatch` 支持 TestPyPI 演练；发布后从包源安装并跑
  安装件自证。
- `.github/workflows/ci.yml` 新增 `package` job：构建 wheel → 干净环境安装 → 自证，
  离线验证制品（不依赖 sibling path）。
- `scripts/smoke_installed_package.py`：安装件自证脚本。断言 `automation_core` 来自
  site-packages、版本三方一致、随包资源齐全、console script 可执行、`[yaml]` extra 已
  声明、CLI 与 flow 校验器可用。设计成独立脚本而非 pytest，因为本仓测试套件是仓库绑定
  的（读 pyproject/CHANGELOG/docs），且 `tests/__init__.py` 会让 pytest 把仓库根放进
  `sys.path`，对 wheel 跑套件只会测到源码树。
- `tests/test_release_metadata.py`：版本门禁。pyproject / `automation_core.__version__`
  / CHANGELOG 标题一致，声明的包资源存在，tag 与版本匹配。
- `tests/test_imports.py` 的版本字面量断言改为只断言 `__version__` 非空，精确一致性统一
  由 `tests/test_release_metadata.py` 保证，避免版本号散落多处。

## 0.5.0

发布准备完成于 2026-10-18，验证基线见 `docs/development.md` §10.6。

新增（additive，无破坏性变更）：

- `adapters.uia2`：uiautomator2 Android adapter（`Uia2Session`/`Uia2Element`/
  `Uia2SessionFactory`、`by` 词表、`screenshot`/`page_source` artifact）；语义快照
  `semantic_snapshot`、`scroll_into_view`（含 `settle`）、`press_back`/`press_home`
  与 `@N` ref 选择器随演进波 2 一并交付。
- `automation_core.observations`：`ScreenBounds`/`ScreenElement`/`ScreenSnapshot`。
- `adapters.phone_playwright`：`semantic_snapshot` 动作 data 由 markdown 字符串改为
  dict（`to_dict` 结构 + `markdown` 键）。
- `WorkflowStep.artifact(..., capture_on="always"|"failure")`：声明式失败捕获；
  省略参数时行为与历史完全一致。
- CLI 新增子命令 `run-yaml`（YAML 声明式流，flow schema v1，`${param.*}`/`${env.*}`
  插值）与 `report-view`（单文件离线 HTML 报告）。
- `automation_runner.viewer`：prepared artifacts 新增 `text_content` 字段；
  `.md/.json/.txt/.xml` artifact 由 `linked` 改为内嵌 `embedded`。
- 可选依赖 extra `automation-kit[yaml]`（PyYAML）。

未变更：`WorkflowStatus`/`StepStatus` 取值、report schema v2、flow schema v1、
`report-schema-v1.json` 继续冻结。

配套：app 仓依赖范围同步为 `automation-kit>=0.5.0,<0.6.0`。

## 0.4.0

2026-09-03（本文件自 0.5.0 起维护，此条依据 `docs/development.md` §10.4 回填）。

- runtime 模型收口：`ExecutionContext`/`ExecutionFailure`/step result 模型、
  Provider V2 单一异步入口、`WorkflowRuntime`、runtime-owned `ReportCollector` 与
  report schema v2 成为唯一路径；legacy `ManagedWorkflow`/`LegacyWorkflowResult`/
  `run_workflow_steps`/`WorkflowRunner`/task runner/action batch/`RunState`/task event
  模型删除，CLI 与 examples 只产出 report schema v2。
