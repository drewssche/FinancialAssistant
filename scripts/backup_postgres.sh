#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
BACKUP_REMOTE_DIR="${BACKUP_REMOTE_DIR:-}"
BACKUP_ENCRYPTION_PASSWORD_FILE="${BACKUP_ENCRYPTION_PASSWORD_FILE:-}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${BACKUP_REMOTE_DIR:?BACKUP_REMOTE_DIR must point to storage outside the VPS}"
: "${BACKUP_ENCRYPTION_PASSWORD_FILE:?BACKUP_ENCRYPTION_PASSWORD_FILE is required}"

if [[ ! -s "${BACKUP_ENCRYPTION_PASSWORD_FILE}" ]]; then
  echo "Encryption password file is missing or empty" >&2
  exit 2
fi
if ! [[ "${BACKUP_RETENTION_DAYS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "BACKUP_RETENTION_DAYS must be a positive integer" >&2
  exit 2
fi

command -v docker >/dev/null
command -v openssl >/dev/null
command -v rclone >/dev/null

dump_file="$(mktemp "${TMPDIR:-/tmp}/financialassistant-db.XXXXXX.dump")"
encrypted_file="$(mktemp "${TMPDIR:-/tmp}/financialassistant-db.XXXXXX.dump.enc")"
cleanup() {
  rm -f "${dump_file}" "${encrypted_file}"
}
trap cleanup EXIT INT TERM

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
remote_name="financialassistant-${timestamp}.dump.enc"

docker compose exec -T db pg_dump \
  --username "${POSTGRES_USER}" \
  --dbname "${POSTGRES_DB}" \
  --format custom \
  --no-owner \
  --no-acl >"${dump_file}"

openssl enc -aes-256-cbc -salt -pbkdf2 \
  -pass "file:${BACKUP_ENCRYPTION_PASSWORD_FILE}" \
  -in "${dump_file}" \
  -out "${encrypted_file}"

rclone copyto "${encrypted_file}" "${BACKUP_REMOTE_DIR%/}/${remote_name}"
rclone delete "${BACKUP_REMOTE_DIR}" \
  --include "financialassistant-*.dump.enc" \
  --min-age "${BACKUP_RETENTION_DAYS}d"

echo "Encrypted PostgreSQL backup uploaded: ${remote_name}"
