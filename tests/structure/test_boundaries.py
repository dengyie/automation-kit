from pathlib import Path
import importlib


ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = ROOT / "automation_core"


def _read_core_text():
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in CORE_ROOT.rglob("*.py")
    )


def test_core_has_no_business_or_concrete_driver_terms():
    core_text = _read_core_text().lower()

    forbidden = [
        "damai",
        "dianping",
        "cn.damai",
        "com.dianping",
        "target_url",
        "if_commit_order",
        "webdriver",
        "selenium",
        "appium",
    ]

    for term in forbidden:
        assert term not in core_text


def test_core_actions_are_generic():
    core_actions = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "automation_core" / "actions").rglob("*.py")
    ).lower()

    for term in [
        "damai",
        "dianping",
        "selenium",
        "appium",
        "target_url",
        "webdriver",
    ]:
        assert term not in core_actions


def test_example_shell_readmes_exist():
    assert (ROOT / "examples" / "damai_web" / "README.md").exists()
    assert (ROOT / "examples" / "damai_android" / "README.md").exists()


def test_adapter_and_example_shells_import():
    modules = [
        "adapters",
        "adapters.selenium",
        "adapters.appium",
        "examples",
        "examples.damai_web",
        "examples.damai_android",
    ]

    for module in modules:
        assert importlib.import_module(module)
