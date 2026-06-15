def test_automation_core_imports():
    import automation_core

    assert automation_core.__version__ == "0.1.0"


def test_example_workflow_factories_import_without_live_dependencies():
    from examples.damai_android import create_workflow as create_android_workflow
    from examples.damai_web import create_workflow as create_web_workflow

    assert callable(create_web_workflow)
    assert callable(create_android_workflow)
