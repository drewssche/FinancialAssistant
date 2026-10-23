# Passive security observation

Stages 1–2, 2026-10-23. Request limits remain observational: no delays or automatic
bans. Stage 2 adds invitation-only registration and optional moderated alerts.
IP correlation does not identify a person.

## Signals and journal

The app observes exact nonexistent login paths listed in
`app/core/security_observation.py`, keeping the ordinary 404 response. Other 404s
are ignored. Five authentication/authorization failures within five minutes
produce a signal; pending/rejected access denials are excluded. Invalid Telegram
login payloads count, but an isolated login failure does not produce a signal.
A dry-run Nginx limit hit is recorded even if the underlying request succeeds.
These events are evidence for review, not proof of an attack.

JSONL events include UTC timestamp, method, known path or route template, status,
server-generated request ID, client IP, verified user ID when available, rate
status, counts and suppressed event count. No request bodies, authorization,
cookies, query strings, user agent or arbitrary unmatched paths are recorded.
A verified user ID is available after successful authentication of protected
requests; rejected login payloads are never trusted as an identity.

The journal lives in the `security_logs` Docker volume at
`/var/log/financialassistant/security.jsonl`, outside the static tree and database.
The directory is 0700, files 0600. There are at most four 2 MiB files, independent
of ordinary Docker logs. Files idle for seven days are removed on initialization
or the next hourly cleanup during writes. This is a size/idle-age retention
policy, not a per-record seven-day expiry. Recreating app preserves the volume.

Observation state is process-local: up to 4096 sources, five-minute windows, up
to 32 paths per source; ten events/source/minute and 200 events/minute globally.
Repeated same-path probes and failure/rate summaries are sampled once/minute.
Suppressed counts appear in the next emitted event. Counts reset on app restart;
the journal survives. Limits are intentionally generous for shared IPs, and
sampling may omit individual attempts during floods. No background timer is
needed; expiry is evaluated on observation. This is not DDoS protection.

Read on the server (admin SSH only):

```sh
cd /root/FinancialAssistant
docker compose exec -T app tail -n 50 /var/log/financialassistant/security.jsonl
```

There is no new public endpoint for this journal. Stage 2 sends selected summaries.
Do not remove Docker volumes during a normal release.

## Proxy configuration

The host Nginx is the public edge; app is bound to `127.0.0.1:8001`. Install
`deploy/nginx/financialassistant-observation-http.conf` in `/etc/nginx/conf.d/`
and the location snippet in `/etc/nginx/snippets/`. Include the latter **only**
in the finance app's existing `location /`, not the companion app's locations.
Keep existing TLS, proxy, 8 MiB upload limit and Certbot configuration intact.

- Login/refresh: 10 requests/minute per IP, burst 10.
- Other `/api/v1/` traffic: 10 requests/second per IP, burst 40 (login also counts).
- `limit_req_dry_run on` and `nodelay`: only observations, no artificial delay or
  rejection. Health/readiness, assets and non-API callbacks have empty keys.
- The edge keys on `$binary_remote_addr`. Do not trust inbound forwarding headers
  or enable `real_ip_header` without reviewing the upstream trust boundary.
- Nginx overwrites `X-Real-IP` with `$remote_addr`, `X-Forwarded-For` with
  `$remote_addr` (not an appended untrusted list), and `X-FA-Rate-Observation`
  with `$limit_req_status`.
- Uvicorn runs with `--no-proxy-headers`; app reads proxy headers only when the
  socket peer is in `SECURITY_TRUSTED_PROXY_IPS`. Set this server `.env` variable
  to the exact Docker bridge gateway seen by app (currently `172.19.0.1`).
  Do not use `*` or trust an entire private range. Recheck after network changes.
  Without a trusted peer, the socket IP is used and supplied rate headers ignored.
- Uvicorn's raw access log is disabled. Existing structured completion logs use
  route templates and server-generated request IDs, also preventing unbounded
  path cardinality in metrics. Generic Nginx dry-run diagnostics are suppressed
  to avoid duplicating raw URLs; the app receives the dry-run status instead.

Nginx reference: https://nginx.org/en/docs/http/ngx_http_limit_req_module.html

## Documentation

`APP_ENV=production` disables `/docs`, `/docs/oauth2-redirect`, `/redoc` and
`/openapi.json` for everyone. Local development/test retains them. The frontend
uses fixed API routes and does not fetch OpenAPI. Authentication and approval
remain the actual data-access boundary; hiding documentation is supplemental.

## Release and rollback

1. Verify clean local/server trees and the expected origin commit. Save the old
   app image and a private backup of the vhost, `.env`, and any existing snippet
   files outside the repo (directory 0700). Never print `.env` or commit backups.
2. Pull fast-forward, install the two snippets, replace the X-Forwarded-For value,
   add the location include, and set the exact trusted gateway in `.env`.
3. Run `nginx -t` before a graceful `systemctl reload nginx`. On validation failure
   restore the saved files and stop. No nginx restart or neighbor reload is needed.
4. Build app, run auth/security tests in an isolated image, then
   `docker compose up -d --no-deps app`. No schema change or bot restart.
5. Check readiness, public static hashes, docs returning 404, ordinary pending/
   approved/admin test scenarios, spoofed proxy headers, and a small burst against
   an inert signal route. Every burst response must stay 404, with a journal event
   containing `REJECTED_DRY_RUN`. Verify all containers and unchanged neighbors.
6. For rollback restore proxy files and `.env`, `nginx -t`, gracefully reload;
   redeploy the saved app image. Retain `security_logs`. Disabling observation
   does not require banning/unbanning anyone.

Enforcement requires a separate reviewed iteration after observing real
traffic, shared-IP use, reconnect bursts and false positives. No claims are made
that the observation thresholds are already tuned for enforcement.

## Stage 2: invitations and moderate notifications

`REGISTRATION_MODE=invitation` rejects new uninvited Telegram identities **after**
Telegram signature verification but **before** creating a user or token. Existing
approved/active users and configured admins keep access. Add numeric Telegram IDs
to `REGISTRATION_ALLOWED_TELEGRAM_IDS` to permit a new access request; an invited
new user still needs approval. Rejected users cannot log in, and existing tokens
stop working on their next authenticated request. Approval mode remains available
for other deployments. No country/IP-based blocking is enabled.

With `SECURITY_ALERTS_ENABLED=true`, app runs one background digest worker. Both
app and bot enqueue access-status changes into `security-alerts.sqlite3` in the
private shared `security_logs` volume. Bot must be updated with app for its approval
buttons to generate these audit events. Delivery never runs in an HTTP request.
The request journal also feeds repeated failures, at least three distinct suspicious
paths or ten signals in a source's observation window into digests. A lone 404 is
quiet. These are sampled observation counts, not exact total request counts.

- Batch window: 15 minutes from the first queued event.
- Maximum one attempt/hour and six attempts/calendar day (Europe/Minsk), separately
  for each admin Telegram destination and the email destination. No empty digests.
- Counters and pending summaries survive app replacement. Lists in summaries are
  capped at ten entries, access-audit queue at 100 entries; this is not a full SIEM.
- Delivery errors are retried at most three times, subject to the same limits.
  One channel's failure does not repeat a successful delivery on another channel.
- The journal records attempted/sent/failed/unconfigured/abandoned outcomes.
  "Sent" means acceptance by Telegram API or SMTP, not proof of inbox delivery.
- After a crash during sending, the unknown outcome is recorded without automatic
  replay to avoid duplicate messages. New events continue to aggregate. This can
  lose a notification in a crash window; the security event journal remains the
  source for review. Email without SMTP settings is explicitly unconfigured.
- No automatic banning or Nginx enforcement is enabled in this stage. Thresholds
  still need review against normal usage before enabling enforcement.

Email uses TLS only (`SMTP_SECURITY=ssl` or `starttls`) and a fixed recipient from
`SECURITY_ALERT_EMAIL`. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
`SMTP_PASSWORD`, `SMTP_FROM` in the private server `.env`; do not put credentials
in Git, chat, command arguments or diagnostic output. Telegram uses existing bot
and admin settings. A browser Gmail session does not supply server SMTP credentials.

Explicit delivery checks (send a real message, retaining cooldown/day limits):

```sh
docker compose exec -T app python scripts/test_security_notifications.py --channel telegram
docker compose exec -T app python scripts/test_security_notifications.py --channel email
```

These checks skip only the 15-minute batch delay. Review the journal for confirmed
acceptance; a queued/skipped test is not a successful send. If configuring SMTP
for a previously unconfigured channel, reset that channel's `next_at` under an
operator-controlled change so its one-day configuration-error cooldown does not
postpone the first check. Do not reset successful-delivery quotas.

Release app and bot without dependencies, preserve both old images, verify app
readiness and bot polling health, and keep neighboring projects untouched. Neither
this deployment nor the worker changes SSH, the firewall or OS reboot policy.
