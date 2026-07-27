# Plano: Skills Library — Gerenciamento de Skills por Usuário no Frontend Dartha

## Contexto

O backend da Dartha API V3 já possui um sistema completo de skills baseado em banco de dados
(`src/admin/db.py` — tabela `skills` com CRUD + `src/skills/db_loader.py`). Os agentes Agno
carregam skills do banco automaticamente, com suporte a escopo por departamento.

**O que falta:** uma interface no frontend para que administradores criem, editem e removam
skills via UI, sem precisar tocar em código ou reiniciar servidor.

---

## Arquitetura da Solução

```
Dartha Frontend (Next.js 14 App Router)
    ↓ tRPC (padrão do projeto)
Dartha API (FastAPI) — /admin/skills endpoints
    ↓
agno.db — tabela skills
    ↑
DatabaseSkillLoader → Agno Agents
```

**A autenticação já existe:** todos os endpoints `/admin/skills` na API requerem o cookie de sessão
admin, que o frontend já gerencia via `AxiosInstance.ts` com o header `X-Origin-Id`.

---

## Decisão de Arquitetura: tRPC vs Axios direto

O projeto usa **tRPC como padrão** para comunicação backend. Porém, a API de skills é um servidor
**FastAPI separado** (não é o backend tRPC do Next.js). Portanto:

- **Usar `axiosInstance` do projeto** (`src/services/AxiosInstance.ts`) — igual ao padrão
  já usado para outras chamadas diretas à API externa (como `Gateway.ts`).
- **Criar um hook `use-skills.ts`** seguindo o padrão de `use-assistants.ts` e outros hooks do projeto.
- **Criar um tRPC router `skills.ts`** como proxy para manter o padrão de type-safety — o tRPC
  chama o FastAPI internamente. Este é o padrão já usado em `agno-config.ts` e `mcp.ts`.

---

## Estrutura de Arquivos a Criar/Modificar

```
src/
├── server/api/routers/
│   └── skills.ts                          # [NEW] tRPC router — proxy para FastAPI /admin/skills
├── server/api/
│   └── root.ts                            # [MODIFY] Registrar skillsRouter
├── hooks/
│   └── use-skills.ts                      # [NEW] Hook de dados para skills
├── types/
│   └── skill.ts                           # [NEW] Tipos TypeScript para Skill
└── components/admin/
    └── skills/                            # [NEW] Pasta de componentes
        ├── skills-page.tsx                # [NEW] Página principal
        ├── skills-table.tsx               # [NEW] Tabela listagem
        ├── add-skill-dialog.tsx           # [NEW] Dialog criar skill
        ├── edit-skill-dialog.tsx          # [NEW] Dialog editar skill
        ├── delete-skill-dialog.tsx        # [NEW] Dialog confirmar exclusão
        ├── skill-instructions-editor.tsx  # [NEW] Editor markdown para instruções
        └── skill-files-editor.tsx         # [NEW] Editor de scripts e references
```

**Rota de página:**
```
src/app/(pages)/(chat)/admin/skills/       # [NEW] Pasta de rota
└── page.tsx                               # [NEW] Server component da página
```

---

## Passo a Passo da Implementação

### Passo 1 — Tipos TypeScript (`src/types/skill.ts`)

```typescript
export interface SkillFile {
  path: string;     // "scripts/analyze.py" | "references/guide.md"
  content: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  instructions: string;
  department: string | null;   // null = global (todos os agentes)
  license: string | null;
  compatibility: string | null;
  metadata: Record<string, unknown> | null;
  allowed_tools: string[] | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  version: number;
  is_active: boolean;
  files: SkillFile[];          // scripts/ e references/ como texto
}

export interface SkillListItem {
  id: string;
  name: string;
  description: string;
  department: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface CreateSkillInput {
  name: string;           // max 64 chars, lowercase, kebab-case
  description: string;    // max 1024 chars
  instructions: string;   // markdown
  department?: string | null;
  license?: string | null;
  compatibility?: string | null;
  metadata?: Record<string, unknown> | null;
  allowed_tools?: string[] | null;
  files?: SkillFile[];    // opcional — scripts e referencias
}

export type UpdateSkillInput = Partial<CreateSkillInput> & {
  version?: number;       // para optimistic locking
  // files: se omitido mantém os arquivos atuais; se enviado (mesmo []) substitui todos
};
```

---

### Passo 2 — tRPC Router (`src/server/api/routers/skills.ts`)

Seguir o padrão exato de `mcp.ts` — usar `privateProcedureWithOrigin`, validar com Zod, chamar API
interna via fetch/axios. O FastAPI backend roda em `NEXT_PUBLIC_API_URL`.

```typescript
import { z } from "zod";
import { createTRPCRouter, privateProcedureWithOrigin } from "@/server/api/trpc";
import { TRPCError } from "@trpc/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// Helper para chamadas autenticadas à API FastAPI
async function fetchApi(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro na API" }));
    throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: err.detail ?? "Erro desconhecido" });
  }
  return res.json();
}

export const skillsRouter = createTRPCRouter({
  // Listar skills (com filtro opcional por department)
  list: privateProcedureWithOrigin
    .input(z.object({ department: z.string().optional() }))
    .query(async ({ input }) => {
      const params = input.department ? `?department=${input.department}` : "";
      const result = await fetchApi(`/admin/skills${params}`);
      return result.data as SkillListItem[];
    }),

  // Buscar skill completa por ID
  getById: privateProcedureWithOrigin
    .input(z.object({ id: z.string() }))
    .query(async ({ input }) => {
      const result = await fetchApi(`/admin/skills/${input.id}`);
      return result.data as Skill;
    }),

  // Criar nova skill
  create: privateProcedureWithOrigin
    .input(
      z.object({
        name: z.string().min(2).max(64).regex(/^[a-z0-9-]+$/, "Use apenas letras minúsculas, números e hífens"),
        description: z.string().min(10).max(1024),
        instructions: z.string().min(10),
        department: z.string().nullable().optional(),
        license: z.string().nullable().optional(),
        compatibility: z.string().nullable().optional(),
        metadata: z.record(z.unknown()).nullable().optional(),
        allowed_tools: z.array(z.string()).nullable().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const result = await fetchApi("/admin/skills", {
        method: "POST",
        body: JSON.stringify(input),
      });
      if (!result.ok) throw new TRPCError({ code: "BAD_REQUEST", message: result.error });
      return result.data;
    }),

  // Atualizar skill existente
  update: privateProcedureWithOrigin
    .input(
      z.object({
        id: z.string(),
        name: z.string().min(2).max(64).regex(/^[a-z0-9-]+$/).optional(),
        description: z.string().min(10).max(1024).optional(),
        instructions: z.string().min(10).optional(),
        department: z.string().nullable().optional(),
        license: z.string().nullable().optional(),
        compatibility: z.string().nullable().optional(),
        metadata: z.record(z.unknown()).nullable().optional(),
        allowed_tools: z.array(z.string()).nullable().optional(),
        version: z.number().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const { id, ...body } = input;
      const result = await fetchApi(`/admin/skills/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      if (!result.ok) throw new TRPCError({ code: "BAD_REQUEST", message: result.error });
      return result.data;
    }),

  // Deletar skill (soft delete por padrão)
  delete: privateProcedureWithOrigin
    .input(z.object({ id: z.string(), hard: z.boolean().optional() }))
    .mutation(async ({ input }) => {
      const params = input.hard ? "?hard=true" : "";
      const result = await fetchApi(`/admin/skills/${input.id}${params}`, { method: "DELETE" });
      if (!result.ok) throw new TRPCError({ code: "BAD_REQUEST", message: result.error });
      return { success: true };
    }),
});
```

**Registrar em `root.ts`:**
```typescript
// Adicionar import
import { skillsRouter } from "./routers/skills";

// Adicionar no appRouter:
skills: skillsRouter,
```

---

### Passo 3 — Hook de Dados (`src/hooks/use-skills.ts`)

Padrão idêntico ao `use-assistants.ts` do projeto:

```typescript
"use client";
import { api } from "@/trpc/react";
import type { SkillListItem, Skill } from "@/types/skill";

export function useSkills(department?: string) {
  const { data, isLoading, error, refetch } = api.skills.list.useQuery(
    { department },
    {
      staleTime: 1000 * 60 * 2,       // 2 minutos (skills mudam mais que setores)
      refetchOnWindowFocus: false,
      retry: false,
    }
  );

  return {
    skills: (data ?? []) as SkillListItem[],
    isLoading,
    error,
    refetch,
  };
}

export function useSkillById(id: string) {
  return api.skills.getById.useQuery(
    { id },
    { enabled: !!id, staleTime: 1000 * 60 * 2 }
  );
}
```

---

### Passo 4 — Componentes

#### 4.1 — `add-skill-dialog.tsx`

Padrão de `add-setor-dialog.tsx` — Dialog controlado por `useState`, form com `react-hook-form`,
mutation tRPC, `toast.success/error`, reset após sucesso.

**Campos do formulário:**
- `name` — Input text, regex kebab-case, helper: "Use letras minúsculas e hífens. Ex: analise-contratos"
- `description` — Textarea, contador de chars (max 1024), helper: "Este texto decide quando o agente usa esta skill"
- `instructions` — Textarea grande (ou o editor markdown — ver 4.4)
- `department` — Select com opções dos setores disponíveis + "Global (todos os agentes)"

**Validação visual no campo `name`:**
```
✓ analise-contratos      (válido)
✗ Analise Contratos      (inválido — maiúsculas e espaços)
✗ analise--contratos     (inválido — hífens consecutivos)
```

**Aviso no campo `description`:**
```
💡 Esta descrição controla quando o agente usa esta skill automaticamente.
   Seja específico sobre os cenários de uso. Quanto mais detalhada, melhor o triggering.
```

#### 4.2 — `edit-skill-dialog.tsx`

Igual ao `edit-setor-dialog.tsx` — `useEffect` para popular form com valores atuais, `version`
incluído no payload (optimistic locking), prefetch via `useSkillById(id)` ao abrir.

#### 4.3 — `delete-skill-dialog.tsx`

Igual ao `delete-setor-dialog.tsx` — Dialog de confirmação mostrando `skill.name`, aviso de que
será arquivada (soft delete), botão "Deletar Permanentemente" separado (chama com `hard: true`).

```
⚠️ Arquivar skill "analise-contratos"?
O agente não usará mais esta skill. Você pode restaurá-la depois.

[Cancelar]  [Arquivar]  [Deletar permanentemente]
```

#### 4.4 — `skill-instructions-editor.tsx`

Editor de instruções com preview. O campo `instructions` é markdown — usar um `<textarea>` com
opção de preview lado a lado via `useState("edit" | "preview")`. Não precisa de biblioteca externa:

```tsx
// Tabs: "Editar" | "Preview"
// Preview: renderizar markdown como <pre> ou usar uma lib já instalada no projeto
// Checar se "marked" ou "react-markdown" já está em package.json
```

Se não houver lib de markdown instalada, deixar o preview simples como `<pre>` com whitespace-pre-wrap.

#### 4.5 — `skills-table.tsx`

Padrão de `setor-table.tsx` — tabela com colunas:

| Nome | Descrição (truncada 80 chars) | Departamento | Versão | Atualizado em | Ações |
|------|-------------------------------|--------------|--------|---------------|-------|
| `analise-contratos` | Analise contratos... | `juridico` | v2 | há 3 dias | ✏️ 🗑️ |

- Filtro por departamento (select)
- Busca por nome (input)
- Badge colorido para departamento (null = "Global" badge verde)

#### 4.6 — `skills-page.tsx`

Padrão de `setor-page.tsx` / `assistentes-page.tsx`:

```tsx
export default function SkillsPage() {
  const { skills, isLoading } = useSkills();
  // Stats: total, por departamento, global
  // Header com botão "Nova Skill"
  // Tabela com filtros
  // Seção de ajuda explicando o que são skills
}
```

---

### Passo 5 — Rota de Página (`src/app/(pages)/(chat)/admin/skills/page.tsx`)

```tsx
import SkillsPage from "@/components/admin/skills/skills-page";

export const metadata = { title: "Gerenciar Skills" };

export default function Page() {
  return <SkillsPage />;
}
```

---

### Passo 6 — Navegação no Sidebar

Adicionar entrada no sidebar de admin para a rota `/admin/skills`. Verificar como outros itens
de admin são adicionados — provavelmente em `src/components/sidebar/` ou similar.

Ícone sugerido: `Zap` ou `Brain` do `lucide-react`.

---

## Wireframe da Página

```
┌─────────────────────────────────────────────────────────────┐
│ ← Voltar    Skills dos Agentes                              │
│                                                             │
│  ┌─────────┐  ┌──────────────┐  ┌───────────────────┐      │
│  │  Total  │  │  Globais     │  │  Por Departamento  │      │
│  │   12    │  │    5         │  │         7          │      │
│  └─────────┘  └──────────────┘  └───────────────────┘      │
│                                                             │
│  [Buscar skill...]  [Departamento ▼]    [+ Nova Skill]      │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Nome              │ Dept     │ Vers │ Atualizado  │ ⚙ │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ analise-contratos │ juridico │ v2   │ há 3 dias   │ ✏🗑│   │
│  │ criar-campanha    │ marketing│ v1   │ há 1 semana │ ✏🗑│   │
│  │ data-analysis     │ Global   │ v3   │ ontem       │ ✏🗑│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  💡 Skills são instruções que os agentes usam automaticamente│
│     quando o tópico da conversa é relevante.                │
└─────────────────────────────────────────────────────────────┘
```

---

## Dialog "Nova Skill" — Detalhe do Form

```
┌─────────────────────────────────────────────┐
│ Nova Skill                                  │
│                                             │
│ Nome (identificador único)                  │
│ [analise-de-contratos              ]        │
│ ℹ️ Apenas minúsculas e hífens              │
│                                             │
│ Descrição (controla quando o agente usa)    │
│ [Use esta skill quando o usuário...    ]    │
│ [                                      ]    │
│ 234/1024 chars                              │
│ ⚡ Seja específico — a descrição é o        │
│    gatilho automático do agente             │
│                                             │
│ Departamento                                │
│ [Global (todos os agentes)          ▼]      │
│                                             │
│ Instruções (markdown)                       │
│ [Editar] [Preview]                          │
│ ┌────────────────────────────────────────┐  │
│ │ # Skill: Análise de Contratos          │  │
│ │                                        │  │
│ │ Use quando precisar analisar contratos │  │
│ │ ## Processo                            │  │
│ │ 1. Leia o contrato completo           │  │
│ └────────────────────────────────────────┘  │
│                                             │
│              [Cancelar] [Criar Skill]       │
└─────────────────────────────────────────────┘
```

---

## Observações Importantes

### Autenticação
O endpoint `/admin/skills` da FastAPI requer **cookie de sessão admin**, não bearer token.
Verificar se o `axiosInstance` já envia cookies automaticamente — se não, adicionar
`withCredentials: true` nas chamadas para este endpoint.

### CORS
A FastAPI já tem CORS configurado. Confirmar que o domínio do frontend está em `CORS_ALLOWED_ORIGINS`
no `.env` da API.

### Validação de `name` no Frontend
O Agno impõe regras estritas para nomes de skills:
- Apenas `[a-z0-9-]` (minúsculas, números, hífens)
- Não pode começar ou terminar com hífen
- Sem hífens consecutivos
- Máximo 64 caracteres

Colocar essa validação no Zod schema do tRPC **e** no form (feedback em tempo real).

### Campo `description` — UX Crítica
A description é o mecanismo de triggering automático do agente. Adicionar:
1. Contador de chars visível (target: 200–600 chars, máximo 1024)
2. Tooltip explicando que é o "gatilho" do agente
3. Exemplo: "Use esta skill sempre que o usuário mencionar contratos, cláusulas, revisão jurídica..."

### Departamento `null` vs string
- `null` → skill global → aparece no form como "Global (todos os agentes)"
- `string` → scoped → mostrar lista de departamentos via `api.sector.list`

### Hot-reload
A API já implementa hot-reload após CRUD (`_reload_agent_skills()`). O agente reflete mudanças
imediatamente sem reiniciar o servidor.

---

## Checklist de Implementação

- [ ] `src/types/skill.ts` — tipos completos
- [ ] `src/server/api/routers/skills.ts` — router tRPC com 5 procedures
- [ ] `src/server/api/root.ts` — registrar `skills: skillsRouter`
- [ ] `src/hooks/use-skills.ts` — hooks `useSkills` e `useSkillById`
- [ ] `src/components/admin/skills/skills-table.tsx`
- [ ] `src/components/admin/skills/add-skill-dialog.tsx`
- [ ] `src/components/admin/skills/edit-skill-dialog.tsx`
- [ ] `src/components/admin/skills/delete-skill-dialog.tsx`
- [ ] `src/components/admin/skills/skill-instructions-editor.tsx`
- [ ] `src/components/admin/skills/skills-page.tsx`
- [ ] `src/app/(pages)/(chat)/admin/skills/page.tsx`
- [ ] Adicionar entrada no sidebar de admin
- [ ] Testar CRUD completo: criar → listar → editar → deletar
- [ ] Confirmar que editar uma skill reflete no comportamento do agente imediatamente

---

## API Backend Reference

**Base URL:** `NEXT_PUBLIC_API_URL` (variável de ambiente)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/skills` | Listar skills (query: `?department=marketing`) |
| GET | `/admin/skills/{id}` | Buscar skill completa por ID (inclui `files[]`) |
| POST | `/admin/skills` | Criar nova skill (aceita `files[]` opcional) |
| PATCH | `/admin/skills/{id}` | Atualizar skill (aceita `files[]` — substitui todos) |
| DELETE | `/admin/skills/{id}` | Deletar (query: `?hard=true` para deletar permanente) |

**Response format padrão:**
```json
{ "ok": true, "data": { ... } }
// ou
{ "ok": false, "error": "mensagem de erro" }
```

**Auth:** Cookie de sessão admin (mesmo mecanismo do painel `/admin` do FastAPI).

### Payload de criação/atualização com arquivos

```json
{
  "name": "analise-contratos",
  "description": "Use esta skill sempre que...",
  "instructions": "# Skill: Análise de Contratos\n\n## Processo\n1. ...",
  "department": null,
  "files": [
    {
      "path": "scripts/check_clauses.py",
      "content": "#!/usr/bin/env python3\n# Script de análise de cláusulas\n..."
    },
    {
      "path": "references/tipos-de-contrato.md",
      "content": "# Tipos de Contrato\n\n## Contratos de Prestação de Serviço\n..."
    }
  ]
}
```

**Regras de `path`:**
- Deve começar com `scripts/` ou `references/`
- Apenas caracteres seguros: `[a-zA-Z0-9_\-\.]`
- Exemplo válido: `scripts/analyze.py`, `references/guide.md`
- Se `files` não for enviado no PATCH, os arquivos existentes são mantidos
- Se `files` for enviado no PATCH (mesmo `[]`), substitui completamente

### Response do GET por ID (inclui files)

```json
{
  "ok": true,
  "data": {
    "id": "uuid",
    "name": "analise-contratos",
    "description": "...",
    "instructions": "# Skill...",
    "department": null,
    "version": 2,
    "is_active": true,
    "files": [
      { "path": "scripts/check_clauses.py", "content": "..." },
      { "path": "references/guide.md", "content": "..." }
    ]
  }
}
```

---

## Arquivos de Referência no Projeto (para copiar padrões)

- Dialog de criação: `src/components/admin/setores/add-setor-dialog.tsx`
- Dialog de edição: `src/components/admin/setores/edit-setor-dialog.tsx`
- Dialog de exclusão: `src/components/admin/setores/delete-setor-dialog.tsx`
- Tabela com ações: `src/components/admin/setores/setor-table.tsx`
- Página principal: `src/components/admin/setores/setor-page.tsx`
- Hook de dados: `src/hooks/use-assistants.ts`
- Router tRPC: `src/server/api/routers/mcp.ts`
- Instância Axios: `src/services/AxiosInstance.ts`
- Tipos existentes: `src/types/sector.ts`
