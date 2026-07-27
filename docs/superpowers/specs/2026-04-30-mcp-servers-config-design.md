# MCP Servers Configuration System — Design Spec

**Date:** 2026-04-30  
**Scope:** User-managed and global MCP server configuration with encrypted credentials  
**Database:** PostgreSQL Neon (separate instance)  
**Tech Stack:** FastAPI (backend) + tRPC (frontend) + SQLAlchemy + Fernet encryption

---

## 1. Overview

This system allows users to configure and manage MCP (Model Context Protocol) servers in their Dartha workspace. Each user can:
- **Add custom MCP servers** with URL, label, description, and authentication credentials
- **Use global servers** pre-configured by the company
- **Edit and delete** their own server configurations
- **Securely store API keys** encrypted in the database

The system uses the existing **session-based authentication** (cookie) from tRPC — no new auth mechanism required.

---

## 2. Database Schema

### Neon PostgreSQL (Separate Instance)

```sql
-- Global MCP Servers (company-provided)
CREATE TABLE mcp_servers_global (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  label VARCHAR(255) NOT NULL UNIQUE,
  url VARCHAR(2048) NOT NULL,
  description TEXT,
  auth_type VARCHAR(50) NOT NULL DEFAULT 'none', -- 'none', 'api_key', 'oauth'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User-specific MCP Servers
CREATE TABLE mcp_servers_user (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255) NOT NULL,  -- extracted from session cookie
  global_server_id UUID REFERENCES mcp_servers_global(id) ON DELETE SET NULL,
  label VARCHAR(255) NOT NULL,
  url VARCHAR(2048) NOT NULL,
  description TEXT,
  auth_type VARCHAR(50) NOT NULL DEFAULT 'none',
  encrypted_credentials BYTEA,  -- Fernet-encrypted credentials
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_deleted BOOLEAN DEFAULT FALSE,
  UNIQUE(user_id, label),
  INDEX idx_user_servers (user_id),
  INDEX idx_global_ref (global_server_id)
);
```

**Key Design Decisions:**
- `user_id` extracted from session automatically — no manual user identification
- `global_server_id` allows linking user configs to company presets
- `is_deleted` for soft deletes (audit trail)
- Encryption happens before storage — API keys never in plaintext

---

## 3. Backend Architecture (FastAPI)

### Directory Structure
```
src/mcp_servers/
├── __init__.py
├── models.py          # SQLAlchemy ORM models
├── schemas.py         # Pydantic request/response schemas
├── encryption.py      # Fernet encryption utilities
├── crud.py            # Database CRUD operations
├── routes.py          # FastAPI endpoints
└── dependencies.py    # get_current_user middleware
```

### 3.1 Encryption Module (`encryption.py`)

```python
# Uses Fernet (symmetric encryption)
# Key: MCP_ENCRYPTION_KEY environment variable (32-byte base64)

def encrypt_credentials(plaintext: str) -> bytes:
    """Encrypt API key/credentials using Fernet"""
    
def decrypt_credentials(ciphertext: bytes) -> str:
    """Decrypt API key/credentials"""
    
def generate_key() -> str:
    """Generate a new encryption key"""
```

**Key Storage:**
- `MCP_ENCRYPTION_KEY` in `.env` (same for all instances in production)
- Must be backed up securely
- Rotation requires data migration

---

### 3.2 Database Models (`models.py`)

```python
class MCPServerGlobal(Base):
    __tablename__ = "mcp_servers_global"
    id: UUID
    label: str
    url: str
    description: Optional[str]
    auth_type: str
    created_at: datetime
    updated_at: datetime

class MCPServerUser(Base):
    __tablename__ = "mcp_servers_user"
    id: UUID
    user_id: str
    global_server_id: Optional[UUID]
    label: str
    url: str
    description: Optional[str]
    auth_type: str
    encrypted_credentials: Optional[bytes]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
```

---

### 3.3 API Routes

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| GET | `/api/mcp-servers` | List global + user's servers | Session |
| POST | `/api/mcp-servers` | Create new server | Session |
| PATCH | `/api/mcp-servers/{id}` | Update server | Session + Owner check |
| DELETE | `/api/mcp-servers/{id}` | Delete server (soft) | Session + Owner check |
| GET | `/api/mcp-servers/global` | List only global servers | Public |

**Session Extraction:**
- Middleware extracts `user_id` from cookie (Clerk or Neon Auth)
- All endpoints validate that requester owns the server

**Request/Response Example:**

```json
POST /api/mcp-servers
{
  "url": "https://mcp.example.com",
  "label": "My Custom MCP",
  "description": "Custom provider",
  "auth_type": "api_key",
  "credentials": "sk_live_xxxxx"
}

Response (201):
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "label": "My Custom MCP",
  "url": "https://mcp.example.com",
  "description": "Custom provider",
  "auth_type": "api_key",
  "created_at": "2026-04-30T10:00:00Z"
}
```

---

## 4. Frontend Architecture (tRPC)

### tRPC Router (`app/api/trpc/routers/mcpServers.ts`)

```typescript
export const mcpServersRouter = createTRPCRouter({
  list: publicProcedure.query(async ({ ctx }) => {
    const res = await fetch('/api/mcp-servers', {
      credentials: 'include'
    });
    return res.json();
  }),

  create: publicProcedure
    .input(z.object({
      url: z.string().url(),
      label: z.string().min(1).max(255),
      description: z.string().optional(),
      authType: z.enum(['none', 'api_key', 'oauth']),
      credentials: z.string().optional()
    }))
    .mutation(async ({ input }) => {
      const res = await fetch('/api/mcp-servers', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input)
      });
      return res.json();
    }),

  update: publicProcedure
    .input(z.object({
      id: z.string().uuid(),
      ...
    }))
    .mutation(async ({ input }) => { /* ... */ }),

  delete: publicProcedure
    .input(z.object({ id: z.string().uuid() }))
    .mutation(async ({ input }) => { /* ... */ })
});
```

### UI Component (React)

- Form with fields: URL, Label, Description, Auth Type, Credentials
- List view showing servers (global highlighted differently)
- Edit/Delete buttons with confirmation
- Loading states and error handling

---

## 5. Security Considerations

| Concern | Solution |
|---------|----------|
| API keys in plaintext | Fernet encryption before storage |
| Unauthorized access | Session validation + owner check |
| Key rotation | Manual process (document in ops guide) |
| CORS | Existing middleware handles it |
| SQL injection | SQLAlchemy parameterized queries |
| CSRF | Cookies sent with `SameSite=Strict` |

---

## 6. Data Flow

### Create Server
```
1. User fills form (URL, label, auth type, credentials)
2. Frontend: POST /api/mcp-servers (credentials: 'include')
3. Backend middleware: Extracts user_id from cookie
4. Backend: Validates input
5. Backend: Encrypts credentials with Fernet
6. Backend: Saves to mcp_servers_user table
7. Response: Returns server (credentials NOT in response)
```

### Read Servers
```
1. Frontend: GET /api/mcp-servers (credentials: 'include')
2. Backend: Extracts user_id
3. Backend: Queries mcp_servers_user WHERE user_id = ? AND is_deleted = false
4. Backend: Also queries mcp_servers_global
5. Response: Returns list (credentials NOT included)
```

### Use Server (when needed)
```
1. Agent/tool needs to call MCP server
2. Backend: Queries mcp_servers_user by id
3. Backend: Decrypts credentials (in memory only)
4. Backend: Calls MCP server with credentials
5. Credentials never exposed to frontend
```

---

## 7. Error Handling

| Scenario | Status | Response |
|----------|--------|----------|
| Missing/invalid session | 401 | Redirect to login |
| User tries to edit other's server | 403 | Forbidden |
| Invalid URL format | 400 | Validation error |
| Duplicate label | 409 | Conflict |
| Server not found | 404 | Not found |
| Encryption error | 500 | Internal error |

---

## 8. Testing Strategy

- **Unit:** Encryption/decryption functions
- **Integration:** CRUD operations with mock database
- **E2E:** Full flow (create → read → update → delete) via API
- **Security:** Verify encryption happens, credentials not leaked in logs

---

## 9. Deployment Checklist

- [ ] Create new PostgreSQL database on Neon
- [ ] Generate `MCP_ENCRYPTION_KEY` and store in `.env`
- [ ] Run migrations (SQLAlchemy models)
- [ ] Seed global servers (if any)
- [ ] Test authentication flow
- [ ] Verify encryption is working
- [ ] Monitor logs for errors

---

## 10. Future Extensions

- **OAuth flow** for servers that support it (handle redirects)
- **Server health checks** (ping endpoint periodically)
- **Usage analytics** (which servers are used most)
- **Shared servers** (team-level configurations)
- **Audit logs** (who changed what and when)

---

**Status:** Ready for implementation  
**Approved by:** [pending user review]
