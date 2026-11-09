<!-- markdownlint-disable-file MD033 MD045 -->
<div align="center">

# AutomationKit

**面向 Web 与移动端自动化的高可用确定性运行时基元、任务生命周期与工作流编排引擎**

[![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Core_%26_Runner_Decoupled-orange.svg?style=flat-square)](automation_core/)
[![Drivers](https://img.shields.io/badge/Drivers-Selenium_%7C_Appium_%7C_UIAutomator2-blue.svg?style=flat-square)](adapters/)
[![Ecosystem](https://img.shields.io/badge/Ecosystem-Slidex_Visual_Integration-purple.svg?style=flat-square)](https://github.com/dengyie/slidex)
[![Tests](https://img.shields.io/badge/tests-310%20passed-brightgreen.svg?style=flat-square)]()

[English](./README.md) · [简体中文](./README.zh-CN.md) · [核心特性](#核心特性) · [系统架构](#系统架构全景) · [能力平台](#能力平台架构) · [工作流编排](#工作流结构与-runner-cli) · [生态拓扑](#生态拓扑与协同项目)

<br>

<p align="center">
  <b>彻底告别复杂 Web 与 Android 自动化脚本中普遍存在的偶发假死、驱动资源泄漏与非确定性异常。</b><br>
  严格基于 Python 运行时基元构建，解耦任务生命周期、有界重试退避算法、标准化驱动契约与结构化事件日志。<br>
  提供标准化的 Runner CLI 编排执行器、Report Schema v2 事件排序契约、与 Slidex 视觉解题能力的无缝动态挂载，以及 100% 离线的极速 Mock 回归测试套件。
</p>

</div>

---

## 痛点与架构对比

传统的自动化测试与抓取脚本常将业务逻辑、浏览器驱动、元素定位与重试机制混杂在一起。一旦底层驱动崩溃、出现网络抖动或引入 AI 决策，整体链路便极易陷入雪崩：

| 评估维度 | AutomationKit 核心引擎 | 散落的 Selenium/Appium 脚本 | 传统一体化测试框架 |
| :--- | :--- | :--- | :--- |
| **运行时确定性** | 状态机严格管控生命周期，执行、取消与失败状态具有强原子性 | 缺乏统一状态机，脚本在未捕获异常时容易挂死 | 粗粒度的 Pass/Fail，无法区分逻辑中断与环境崩溃 |
| **驱动资源生命周期**| 严格的驱动上下文生命周期托管，退出自动回收，绝不残留僵尸进程 | 经常残留孤儿 Chrome 或 ADB 僵尸连接，耗尽句柄 | 依赖全局夹具管理，多用例并发时极易互相污染 |
| **重试与退避机制** | 强时限守护的自适应有界退避策略，杜绝死循环 | 盲目 `while True` 或死循环 `sleep`，导致线程卡死 | 简单的全局重试，无法按步骤或错误特征做策略路由 |
| **高阶能力解耦** | 基于标准 Capability 契约动态解析，业务无需直连 AI 底层实现 | 强制硬编码集成三方推理 SDK，导致依赖极度臃肿 | 插件机制沉重，难以在轻量容器中无感组合 |
| **离线测试质量** | 310 项全量 Mock 回归，零硬件依赖可在 1 秒内执行完毕 | 强依赖真机或实际浏览器，CI 执行耗时动辄数十分钟 | 依赖体积庞大的模拟器镜像，维护成本极高 |

---

## 核心特性

| 模块 | 特性亮点 | 技术实现与工程优势 |
| :--- | :--- | :--- |
| **确定性运行时基元** | 强契约的状态生命周期 | 严格解耦任务生命周期、执行上下文、有界重试、驱动契约、动作批处理、脱敏过滤器与结构化制品存储。 |
| **双层架构解耦设计** | `core` 与 `runner` 职责分离 | `automation_core` 仅承载通用协议与能力契约；`automation_runner` 提供工作流收集器、动态配置加载与 CLI。 |
| **标准化能力平台** | 动态注册与统一执行器 | 通过 `CapabilityRegistry` 与 `CapabilityExecutor` 接入高阶能力（如接入 Slidex 视觉拼图/文字验证码识别），业务无需感知底层实现。 |
| **平台感知驱动适配** | Web 与移动端无缝协同 | 提供平台感知的驱动适配层，完美兼容 Selenium Web 以及 Appium（Android UIAutomator2 / iOS XCUITest 复杂手势）。 |
| **Report Schema v2** | 严格事件时序审计日志 | 规范化生成机器可读的结构化执行报告，严格保障事件发射顺序，对取消状态赋予 `exit code 130` 与独立的 `cancelled` 标头。 |
| **多源参数动态分层** | 命令行/环境/配置分级覆盖 | 支持从 CLI 覆盖、系统环境变量以及 JSON 字符串中提取工作流参数，类型预检机制确保在加载工厂前尽早暴露配置错误。 |
| **敏捷脱敏与制品存证**| 敏感凭证过滤与按需排查 | 内置动态脱敏机制阻断密钥落地；结构化 ArtifactStore 统一收敛截屏、页面快照与日志，保障排障取证可溯。 |
| **极速轻量回归基座** | 零外部依赖的全量自测 | 包含 310 个高密度单元测试，无需真实 Chrome、Appium、ADB 或设备网络，1 秒内完成全量质量门禁。 |

---

## 系统架构全景

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        业务应用与工作流编排层                          │
│   automation-app-damai · automation-app-dianping · 自定义业务脚本      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 调用工作流工厂 create_workflow()
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               automation_runner (执行引擎与 CLI 编排层)                │
│  ┌──────────────────────┐ ┌──────────────────────┐ ┌────────────────┐  │
│  │ automation-runner CLI│ │ 工作流收集器与参数解析│ │ Report Schema  │  │
│  │ --dry-run / --live   │ │ CLI > ENV > Config   │ │ v2 机器可读报告│  │
│  └──────────┬───────────┘ └──────────┬───────────┘ └────────┬───────┘  │
│             │                        │                      │          │
│             ▼                        ▼                      ▼          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │          automation_core (确定性运行时契约与核心基元)            │  │
│  │  任务上下文 · 有界退避重试 · 驱动会话所有权 · 动态脱敏 · 制品存证 │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────────────┼──────────────────────────────────┘
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        ▼                                                           ▼
┌────────────────────────────────┐          ┌────────────────────────────────┐
│  Capability 开放能力平台       │          │   平台感知底层驱动适配层       │
│  ├─ CapabilityRegistry         │          │   ├─ Selenium (Web Chrome/FF)  │
│  ├─ CapabilityExecutor         │          │   ├─ Appium (UIAutomator2)     │
│  └─ 挂载 Slidex 智能视觉解题   │          │   └─ XCUITest (iOS 原生手势)   │
└────────────────────────────────┘          └────────────────────────────────┘
```

---

## 能力平台架构

业务应用通过核心契约透明调用高阶扩展能力（如验证码识别、图像分割、语义模型），无需直接导入下游具体实现库：

```python
from automation_core.capabilities import (
    CapabilityExecutor,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
)
from automation_core.execution import ExecutionContext

# 1. 初始化能力注册表并注册 Provider
registry = CapabilityRegistry()
registry.register(visual_provider)

# 2. 创建执行上下文
context = ExecutionContext(
    run_id="run-001",
    task_id="task-001",
    workflow_name="login-flow",
)

# 3. 统一分发执行能力请求
executor = CapabilityExecutor(CapabilityResolver(registry))
result = await executor.execute(
    CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters={
            "challenge_type": "image_text",
            "context": "image_bytes",
            "image_bytes": image_bytes,
        },
    ),
    context,
)
```

Providers 需声明 `CapabilityManifest`，暴露 `execution_profile(request)`，并实现异步 `execute(request, context)` 接口。

---

## 工作流结构与 Runner CLI

业务工作流保持在 `automation_core` 外部，工作流工厂返回具备 `run()` 方法的实例对象：

```python
from examples.damai_web import build_steps, create_workflow

workflow = create_workflow(
    session_factory=make_session,
    url="https://example.test/damai",
)
result = workflow.run()  # 返回 automation_core.execution.WorkflowResult

for step in result.steps:
    print(step.step_name, step.status.value)
```

### 常用 CLI 操作示例

```bash
# 查看内置工作流列表（干跑模式 / JSON 元数据）
automation-runner examples --dry-run
automation-runner examples --json

# 运行指定工作流并输出结构化 JSON 报告
automation-runner run damai-web-smoke --json --url https://example.test/damai

# 启用真实环境驱动会话执行
automation-runner run damai-web-smoke --live --json \
  --factory tests.runner.fixtures:make_session \
  --url https://example.test/damai

# 动态加载外部包的工作流工厂并传递多键值参数
automation-runner run --workflow-factory my_package.workflow:create_workflow \
  --json \
  --param account=test-user \
  --param city=shanghai

# 打印规范化的机器可读报告契约模式
automation-runner report-schema --version 1
```

---

## 生态拓扑与协同项目

- **核心规范**：[dengyie/automation-kit](https://github.com/dengyie/automation-kit)
- **视觉能力集成**：[dengyie/slidex](https://github.com/dengyie/slidex)
- **大麦网实战应用**：[dengyie/automation-app-damai](https://github.com/dengyie/automation-app-damai)
- **大众点评实战应用**：[dengyie/automation-app-dianping](https://github.com/dengyie/automation-app-dianping)

---

## 质量验证与自动化测试

本项目默认测试套件严格解耦硬件环境，不需要 Chrome、Appium、ADB 或真实网络：

```bash
# 安装依赖
poetry install

# 执行全量单元测试与架构边界校验 (310 项全绿)
pytest tests/
```

---

## 参与贡献与许可证

欢迎提交 Issue 与 Pull Request！在提交代码变更前，请确保全量测试套件执行通过：

```bash
pytest tests/
```

本项目采用 [MIT License](LICENSE) 开源协议。
