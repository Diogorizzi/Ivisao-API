# Guia de 5 Minutos — Quickstart

Este guia foca em colocar a **Dartha API V3** rodando o mais rápido possível no seu ambiente local.

---

## 1. Requisitos Prévios
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recomendado) ou pip
- Uma conta e API Key da OpenAI (ou Claude/Google/Groq)

---

## 2. Passo a Passo

### 1- Setup de Pastas e Env
No terminal, na raiz do projeto:
```bash
cp .env.example .env
```
Abra o arquivo `.env` e insira sua chave:
```env
OPENAI_API_KEY=sk-sua-chave-...
```

### 2- Instalação
Usando `uv`:
```bash
uv venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

uv pip install -e .
```

### 3- Iniciar a API
```bash
python -m src.app
```
*A mensagem "INFO: Application startup complete." indica que está tudo pronto.*

---

## 3. Testando

### Via Agno UI (Recomendado)
1. Vá para [os.agno.com](https://os.agno.com)
2. Clique em **"Add Local OS"**
3. Insira o endereço: `http://localhost:7777`
4. Selecione o **"General Assistant"** e comece a conversar.

### Via Swagger (Documentação Técnica)
Acesse: `http://localhost:7777/docs`

---

## 4. Próximos Passos
- Para adicionar novos agentes, veja `src/agents/`.
- Para configurar o Knowledge Base (RAG), aguarde a Fase 2 ou consulte `docs/rag_guide.md` (em breve).
- Todas as alterações ficam registradas no `memory_bank/`.
