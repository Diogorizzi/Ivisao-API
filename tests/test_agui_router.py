# tests/test_agui_router.py
from unittest.mock import MagicMock

from src.agui.router import build_agui_router


def _make_agent(name: str):
    """Create a minimal agent mock with a .name attribute."""
    agent = MagicMock()
    agent.name = name
    return agent


def test_build_agui_router_registers_routes():
    """build_agui_router must register POST + GET routes for each agent."""
    agent = _make_agent("Test Agent")
    router = build_agui_router([agent])

    route_paths = [r.path for r in router.routes]
    assert "/agui/test-agent/agui" in route_paths
    assert "/agui/test-agent/status" in route_paths


def test_build_agui_router_multiple_agents():
    """Routes are registered independently for each agent without conflicts."""
    agents = [_make_agent("Alpha"), _make_agent("Beta")]
    router = build_agui_router(agents)

    route_paths = [r.path for r in router.routes]
    assert "/agui/alpha/agui" in route_paths
    assert "/agui/alpha/status" in route_paths
    assert "/agui/beta/agui" in route_paths
    assert "/agui/beta/status" in route_paths
    assert len(route_paths) == 4
