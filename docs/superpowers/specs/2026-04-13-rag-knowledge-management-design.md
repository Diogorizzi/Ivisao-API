# RAG Knowledge Management System — Design Spec

**Date:** 2026-04-13  
**Status:** Approved — Implementation in progress

---

## Context

The project had a working but unmanageable RAG pipeline: ingestion done manually via CLI scripts, no UI to inspect what's loaded, and documents can only be removed by wiping the entire ChromaDB collection. Non-technical users cannot manage their own knowledge base. This spec delivers a self-contained admin panel for uploading, viewing, and removing documents per department — integrated into the existing FastAPI server — with a significantly improved ingestion pipeline using Agno's native chunking.

---

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| Admin scope | Global admin (single user) | Centralized, simpler |
| Auth | JWT in httponly cookie | Secure, single user, no extra infra |
| UI approach | FastAPI + Jinja2 + Alpine.js | Zero build step, 100% Python stack |
| UI layout | Cards overview + drill-down per dept | Best for panorama + selective management |
| Ingestion trigger | Async via BackgroundTasks + SSE progress | Non-blocking, real-time feedback |
| Chunking | Agno's RecursiveChunking with overlap | Stays in Agno ecosystem, no LangChain |
| Deletion | Selective via stored chroma_ids | Enables per-document removal |
| Integration | Mounted into existing `src/app.py` | Same process, same port, no extra deploy |

---

## New Module: `src/admin/`

```
src/admin/
├── __init__.py
├── auth.py          ← JWT cookie logic (python-jose + passlib/bcrypt)
├── routes.py        ← FastAPI APIRouter, all /admin endpoints
├── queue.py         ← BackgroundTask processor + SSE event emitter
├── db.py            ← SQLite CRUD for knowledge_documents table
└── templates/
    ├── _layout.html
    ├── login.html
    ├── dashboard.html
    └── department.html
```

---

## Data Model

```sql
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id           TEXT PRIMARY KEY,
    department   TEXT NOT NULL,
    filename     TEXT NOT NULL,
    file_path    TEXT NOT NULL,
    file_size    INTEGER,
    file_type    TEXT,
    status       TEXT DEFAULT 'pending',   -- pending | processing | indexed | error
    error_msg    TEXT,
    chunk_count  INTEGER,
    chroma_ids   TEXT,                     -- JSON array
    uploaded_at  TEXT DEFAULT (datetime('now')),
    indexed_at   TEXT
);
```

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET/POST | `/admin/login` | Login form + auth |
| GET | `/admin/logout` | Clear session |
| GET | `/admin/` | Dashboard — department cards |
| GET | `/admin/{dept}` | Document list for department |
| POST | `/admin/{dept}/upload` | Upload + trigger ingestion |
| DELETE | `/admin/{dept}/docs/{id}` | Remove from ChromaDB + disk + DB |
| GET | `/admin/queue/events?doc_id={id}` | SSE progress stream |

---

## Ingestion Pipeline

```
Upload → save to disk → DB record (pending) → BackgroundTask
  → status: processing
  → MarkItDownReader reads file
  → Agno RecursiveChunking(chunk_size=400, overlap=80)
  → Per chunk: Gemini embed → ChromaDB add → collect chroma_id
  → status: indexed, chunk_count=N, chroma_ids=[...]
```

Duplicate handling: 409 conflict → frontend confirm → re-POST with `?replace=true`.

---

## RAG Quality Improvements

| Before | After |
|---|---|
| 1 chunk per PDF page | RecursiveChunking 400 tokens + 80 overlap |
| Only dept + file metadata | + doc_title, chunk_index, file_type |
| No duplicate detection | Check by filename + dept |
| No document tracking | Full knowledge_documents table |
| Selective deletion impossible | Delete by stored chroma_ids |
| num_documents=5 hardcoded | Configurable per agent in agents.yaml |

---

## Auth

- Credentials: `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH` (bcrypt) in `.env`
- JWT (HS256) in `httponly + samesite=strict` cookie, 8h TTL
- All `/admin` routes protected by `get_current_admin()` dependency

---

## New Environment Variables

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...
ADMIN_SESSION_TTL=28800
ADMIN_SECRET_KEY=<random 32-char string>
```
