<!-- markdownlint-disable-file MD033 MD045 -->
<div align="center">

# AutomationKit

**Deterministic Runtime Primitives, Task Lifecycle & Cross-Platform Workflow Engine for Web and Mobile Automation**

[![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Core_%26_Runner_Decoupled-orange.svg?style=flat-square)](automation_core/)
[![Drivers](https://img.shields.io/badge/Drivers-Selenium_%7C_Appium_%7C_UIAutomator2-blue.svg?style=flat-square)](adapters/)
[![Ecosystem](https://img.shields.io/badge/Ecosystem-Slidex_Visual_Integration-purple.svg?style=flat-square)](https://github.com/dengyie/slidex)
[![Tests](https://img.shields.io/badge/tests-932%20passed-brightgreen.svg?style=flat-square)]()

[English](./README.md) · [简体中文](./README.zh-CN.md) · [Core Features](#core-features) · [Architecture](#system-architecture) · [Capability Platform](#capability-platform) · [Workflow Runtime](#workflow-shape--runner-cli) · [Ecosystem](#ecosystem-topology)

<br>

<p align="center">
  <b>Terminates flaky executions, leaky driver state, and untyped error cascades across website and mobile automation pipelines.</b><br>
  Engineered around deterministic Python-first runtime contracts with bounded retry backoffs, platform-aware driver adapters, structured event auditing, and capability manifests.<br>
  Delivers decoupled runner CLI orchestration, report schema v2 event ordering, hot-swappable visual solvers (Slidex integration), and headless mock regression suites.
</p>

</div>

---

## Motivation & Architecture Comparison

Traditional browser and mobile automation scripts often couple domain workflows, driver lifecycles, element locators, and fragile retry loops into unmaintainable scripts. When drivers freeze, networks fluctuate, or AI solvers are introduced, standard scripts cascade into unrecoverable states:

| Evaluation Dimension | AutomationKit Platform | Ad-Hoc Selenium/Appium Scripts | Monolithic Test Frameworks |
| :--- | :--- | :--- | :--- |
| **Runtime Determinism** | Atomic task lifecycles with distinct failure, cancellation, and exit contracts | Unmanaged exception loops prone to hangs and unhandled crashes | Coarse pass/fail verdicts conflating logic errors with runtime panics |
| **Driver Resource Safety**| Strict driver context scoping with automated cleanup preventing leaks | Frequently leaves orphaned Chrome or ADB processes exhausting handles | Relies on global test fixtures that bleed state across test iterations |
| **Bounded Retry Backoff** | Deadline-bounded backoff strategies preventing infinite loops | Unbounded `while True` or blind `time.sleep` calls stalling threads | Simple blind retries failing to distinguish step-level retryability |
| **High-Level Capabilities**| Dynamic capability manifests decoupling business logic from solver SDKs | Hardcodes third-party solver SDKs directly into automation steps | Heavy plugin ecosystems difficult to orchestrate in headless containers |
| **Offline Testability** | 310 mock regression tests executing in under a second without hardware | Requires connected mobile devices, real browsers, and live networks | Requires heavyweight emulator containers with prolonged CI build times |

---

## Core Features

| Module | Feature Highlight | Technical Implementation & Advantage |
| :--- | :--- | :--- |
| **Deterministic Primitives** | Contract-driven execution | Enforces strict boundaries across task lifecycles, execution contexts, bounded retries, driver ownership, action batches, and artifact stores. |
| **Decoupled Architecture** | Separation of Core & Runner | `automation_core` encapsulates runtime contracts and capability registries; `automation_runner` manages workflow discovery, config resolution, and CLI. |
| **Capability Platform** | Extensible plug-and-play solvers | Connects external solvers (e.g. Slidex visual puzzle and text verification solvers) via `CapabilityRegistry` without polluting core dependencies. |
| **Platform-Aware Adapters** | Universal Web and mobile drivers | Provides driver contracts seamlessly adapting Selenium Web and Appium (supporting Android UIAutomator2 and iOS XCUITest gestures). |
| **Report Schema v2** | Strict event-ordered audit reports | Generates machine-readable execution reports maintaining chronological event ordering; exits with code `130` on cancellation. |
| **Multi-Tier Configuration**| Precedence-based parameter merging| Layers CLI flags over environment variables and JSON configs; validates type signatures before initializing workflow factories. |
| **Credential Redaction** | Safeguards sensitive data in logs | Built-in redaction pipes scrub secrets from traces; `ArtifactStore` standardizes screenshots, logs, and network dumps for post-run analysis. |
| **Ultra-Fast Mock Suite** | 100% offline unit test suite | Ships with 310 deterministic test cases running in under 1 second without Chrome, Appium, ADB, Android devices, or internet access. |

---

## System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                     Application & Workflow Layer                       │
│   automation-app-damai · automation-app-dianping · Custom Workflows    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Invokes create_workflow() factory
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            automation_runner (Execution Engine & CLI Layer)            │
│  ┌──────────────────────┐ ┌──────────────────────┐ ┌────────────────┐  │
│  │ automation-runner CLI│ │ Parameter Resolution │ │ Report Schema  │  │
│  │ --dry-run / --live   │ │ CLI > ENV > Config   │ │ v2 JSON Audit  │  │
│  └──────────┬───────────┘ └──────────┬───────────┘ └────────┬───────┘  │
│             │                        │                      │          │
│             ▼                        ▼                      ▼          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │         automation_core (Deterministic Contracts & Primitives)   │  │
│  │  Lifecycle · Bounded Retries · Driver Ownership · Redaction Store│  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────────────┼──────────────────────────────────┘
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        ▼                                                           ▼
┌────────────────────────────────┐          ┌────────────────────────────────┐
│   Capability Platform          │          │   Platform-Aware Adapters      │
│  ├─ CapabilityRegistry         │          │   ├─ Selenium (Chrome/Firefox) │
│  ├─ CapabilityExecutor         │          │   ├─ Appium (UIAutomator2)     │
│  └─ Dynamic Slidex Solver      │          │   └─ XCUITest (iOS Gestures)   │
└────────────────────────────────┘          └────────────────────────────────┘
```

---

## Capability Platform

Applications invoke high-level capabilities through the core contract without importing provider internals directly:

```python
from automation_core.capabilities import (
    CapabilityExecutor,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
)
from automation_core.execution import ExecutionContext

# 1. Initialize registry and register capability providers
registry = CapabilityRegistry()
registry.register(visual_provider)

# 2. Establish execution context
context = ExecutionContext(
    run_id="run-001",
    task_id="task-001",
    workflow_name="login-flow",
)

# 3. Dispatch execution request
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

Providers declare a `CapabilityManifest`, expose `execution_profile(request)`, and implement an asynchronous `execute(request, context)` method. Slidex provides the recommended visual solver integration via `slidex.integrations.automation_kit.SlidexVisualCapability`.

---

## Workflow Shape & Runner CLI

Workflows live outside `automation_core`. A workflow factory returns an object with a `run()` method:

```python
from examples.damai_web import build_steps, create_workflow

workflow = create_workflow(
    session_factory=make_session,
    url="https://example.test/damai",
)
result = workflow.run()  # Returns automation_core.execution.WorkflowResult

for step in result.steps:
    print(step.step_name, step.status.value)
```

### Common CLI Commands

```bash
# Inspect built-in workflows (dry-run mode / JSON metadata)
automation-runner examples --dry-run
automation-runner examples --json

# Run workflow and export structured JSON report
automation-runner run damai-web-smoke --json --url https://example.test/damai

# Execute live browser workflow with driver factory
automation-runner run damai-web-smoke --live --json \
  --factory tests.runner.fixtures:make_session \
  --url https://example.test/damai

# Dynamically load external workflow factory with parameters
automation-runner run --workflow-factory my_package.workflow:create_workflow \
  --json \
  --param account=test-user \
  --param city=shanghai

# Inspect packaged machine-readable report schema contract
automation-runner report-schema --version 1
```

---

## Ecosystem Topology

- **Core Primitives**: [dengyie/automation-kit](https://github.com/dengyie/automation-kit)
- **Visual Intelligence**: [dengyie/slidex](https://github.com/dengyie/slidex)
- **Damai App Automation**: [dengyie/automation-app-damai](https://github.com/dengyie/automation-app-damai)
- **Dianping App Automation**: [dengyie/automation-app-dianping](https://github.com/dengyie/automation-app-dianping)

---

## Testing & Quality Assurance

The default test suite runs completely offline without requiring Chrome, Appium, ADB, or physical hardware:

```bash
# Install dependencies
poetry install

# Run 310 regression tests and boundary verifications
pytest tests/
```

---

## Contributing & License

Contributions are welcome. Please ensure all tests pass prior to submitting changes:

```bash
pytest tests/
```

Licensed under the [MIT License](LICENSE).
