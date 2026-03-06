#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
TOKEN="${TOKEN:-}"
PERIOD="${PERIOD:-month}"
MAX_P95_MS="${MAX_P95_MS:-250}"
MIN_CACHE_HIT_RATIO="${MIN_CACHE_HIT_RATIO:-0.0}"
MAX_SUMMARY_GET_TOTAL="${MAX_SUMMARY_GET_TOTAL:-0}"

if [[ -z "${TOKEN}" ]]; then
  echo "TOKEN is required (Bearer token for API access)."
  echo "Example:"
  echo "  TOKEN=... BASE_URL=http://localhost:8001 ./scripts/health_check.sh"
  exit 2
fi

AUTH_HEADER="Authorization: Bearer ${TOKEN}"

echo "[1/4] Checking service health: ${BASE_URL}/health"
health_json="$(curl -fsS --max-time 10 "${BASE_URL}/health")"
python3 -c 'import json,sys; p=json.loads(sys.stdin.read()); assert p.get("status")=="ok", p; print("health: ok")' <<<"${health_json}"

echo "[2/4] Checking dashboard summary endpoint"
summary_json="$(curl -fsS --max-time 10 -H "${AUTH_HEADER}" "${BASE_URL}/api/v1/dashboard/summary?period=${PERIOD}")"
python3 -c 'import json,sys; p=json.loads(sys.stdin.read()); required=["income_total","expense_total","balance"]; missing=[k for k in required if k not in p]; assert not missing, missing; print("summary: ok")' <<<"${summary_json}"

echo "[3/4] Reading dashboard metrics"
metrics_json="$(curl -fsS --max-time 10 -H "${AUTH_HEADER}" "${BASE_URL}/api/v1/dashboard/summary/metrics")"
python3 - "$MAX_P95_MS" "$MIN_CACHE_HIT_RATIO" "$MAX_SUMMARY_GET_TOTAL" <<'PY' <<<"${metrics_json}"
import json
import sys

payload = json.loads(sys.stdin.read())
max_p95 = float(sys.argv[1])
min_hit = float(sys.argv[2])
max_get_total = int(sys.argv[3])

latency = payload.get("latency_total") or {}
p95 = float(latency.get("p95_ms") or 0.0)
hit_ratio = float(payload.get("cache_hit_ratio") or 0.0)
totals = payload.get("endpoint_request_totals") or {}
summary_get_total = int(totals.get("GET /api/v1/dashboard/summary") or 0)

errors = []
if p95 > max_p95:
    errors.append(f"latency_total.p95_ms={p95} > {max_p95}")
if hit_ratio < min_hit:
    errors.append(f"cache_hit_ratio={hit_ratio} < {min_hit}")
if max_get_total > 0 and summary_get_total > max_get_total:
    errors.append(f"GET /api/v1/dashboard/summary={summary_get_total} > {max_get_total}")

print(f"metrics: cache_hit_ratio={hit_ratio:.4f}, latency_total.p95_ms={p95:.3f}, summary_get_total={summary_get_total}")
if errors:
    print("FAILED checks:")
    for item in errors:
        print(f"- {item}")
    sys.exit(1)
PY

echo "[4/4] Manual UI sanity (recommended)"
echo "- Open Dashboard, Operations, Debts sections once and confirm no visible lag/errors."
echo "Health check passed."
