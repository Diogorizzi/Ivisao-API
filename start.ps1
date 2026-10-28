# start.ps1 - Instituto da Visao API
# Inicia o servidor via "uv run" (gerencia o interpretador/venv sozinho —
# mais robusto do que ativar .venv\Scripts\Activate.ps1 diretamente, que
# pode falhar a resolver o Python gerenciado pelo uv dependendo do
# contexto do processo, ex: quando chamado por uma Tarefa Agendada).

# Garante que estamos no diretório certo
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Garante que o uv está no PATH mesmo em contextos sem o perfil do usuário carregado
$uvBin = "$env:USERPROFILE\.local\bin"
if ($env:Path -notlike "*$uvBin*") {
    $env:Path = "$uvBin;$env:Path"
}

if (-Not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv não encontrado em $uvBin. Instale com: irm https://astral.sh/uv/install.ps1 | iex"
    exit 1
}

# Força UTF-8 no Python: sessões não-interativas (ex: Tarefa Agendada) usam
# a codepage legada do Windows por padrão, que quebra ao imprimir emojis.
$env:PYTHONUTF8 = "1"

# Valida configuração antes de iniciar
Write-Host "`nValidando configuração..." -ForegroundColor Yellow
uv run python scripts/validate_config.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Configuração inválida. Corrija os erros antes de continuar." -ForegroundColor Red
    exit 1
}

# ChromaDB: usa servidor Docker se disponível (CHROMA_HOST/CHROMA_PORT no .env),
# senão cai automaticamente para o modo local persistente — não precisa de Docker.

# Inicia API
Write-Host "`nIniciando servidor..." -ForegroundColor Green

uv run python -m src.app
