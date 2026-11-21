#!/usr/bin/env sh
# Certificado autoassinado para testar o compose de produção localmente (https://localhost).
# Em um servidor real, use certificados de uma CA (ex.: Let's Encrypt) com os mesmos nomes de arquivo.
set -eu
DIR="$(cd "$(dirname "$0")/.." && pwd)/deploy/certs"
mkdir -p "$DIR"
openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
  -keyout "$DIR/privkey.pem" -out "$DIR/fullchain.pem" \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
chmod 600 "$DIR/privkey.pem"
echo "certificado autoassinado em deploy/certs/ (válido por 30 dias, só para testes locais)"
