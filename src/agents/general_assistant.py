from agno.tools.duckduckgo import DuckDuckGoTools
from src.tools.smart_pandas import SmartPandasTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.skills import Skills, LocalSkills
from pathlib import Path

# Patch FileTools to safely read .docx and prevent reading .xlsx binaries
_orig_read_file = FileTools.read_file
def _patched_read_file(self, file_name: str, encoding: str = "utf-8") -> str:
    name_lower = file_name.lower()
    
    if ".docx" in name_lower:
        try:
            from docx import Document
            doc = Document(file_name)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            return f"ERRO ao ler DOCX internamente: {str(e)}"
            
    if ".xlsx" in name_lower or ".xls" in name_lower:
        return (
            "ERRO: Não utilize read_file para planilhas de Excel. "
            "Use a ferramenta create_pandas_dataframe com engine='openpyxl'."
        )
        
    return _orig_read_file(self, file_name, encoding)
FileTools.read_file = _patched_read_file

from src.agents._base import create_base_agent
from src.config.settings import settings
from src.knowledge.base import get_knowledge_base

from src.tools.dynamic_loader import load_dynamic_tools

def get_general_assistant(user_id: str = "default_user", tools_json: list = None):
    """
    Retorna uma instância do General Assistant configurada com memória e conhecimento.
    Aceita user_id para isolamento dinâmico da base de memórias (multitenancy).
    Aceita tools_json para carregar as permissões do sistema.
    """
    # Preparar diretórios para ferramentas avançadas
    PYTHON_WORKSPACE = Path("tmp/workspace")
    PYTHON_WORKSPACE.mkdir(parents=True, exist_ok=True)
    
    SKILLS_DIR = Path("src/skills")
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    
    if tools_json is not None:
        agent_tools = load_dynamic_tools(tools_json)
    else:
        # Default fallback
        agent_tools = [
            DuckDuckGoTools(),
            SmartPandasTools(),
            FileTools(base_dir=Path(".")),
            PythonTools(base_dir=Path(".")),
        ]
    
    return create_base_agent(
        name="General Assistant",
        user_id=user_id,
        instructions=[
            "Você é o assistente principal da Liderando com IA.",
            "Ajude o usuário com informações gerais, resumos e interações produtivas.",
            "Você tem acesso a ferramentas de pesquisa na web, manipulação de dados (Pandas) e leitura de arquivos locais.",
            # ── MEMÓRIA AGÊNTICA ──────────────────────────────────────────────────────
            "REGRAS DE MEMÓRIA (siga rigorosamente):",
            "  QUANDO SALVAR NA MEMÓRIA:",
            "    - O usuário fala algo pessoal sobre si mesmo de forma explícita.",
            "    - Exemplos que DEVEM ser salvos: nome, idade, profissão, cidade, interesses pessoais (ex: 'gosto de filosofia'),",
            "      hobbies, hábitos, metas de vida, preferências de comunicação.",
            "    - Se o usuário disser 'meu nome é X', 'eu trabalho com Y', 'gosto de Z', 'prefiro W' → SALVE IMEDIATAMENTE.",
            "  QUANDO NÃO SALVAR:",
            "    - O usuário enviou um arquivo, planilha ou documento para análise. NUNCA extraia memórias de arquivos.",
            "    - Dados dentro de documentos, planilhas, tabelas ou qualquer conteúdo de arquivo → NUNCA salve.",
            "    - Metadados internos: nomes de ferramentas, caminhos de arquivo, status de execução → NUNCA salve.",
            "    - Em caso de dúvida: NÃO salve. Prefira poupar memória a salvar algo irrelevante.",
            # ── PLANILHAS EXCEL ───────────────────────────────────────────────────────
            "REGRA CRÍTICA PARA PLANILHAS EXCEL (.xlsx/.xls):",
            "  - SEMPRE use create_pandas_dataframe com create_using_function='read_excel'",
            "  - O parâmetro OBRIGATÓRIO é 'io' (NÃO filepath_or_buffer)",
            "  - SEMPRE inclua engine='openpyxl' nos function_parameters",
            "  - NUNCA use read_csv ou read_file para arquivos .xlsx",
            "  - Exemplo: {dataframe_name: 'df', create_using_function: 'read_excel', function_parameters: {io: 'caminho.xlsx', engine: 'openpyxl'}}",
            "  - Para operar no dataframe criado, use run_dataframe_operation com operation_parameters (dict obrigatório, mesmo que vazio {}).",
            "Para arquivos .docx, use a ferramenta read_file no caminho .md fornecido.",
            "Se o usuário pedir cálculos complexos, simulações avançadas ou análises exatas com planilhas e números: CRIE UM SCRIPT PYTHON",
            "Sempre que precisar garantir a precisão matemática ou executar lógica customizada, USE PythonTools para formatar a resposta.",
            "Explore suas SKILLS (Habilidades) disponíveis se o usuário solicitar algo que exija contexto customizado.",
        ],
        tools=agent_tools,
        skills=Skills(loaders=[LocalSkills(str(SKILLS_DIR))]),
        knowledge=get_knowledge_base(),
        # add_datetime_to_instructions=True,
    )

# Instância padrão para exportação
general_assistant = get_general_assistant()
