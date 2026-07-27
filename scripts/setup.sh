#!/bin/bash
# setup.sh — Executar UMA VEZ na VM do GCP após criação
# Instala Docker, clona o repo e prepara o ambiente.
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/Opedroaguiarr/Dartha-API-V3/master/scripts/setup.sh | bash

set -euo pipefail

REPO_URL="https://github.com/Opedroaguiarr/Dartha-API-V3.git"
APP_DIR="$HOME/dartha"

echo "==> [1/5] Atualizando sistema..."
sudo apt-get update -qq && sudo apt-get upgrade -y -qq

echo "==> [2/5] Instalando Docker..."
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"

echo "==> [3/5] Abrindo portas no firewall da VM..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# Bloqueia acesso direto às portas internas (7777, 8000, 5432)
sudo ufw deny 7777/tcp
sudo ufw deny 8000/tcp
sudo ufw deny 5432/tcp
sudo ufw --force enable

echo "==> [4/5] Clonando repositório..."
if [ -d "$APP_DIR" ]; then
  echo "    Diretório $APP_DIR já existe. Pulando clone."
else
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> [5/5] Criando .env a partir do exemplo..."
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo ""
  echo "  ATENÇÃO: edite $APP_DIR/.env antes de continuar."
  echo "  Preencha as API keys, ADMIN_*, POSTGRES_PASSWORD e CORS_ALLOWED_ORIGINS."
  echo ""
else
  echo "    .env já existe. Pulando."
fi

echo ""
echo "==========================================="
echo "  Setup concluído!"
echo "  Próximos passos:"
echo ""
echo "  1. Edite o .env:"
echo "       nano $APP_DIR/.env"
echo ""
echo "  2. Aponte o domínio dartha.api.br para o IP desta VM"
echo "     e aguarde propagar (pode levar até 10 min)."
echo ""
echo "  3. Execute o SSL inicial:"
echo "       cd $APP_DIR && bash scripts/init-ssl.sh"
echo ""
echo "  4. Suba a stack:"
echo "       cd $APP_DIR && bash scripts/deploy.sh"
echo "==========================================="
echo ""
echo "  IMPORTANTE: faça logout e login novamente para o"
echo "  grupo 'docker' ser aplicado ao seu usuário."
echo ""
