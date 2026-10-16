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

## Line discount migration (`20261012_0047`)

- Adds nullable mode/value/subtotal to purchase and plan lines and widens their unit prices from `Numeric(14,2)` to `Numeric(18,6)`. No historical values are recalculated. Compare all prior fields in five core tables, normalizing only numeric trailing zeros when hashing unit prices.
- Refresh and restore the authorized encrypted computer backup before migration. After GitHub publication and server pull, build the exact image, run isolated tests, restore a separate copy and upgrade it with that image before touching production. Do not run destructive migration tests on production.
- Preserve `before-discounts-20261012` app/bot image tags. Apply the migration before starting the new app/bot and verify `/ready` revision `20261012_0047` plus served pricing-helper/bootstrap/receipt-CSS hashes. Recreate only app/bot using `--no-deps`; preserve DB, Redis and poopbot.
- Downgrade intentionally refuses while new-mode rows exist; even an application-only old-image rollback can silently rewrite exact totals through old receipt replacement. Use a forward fix or compatibility-patched writer after these fields have been used.

## Release `1a5bce1` — exact line discounts, 2026-10-12

- Published to GitHub `main` before the clean server checkout advanced with `git pull --ff-only origin main`; exact SHA checked before build. The built Linux image passed 38 focused tests; two optional PostgreSQL tests were verified separately against the disposable local PostgreSQL 15.
- Refreshed the authorized encrypted computer backup at 20:07 UTC, verified restore and then upgraded a separate restored PostgreSQL 16 copy using the published release image. Fingerprints cover every pre-existing field in products, purchase receipt rows, plan receipt rows, operations and plans; unit-price numeric scale alone is normalized before hashing. Values matched and all new mode/value/subtotal fields stayed null. Temporary restore containers were removed.
- Saved app/bot `before-discounts-20261012` images, explicitly migrated to `20261012_0047` and recreated only app/bot with `--no-deps`. Live pre/post fingerprints match: 545 products, 1135 purchase lines, 11 plan lines, 3339 operations, 10 plans. Readiness and three served asset SHA-256 hashes verified. DB, Redis and both poopbot containers remain healthy, without recreation.
- Final post-release check: app, bot, PostgreSQL, Redis and both poopbot containers healthy, all six restart counters zero. This is a short post-release check, not a long-term stability claim. Documentation-only commits after this release may advance the checkout without rebuilding the running `1a5bce1` image. The downgrade/old-writer restrictions above remain in effect.

## Retailer watches — release d2b20fb, 2026-10-16

- Additive revision `20261016_0051`: opt-in product watches, source bindings/latest observations, durable change events. No financial tables/backfill changed. Keep the additive schema on image rollback; downgrade refuses populated tracking tables.
- First provider: public `edostavka.by/product/<id>` cards. Strict URL allowlist, no redirects, bounded response/timeout. Product and size confirmed before linking; source must be Е-доставка/Евроопт. Public website price is explicitly separate from offline purchase history.
- Worker checks up to three due offers per existing reminder cycle; next successful check in six hours, failed request retry in one hour. First observation is silent; unchanged prices and availability/package/conditions transitions do not produce price alerts. Telegram sends bounded batches; delivery errors preserve pending events, successful sends persist acknowledgement. As with existing Telegram delivery, a crash after remote acceptance but before local commit can repeat a message; no exactly-once guarantee is claimed.
- Passed: provider/API owner isolation, link confirmation, unsubscribe, deduplication, stale price preservation, Telegram failure/retry and existing bot regressions (41 checks); core product/API/bootstrap/migration checks (17); complete PostgreSQL 16 upgrade/downgrade chain (5); mobile/desktop linking and product editing (15 browser checks). Live provider reads verified on two public product cards, including discounted pricing.
- Backup gate resolved with explicit user consent on 16 October. A fresh 1,511,904-byte encrypted backup is retained on the computer outside Git/Docker context, mode 0600, in a private directory; its key is retained in a separate private directory. Restored into isolated local PostgreSQL 16 and applied the release migration: all 37 pre-existing table fingerprints unchanged, all three new tables empty. The temporary decrypted database cluster was removed afterwards.
- Published code `d2b20fb` reached the server by `git pull --ff-only origin main`. Built app/bot images, then passed 43 focused checks in the exact isolated Linux app image before activation. Only app and bot were recreated. Readiness reports `20261016_0051`; live retailer fetching from the server succeeded; owner-scoped dashboard reads succeeded with no subscriptions created.
- Rollback tags retained: `financialassistant-app:before-price-watch-20261016` and `financialassistant-bot:before-price-watch-20261016`. Keep the additive schema on rollback. The existing scheduled external backup remains unverified; this authorized one-off computer backup does not repair that separate job.
- Final verification: all 11 changed static-file hashes match the running release; all six containers healthy. App/bot have zero restarts; the four companion services retain their exact image/start/restart state. Telegram health confirms recent successful polling. Running code remains `d2b20fb`; the subsequent documentation-only pull needs no rebuild.

## Source sizes and scan entry — release abfb6dc, 2026-10-16

- New-operation form exposes a text receipt-scanning action immediately. Offers inherit the product size unless a source has its own size; resetting returns inheritance. Explicit catalog selection in a receipt uses that source's size while keeping receipt prices and manual unit choices.
- Source overrides reuse existing offer/variant links. No migration or historical purchase rewrite; schema stays `20261016_0051`. Changing a source size creates/reuses the matching variant without moving old barcodes. Duplicate size records require and retain an explicit variant choice.
- Passed targeted API and browser checks for inheritance/reset, cancellation, atomic validation, barcode conflicts, store SKU lookup, preserved receipt money, explicit variant choice and 320/390/1440 px layouts. The critical API/browser regression matrix passed. Two stale test assumptions were updated: revealing receipt details before input, and treating POST code lookup as read-only.
- Published through GitHub main, then pulled with `--ff-only`. The final isolated Linux image passed 50 focused checks. Only app was recreated, with rollback image `financialassistant-app:before-offer-sizes-20261016` retained. Production configuration presence and host headroom verified without printing secrets.
- Final verification: `/ready` reports ready/database ok/revision `20261016_0051`; nine served static-file hashes match. All six containers healthy. App started at `2026-10-16T09:52:09.128845852Z` with zero restarts; all five companion services retain their prior image/start/restart state. Running app code is `abfb6dc`, bot remains `d2b20fb`. Subsequent documentation-only pull does not require rebuilding.

## Receipt code saving and duplicate grouping — release 880f8f6, 2026-10-16

- Code saving now states its catalog purpose and explains unavailable states before clicking. Valid GTIN is suggested as barcode without losing ambiguous automatic lookup across code kinds. An explicit checkbox choice cancels stale lookup selection; scan unit/identity changes synchronize the checkbox with its draft.
- Explicit scan-review grouping combines compatible repeated GTIN rows, preserving summed quantity, discounts and paid totals. Different prices/discount rates/identities, variable-weight codes, invalid arithmetic and rounding differences stay separate. Raw OCR text remains available. No backend/schema changes or historical data rewrite.
- Passed 34 targeted parser/API/bootstrap checks and 29 browser scenarios, including the user's five-line receipt becoming two lines with total 10.39. Critical matrix: ten API checks and nine browser checks passed initially; the rejected-user login case timed out. Its isolated repeat (both pending and rejected cases) passed without code changes. The exact isolated Linux image passed 12 API/bootstrap checks.
- GitHub main published before server `git pull --ff-only`; rollback image retained as `financialassistant-app:before-receipt-code-merge-20261016`. Only app was recreated. Readiness is ready/database ok on unchanged schema `20261016_0051`; all six changed static hashes match.
- All six containers healthy. App started `2026-10-16T10:31:20.188670258Z`, zero restarts. Five companion services retain their prior image/start/restart state; bot remains on `d2b20fb`. Running app code is `880f8f6`; documentation-only follow-up needs no rebuild.


## Automatic receipt grouping and reversible split — release db7edf7, 2026-10-16

- Compatible verified GTIN rows group on OCR/text reparse; the global merge button is removed. Each group can restore original lines and ordering while retaining catalog/category/unit/code edits. Monetary edits require an inline restore explanation; split rows stay separate during ordinary editing. No backend/schema or historical operation changes.
- Passed 29 local parser/bootstrap checks and 32 browser checks; the final nine code-saving/split cases passed after order/lookup refinements. Critical matrix passed all ten API and ten browser cases. Mobile layout inspected. The exact isolated Linux release image passed 12 API/bootstrap tests.
- Published through GitHub main, pulled with --ff-only, built and activated only app. Rollback image: `financialassistant-app:before-auto-merge-20261016`. Readiness ready/database ok/revision `20261016_0051`; six served static hashes match.
- All six containers healthy. App started `2026-10-16T10:43:14.163242459Z`, zero restarts. All five companion services retain their previous image/start/restart state; bot remains on `d2b20fb`. Subsequent documentation-only pull requires no rebuild.
