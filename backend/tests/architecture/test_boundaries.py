from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"


def test_legacy_ambiguous_packages_are_not_reintroduced():
    for name in ("services", "skills", "mcp", "ws"):
        assert not (APP_ROOT / name).exists(), f"Use the responsibility-specific package instead of app/{name}"


def test_production_runtime_does_not_import_evaluation_layer():
    for path in APP_ROOT.rglob("*.py"):
        if "evaluation" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "from app.evaluation" not in text
        assert "import app.evaluation" not in text


def test_langgraph_is_primary_customer_service_orchestrator():
    graph_root = APP_ROOT / "agent" / "graph"
    assert (graph_root / "workflow.py").exists()
    assert (graph_root / "state.py").exists()
    assert (graph_root / "routes.py").exists()

    workflow = (graph_root / "workflow.py").read_text(encoding="utf-8")
    runtime = (APP_ROOT / "agent" / "runtime.py").read_text(encoding="utf-8")
    assert "StateGraph(CustomerServiceState)" in workflow
    assert 'graph.add_conditional_edges(' in workflow
    assert '"execute_tools"' in workflow
    assert '"handoff"' in workflow
    assert "run_customer_service_graph" in runtime
    assert "for step in range" not in runtime
