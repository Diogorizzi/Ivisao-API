import os
import uuid
from typing import List, Optional, Any
from pathlib import Path
from agno.agent import Agent
from src.config.llm_providers import get_model
from src.config.database import get_db
from src.memory.user_memory import get_memory_manager
from src.tools.file_parser import convert_file_to_text

def filter_unsupported_files(run_input: Any, **kwargs):
    """
    Remove arquivos não suportados do payload de anexos da LLM e os salva em disco.
    Para facilitar a vida do Agente, tentamos converter o arquivo para Markdown e 
    fornecemos o caminho do texto legível também.
    """
    if hasattr(run_input, "files") and run_input.files:
        supported_files = []
        arquivos_anexados = []
        
        # Cria a pasta de arquivos temporários
        tmp_dir = Path("tmp/files")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        
        for f in run_input.files:
            filename = getattr(f, "filename", "") or getattr(f, "name", "") or getattr(f, "filepath", "") or getattr(f, "url", "")
            if not filename:
                filename = f"file_{uuid.uuid4().hex[:8]}"
            
            # DEBUG: Log what we receive from Agno
            print(f"[HOOK DEBUG] filename='{filename}', type={type(f).__name__}, attrs={[a for a in dir(f) if not a.startswith('_')]}")
                
            ext = Path(filename.split("?")[0]).suffix.lower()
            
            # OpenAI suporta nativamente PDF e imagens no chat message
            if ext in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                supported_files.append(f)
            else:
                # REVERT FAKE EXTENSIONS ADDED BY APP.PY
                # Remove extensões fake em loop (handles .xlsx.csv.csv, .xlsx.csv, etc.)
                # Continua removendo .csv e .txt do final até não ter mais extensão fake
                changed = True
                while changed:
                    changed = False
                    if filename.endswith(".xlsx.csv"):
                        filename = filename[:-4]  # Remove ".csv"
                        ext = ".xlsx"
                        changed = True
                    elif filename.endswith(".xls.csv"):
                        filename = filename[:-4]
                        ext = ".xls"
                        changed = True
                    elif filename.endswith(".docx.txt"):
                        filename = filename[:-4]
                        ext = ".docx"
                        changed = True
                    elif filename.endswith(".pptx.txt"):
                        filename = filename[:-4]
                        ext = ".pptx"
                        changed = True
                    elif filename.endswith(".csv.csv"):
                        filename = filename[:-4]  # Remove duplicate .csv
                        ext = ".csv"
                        changed = True
                
                print(f"[HOOK DEBUG] after revert: filename='{filename}', ext='{ext}'")
                
                # Extrair bytes do arquivo (pode vir como content ou via file object)
                content = getattr(f, "content", None)
                file_bytes = None
                
                if content is not None and isinstance(content, bytes):
                    file_bytes = content
                else:
                    # Tenta ler do file object interno (UploadFile do Starlette)
                    file_obj = getattr(f, "file", None)
                    if file_obj is not None:
                        try:
                            pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
                            if hasattr(file_obj, 'seek'):
                                file_obj.seek(0)
                            file_bytes = file_obj.read()
                            if hasattr(file_obj, 'seek'):
                                file_obj.seek(pos)
                        except Exception:
                            pass
                    
                    # Fallback: ler do filepath em disco
                    if not file_bytes:
                        filepath = getattr(f, "filepath", None)
                        if filepath:
                            try:
                                file_bytes = Path(filepath).read_bytes()
                            except Exception:
                                pass
                
                caminho = None
                md_caminho = None
                
                if file_bytes:
                    # Salva com a extensão CORRETA (já revertida)
                    clean_name = Path(filename).name
                    safe_filename = f"{uuid.uuid4().hex[:8]}_{clean_name}"
                    file_path = tmp_dir / safe_filename
                    file_path.write_bytes(file_bytes)
                    
                    try:
                        caminho = str(file_path.relative_to(Path.cwd()))
                    except ValueError:
                        caminho = str(file_path)
                    
                    # Tenta converter para Markdown usando MarkItDown
                    try:
                        md_text = convert_file_to_text(file_bytes, filename)
                        if md_text:
                            md_file_path = file_path.with_suffix(".md")
                            md_file_path.write_text(md_text, encoding="utf-8")
                            try:
                                md_caminho = str(md_file_path.relative_to(Path.cwd()))
                            except ValueError:
                                md_caminho = str(md_file_path)
                    except Exception as e:
                        print(f"Erro ao converter arquivo {filename} para texto: {e}")
                else:
                    caminho = "Caminho Indisponível (o arquivo não pôde ser lido localmente)"
                
                # Montar a instrução para o LLM
                if md_caminho and ext in {".docx", ".pptx", ".doc", ".pdf"}:
                    info = f"- Arquivo: {filename}\n  Caminho para Leitura (Use read_file aqui): {md_caminho}"
                elif ext in {".xlsx", ".xls"}:
                    info = (
                        f"- Arquivo Excel: {filename}\n"
                        f"  Caminho do Arquivo: {caminho}\n"
                        f"  AÇÃO OBRIGATÓRIA: Use create_pandas_dataframe com:\n"
                        f"    dataframe_name: \"df\"\n"
                        f"    create_using_function: \"read_excel\"\n"
                        f"    function_parameters: {{\"io\": \"{caminho}\", \"engine\": \"openpyxl\"}}"
                    )
                    if md_caminho:
                        info += f"\n  Prévia em Texto (para contexto rápido): {md_caminho}"
                else:
                    info = f"- Arquivo: {filename}\n  Caminho Original: {caminho}"
                    if md_caminho:
                        info += f"\n  Versão em Texto (Opcional): {md_caminho}"
                arquivos_anexados.append(info)
        
        run_input.files = supported_files
        
        if arquivos_anexados:
            aviso = (
                "O usuário enviou arquivos que foram pré-processados e salvos localmente.\n"
                "INSTRUÇÕES CRÍTICAS (SIGA ESTRITAMENTE, SEM EXCEÇÕES):\n\n"
                "📄 DOCUMENTOS (Word/PDF): Use `read_file` no 'Caminho para Leitura' (.md).\n\n"
                "📊 PLANILHAS EXCEL (.xlsx/.xls): NUNCA use read_csv, read_file, ou tente abrir como texto.\n"
                "   Use EXATAMENTE a ferramenta `create_pandas_dataframe` com estes parâmetros:\n"
                "   {\"dataframe_name\": \"df\", \"create_using_function\": \"read_excel\", \"function_parameters\": {\"io\": \"CAMINHO_DO_ARQUIVO\", \"engine\": \"openpyxl\"}}\n\n"
                "📝 PLANILHAS CSV (.csv): Use `create_pandas_dataframe` com:\n"
                "   {\"dataframe_name\": \"df\", \"create_using_function\": \"read_csv\", \"function_parameters\": {\"filepath_or_buffer\": \"CAMINHO_DO_ARQUIVO\"}}\n\n"
                "🔧 APÓS criar o dataframe, use `run_dataframe_operation` para operar nele:\n"
                "   {\"dataframe_name\": \"df\", \"operation\": \"head\", \"operation_parameters\": {\"n\": 10}}\n\n"
                "Arquivos Disponíveis:\n" + "\n".join(arquivos_anexados)
            )
            if isinstance(run_input.input_content, str):
                run_input.input_content += f"\n\n[Instrução do Sistema]: {aviso}"
            elif run_input.input_content is None:
                run_input.input_content = f"[Instrução do Sistema]: {aviso}"
            elif isinstance(run_input.input_content, list):
                run_input.input_content.append(f"\n\n[Instrução do Sistema]: {aviso}")

def create_base_agent(
    name: str,
    instructions: List[str] = None,
    tools: List = None,
    knowledge: Any = None,
    markdown: bool = True,
    debug_mode: bool = False,
    **kwargs
) -> Agent:
    """
    Cria um agente Agno com as configurações base do projeto Dartha.
    """
    # Resolve o modelo antecipadamente para evitar problemas de recursão/resolução no Agno
    # If model was provided (already resolved by caller), use it directly.
    # Otherwise fall back to settings default.
    if "model" in kwargs:
        model = kwargs.pop("model")
    else:
        from src.config.settings import settings
        model_str = settings.DEFAULT_MODEL_ID
        if ":" not in model_str:
            model_str = f"{settings.LLM_PROVIDER}:{model_str}"
        model = get_model(model_str)
    
    # Adiciona o hook de filtro de arquivos aos pre_hooks existentes ou cria um novo
    pre_hooks = kwargs.get("pre_hooks", [])
    if filter_unsupported_files not in pre_hooks:
        pre_hooks.append(filter_unsupported_files)
    
    # Configurações padrão que podem ser sobrescritas por kwargs
    agent_params = {
        "name": name,
        "model": model, 
        "db": get_db(),
        "memory_manager": get_memory_manager(),
        "enable_agentic_memory": True,
        "add_memories_to_context": True,
        # Agentic RAG: LLM decide quando buscar no knowledge (search_knowledge=True expõe a tool).
        # Os arquivos de upload ainda são processados pelas ferramentas (PandasTools/FileTools).
        "knowledge": knowledge,
        "add_knowledge_to_context": False,
        "search_knowledge": True,
        "update_knowledge": False,
        "instructions": instructions or [],
        "tools": tools or [],
        "pre_hooks": pre_hooks,
        "add_datetime_to_context": True,
        "add_history_to_context": True,
        "num_history_runs": 10,
        "markdown": markdown,
        "debug_mode": debug_mode,
    }
    
    # Sobrescreve padrões com valores passados em kwargs (removendo pre_hooks para não duplicar)
    if "pre_hooks" in kwargs:
        del kwargs["pre_hooks"]
    agent_params.update(kwargs)
    
    return Agent(**agent_params)
