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

复查（2026-10-19）修掉发布门禁自身的一个假绿并收紧自证：

- `publish.yml` 的 `verify-from-index` 补 `always()`。实测 `needs` 里的依赖被 skip 时，
  依赖方 job 也会被 skip（哪怕它自己的 `if` 为真）；tag 路径上 `publish-testpypi` 恒被
  skip，所以原先这道「发布后从包源装一遍」的最关键验证会在最需要它的时刻静默不执行，
  而 run 仍报成功。
- `scripts/smoke_installed_package.py` 收紧：`automation_runner` 也断言来自 site-packages；
  CLI 子进程固定 cwd（`python -m` 会把 cwd 放进 `sys.path`，从仓库根跑时会导入源码树）；
  console script 改为真的执行 `automation-runner --version`；`yaml` extra 增加「真能解析
  最小 YAML 流」的功能检查（缺 PyYAML 明确失败而非静默跳过）；flow 校验器增加反向对照
  （必须拒绝非法流）。
- `ci.yml` 的 `package` job 改为 `pip install "<wheel>[yaml]"`，让 pip 真正消费 extra
  元数据（原先是手工补装 pyyaml，会掩盖 extra 声明错误）。
- `tests/test_release_metadata.py` 新增三个门禁测试：tag 门禁确实读 `GITHUB_REF_*` 且会因
  错误 tag 失败；`verify-from-index` 的 `if` 必须带 `always()`；所有 workflow 调用冒烟时
  必须传期望版本（漏传等于版本门禁不存在）。
- 制品矩阵补上 sdist 腿：发布上传 sdist + wheel 两种制品，但原先只有 wheel 被安装过。
  `ci.yml` 的 `package` job 改为 `artifact: [wheel, sdist]` 矩阵（构建步骤不能加 `--wheel`）；
  `verify-from-index` 增加 `--no-binary automation-kit` + 独立 venv 的源码构建腿（共用
  解释器时 pip 判定「已满足」而不构建，这条腿会沦为空跑）。实测当前 `0.5.0` sdist 本身
  无问题（tarball 含 4 个声明资源、干净 venv 安装成功并由声明带出 pyyaml、自证 8 项全 ok），
  补的是「每次 push 都会检查」这件事；两条不变量由
  `test_ci_package_job_installs_both_artifact_kinds` 与
  `test_verify_job_installs_published_sdist_too` 钉住。
- 发布定位澄清（文档，无代码行为变更）：核实消费侧真实取用方式后确认——本地与四仓 CI
  一律 sibling 检出 + `pip install -e ../automation-kit`，pyproject 里的
  `automation-kit>=0.5.0,<0.6.0` 从未被任何包源解析。故**上架包源是可选动作、不是缺口**：
  `v0.5.0` 作为仓库内版本基线属既定状态（tag 已打在发布基线上）。`docs/development.md`
  §10.8（PyPI 配置标为可选）、§11.3 阶段 3（从交付要求降级为可选，含核实依据）、§14 第 8 条
  同步更新；publish 机制与 `package` 门禁保留，需要对外分发时配好凭据走一次 tag 即可。

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
