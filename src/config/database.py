import uuid
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb
from src.config.settings import settings

def get_db(table_name: str = "agno_sessions"):
    unique_suffix = uuid.uuid4().hex[:8]
    if settings.DATABASE_URL.startswith("sqlite"):
        # Remove sqlite:/// from start
        db_file = settings.DATABASE_URL.replace("sqlite:///", "")
        return SqliteDb(id=f"sqlite-{table_name}-{unique_suffix}", db_file=db_file, session_table=table_name)
    else:
        return PostgresDb(id=f"postgres-{table_name}-{unique_suffix}", session_table=table_name, db_url=settings.DATABASE_URL)
