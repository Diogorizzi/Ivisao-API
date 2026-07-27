#!/bin/bash
# deploy.sh — Sobe ou atualiza a stack em produção.
# Primeiro deploy e também usado para qualquer atualização posterior.
#
# Uso:
#   cd ~/dartha && bash scripts/deploy.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "==> [1/4] Verificando .env..."
if [ ! -f ".env" ]; then
  echo "  ERRO: .env não encontrado. Copie .env.example e preencha as variáveis."
  exit 1
fi

# Garante que POSTGRES_PASSWORD está definido
if ! grep -q "^POSTGRES_PASSWORD=" .env || grep -q "^POSTGRES_PASSWORD=$" .env; then
  echo "  ERRO: POSTGRES_PASSWORD não definido no .env."
  exit 1
fi

# Garante que ADMIN_SECRET_KEY foi trocado
if grep -q "change-me-in-production" .env; then
  echo "  ERRO: ADMIN_SECRET_KEY ainda é o valor padrão. Troque no .env."
  exit 1
fi

echo "==> [2/4] Baixando atualizações do repositório..."
git pull origin master

echo "==> [3/4] Fazendo build e subindo serviços..."
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo "==> [4/4] Verificando saúde dos serviços..."
sleep 5
docker compose -f docker-compose.prod.yml ps

echo ""
echo "==========================================="
echo "  Deploy concluído!"
echo "  Logs: docker compose -f docker-compose.prod.yml logs -f api"
echo "==========================================="
