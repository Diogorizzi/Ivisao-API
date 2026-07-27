from agno.memory import MemoryManager
from src.config.database import get_db
from src.config.llm_providers import get_model

def get_memory_manager():
    """
    Retorna um MemoryManager configurado para persistir memórias do usuário no banco de dados.
    """
    db = get_db(table_name="agno_user_memories")
    from src.config.settings import settings
    _model_str = settings.DEFAULT_MODEL_ID
    if ":" not in _model_str:
        _model_str = f"{settings.LLM_PROVIDER}:{_model_str}"
    model = get_model(_model_str)
    
    return MemoryManager(
        db=db,
        model=model,
        add_memories=True,
        update_memories=True,
        additional_instructions=(
            "MEMORY EXTRACTION — STRICT RULES:\n"
            "ONLY extract memories when the user explicitly shares personal facts about themselves "
            "(name, age, profession, location, personal preferences, hobbies, habits, goals, routines).\n"
            "\n"
            "NEVER extract from documents, spreadsheets, or files the user sends for analysis.\n"
            "NEVER extract business data, spreadsheet rows, company values, or bullet-point content from uploaded files.\n"
            "NEVER extract file paths, filenames, tool names, or internal processing metadata.\n"
            "NEVER create a memory if the information came from a document rather than the user speaking about themselves.\n"
            "\n"
            "If the user says something like 'analyze this file' or shares data — do NOT create any memories.\n"
            "Only create a memory when the user says something like 'I am...', 'My name is...', 'I prefer...', "
            "'I like...', 'I work at...', 'I usually...'.\n"
            "\n"
            "If in doubt, DO NOT create a memory. Less is more."
        ),
    )
