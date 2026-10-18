# Changelog

已发布版本历史。架构与开发规范在 `docs/development.md`，本文件不承担规范职责。

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
