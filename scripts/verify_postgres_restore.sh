#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
BACKUP_OBJECT="${BACKUP_OBJECT:-}"
BACKUP_ENCRYPTION_PASSWORD_FILE="${BACKUP_ENCRYPTION_PASSWORD_FILE:-}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${BACKUP_OBJECT:?BACKUP_OBJECT must identify one encrypted rclone object}"
: "${BACKUP_ENCRYPTION_PASSWORD_FILE:?BACKUP_ENCRYPTION_PASSWORD_FILE is required}"

command -v docker >/dev/null
command -v openssl >/dev/null
command -v rclone >/dev/null

encrypted_file="$(mktemp "${TMPDIR:-/tmp}/financialassistant-restore.XXXXXX.dump.enc")"
dump_file="$(mktemp "${TMPDIR:-/tmp}/financialassistant-restore.XXXXXX.dump")"
restore_db="financialassistant_restore_check_$(date -u +%Y%m%d%H%M%S)"
cleanup() {
  docker compose exec -T db dropdb --username "${POSTGRES_USER}" --if-exists "${restore_db}" >/dev/null 2>&1 || true
  rm -f "${encrypted_file}" "${dump_file}"
}
trap cleanup EXIT INT TERM

rclone copyto "${BACKUP_OBJECT}" "${encrypted_file}"
openssl enc -d -aes-256-cbc -pbkdf2 \
  -pass "file:${BACKUP_ENCRYPTION_PASSWORD_FILE}" \
  -in "${encrypted_file}" \
  -out "${dump_file}"

docker compose exec -T db createdb --username "${POSTGRES_USER}" "${restore_db}"
docker compose exec -T db pg_restore \
  --username "${POSTGRES_USER}" \
  --dbname "${restore_db}" \
  --exit-on-error <"${dump_file}"

table_count="$(docker compose exec -T db psql --username "${POSTGRES_USER}" --dbname "${restore_db}" --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")"
if [[ "${table_count}" -le 0 ]]; then
  echo "Restore verification failed: no public tables found" >&2
  exit 1
fi

echo "Restore verification passed: ${table_count} public tables"
