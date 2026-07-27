import logging
from typing import List, Dict, Any
from agno.tools.duckduckgo import DuckDuckGoTools
from src.tools.smart_pandas import SmartPandasTools

_log = logging.getLogger(__name__)

# PythonTools and FileTools are intentionally absent — they allow arbitrary
# filesystem access / code execution and must never be instantiated via an
# unauthenticated HTTP payload.
_SAFE_TOOLS = {"DuckDuckGoTools", "SmartPandasTools"}


def load_dynamic_tools(tools_json: List[Dict[str, Any]]) -> List[Any]:
    """
    Instantiates Agno tools from a JSON list.
    Only tools in _SAFE_TOOLS are allowed; all others are silently skipped.
    """
    agent_tools = []
    for tool_config in tools_json:
        name = tool_config.get("name")
        kwargs = tool_config.get("kwargs", {})

        if name not in _SAFE_TOOLS:
            _log.warning("Skipping unknown/unsafe tool: %s", name)
            continue

        if name == "DuckDuckGoTools":
            agent_tools.append(DuckDuckGoTools(**kwargs))
        elif name == "SmartPandasTools":
            agent_tools.append(SmartPandasTools(**kwargs))

    return agent_tools
