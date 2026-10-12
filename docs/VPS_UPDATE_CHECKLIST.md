# VPS Update Checklist

Reviewed: 2026-10-12, including reliability release `c86c196`, search release `918f486` and the GitHub deployment workflow.

Use this with [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). Dated production facts and open issues are in [OPERATIONS_REVIEW_2026-10-12.md](OPERATIONS_REVIEW_2026-10-12.md); recheck them before deployment.

## What Changed in Telegram/Bot Terms

The current application does not require a new BotFather setting merely for a normal code update.

Current expectations remain:

- `TELEGRAM_BOT_TOKEN` is valid
- `TELEGRAM_BOT_USERNAME` matches the real bot username if browser Telegram login is needed
- Mini App opens over valid `https://`

## When BotFather Action Is Required

You need to recheck BotFather / Telegram-side settings only if one of these changed:

- bot username changed
- public domain/hostname changed
- Mini App launch URL changed
- you want browser Telegram Login Widget to keep working on a different domain

If none of that changed, recent auth/mobile/UI changes do not require a new BotFather update by themselves.

## Important Practical Note

Browser Telegram login is now stricter:

- backend rejects `/api/v1/auth/telegram/browser` when `TELEGRAM_BOT_USERNAME` is not configured
- placeholder values (`change_me`, `change_me_bot`, `your_bot_username`) are treated as not configured
- frontend relies on server `browser_login_available`

So after update, browser login still works only when:

- `TELEGRAM_BOT_USERNAME` is set correctly
- Telegram-side domain/widget configuration is still valid for your current public hostname

Mini App login via `initData` is unaffected by this change as long as the Mini App is opened from Telegram.

## VPS Update Steps

GitHub `origin/main` (`https://github.com/drewssche/FinancialAssistant`) is the source of production updates. Publish reviewed and tested changes there before updating the VPS. Do not deploy local Git bundles, copied source files or unpublished commits. Keep credentials, backups and local diagnostic artifacts outside Git.

Develop on a feature branch, fetch the current `origin/main`, integrate changes without overwriting others, and run the required checks on the resulting release. Advance `main` without a force push (use the repository's PR process if required). Record the published commit SHA. On the server, use a clean `main` tracking `origin/main` and `git pull --ff-only origin main`; verify that `HEAD` equals the tested, published SHA before rebuilding. If it differs or the checkout is dirty/diverged, stop the release and reconcile it explicitly. A documentation-only pull does not require rebuilding running application images; record their code revision separately.

1. Record the current commit, running image IDs/tags, dirty files, migration revision and restart counters. Confirm the intended checkout and release; do not overwrite local server changes or recreate unrelated projects.
2. Before changing schema or financial data, confirm a recent encrypted off-host backup and a successful restore check in an isolated target. If Yandex is unavailable, explicitly choose another destination before the release. Preserve the current images needed for rollback.
3. Publish the checked release to GitHub, then pull `origin/main` on the VPS with `--ff-only` as described above. Verify the exact release SHA and inspect its migrations/config changes before rebuild. Run the appropriate local release/regression checks; PostgreSQL migration tests must use a disposable database, never production.
4. Confirm production env still contains:
   - `APP_ENV=production`
   - valid `APP_SECRET_KEY`
   - valid `TELEGRAM_BOT_TOKEN`
   - valid `TELEGRAM_BOT_USERNAME` if browser login is needed
   - valid `ADMIN_TELEGRAM_IDS`
5. Check host headroom with `free -m`, `swapon --show`, `df -h /` and `docker stats --no-stream`. Avoid concurrent builds on the shared VPS. The existing `/swapfile` is enabled persistently at 2 GiB as of this review; recheck rather than recreating it.
6. Rebuild/recreate only services affected by the release. Use the correct Compose project and preserve the current cache profile. A typical app+bot release uses `docker compose up --build -d app bot`; do not recreate DB/Redis or poopbot unless the release explicitly requires it. App startup applies Alembic migrations, so step 2 must already be satisfied.
7. Check containers:
   - `docker compose ps`
   - `docker compose logs app --tail=100`
   - `docker compose logs bot --tail=100`
8. Run quick health check:
   - `/health`
   - `/ready` (database reachable and expected migration revision)
   - `TOKEN=... BASE_URL=https://your-domain ./scripts/health_check.sh`
   - login in Telegram Mini App
   - if browser login is used, verify widget is still shown and works on current domain
9. Check bot progress, successful provider/job events, growing restart counters and exceptions. `Up` alone is insufficient. Release `c86c196` adds a Docker healthcheck of recent worker progress and successful polling; it is deployed on the checked VPS. An unhealthy status alone does not trigger Docker restart or send an alert. Do not start a second diagnostic `getUpdates` consumer against the live token.
10. Run the affected manual scenarios below, inspect error/latency changes and record the release outcome. Do not prune rollback images immediately after deployment.

## Backup and Recovery

- Inspect the timer and last successful upload, not only whether `financialassistant-backup.timer` is enabled. The current schedule is daily at 04:15 Europe/Minsk; system journal output may use UTC.
- `scripts/backup_postgres.sh` runs pg_dump, encryption, rclone upload and remote retention. Release `c86c196` adds `backup_queue.py`; deploy it together with the wrapper. Configure a private `BACKUP_SPOOL_DIR` (default `/var/lib/financialassistant-backups`, mode 0700), `BACKUP_SPOOL_MAX_MB` (512), `BACKUP_SPOOL_MAX_AGE_DAYS` (7) and retain `BACKUP_RETENTION_DAYS=30`. Failed uploads remain encrypted in the queue; expired pending copies are explicitly logged. `last-run.json` separates creation/upload/retention and `last-upload.json` records the external snapshot. The queue is not an off-host backup.
- `scripts/verify_postgres_restore.sh` accepts a selected `BACKUP_OBJECT` and encryption password file via the protected environment. It creates a separately named temporary database inside the existing PostgreSQL service and drops that temporary database afterwards. Allow for its disk/CPU cost; do not describe it as a separate server.
- A successful script run verifies restore and the presence of public tables. Full release verification should additionally check the schema revision, critical relationships and selected financial totals in an isolated environment. Never restore over the working database as a test.
- Run `python3 scripts/check_backup_health.py` from external monitoring/systemd to detect unknown/stale snapshots (36 hours by default), failed uploads and retention errors. It reports status without making network calls; an alert delivery channel still needs integration.
- Keep encryption keys recoverable separately from the VPS. Do not print environment files, tokens or database credentials in diagnostics.
- Define rollback compatibility before deployment. Older application images must safely read data written by the new version; a destructive schema downgrade is not a default rollback mechanism.

## Scoped Disk Maintenance

- Treat Docker build cache, rollback images and database volumes as different resources. Estimate reclaimable space before changes; image/cache layers may overlap.
- Preserve FinancialAssistant and poopbot containers, their volumes and needed rollback images. Do not use a blanket prune with volumes for cache cleanup.
- Rotate/reduce journal history only after retaining incident evidence. Clearing package archives is separate from removing installed packages. Disk cleanup is a separate execution task, not an implicit deployment step.

## Manual Smoke After Update

- open app from Telegram Mini App
- verify login works
- verify previously approved user still enters workspace
- verify `pending/rejected` handling still behaves correctly
- verify one long mobile modal and one batch modal on phone
- verify analytics calendar opens and scrolls normally
- verify create/edit of a receipt, plan confirmation/resumption, debt repayment and the work/payment views when their dependencies changed
- verify nested picker/calculator windows, Escape, focus restoration and preserved drafts on narrow and desktop screens
- after a bot-input fix, verify non-text/service-message handling with test fixtures before any deliberate production message test


## Release c86c196 — 2026-10-12

- Originally transferred by a local Git bundle without a GitHub push, with a detached VPS checkout. This records the historical release method; it is superseded by the mandatory GitHub-first workflow above.
- Saved rollback tags: `financialassistant-app:before-reliability-20261012` and `financialassistant-bot:before-reliability-20261012`. Rebuilt one common image and recreated only app/bot with `--no-deps`; DB/Redis/poopbot were not recreated.
- Readiness returned `ready`, database `ok`, revision `20260907_0045`; app and bot health are healthy. New containers have zero restarts on the short post-release check. The previous bot's 6420 restarts are historical and its incident log was retained before recreation.
- Local non-browser suite: 626 passed, two PostgreSQL migration tests skipped. The final backup-diagnostic addition passed its focused suite; 49 focused checks also passed in the exact Linux release image, isolated from the network/production volumes. Request-budget guard passed. No migration or UI changes were included; a full browser suite was not run.
- Manual backup run: creation succeeded, upload returned `http_410`, retention did not run, one encrypted archive remained. Its decryption and PostgreSQL archive listing were checked successfully. The daily timer stays active; a failed upload is still reported as failure.
- One-off off-host copy was restored in a separate temporary PostgreSQL 16 instance with no production volumes/network; the test container was removed. Regular remote retention remains 30 days.
- Remaining reliability work: supported Sber endpoint, automatic alert delivery/restart-burst monitoring, architecture graph rebuild. Product features remain in the staged plan.

## Measurement migration (`20261012_0046`)

- Adds three nullable fields to each of products, purchase rows and plan rows. Old values remain null; there is no inference, financial recalculation or destructive upgrade.
- Before rollout, restore a recent encrypted off-host copy in an isolated PostgreSQL 16 and apply the migration there; compare record counts and monetary totals before/after. Test the exact release image separately from production.
- Save app/bot rollback images before replacing them. Do not automatically downgrade this migration: downgrade drops the new snapshots. Older images can read the expanded schema, but do not preserve measurements when replacing receipt rows. After measurements have been saved, use a forward fix or a compatibility-patched rollback rather than allowing the old editor to overwrite those rows.
- Update from GitHub first. Confirm `/ready` reports `20261012_0046`, serve the new JS/CSS assets, and check app/bot health. Preserve PostgreSQL, Redis and poopbot containers/volumes.

## Release `067f240` — units and package snapshots, 2026-10-12

- Published to GitHub `main` first; clean server `main` advanced using `git pull --ff-only origin main`, with the exact SHA checked before build. Local-bundle deployment is no longer used.
- Refreshed the authorized one-off encrypted computer backup at 19:38 UTC. Restored it in an isolated PostgreSQL 16 with no production volumes. Repeated the restore and applied the exact release-image migration: fingerprints of all pre-existing fields in products, operation receipt rows, plan receipt rows, operations and plans matched; new measurements remained NULL. The first diagnostic attempts exposed temporary-container readiness and PYTHONPATH setup issues; both were corrected and the complete check passed before production migration. Temporary containers were removed.
- Preserved `before-units-20261012` app/bot tags; applied additive migration `20261012_0046`, then recreated only app/bot. Production read-only pre/post fingerprints match for all five checked tables. Readiness reports the new revision and the served measurement helper, bootstrap and receipt stylesheet match local SHA-256 hashes.
- Validation details are in the roadmap. The rollback compatibility restriction above applies once users save measurements; do not drop these columns to roll back the interface.
- Final post-release healthcheck: app, bot, PostgreSQL, Redis and both poopbot containers healthy; all inspected restart counters zero. This is a short post-release check, not a claim about long-term stability. Subsequent documentation/test-only commits may advance the checkout without rebuilding the runtime image from `067f240`.
