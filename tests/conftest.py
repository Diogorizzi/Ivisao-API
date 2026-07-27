"""
Pytest configuration and fixtures for tests.
Mocks external dependencies that may not be available in test environment.
"""
import sys
import types
from unittest.mock import MagicMock

# List of all agno modules that need to be mocked
AGNO_MODULES = [
    'agno',
    'agno.agent',
    'agno.db',
    'agno.db.postgres',
    'agno.db.sqlite',
    'agno.db.sqlite.sqlite',
    'agno.knowledge',
    'agno.knowledge.document',
    'agno.knowledge.embedder',
    'agno.knowledge.embedder.google',
    'agno.knowledge.knowledge',
    'agno.knowledge.reader',
    'agno.knowledge.reader.base',
    'agno.memory',
    'agno.models',
    'agno.models.anthropic',
    'agno.models.aws',
    'agno.models.aws.bedrock',
    'agno.models.google',
    'agno.models.groq',
    'agno.models.openai',
    'agno.models.openrouter',
    'agno.models.vertexai',
    'agno.models.vertexai.claude',
    'agno.os',
    'agno.os.config',
    'agno.os.interfaces',
    'agno.os.interfaces.agui',
    'agno.os.interfaces.agui.utils',
    'agno.skills',
    'agno.tools',
    'agno.tools.duckduckgo',
    'agno.tools.file',
    'agno.tools.function',
    'agno.tools.python',
    'agno.utils',
    'agno.utils.log',
    'agno.vectordb',
    'agno.vectordb.chroma',
    'chromadb',
]

# Mock all agno modules
for module_name in AGNO_MODULES:
    sys.modules[module_name] = MagicMock()


def _real_get_agent_by_id(agent_id, agents=None, db=None, registry=None, version=None, create_fresh=False):
    """Minimal real implementation matching agno.os.utils.get_agent_by_id behaviour."""
    if agent_id is None:
        return None
    if agents:
        for agent in agents:
            if agent.id == agent_id:
                if create_fresh:
                    fresh = agent.deep_copy()
                    fresh.team_id = None
                    fresh.workflow_id = None
                    return fresh
                return agent
    return None


# Replace agno and agno.os mocks with real ModuleType objects so that
# `import agno.os.utils` resolves via sys.modules rather than MagicMock.__getattr__.
# All other agno sub-mocks remain as MagicMock via sys.modules, preserving
# existing test behaviour.
_agno_mod = types.ModuleType('agno')
_agno_os_mod = types.ModuleType('agno.os')
_agno_os_utils_stub = types.ModuleType('agno.os.utils')
_agno_os_utils_stub.get_agent_by_id = _real_get_agent_by_id

# Wire up parent→child attribute references so attribute-based access also works
_agno_mod.os = _agno_os_mod
_agno_os_mod.utils = _agno_os_utils_stub

# Copy MagicMock child attributes from the old agno/agno.os mocks onto the new modules
# so any code doing `agno.agent`, `agno.tools`, etc. still gets MagicMocks.
for _attr in ['agent', 'db', 'knowledge', 'memory', 'models', 'skills', 'tools', 'utils', 'vectordb']:
    setattr(_agno_mod, _attr, sys.modules.get(f'agno.{_attr}', MagicMock()))
for _attr in ['config', 'interfaces']:
    setattr(_agno_os_mod, _attr, sys.modules.get(f'agno.os.{_attr}', MagicMock()))

sys.modules['agno'] = _agno_mod
sys.modules['agno.os'] = _agno_os_mod
sys.modules['agno.os.utils'] = _agno_os_utils_stub
