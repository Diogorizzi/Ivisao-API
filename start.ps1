# start.ps1 - Dartha API V3
# Ativa o venv isolado deste projeto e inicia o servidor

# Garante que estamos no diretório certo
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Ativa o venv local
$activateScript = Join-Path $scriptDir ".venv\Scripts\Activate.ps1"
if (-Not (Test-Path $activateScript)) {
    Write-Error "Venv não encontrado. Execute: uv venv --python 3.13 .venv && uv sync"
    exit 1
}

& $activateScript

Write-Host "✅ Venv ativado: Python $(python --version)" -ForegroundColor Green

# Valida configuração antes de iniciar
Write-Host "`n📋 Validando configuração..." -ForegroundColor Yellow
python scripts/validate_config.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Configuração inválida. Corrija os erros antes de continuar." -ForegroundColor Red
    exit 1
}

# Verifica ChromaDB
Write-Host "`n🔍 Verificando ChromaDB..." -ForegroundColor Yellow
docker-compose ps chromadb | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ ChromaDB não está rodando. Iniciando..." -ForegroundColor Yellow
    docker-compose up -d chromadb
    Start-Sleep -Seconds 3
}

# Inicia API
Write-Host "`n✨ Iniciando servidor..." -ForegroundColor Green

python -m src.app
