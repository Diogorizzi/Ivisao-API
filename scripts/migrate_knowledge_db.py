"""
Migração: cria a tabela knowledge_documents no agno.db
Execute uma vez: uv run python scripts/migrate_knowledge_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("agno.db")

def run():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id           TEXT PRIMARY KEY,
            department   TEXT NOT NULL,
            filename     TEXT NOT NULL,
            file_path    TEXT NOT NULL,
            file_size    INTEGER,
            file_type    TEXT,
            status       TEXT DEFAULT 'pending',
            error_msg    TEXT,
            chunk_count  INTEGER,
            chroma_ids   TEXT,
            uploaded_at  TEXT DEFAULT (datetime('now')),
            indexed_at   TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"[OK] Tabela knowledge_documents criada/verificada em {DB_PATH}")

if __name__ == "__main__":
    run()
