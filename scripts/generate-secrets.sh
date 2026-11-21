#!/usr/bin/env sh
# Gera os segredos de infraestrutura usados pelo Docker Compose (montados em /run/secrets).
#
#   ./scripts/generate-secrets.sh          # cria só os que faltam (nunca sobrescreve)
#   ./scripts/generate-secrets.sh --rotate-credential-key   # troca a chave do cookie da credencial
#   ./scripts/generate-secrets.sh --rotate-internal-token   # troca o segredo backend <-> auth
#
# - secrets/llm_credential_encryption_key: 32 bytes aleatórios em base64url. Cifra (JWE) o cookie da
#   chave OpenRouter dos usuários. Trocar invalida os cookies de credencial já emitidos: cada usuário
#   só precisa informar a chave de novo (a sessão de login continua válida).
# - secrets/auth_internal_token: segredo que o backend apresenta ao serviço de autenticação na
#   verificação interna de sessões. Trocar exige reiniciar backend e auth juntos.
#
# Os arquivos ficam fora do Git (.gitignore). O diretório tem permissão 700 (outros usuários do host não
# o atravessam) e os arquivos 644, porque os segredos do Compose são montados sem mapear o dono e o
# processo do container roda com usuário próprio, sem root. Não reaproveite valores de exemplo.
set -eu

DIR="$(cd "$(dirname "$0")/.." && pwd)/secrets"
mkdir -p "$DIR"
chmod 700 "$DIR"

random_b64url() {
  python3 -c 'import base64, secrets, sys; sys.stdout.write(base64.urlsafe_b64encode(secrets.token_bytes(int(sys.argv[1]))).decode().rstrip("="))' "$1"
}

write_secret() {
  name="$1"; bytes="$2"; force="$3"
  target="$DIR/$name"
  if [ -s "$target" ] && [ "$force" != "yes" ]; then
    echo "mantido: secrets/$name"
    return
  fi
  umask 077
  random_b64url "$bytes" > "$target.tmp"
  mv "$target.tmp" "$target"
  chmod 644 "$target"
  echo "gerado:  secrets/$name"
}

ROTATE_KEY=no
ROTATE_TOKEN=no
for arg in "$@"; do
  case "$arg" in
    --rotate-credential-key) ROTATE_KEY=yes ;;
    --rotate-internal-token) ROTATE_TOKEN=yes ;;
    *) echo "opção desconhecida: $arg" >&2; exit 2 ;;
  esac
done

write_secret llm_credential_encryption_key 32 "$ROTATE_KEY"
write_secret auth_internal_token 48 "$ROTATE_TOKEN"
