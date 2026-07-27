#!/bin/bash
# init-ssl.sh — Geração do certificado SSL inicial via Let's Encrypt.
# Executar UMA VEZ, depois do domínio já apontar para o IP da VM.
#
# Uso:
#   cd ~/dartha && bash scripts/init-ssl.sh

set -euo pipefail

DOMAIN="dartha.api.br"
EMAIL="${SSL_EMAIL:-}"

if [ -z "$EMAIL" ]; then
  read -rp "E-mail para notificações do Let's Encrypt: " EMAIL
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "==> [1/4] Ativando config HTTP temporária (sem SSL)..."
cp nginx/dartha-nossl.conf nginx/active.conf

echo "==> [2/4] Subindo nginx com config temporária..."
sudo docker compose -f docker-compose.prod.yml up -d nginx
sleep 3

echo "==> [3/4] Solicitando certificado para $DOMAIN..."
sudo docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d "$DOMAIN" \
  -d "www.$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email

echo "==> [4/4] Ativando config HTTPS completa e reiniciando nginx..."
cp nginx/dartha.conf nginx/active.conf
sudo docker compose -f docker-compose.prod.yml restart nginx

echo ""
echo "==========================================="
echo "  SSL configurado com sucesso!"
echo "  A API está disponível em https://$DOMAIN"
echo "==========================================="
