# Roadmap

- [x] 2026-09-19: the operation calculator participates in the shared modal stack, so its fields, tabs, and close button remain clickable above create/edit forms and after nested windows. Escape closes only the top eligible window, preserves the operation draft, and returns focus to the calculator button. Browser regressions cover real clicks at 320, 390, and 1440px.

- [x] 2026-09-10: completed plans open for editing directly from operation source chips, plan history, and the activity journal. Enabling recurrence offers the next date and an explicit “Сохранить и возобновить” action; saving reactivates the same plan with its history and linked operations preserved. A read-only server preview and locked save validate dates/end dates, prevent replay of completed occurrences and duplicate reactivation, and refresh reminders. Ordinary edits keep completed plans completed.

## Product Scope
- MVP-1 is implemented: Telegram auth, dashboard summary, operations CRUD, categories/groups, batch operation creation, receipt items, item catalog, debts, plans, currency/FX, admin access states, persisted UI preferences, and Docker Compose runtime.
- MVP-2 backlog: Google auth provider, budgets/limits, richer reports/charts, export/import.
- MVP-3 backlog: deeper Telegram Mini App optimization, async jobs and notifications, advanced analytics, optional position-level analytics.

## Production Track
- Keep Telegram WebApp auth as the primary production path; browser Telegram login remains an optional fallback only when `TELEGRAM_BOT_USERNAME` is configured.
- Maintain release checks for `initData` freshness, admin approval, rejected/pending states, and admin actions.
- Continue mobile-first validation for 320-430px viewports, tap targets, keyboard overlap, sticky actions, modal/sheet behavior, and hover-free critical flows.
- Keep Telegram-specific behavior in the client runtime; backend contracts stay shared between Web UI and Telegram.

## Current Sprint
### Whole-app UX audit — 2026-10-13
- [x] Inspect all 11 navigation sections, analytics/catalog/work subviews and selected entry forms against the visual contract using the current code, local mock renders at 390/1440 px and the user's populated catalog screenshot. Record findings, coverage limits and proposed stages in [the UX audit](UI_AUDIT_2026-10-13.md). No application/server changes in this audit.
- [x] User approved the proposed order: catalog and product workspace → operations/plans/debts → timesheet → analytics/dashboard/currency → remaining directories/settings/admin. Do not treat the audit as a completed redesign.
- [x] Mapped analytics destinations in the consolidation entry below. Structure and Calendar remain; purchases/discounts move to Catalog, currency reports to Currency, trends alongside Structure.
- [ ] Apply the selected stages with filled-state visual review and scoped behavior checks. OCR/retailer work remains deferred while UX is the priority.

### Catalog simplification and icon actions — 2026-10-13
- [x] Make action icons the default in the visual contract, including add/save/edit/delete. Keep navigation and mode labels readable; preserve explicit destructive confirmations and accessible names.
- [x] Separate purchase price changes from the product list. Use compact responsive rows, one selected comparison metric and visible uncertainty flags; retain comparison details with the product history.
- [x] Compact catalog counts/toolbars and mobile product rows. Show product measurements directly, move identity/replacements to a named tab, remove offer/product/price «Ещё» menus in favor of direct icon actions, and retain drafts across tabs.
- [x] Prevent a repeated unchanged receipt-store event from replacing the item input during direct typing after selecting a store.
- [x] Local validation: 733 non-E2E checks passed, 3 skipped; 42 targeted browser scenarios passed (14 product/price/identity/replacement, 4 source/measurement, 3 brand, 21 operation-entry/discount). Updated stale selectors/contracts from prior UI releases and the legacy catalog fixture. Inspected rendered product/list/offer states at 320/390/1024/1100/1440 px; corrected photo overlap, mobile toolbar stacking and title/button overlap. No schema/API or financial-calculation changes.
- [x] Released `6d0d467` through GitHub `main` → clean server `git pull --ff-only origin main` → app-only build/recreation. Assets `20261013-catalog-compact1`; all 19 served file hashes verified. Schema remains `20261013_0050`; eight table fingerprints match. All six containers healthy with zero restarts at the short post-release check; bot, DB, Redis and poopbot start times unchanged. Rollback app image: `before-catalog-20261013`. Manual CI policy retained. Other audit stages remain pending.

### Visual consistency — 2026-10-13
- [x] Add [visual contract](UI_VISUAL_CONTRACT.md) to the UI and engineering source-of-truth docs: shared styling, icon actions, low hint density, sizing and mandatory rendered-state review.
- [x] Replace browser-native receipt store suggestions with an app-styled combobox using shared popup positioning and search normalization; retain manual names and the existing store inheritance flow. Clamp floating popup width to the viewport at 320 px.
- [x] Fill the receipt-mode segmented track with equal buttons. Remove «Ещё» from operation headers and show available preview/history/receipt/session/calculator actions directly as icons; retain accessible names and header wrapping on phones.
- [x] Local validation: 56 selected browser scenarios passed (18 UX, 3 discounts, 21 money-flow/calculator, 14 plans/resumption). One calculator scenario timed out during mock startup before reaching the form and passed in isolation; final 18 UX cases passed after header sizing and ArrowUp corrections. Mobile and desktop screenshots reviewed; syntax/diff checks pass.
- [x] Released `531bc11` via GitHub → server `git pull --ff-only origin main` → build/run. Assets `20261013-visual-consistency1`; all nine changed static file hashes verified. Schema remains `20261013_0050`; full-field fingerprints of eight tables unchanged. All six containers healthy with zero restarts at the final short check; only app/bot recreated. Rollback image tags: `before-visual-consistency-20261013`. Manual CI policy retained.

### Operation entry UX — 2026-10-13
- [x] Reproduce mobile clutter and overlapping long receipts on local test data.
- [x] Implement adaptive creation/editing forms, shared receipt store, compact product search, independent discount details, optional comments/FX/preview and natural receipt height.
- [x] Released `f1b9e28` through GitHub → server fast-forward pull; assets `20261013-operation-ux1`, unchanged schema `20261013_0050`. Main non-E2E suite passed; 54 selected browser scenarios passed across operation entry, discounts, calculator, money flow, plans/resumption, variants and price hints, with eight UX checks repeated after the cents-comparison fix. Run pytest-playwright plans and standalone Sync API receipt fixtures in separate processes. All 12 changed served assets match, all fields of eight data tables match pre-release fingerprints, and all six containers are healthy with zero restarts at the final short check. Only app/bot recreated; rollback images `before-operation-ux-20261013` retained. Actual Telegram keyboard behavior and user comfort still need real-device feedback.
- [x] Desktop refinement: visible comment/receipt amount, open entry tabs, receipt/summary columns from 1100 px and three summary cells at 900–1099 px, one optional settings block, toolbar preview and sticky save. Fixed legacy responsive grid/header conflicts. Local browser validation: 52 selected scenarios (14 UX, 3 discounts, 21 money-flow/calculator, 14 plans/resumption); final UX rerun after visual sizing adjustments. No schema or financial calculation changes. Assets `20261013-operation-desktop2`; released as `95e2266` through GitHub → server fast-forward pull. Readiness and 12 served asset hashes verified; all fields of eight tables match pre-release fingerprints; all six containers healthy with zero restarts at the final check. Only app/bot recreated. Rollback image tags: `before-operation-desktop-20261013`. Final 14 UX checks passed after sizing adjustments; screenshots reviewed for desktop common/discounted/long receipts and laptop layouts. Manual CI retained.
- [ ] User evaluation with real receipts, then further refinement. OCR/retailer/analytics stages remain on hold in the existing plan.

### Reliability And Documentation 2026-10-12
- [x] Investigate the 6420 bot restarts: retained `IndexError` failures match the counter; missing/empty message text reaches unchecked token indexing. Documented in [the operations review](OPERATIONS_REVIEW_2026-10-12.md).
- [x] Activate the existing 2 GiB swap file and persist it in fstab; retain swappiness 10 and verify the generated active swap unit. No application restarts required.
- [x] Update current architecture, product semantics, documentation status and release/VPS checks against `e5eaee1`; distinguish incomplete price history from future observation history.
- [x] Diagnose external providers without modifying them: Sber API host has no address records in checked DNS responses; Yandex quota succeeds while file-resource API returns 410, including direct API access.
- [x] Implement and deploy (`c86c196`): bot non-text/service-message guard, isolated update handling, bounded retries and event-type diagnostics. Retry response delivery after a completed action without replaying the action; tested against a real plan confirmation transaction. Post-release app/bot health checks passed.
- [ ] Worker progress/poll freshness healthcheck deployed and healthy. Remaining: restart-burst monitoring and alert delivery; Docker healthcheck alone does not notify/restart.
- [ ] Verify a supported Sber cash-rate source; bounded provider backoff and DNS/network/HTTP/parse diagnostics are deployed without changing historical FX snapshots. The replacement endpoint is still unverified.
- [ ] Encrypted retry spool, separate upload/retention status and backup-age check deployed. Real HTTP 410 test retained a valid encrypted archive. Remaining: integrate alert delivery; Yandex availability is still an external issue. User selected a one-off encrypted copy on this computer; created and successfully restored into an isolated PostgreSQL 16 container, then removed the test container. Regular retention remains 30 days.
- [ ] Refresh the generated architecture graph with verified scope and commit metadata; current graph remains historical rather than being relabeled as up to date.
- [x] Perform scoped disk cleanup: unused build cache older than seven days (2 GB reserve), journal older than 30 days after retaining incident evidence, and downloaded APT archives. About 4 GiB freed by filesystem reporting; FinancialAssistant, poopbot, volumes and rollback images preserved.

### Purchases And Product Analytics 2026-10-12
- [x] Implement shared RU/EN keyboard search, case/whitespace/ё normalization, literal wildcard handling and safe highlighting across server lists and local pickers/tables. Keep identity matching exact.
- [x] Verify new API search scenarios against SQLite and disposable PostgreSQL (including C locale), priority before pagination, related catalog fields and user isolation.
- [x] Browser checks: receipt/category pickers, operations, plans, brands, table sorting and debts; the new wrong-layout receipt/category scenarios pass. Initial combined-suite fixture conflicts and intermittent timeouts were investigated and affected cases pass in isolation.
- [x] Pre-release read-only VPS validation: normal and wrong-layout milk/bread/coffee queries return identical catalog and operation records. Replaced the slow first SQL draft before switching services: measured combined catalog+operation checks fell from 1.4–3.8 s to 0.25–0.46 s (previous version 0.11–0.24 s; small sample, not an SLA).
- [x] Deploy the verified search iteration (`918f486`) with asset version `20261012-search1`; readiness returns 200 and the served search-script SHA-256 matches the local source. App and bot healthchecks pass with zero restarts; final read-only catalog+operation checks took 0.16–0.37 s. No schema change or purchase-data rewrite.
- Validation: 652 non-E2E tests passed, 2 optional migration tests skipped; request-budget guard 6 passed; 7 API cases plus 16 contract examples passed on disposable PostgreSQL. The 78 targeted browser scenarios passed across isolated groups/retries (initial fixture conflicts and Telegram-mock login timeouts were not treated as product failures). Exact Linux release image: 30 passed, 1 skipped because Node is absent.
- Rollback images: `financialassistant-app:before-search-20261012` and `financialassistant-bot:before-search-20261012`; preceding checkout `2dfad73`. PostgreSQL, Redis and poopbot were not recreated. Normal and wrong-layout queries were compared in READ ONLY transactions on the live catalog before and after the release.
- [x] Stage 2a implementation: optional sale units/package contents on products, receipt and plan snapshots, explicit legacy unknown values, stale-client protection, compatible nullable migration `20261012_0046`. No money recalculation or historical backfill.
- Stage 2a validation: 665 non-E2E passed, 2 optional PostgreSQL tests skipped in that run; the full migration suite separately passed 5/5 on disposable PostgreSQL 15. All 12 new API scenarios also pass on PostgreSQL. Browser groups: 31 receipt/catalog scenarios + 16 plan/work scenarios + the extra 320 px measurement case passed; new fields were checked at 320/390/1440 px. Exact Linux image: 34 passed, 2 optional migration tests skipped, one existing anyio deprecation warning. Browser fixtures now wait for startup and mock the external Telegram SDK; a larger local HTTP listen backlog fixes observed asset connection resets.
- [x] Stage 2a deployed from GitHub `main` at `067f240`, asset version `20261012-units1`, schema `20261012_0046`. A refreshed encrypted local off-host copy was restored to isolated PostgreSQL 16; upgrading that copy preserved all old fields in five core tables and left all new fields null. Production pre/post fingerprints of those same tables match; readiness and three served asset hashes pass. App and bot are healthy with zero restarts at the post-release check; DB/Redis/poopbot remain healthy. Rollback tags: `financialassistant-app:before-units-20261012` and `financialassistant-bot:before-units-20261012`. No DB/Redis/poopbot recreation.
- Next: line-total discounts and comparable purchase/package/mass/volume metrics. Reliability follow-ups (alerts, provider recovery and graph regeneration) remain tracked separately.
- [x] Stage 2b implementation: line discount amount/percent/direct paid total, independent calculation mode/reason, precise paid totals and six-decimal derived prices, stale-client guard, plan confirmation and delete/restore round trips. Legacy receipt values are preserved. Preview, FX receipt totals and discount savings use rounded line totals; unknown original prices remain unknown.
- [x] Stage 2b local validation: 688 non-E2E passed, two optional PostgreSQL tests skipped in that run; all six migration checks passed separately with PostgreSQL 15, including the full migration chain. New discount + measurement API suite: 33 passed on PostgreSQL. Browser regression: 32 receipt/catalog/autofill, 9 plans, 7 resumption, 13 work KPI tests; three new discount workflows at 320/390/1440 px. Run work KPI and plan suites in separate processes because their Playwright lifecycles conflict. Refreshed encrypted computer backup restored to isolated PostgreSQL 16 successfully before rollout.
- [x] Stage 2b deployed from GitHub `main` at `1a5bce1`, asset version `20261012-discounts1`, schema `20261012_0047`. Exact Linux image: 38 passed, two optional PostgreSQL tests skipped (run separately above). Restored-copy PostgreSQL 16 migration preserved every pre-existing field in five core tables after normalizing numeric trailing zeros; production pre/post fingerprints also match. Readiness and pricing-helper/bootstrap/receipt-CSS hashes verified. Rollback images retained as `before-discounts-20261012`; only app/bot recreated. Final post-release check: app, bot, PostgreSQL, Redis and both poopbot containers healthy, all six restart counters zero. This is a short post-release check, not a long-term stability claim.

- [x] Stage 2c implementation: distinct receipt counts across duplicate rows/source offers, separate pieces/packages/kg/l/content pieces, snapshot-only measurement totals with unknown coverage, per-currency paid line spending, shared canonical frequent-product ranking and product drilldown. Old scalar API totals remain compatibility-only. Discount purchase counts deduplicate receipt IDs. No schema migration or financial-data writes.
- [x] Stage 2c local validation: 698 non-E2E tests passed; two optional PostgreSQL migration tests skipped (schema unchanged). All 10 new API scenarios separately passed on disposable PostgreSQL 15. Analytics browser regression: 31 passed, including new mixed-unit/currency/legacy-preference/product-drilldown scenarios at 320/390/1440 px. Screenshots reviewed; mobile summary widened for measurements. Changed JavaScript syntax and diff whitespace checks passed.
- [x] Stage 2c deployed from GitHub `main` at `f00d7cb`, asset version `20261012-quantities1`; server updated through `git pull --ff-only`. Exact Linux image: 110 selected API/regression tests passed with one existing anyio deprecation warning. Read-only production parity matched distinct receipts, row counts and paid totals per currency against independent SQL for every user. Slowest full-history aggregation in that one loaded-container check was 0.732 s; this is not a latency SLO. All fields of five core tables match pre/post fingerprints. Schema stays `20261012_0047`; readiness, three served asset hashes and actual app/bot image IDs verified. All six containers healthy with zero restarts at the final check; only app/bot recreated. Rollback images retained as `before-quantities-20261012`. Stage 2 is complete; next is stage 3 (compact product/receipt cards and unified product modal).
- [x] Stage 3 implementation: tabbed product workspace, compact known receipt rows, source/receipt entry points, retained bulk merge/detach/history deletion and paged purchase drilldown. Forms/photo drafts survive tab changes and nested dialogs; opening a purchase cannot replace an existing edit draft. No schema/backend arithmetic changes.
- [x] Stage 3 local validation (2026-10-13): 698 non-E2E passed; two optional migration checks skipped (schema unchanged). Final receipt/catalog/picker/autofill browser group: 60 passed; plans/resumption: 16 passed separately. Five product-workspace cases passed again after compact desktop layout refinement, including 320/390/1440 px, preserved drafts, 51-row pagination/return focus, late-response rejection, nested-edit protection, detach, price deletion and bulk merge. Screenshots reviewed for compact/expanded receipt rows and product prices. Changed JavaScript syntax and diff whitespace checks pass.
- [x] Stage 3 deployed on 2026-10-13 from GitHub `main` at `8ebbb87` through `git pull --ff-only`; asset version `20261012-product-ui1`. Exact Linux image: 75 selected regression tests passed (one existing anyio deprecation warning). Five core-table fingerprints match before/after; schema stays `20261012_0047`. Readiness, five served asset hashes and actual app/bot image IDs verified. All six containers healthy with zero restarts at the final short post-release check; only app/bot recreated, DB/Redis/poopbot retained. Rollback images: `financialassistant-app:before-product-ui-20261013` and `financialassistant-bot:before-product-ui-20261013`. Stage 3 is complete; next is stage 4 (product identification and complete price observations/graphs).
- [x] Stage 4a implemented: complete actual-purchase observations, stepped price graph, per-step/period percentages, date/type/unit filters, separate currency/shop/package series and receipt links. No schema migration or receipt writes. Identifiers/confirmed variants and catalog-wide change views remain stage 4b. Local validation: 704 non-E2E passed, two optional migration checks skipped (schema unchanged); all six new API scenarios also passed on disposable PostgreSQL 15. Receipt/catalog browser regression: 62/63 initially passed, with one old picker form-open timeout; all 13 picker/workspace/history cases passed on rerun, and all five picker cases passed again using the shared higher-backlog static fixture server. Three new history cases additionally verified preserved series/focus after an edited receipt at 320/390/1440 px; screenshots reviewed. JavaScript syntax/diff checks pass. Exact Linux image: 81 selected tests passed (one existing anyio deprecation warning).
- [x] Stage 4a deployed on 2026-10-13 from GitHub `main` at `b4b2afe` through server `git pull --ff-only`; asset version `20261013-price-history1`. Read-only production parity for the 25 offers with most receipt rows matched all 389 observations, exact paid prices and purchase dates against independent SQL; normalized coverage also matched. Slowest sampled history query was 0.154 s in that check, not a latency guarantee. Five core-table fingerprints match before/after; schema stays `20261012_0047`. Readiness, five served asset hashes and actual runtime image IDs verified. All six containers healthy with zero restarts at the final short check; only app/bot recreated. Rollback tags: `financialassistant-app:before-price-history-20261013` and `financialassistant-bot:before-price-history-20261013`. Next: identifiers/confirmed variants and catalog-wide change views (stage 4b), then OCR/retailers/analytics consolidation.
- [x] Stage 4b1 implemented: optional manual package variants/GTINs, source-specific retailer identifiers/titles/links, explicit offer-variant mappings and opt-in catalog identifier search. No receipt defaults or historical amounts are rewritten. Merge/detach/archive paths retain identity integrity. Revision `20261013_0048` adds three empty tables; nonempty downgrade is refused. Local validation: 710 non-E2E passed (two unrelated optional PG migration checks skipped), all five new API scenarios also passed on disposable PostgreSQL 15, full migration upgrade/downgrade/upgrade passed there; 26 browser catalog/workspace/price/identity cases passed at mobile/desktop sizes. Three identity cases additionally verified dirty-form preservation after an offer refresh. Fresh authorized encrypted local backup was restored to isolated PostgreSQL 16; upgrading to `20261013_0048` preserved every field in five core tables and left the three new tables empty. Exact Linux image: 87 selected checks passed (one existing anyio deprecation warning).
- [x] Stage 4b1 deployed on 2026-10-13 from GitHub `main` at `40cf7ea` through server `git pull --ff-only`; asset version `20261013-identity1`, schema `20261013_0048`. Production pre/post fingerprints match in all five core tables. The new registry reads successfully and all three new tables are empty; no automatic matching/backfill ran. Readiness, five served asset hashes and runtime image IDs verified. All six containers healthy with zero restarts at the final short check; only app/bot recreated, DB/Redis/poopbot retained. Rollback image tags: `financialassistant-app:before-identity-20261013` and `financialassistant-bot:before-identity-20261013`. Keep the additive schema on an application rollback; after identity data has been entered, prefer a forward fix because older merge/detach code does not maintain variant mappings. Next: explicit variant selection and immutable purchase identity, confirmed replacement relations and catalog-wide price changes (stage 4b2).
- [x] Stage 4b2 implemented: explicit receipt package selection, historical name/GTIN snapshots through operation/plan edit, confirmation and operation restore; catalog changes preserve those snapshots. Manual dimensions/product changes clear identity; quantity/discount changes preserve it. Revision `20261013_0049` adds nullable JSON columns without backfill and refuses populated downgrade. Local validation: 717 non-E2E checks passed, two unrelated optional migration checks skipped; 43 receipt/catalog browser cases passed, with all three final variant scenarios additionally checking plan hydration/product unlink at 320/390/1440 px. Ten API cases passed on disposable PostgreSQL 15; the first run used leftover pre-migration tables and failed once, then passed on clean fixture tables. Fresh PostgreSQL full upgrade/downgrade/upgrade passed. Activity summaries also retain repeated offer rows and detect identity-only changes. Exact Linux image: 68 selected checks passed (one existing anyio deprecation warning).
- [x] Stage 4b2 deployed on 2026-10-13 from GitHub `main` at `00667a9` through server fast-forward pull; schema `20261013_0049`, assets `20261013-receipt-variant1`. Fresh encrypted local backup (`20261012T221519Z`, UTC) restored to isolated PostgreSQL 16; migration preserved all pre-existing fields in eight tables and left historical snapshots NULL. Production pre/post fingerprints match those eight tables (545 products, 1,135 operation receipt rows, 11 plan receipt rows, 3,339 operations, 10 plans; identity registry still empty). Existing operation/plan serialization, readiness and six served asset hashes verified. Each app/bot container matches its corresponding built image; the initial helper incorrectly expected both to share an image ID and was corrected. All six containers healthy with zero restarts at the final short check; only app/bot recreated. Rollback tags: `financialassistant-app:before-receipt-variant-20261013` and `financialassistant-bot:before-receipt-variant-20261013`. Keep the additive schema; after snapshots are used, prefer a forward fix because the previous application drops them when replacing receipts. No OCR upload, retailer polling or notification delivery enabled.
- [x] Stage 4c implemented: catalog-wide receipt price comparisons, separate period/last-step direction, counts, normalized package prices and reference-price cost of the latest purchased volume. A single streaming query, owner isolation, date/layout-aware search and pagination; lazy responsive UI with filtered chart drilldown. No schema or financial writes. Local validation: 723 non-E2E checks passed, two optional migration tests skipped (no schema change); all 12 summary/history API checks passed on disposable PostgreSQL 15. All 26 catalog/workspace/chart/browser cases passed after the existing column-drag test was corrected to scroll its header handle into view; no resize assertions were removed. New summary scenarios verify lazy loading, pagination, filters, matching chart series, focus return, retry and cleanup at 320/390/1440 px. Exact Linux image: 60 selected checks passed (one existing anyio deprecation warning).
- [x] Stage 4c deployed on 2026-10-13 from GitHub `main` at `3bd3b69` through server fast-forward pull; assets `20261013-price-changes1`, unchanged schema `20261013_0049`. Read-only production parity over the 25 most-used active offers matched 29 series / 401 observations across paid/regular and unit/normalized modes against the existing full history service, including exact paid last-volume totals. Slowest sampled catalog summary read was 0.829 s (not a performance guarantee). All fields in eight core/catalog-identity tables match pre/post fingerprints. Readiness, six served asset hashes and corresponding app/bot image IDs verified; all six containers healthy with zero restarts at the final short check. Only app/bot recreated; DB/Redis/poopbot retained. Rollback tags: `financialassistant-app:before-price-changes-20261013` and `financialassistant-bot:before-price-changes-20261013`; no data/schema rollback is needed for this read-only release. Confirmed replacement relations, receipt hints, OCR and retailer polling remain pending.
- [x] Stage 4e confirmed package replacements deployed (`6227e39`); receipt-time hints are deployed.
- [ ] Stages 5–7: OCR, retailer sources/notifications and analytics consolidation.
- Implementation authorized on 2026-10-12; the first reliability release is deployed (`c86c196`). Stage 1 (keyboard-layout search) is deployed as `918f486`; stage 2a (units/package snapshots) is deployed as `067f240`; stage 2b (line discounts) is deployed as `1a5bce1`; stage 2c (comparable quantity metrics) is deployed as `f00d7cb`; stage 3 (product workspace and compact receipt rows) is deployed as `8ebbb87`; stage 4a (actual-purchase price history) is deployed as `b4b2afe`; stage 4b1 (manual variants/identifiers/retailer references) is deployed as `40cf7ea`; stage 4b2 (explicit receipt variant snapshots) is deployed as `00667a9`; stage 4c (catalog-wide price comparisons and last-volume costs) is deployed as `3bd3b69`; stage 4d (receipt-time paid-price hints) is deployed as `50b7da7`; stage 4e (confirmed package replacements) is deployed as `6227e39`; OCR and automated retailer stages remain pending; [the free OCR pilot](OCR_PILOT_2026-10-12.md) is complete as an experiment, not a production scanning feature. See [the decision record](RECEIPTS_AND_PRODUCT_ANALYTICS_PLAN.md).
- Agreed direction: optional units and package sizes with purchase snapshots, discounts on receipt line totals, complete price observations, compact known-product receipt cards, RU/EN keyboard-layout search, and consolidation of rarely used analytics views.
- Confirmed after clarification: preserve structure and calendar in their current locations; receipt recognition should produce a reviewable draft before saving. Provider selection and integration details remain to be designed.
- Include retailer links, product identifiers, catalog matching, price-change charts and configurable notifications in planning. Manual catalog identity forms are available; no automatic matching, polling schedules or external integrations have been activated.
- Consolidate product and offer actions into one product modal while preserving existing workflows; keep common receipt edits directly accessible. Browser access to Edostavka is confirmed; automated integration remains to be evaluated.
- Follow the staged plan with regression gates, compatible schema changes and verified off-host backup restoration before migrations. The October 11–12 upload failures remain open despite the earlier completed backup milestone below; a different explicitly chosen destination can satisfy the release requirement.

### Work KPI And Period Earnings 2026-09-09
- Hourly and daily salary estimates are integrated into the corresponding hours/days KPI cards. Their salary month and fact/forecast basis remain explicit; the denominator stays the salary month's work norm, excluding one-off extras.
- The salary cycle shows each actual payment amount once, with its operation action preserved. Empty extras and duplicate received/total/zero-remaining cards are hidden; incomplete and forecast states remain visible.
- Work statistics now show actual earnings for month, year, all-time, and custom dates, plus monthly amounts. Earnings follow payment dates and include explicit payroll links and current/historically confirmed payroll categories, once per live income operation. Deleted operations, unrelated income, future payments, and forecasts are excluded. Currency conversion uses stored base-currency snapshots; different base currencies stay separate.
- All-time statistics include the earliest known payroll payment. Rapid period changes cancel old requests and prevent stale responses from replacing the selected period's earnings.

### Technical Debt Audit 2026-07-16
- [x] Complete a read-only audit of data integrity, background delivery, deployment, performance, security, observability, and test coverage. Baseline: non-E2E tests pass; the isolated Telegram login-readiness race found by the combined browser run is fixed and covered by deterministic smoke CI.
- [x] P0: make operation rollback lossless and transactional.
  - Restore foreign-currency amounts, receipt positions, linked currency settlement, and every edited operation field from a server-side snapshot instead of reconstructing an operation in the browser.
  - Preserve `icon` and `include_in_statistics` when rolling back category changes; add create/edit/delete rollback coverage for operations and categories.
- [x] P1: make every scheduled Telegram delivery idempotent across overlapping bot instances.
  - Apply the currency-alert locking pattern to plan reminders, debt reminders, and digest delivery; persist a delivery key before sending and cover restart/deploy races.
- [x] P1: add a tested PostgreSQL backup and recovery path.
  - Stream a compressed encrypted daily dump to storage outside the VPS, keep no permanent local archive, apply bounded remote retention, monitor upload/cleanup failures, and verify restoration quarterly and before risky migrations.
  - Production uses a root-only `rclone` remote to Yandex Disk, an encrypted daily systemd timer at `04:15 Europe/Minsk`, and 30-day hard-delete retention with no permanent local dump.
  - The first production archive and disposable restore drill passed on 2026-07-19 with 23 public tables; the encryption recovery key also has a protected copy outside the VPS.
- [x] P1: turn deployment checks into real readiness gates.
  - Run the complete Alembic chain against a fresh PostgreSQL database in tests; add an application readiness check and make the bot wait for readiness rather than only for a started container.
- [ ] P1: reduce frontend startup cost and stale-asset risk.
  - Replace the sequential graph of more than 100 scripts with a bundled/versioned build, immutable asset caching, and a small versioned entry document.
  - Manifest scripts now fetch in parallel while preserving execution order; versioned assets are immutable and the entry document revalidates. Replacing the manifest graph with a real bundle remains pending.
- [x] P1: bound expensive and stalled requests.
  - Keep `all_time` cashflow/search aggregation in SQL with pagination or explicit limits; add client request timeouts and cancellation without breaking coalesced dashboard panels.
- [x] P1: distinguish dashboard loading, empty, stale, and failed states.
  - Do not cache request failures as valid zero data; retain the last successful panel result, expose a local retry, and add structured timing/error logs per panel.
- [x] P2: harden runtime configuration without requiring a server `.env` migration.
  - First add a non-secret preflight check and warning for the current VPS environment value. Preserve the existing valid `production`, `development`, or `test` values and do not enable a new startup failure in the same deployment.
  - After production is verified, restrict `APP_ENV` to the explicit enum so future typos fail startup; require non-default secrets, database credentials, admin IDs, Telegram token, and allowed CORS origins only for the production profile.
  - The production VPS passed the non-secret strict preflight on 2026-07-16. `APP_ENV` is now an explicit normalized enum, and production startup rejects default database credentials or unsafe CORS origins.
- [ ] P2: reduce browser-side injection impact.
  - Remove dynamic HTML from toast rendering, define a Content Security Policy, and review long-lived token storage together with the existing in-place session recovery flow.
  - Dynamic toast HTML is removed and CSP, MIME-sniffing, and referrer headers are active. The token-storage tradeoff remains pending because moving from persistent storage changes Telegram WebApp login behavior.
- [x] P2: make optional infrastructure self-healing.
  - Retry Redis initialization after an initial outage and expose cache availability in diagnostics without making Redis a hard dependency.
- [x] P2: add continuous quality and performance gates.
  - Run lint, type checks, dependency/security checks, migration tests, and deterministic browser smoke tests in CI; track SQL/query duration and response size in addition to request count.
  - GitHub CI now enforces dependency consistency and vulnerability audit, Ruff, a clean core/schema mypy baseline, Python/JavaScript syntax, non-E2E tests, PostgreSQL migration round-trip, and deterministic browser smoke; runtime metrics expose SQL count/latency and endpoint response size.
- [x] P2: keep local and production runtime definitions comparable.
  - Add the same application health/readiness behavior to local Compose, document the intentional port/proxy differences, and remove the remaining combined-release login race.
  - Local Compose now gates the bot on application readiness, and the delayed Telegram startup/session-recovery browser test is part of CI.

#### Audit implementation status
- Completed in code: lossless rollback, idempotent reminder/digest claims, readiness/migration gates, bounded requests, stale dashboard states, CSP-safe toasts, Redis retry/diagnostics, runtime metrics, and baseline CI.
- Production operations verified: strict runtime preflight, off-host encrypted backup schedule, bounded retention, and the first restore drill.
- Remaining engineering backlog: frontend bundling and persistent-token review.

### Currency Rate Unit Audit 2026-07-16
- [x] P0: normalize NBRB rates to the price of one currency unit.
  - Divide `Cur_OfficialRate` by `Cur_Scale` for every provider response instead of treating the nominal quote as a single-unit rate.
  - Keep USD/EUR unchanged and correctly normalize RUB `/100`, CNY `/10`, and PLN `/10` for the currently supported currencies.
  - Add migration `20260716_0031` to normalize existing automatic NBRB snapshots without changing manual rates or historical trades.
- [x] P0: preserve sufficient rate precision across the whole product.
  - Use one adaptive 4-6 digit formatter in currency forms, operation FX fields, previews, dashboard, analytics charts, trade lists, and admin diagnostics.
  - Cover `5500 RUB`, official single-unit rate `0.037044`, and an actual paid total of `194.70 BYN` producing a deal rate of `0.0354` in API and browser tests.

### Session Timing 2026-07-16
- [x] P1: show when the current session started and when its token was last renewed.
  - Read the root session start and token issue time from JWT claims; keep `Начата HH:MM` stable and update `Обновлена HH:MM` after automatic or manual renewal.
  - Preserve the open operation modal and every unsaved field while renewing.
  - Done 2026-07-19: the sidebar now labels the countdown as `Осталось`, shows the calculated token end time as `Завершится HH:MM`, and updates both after an in-place renewal.

### Global Action History 2026-07-20
- [x] P2: add a compact cross-section action center without creating a second audit source.
  - The title-bar history control opens a content-sized desktop drawer and a mobile bottom sheet with the seven latest persisted activity events; `Вся история` reuses the existing paginated activity modal.
  - Activity responses now include entity labels, compact summaries, existence state, and backend-owned action capabilities.
- [x] P2: add contextual navigation and safe quick actions.
  - Existing operations, debts, plans, categories, groups, catalog positions, currency trades, and the currency portfolio open in their native section/modal.
  - Desktop actions appear on hover/focus; mobile actions remain visible. Deleted operations and categories expose `Восстановить` only when an unused server-side restore snapshot exists.
- [x] P2: connect successful mutations, toasts, and the action center.
  - Confirmed financial POST/PATCH/DELETE requests refresh an open feed or set a session-local new-activity dot while collapsed; related success toasts expose a compact history action.
  - Errors remain transient toasts and are not written into the audit feed as successful actions.
- [ ] P2: add conflict-safe rollback for historical update events.
  - Enable only for the latest compatible event when the current entity still matches that event's `after` state; reject stale rollback atomically on the backend.
  - Receipt and linked FX changes require complete before/after snapshots. Do not expose a generic `Отменить` until those domain snapshots and conflict tests exist.
- [ ] P3: add full-history filters and optional persistent read state after real-data usage validates the compact feed.

### Interface Settings And Activity Geometry 2026-07-21
- [x] P1: make the interface scale affect text consistently instead of only rem-based layout dimensions; persistence, computed font growth, and 115% mobile overflow are browser-tested.
- [x] P1: keep the complete `Вся история` footer inside the recent-actions drawer and give the first full-history event enough hover clearance below the modal header.
- [x] P2: expand the category icon picker from current production category context and organize the larger pool into compact thematic groups with bounded scrolling on desktop and mobile.

### Currency Balance Settlement 2026-07-16
- [x] P0: make foreign-currency expenses optionally reduce the tracked currency balance.
  - Replace the ambiguous `Оплата с валютной карты / Использовать` wording with one explicit switch: `Списать из валютного остатка`.
  - Keep the switch off by default because an operation may use untracked cash or an external card.
  - For an operation and settlement in the same foreign currency, synchronize settlement quantity with the original operation amount and settlement rate with the operation FX rate.
  - For a base-currency operation or a different settlement currency, retain explicit currency, quantity, and rate controls.
  - Show the amount available for historical settlement and the projected balance after the operation; exclude the operation's existing linked settlement while editing.
  - Done 2026-07-16: the existing settlement switch now preserves the operation currency, directly synchronizes matching foreign amounts/rates, and shows a date-aware safe debit plus projected balance.
- [x] P0: support retrospective changes safely.
  - Enabling settlement on an old operation creates the linked currency debit without changing the operation's original currency.
  - Editing amount, currency, rate, or date updates the linked debit; disabling settlement restores the balance; deleting the operation removes its linked debit.
  - Preserve the single cashflow expense: the linked currency trade remains an inventory movement and is not counted as another expense.
  - Done 2026-07-16: old foreign operations can add, update, disable, re-enable, and delete linked settlements without changing their original currency; operation deletion now removes the linked trade explicitly instead of relying only on database cascade settings.
- [x] P1: cover same-currency, cross-currency, insufficient-balance, create, edit, disable, and delete flows in API/frontend/browser tests, including mobile modal geometry.
  - Covered by the complete operations/currency API suites, frontend contracts, and a browser scenario for retrospective USD settlement with desktop and 390px overflow checks.

### Dashboard Loading Recovery 2026-07-16
- [x] P0: normalize cached debt issuance/repayment dates before all-time cashflow comparison; production traceback confirmed mixed cached strings and database `date` values caused dashboard summary `500` responses.
- [x] P0: keep explicit loading states for dashboard plans/debts and their full sections, then show a local retry action only after the final failure.
- [x] P0: version the complete frontend asset graph so Telegram WebView cannot mix new JavaScript with stale debt KPI or modal CSS.
- [x] P1: keep debt KPI semantics consistent: receivables positive, payables negative, and net position colored from its sign.

### Compact Modal Actions 2026-07-16
- [x] P1: standardize modal-header utility actions as compact icon-only controls with equal dimensions, accessible labels, and tooltips while keeping primary form actions textual.
- [x] P1: make sidebar and operation-modal session renewal controls icon-only without changing the in-place refresh behavior.
- [x] P1: visually separate operation-modal session renewal from record-specific journal/calculator actions while preserving equal control dimensions.
- [x] P0: render the official BYN sign through the bundled NBRB font in the shared formatter, selectors, previews, and every money surface.

### Currency, Debt KPI And Position Metrics 2026-07-16
- [x] P0: keep BYN rendering centralized in the shared currency formatter and cover the bundled official glyph/font contract.
- [x] P1: add contextual debt KPI states: receivables positive, payables negative, and net position colored by sign while zero remains neutral.
- [x] P1: make quantity the default position-ranking metric, keep amount visible in ranking context, and leave purchase/event count in the KPI summary and optional metric switch.

### Analytics Prices, Discounts And Drilldown Navigation 2026-07-16
- [x] P0: keep the category structure chart inside its fixed desktop panel and responsive mobile bounds.
  - Size the donut from the available card width and height instead of allowing a `36rem` square inside a `34rem` panel with padding.
  - Keep SVG hover expansion clipped to a deliberate chart viewport and cover 320/390/768/desktop widths without page overflow.
  - Done 2026-07-16: donut sizing now uses the card's available inner height, SVG overflow is clipped, and desktop geometry asserts that the chart remains inside the equal-height card.
- [x] P0: make contextual back navigation visible and stateful.
  - Preserve the existing section-back stack during analytics/category/position drilldowns instead of clearing it in the following section switch.
  - Use one compact icon button with a destination tooltip; restore the analytics tab, period, selected position, filters, sort order, and useful scroll context.
  - Keep ordinary sidebar navigation as a fresh navigation that clears contextual history.
  - Done 2026-07-16: contextual switches preserve the stack and open the destination at the top so the icon Back control is visible; Back restores the source tab, position analytics state, filters, and scroll position.
- [x] P1: add a dedicated `Цены и скидки` analytics tab and remove price/discount rankings from `Структура`.
  - Reuse the global analytics period and present `Цены` / `Скидки` as an internal segmented mode.
  - Price view: ranked bars for percentage change, absolute change, and current average price; expose previous/current purchase counts so one-off observations are not presented as reliable trends.
  - Discount view: ranked bars for saved amount, discount rate, and purchase count; filter by all/promo/coupon/loyalty-points using compact chips.
  - Selecting an item opens a focused time view and bucket drilldown to matching operations. Keep popular positions in `Позиции`, categories in `Структура`, and defer unrelated anomalies/largest operations to a future observations surface.
  - Done 2026-07-16: `Структура` contains only category/group composition. `Цены и скидки` reuses the global period and provides price/discount modes, metric rankings, discount-type filters, compact KPI summaries, selected-item timelines, and operation drilldown.
  - Done 2026-07-16: highlights include template IDs, absolute price change, current/previous sample and purchase counts, price timelines, discount type breakdowns, and type-aware savings timelines without an additional request.
- [x] P1: make position analytics visibly interactive.
  - Add restrained hover/focus motion, stronger active color, pointer affordance, and an explicit operation-drilldown tooltip to non-empty ranking/bucket controls.
  - Respect `prefers-reduced-motion`; do not add persistent pulse or layout-shifting animation.
  - Done 2026-07-16: ranking rows and non-empty timeline/matrix buckets use restrained hover/focus motion, stronger feedback, explicit pointer behavior, and operation-drilldown tooltips with reduced-motion support.
- [x] P1: replace passive operation filter labels with a consistent active-filter strip.
  - Render compact label/value chips with individual removal and one icon-only reset-all action.
  - Ensure reset-all clears every visible drilldown constraint, while Back restores the source analytics context.
  - Done 2026-07-16: active filters render as compact label/value controls with individual removal plus one icon-only reset-all action; drilldown Back remains independent from filter reset.
- [x] P1: extend tests and visual validation.
  - Cover price/discount API semantics, comparison sample counts, discount-type filtering, ranking sort, bucket drilldown, Back restoration, filter removal, and desktop/mobile overflow.
  - Done 2026-07-16: dashboard/API and frontend contracts pass; the full analytics browser suite covers Back restoration, filter removal, structure containment, and the new tab at 320/390/768/1440px. Targeted operations and session browser regressions also pass.

### Session Reliability And Telegram Startup 2026-07-16
- [x] P0: make Telegram Mini App startup reliable without a manual reload.
  - Replace the one-shot `Telegram.WebApp.initData` check with a bounded readiness wait and short backoff while the branded session-check animation remains visible.
  - Retry automatic login on `pageshow` and when the document becomes visible if no token exists and Telegram later provides `initData`.
  - Coalesce startup/login attempts so SDK readiness, visibility events, and user actions cannot submit duplicate authentication requests or bootstrap the app twice.
  - Stop waiting after a small fixed deadline and show the existing actionable login state instead of leaving an endless loader.
  - Cover delayed `initData`, immediate `initData`, absent Telegram SDK, resumed WebApp, failed authentication, and duplicate-event behavior with runtime and browser tests.
  - Done 2026-07-16: startup keeps the branded checking state while waiting up to five seconds for Telegram launch data, retries on `pageshow`/visibility recovery, and coalesces both authentication and bootstrap work.
- [x] P0: add in-place session renewal that never closes an operation modal or clears a receipt draft.
  - Add an authenticated `POST /api/v1/auth/refresh` endpoint that renews only a still-valid approved session and returns the new token with its exact expiration time.
  - Replace only the client token and expiration metadata; do not call `bootstrapApp()`, `logout()`, section navigation, modal close handlers, or data reloads after a successful refresh.
  - Coalesce parallel refresh attempts and renew automatically five minutes before expiry while the document is active; recheck immediately after the app returns to the foreground.
  - Keep a bounded absolute session lifetime (target: 12 hours) before full Telegram authentication is required.
  - Cover refresh authorization, expiry boundaries, rejected/deleted users, parallel requests, modal continuity, and preservation of a large receipt form.
  - Done 2026-07-16: authenticated `/auth/refresh` rotates a still-valid JWT, preserves its original session start, enforces a configurable 12-hour absolute lifetime, and returns exact expiration metadata without a database migration.
  - Done 2026-07-16: the shared request pipeline performs one background recovery and retries the original request after `401`; it no longer calls destructive logout for an authentication timeout.
- [x] P1: expose a quiet session status and manual renewal control.
  - Add a compact status to the user area, updated every 30 seconds: normal remaining time, an amber warning near expiry, and an icon button with the tooltip `Продлить сессию`.
  - Keep the control usable in desktop, mobile, and Telegram layouts without competing with primary operation actions.
  - Show success/failure feedback through the existing toast system and keep renewal fully background-safe for open modals.
  - Done 2026-07-16: the user block shows remaining time and a compact renewal control; create/edit operation headers expose the same control while a modal covers the sidebar. Automatic checks run every 30 seconds and refresh inside the final five-minute window.
- [x] P1: use the same branded authorization motion in browser and Telegram WebApp flows.
  - Explicitly enter the shared session-check state before stored-token validation and Telegram auto-login, reusing the lightweight logo float/pulse and `prefers-reduced-motion` behavior.
  - Do not add an artificial delay: animation remains visible only while readiness, authentication, or bootstrap work is actually pending.
  - Done 2026-07-16: stored-token validation and Telegram auto-login explicitly reuse the existing lightweight logo motion, with no artificial delay and unchanged reduced-motion behavior.
- [x] P1: preserve unsaved work if a session has already expired.
  - Do not invoke the current destructive `logout()` path immediately on an authentication timeout because it closes modals and clears runtime state.
  - Present a compact re-authentication layer over the current app, keep operation/receipt fields mounted, and resume the interrupted action after successful authentication when safe.
  - Treat explicit user logout and account rejection/deletion as destructive flows that still clear protected UI state.
  - Done 2026-07-16: failed background recovery opens a dedicated re-authentication layer over the mounted app. Telegram can recover in place; browser login can temporarily show the login surface without invoking modal close handlers.
  - Covered by auth API tests, frontend/modal contracts, and browser tests for delayed Telegram `initData`, single-login/bootstrap behavior, session refresh, `401` retry, retained operation amount/comment, and 390px modal geometry.

### Currency Alert Reliability And Context Actions 2026-07-15
- [x] P0: send currency threshold alerts only when the rate enters the configured zone.
  - Replace snapshot-marker semantics (`rate_date + rate + threshold`) with persisted above/below zone state. A new rate snapshot must not repeat an alert while the condition remains true.
  - Rearm a direction only after the rate leaves its trigger zone; changing the configured threshold also rearms the corresponding direction.
  - Guard the alert scan against overlapping bot instances during deploy/restart and preserve structured logs for trigger, suppression, rearm, delivery, and failure outcomes.
  - Cover transitions below -> above -> above -> below -> above, both threshold directions, threshold edits, bot restarts, and overlapping scans.
  - Done 2026-07-15: alert markers now persist the active threshold zone instead of a rate snapshot, legacy markers remain compatible, leaving the zone rearms delivery, and threshold edits create a new zone state.
  - Done 2026-07-15: the scan uses a PostgreSQL advisory lock with a local test fallback; structured events cover trigger, suppression, rearm, sent, failed, and overlapping-scan outcomes.
- [x] P1: keep contextual row/kebab actions and edit-modal actions in sync.
  - Introduce one entity-action registry used to derive both row menus and modal actions instead of maintaining duplicated button markup.
  - Add `История` to the item-template edit modal; add contextual `Добавить категорию` to category-group editing and `Добавить позицию` to item-source editing.
  - Preserve the already-correct category actions (`Журнал`, `Операции`) and avoid redundant actions where the modal already exposes the same content, such as receipt positions inside operation editing.
  - Show at most three frequent non-destructive actions directly in a modal header; keep destructive and less frequent actions in a compact modal action menu, especially on mobile.
  - Add contract tests for action parity plus desktop/mobile e2e for item history, contextual creation, modal-menu geometry, and action routing.
  - Done 2026-07-15: one contextual action registry now drives category, category-group, item-template, and source row menus; edit modals expose the applicable frequent actions.
  - Done 2026-07-15: item editing includes `История`; group/source editing includes prefilled child creation. Contract coverage and mobile item-history routing e2e pass.
- [x] P1: add visual position-purchase analytics for day, week, month, and year periods.
  - Add a dedicated `Позиции` analytics tab with a matrix chart: position rows, period buckets on the horizontal axis, intensity/short bars for values, and a fixed total scale per row.
  - Use one bucket and ranked horizontal bars for a day, Monday-Sunday daily buckets for a week, calendar days for a month, and months for a year. Do not imply hourly precision while operations store only a date.
  - Provide segmented metrics `Покупки` (distinct receipts/operations), `Количество` (sum of receipt quantity), and `Сумма`; default to purchases.
  - Keep position/source labels and totals sticky on desktop with controlled horizontal scrolling. On mobile, show the selected position's bucket chart above a ranked position list, while retaining access to the full scrollable matrix.
  - Support position search, source filtering, top-10/all display, period arrows, tooltips, and drilldown from a bucket to matching operations.
  - Aggregate directly in SQL by operation date and item template, with a normalized name/source fallback for legacy or deleted templates; cover API semantics, cache invalidation, interaction routing, and 320/390/768/desktop geometry.
  - Done 2026-07-15: the `Позиции` tab provides day/week/month/year buckets, purchases/quantity/amount metrics, search and source filtering, top-10/all, period navigation, sticky totals, mobile focus bars, and bucket drilldown into filtered operations.
  - Refined 2026-07-16: week view uses Monday-Sunday daily buckets; the mobile period control has equal compact arrows around a wider `Текущий` action, and summary values use compact KPI chips.
  - Done 2026-07-15: API aggregation groups receipt positions by operation date and template with historical name/source fallback. Existing operation and receipt composite indexes already cover the query path, so no redundant schema migration is required.
  - Covered by API aggregation tests, frontend/runtime contracts, action-routing e2e, and screenshot-backed overflow/sticky-column checks at 320, 390, 768, and 1440px.
  - [x] Add a visual ranking above the position timeline: horizontal bars follow the selected metric, selecting a row focuses the timeline/matrix, and an icon control switches value order between descending and ascending with an explicit title (`Чаще` / `Реже`, etc.).
    - Done 2026-07-16: ranking order follows purchases, quantity, or amount; selection drives the adjacent timeline and matrix, while the compact arrow control switches between explicit descending and ascending views.
  - [x] Add a fixed descending top-5 `Чаще всего покупали` dashboard block for the dashboard period, with purchases as the primary value, quantity/amount as context, operation drilldown, and a link to the full positions tab.
    - Done 2026-07-16: the dashboard highlights response includes a distinct-purchase top five with quantity and spend context; rows drill into matching operations and `Все позиции` opens the full analytics tab with the dashboard period.
  - [x] Replace the positions-specific period layout and date shifting with the shared `period-control` markup, popover lifecycle, and `period-control-utils.shiftPeriodBounds`, while retaining independent day/week/month/year state and excluding unbounded matrix ranges.
    - Done 2026-07-16: positions reuse the shared arrows, central period trigger, popover lifecycle, and period shifting utility while retaining independent day/week/month/year preferences. Compact control dates remain readable at 320px.
  - Covered by dashboard/API contracts and browser scenarios for ranking order, selection, weekly shifting, operation drilldown, shared-control geometry, sticky columns, and page overflow at 320, 768, and desktop widths.

### Operation Modal Calculator And Row Toggles 2026-06-23
- [x] Calculator in operation modals.
  - Done 2026-06-23: create/edit operation modals now expose a calculator button in the header action area. The existing calculator opens in a modal-attached side panel without the global overlay and closes automatically when the operation modal closes.
  - Mobile behavior remains a bottom sheet to preserve usable modal width.
- [x] Wider group/source row toggles.
  - Done 2026-06-23: category group rows and item source rows now collapse/expand from clicks on the row surface, while buttons, kebab menus, inputs, links and popovers keep their own actions.
- [x] Regression coverage.
  - Covered by finance-calculator e2e for modal-attached geometry/calculation/autoclose and by category/catalog e2e for row collapse/expand plus preserved contextual `+` actions.
- [x] Calculator entry points and drawer overflow.
  - Done 2026-06-24: calculator buttons remain only in create/edit operation modals; the side panel uses a compact close control and prevents horizontal overflow.
- [x] Compact analytics calendar picker.
  - Done 2026-06-24: month/year popovers size to their longest option instead of inheriting the wide generic popover width, with a viewport cap for small screens.
- [x] Reproducible production dependency resolution.
  - Done 2026-06-24: pin Pydantic to a version compatible with the current FastAPI and pydantic-settings stack so Docker builds do not backtrack across unavailable pydantic-core releases.
- [x] Calculator tab fit.
  - Done 2026-06-24: calculator modes use four equal compact columns, with a two-column fallback on very narrow screens, so `Разделить` stays inside the drawer.
- [x] Branded session loading and favicon.
  - Done 2026-06-24: reloads show a centered `ФинАсист` session check instead of flashing the login form; the login card is compact and centered, and the favicon uses the new orange Cyrillic `Ф` with a mint status accent.
  - Refined 2026-06-24: the login mark is constrained to 52px in widget environments; session checking uses a lightweight transform/opacity pulse with reduced-motion support.
  - Refined 2026-06-24: the sidebar now uses the same branded `Ф` mark instead of the legacy `ФА` badge.
- [x] Receipt discount input and analytics.
  - Done 2026-06-27: receipt item price fields now accept the same math expressions as the main operation amount, including discounted regular-price fields and the finance calculator's amount inputs.
  - Done 2026-06-27: discounted receipt rows store a compact discount type (`promo`, `coupon`, `loyalty_points`) through operations, plans, activity diffs, and API responses. The UI uses inline chips (`Акция`, `Купон`, `Баллы`) instead of selects.
  - Done 2026-06-27: analytics highlights keep the existing total savings KPI and add a compact savings breakdown by discount type for future product reporting.
  - Covered by receipt e2e for receipt-only amount creation and discounted receipt creation with math input plus `Купон` payload.
  - Refined 2026-06-27: regular operations can convert the entered amount into a one-line discounted receipt, keeping discount analytics on receipt items instead of duplicating operation-level discount fields.

### Category And Catalog Interaction Fixes 2026-06-23
- [x] Category group creation modal reliability.
  - Done 2026-06-23: `Создать группу` no longer depends on bulk-import bindings for close, kind switch, and submit handlers. Create-group modal controls are bound in the regular app init path, with bulk duplicate bindings removed to avoid double submits.
- [x] Category group picker stability.
  - Done 2026-06-23: create/edit category group pickers now use the shared popover lifecycle with owner scopes and guarded click propagation, so clicking the group field keeps the picker open until selection, Escape, or outside click.
- [x] Contextual `+` placement.
  - Done 2026-06-23: category-group and item-source hover/focus `+` buttons moved next to the group/source name instead of the far-right action area; kebab actions remain on the right and touch-device actions remain in menus.
- [x] Regression coverage.
  - Covered by `tests/e2e/test_bulk_import_sections_e2e.py -m e2e`: category picker stays open and selects a group, create-group modal submits once and closes, contextual `+` prefill still works, and category/catalog `+` geometry stays close to the visible name.

### Product Utility And Naming 2026-06-23
- [x] Finance calculator side drawer, first increment.
  - Done 2026-06-23: added a local-only right drawer calculator with discount, price-change, unit-price, and split-check modes. The drawer is available from the topbar, uses current frontend money formatting, and has a mobile bottom-sheet layout.
  - Covered by frontend UI contract and isolated finance-calculator e2e geometry/calculation test. Future iteration: optional integration with operation/receipt forms after visual review.
- [x] Product naming first pass.
  - Done 2026-06-23: visible web title/login heading and sidebar mark now use `ФинАсист` / `ФА`.
  - Remaining manual step: update Telegram BotFather display name/description/username if the final public name is approved and available.

### Release Validation 2026-06-16
- [x] Commit under validation: `34870fa f`; working tree was clean before validation fixes.
- [x] API suite: `./.venv/bin/pytest -q tests/api` passed.
- [x] E2E domain suites passed in isolated pytest processes: operations money-flow, analytics mobile/desktop structure, bulk/contextual actions, mobile shell cards, debts, plans, currency, receipt/category pickers, batch create, and sort preference persistence.
- [x] Local Docker stack is running; app health is OK from inside the app container via `http://127.0.0.1:8000/health`.
- Notes:
  - `tests/e2e/test_sort_preset_persistence_e2e.py` must remain an isolated pytest process because it owns a sync Playwright lifecycle and conflicts with pytest-playwright async-loop fixtures when mixed into a large command.
  - Host `curl http://127.0.0.1:8001/health` failed in this validation shell even though `docker compose ps` showed the app published on `8001` and container-internal health returned OK.

### Production Hardening 2026-06-16
- [x] Browser Telegram login default safety.
  - Done 2026-06-16: `.env.example` no longer enables browser Telegram login by placeholder username. `TELEGRAM_BOT_USERNAME` placeholders (`change_me`, `change_me_bot`, `your_bot_username`) normalize to empty, while real usernames normalize without leading `@`.
  - Covered by config/auth API tests and auth-login UI e2e.
- [x] Release check script hardening.
  - Done 2026-06-16: `scripts/release_check.sh` no longer mixes all e2e tests into one pytest process when `RUN_E2E=1`; it runs domain e2e groups explicitly and keeps sort-preference sync Playwright tests isolated.
  - Fast release mode (`./scripts/release_check.sh`) passes locally: non-e2e baseline, request-budget guard, and tokenless health-check skip path.
  - Full local release mode (`RUN_E2E=1 ./scripts/release_check.sh`) passes with elevated socket permissions: non-e2e baseline, auth, operations money-flow, analytics, bulk/batch, mobile shell, debts, plans, currency, receipt/category pickers, isolated sort preferences, and request-budget guard.
- [x] Legacy plan confirmation compatibility.
  - Done 2026-06-16: plan confirmation and serialization fall back from zero/empty `original_amount` to positive `amount`, so older or manually-created plan rows can still be confirmed from Telegram without creating a zero-amount operation.
  - Covered by Telegram plan bot service tests and adjacent plan/reminder service tests.
- [x] Release/deploy checklist documentation sync.
  - Done 2026-06-16: release docs now prefer `release_check.sh` over a mixed full pytest command, VPS checklist documents placeholder-safe `TELEGRAM_BOT_USERNAME`, and scripts README explains the isolated e2e release mode.
- [ ] Production deploy checklist execution.
  - Next: decide whether to run the deploy-side checklist against a real VPS/domain or keep validation local until a production snapshot/domain is available.

### Period Controls, All-Time Performance, And Geometry Audit 2026-06-16
- [x] Stage 1: audit period handling across dashboard, operations, analytics structure/highlights, analytics trends, calendar, debts and plans where applicable.
  - Done 2026-06-16: verified `all_time` highlights on backend, found frontend label drift in trends, found old dashboard analytics tabs, and confirmed operations money-flow had a backend pagination bottleneck for large all-time operation datasets.
- [x] Stage 2: unify period controls.
  - Done 2026-06-16: dashboard analytics now uses the same arrow period-control pattern as analytics/operations; hidden segmented tabs remain as compatibility state holders. Dashboard/analytics all-time arrows no-op instead of shifting meaningless ranges.
- [x] Stage 3: optimize `all_time` loading.
  - Done 2026-06-16 frontend hardening: operations summary requests now abort stale in-flight requests and ignore stale responses during fast period/filter switching.
  - Done 2026-06-16 backend fast path: `/api/v1/operations/money-flow` now uses SQL-level pagination for operation-only views (`source=operation`) and operation drilldowns (`category_id`, `item_template_id`), loading receipt rows only for the returned page.
  - Done 2026-06-16 mixed all-time fast path: default `source=all` list now fetches only the needed SQL window of operations before merging debt/FX rows; `money-flow/summary` uses SQL aggregation for operations instead of materializing every operation.
  - Residual future work: text search `q` in mixed `source=all` intentionally keeps the old full-materialization path for correctness across operation/debt/FX fields. If debts/FX grow to operation-scale volumes, add source-level SQL pagination/aggregation for those domains too.
- [x] Stage 4: fix desktop/mobile geometry.
  - Done 2026-06-16: analytics and dashboard category-structure grids now use equal fixed desktop panel heights for chart and right-side list; mobile overrides restore natural stacked height.
- [x] Stage 5: interaction regression pass.
  - Done 2026-06-16 targeted pass: analytics structure `all_time`, analytics period arrows, operations period popover, and desktop structure geometry are covered by e2e.
  - Done 2026-06-16 broader pass: contextual `+` actions for category groups and item sources now have browser regressions; analytics category drilldown verifies operations filters/API query; targeted kebab, sticky CTA and mobile shell geometry checks pass. Remaining future work is periodic full-matrix visual QA on real data/devices, not a blocker for this sprint.
- [x] Stage 6: test and visual validation.
  - Done 2026-06-16: frontend/API contracts, dashboard all-time highlights regression, analytics all-time/period e2e, operations period e2e, and desktop geometry e2e pass for the changed paths. Mixed e2e suites with different sync Playwright fixtures can still hit the known asyncio-loop setup conflict; affected tests pass when run in isolated pytest processes.

### Reliability And UX Audit 2026-06-15
- [x] Dashboard reliability.
  - Done 2026-06-16: summary loading now has an independent lifecycle from optional currency/plans/debts panels. Repeated dashboard refreshes coalesce in-flight optional work instead of aborting it, and standalone dashboard-plan refreshes reuse the same in-flight work.
- [x] Frontend actions and popovers.
  - Done 2026-06-16: create-group modal ownership moved to category runtime, batch category tests use stable nav selectors, picker init no longer reads the global action facade, and money-flow receipt chips open through the operations runtime. Covered by frontend contracts, bulk import e2e, and receipt-chip money-flow e2e.
- [x] Activity journal readability.
  - Done 2026-06-16: raw `old/new` values remain in the API, while display values now format enums, dates, money/rates, booleans, and resolve category/group/counterparty references on read. Operation receipt updates add compact added/removed/changed item metadata; deleted historical references fall back to `#id (удалена)`.
- [x] Analytics Year view by quarters.
  - Done 2026-06-16: the Year calendar now renders four quarter rows from the existing 12-month API payload. Each quarter shows totals for inflow, outflow, events, operating surplus/deficit, and cash flow; month cards remain clickable.
- [x] Categories and Item Catalog contextual creation.
  - Done 2026-06-16: category groups and item sources now expose contextual `+` actions on hover/focus and matching kebab-menu actions for touch devices. Category creation opens with the group preselected; item-template creation opens with the source prefilled.
- [x] Audit closeout.
  - Done 2026-06-16: roadmap collapsed to the current source of truth, targeted frontend/API/e2e checks passed. One broad mixed e2e command still hits the existing sync Playwright inside asyncio-loop fixture limitation; the same failing scenarios pass when run in isolated pytest processes.

## Recently Closed Work
- Operations is money-flow first: legacy operation-list mode and mass-selection UI are removed from the active UX.
- Operations filters support category and item-template navigation from analytics, category usage, item usage, and receipt flows.
- Category and item cards include usage modals with KPIs and related operations.
- Debts use `Движения` for financial movement history and keep audit `Журнал` separate.
- Debt movements, debt additions, repayments, and forgiveness stay reflected in money-flow and dashboard/debt caches.
- Dashboard analytics endpoints share the backend cache namespace and invalidation path.
- Runtime registry is the preferred frontend dependency path for feature modules; low-risk action-bus/global consumers have been migrated where practical.

## Key Modules
- Dashboard: `static/js/app-features-dashboard.js`, `static/js/app-dashboard-data.js`, `app/api/v1/endpoints/dashboard.py`.
- Analytics calendar: `static/js/app-features-analytics-calendar.js`, `static/css/components-analytics-summary.css`, `tests/e2e/test_analytics_mobile_e2e.py`.
- Categories: `static/js/app-categories.js`, `static/js/app-categories-ui.js`, `static/js/app-categories-table-ui.js`, `static/js/app-bulk-bindings-categories.js`.
- Item catalog: `static/js/app-item-catalog*.js`, `static/js/app-init-features-pickers.js`, `static/js/templates/shell-sections-secondary.js`.
- Activity journal: `app/services/activity_service.py`, `app/schemas/activity.py`, `static/js/app-activity.js`.
- Operations and receipts: `app/services/operation_service.py`, `app/services/operation_money_flow_service.py`, `static/js/app-features-operations.js`, `static/js/app-init-features-operations.js`.
- Frontend contracts and e2e: `tests/api/test_frontend_*_contract.py`, `tests/e2e/`.

## Test Baseline
- Fast frontend contracts: `./.venv/bin/pytest -q tests/api/test_frontend_ui_contract.py tests/api/test_frontend_runtime_contract.py`
- Dashboard/action contracts: `./.venv/bin/pytest -q tests/api/test_frontend_runtime_contract.py tests/api/test_frontend_bootstrap_contract.py tests/api/test_frontend_ui_contract.py`
- Activity journal regression: `./.venv/bin/pytest -q tests/api/test_operations_api.py::test_activity_journal_tracks_operation_create_update_delete`
- Operation money-flow API regression: `./.venv/bin/pytest -q tests/api/test_operations_api.py`
- Targeted e2e used in this audit:
  - `./.venv/bin/pytest -q tests/e2e/test_operations_money_flow_e2e.py::test_operations_period_popover_changes_period -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_operations_money_flow_e2e.py::test_operations_receipt_chip_opens_same_positions_modal_as_kebab -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_bulk_import_sections_e2e.py -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_analytics_mobile_e2e.py::test_mobile_analytics_category_drilldown_opens_operations_with_filter -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_plans_ui_e2e.py::test_plan_kebab_menu_actions_work_from_floating_popover -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_mobile_shell_cards_e2e.py -m e2e`
  - `./.venv/bin/pytest -q tests/e2e/test_analytics_mobile_e2e.py::test_mobile_analytics_calendar_scroll_wrap_reaches_last_columns tests/e2e/test_analytics_mobile_e2e.py::test_mobile_analytics_year_view_card_opens_month_view -m e2e`

### CI notification policy — 2026-10-13

Automatic GitHub CI runs on pushes and pull requests are disabled at the owner’s request. The workflow remains available through `workflow_dispatch`; local/release checks remain required. Latest failed run `38318224189` stopped at the python-jose advisory `GHSA-3qf3-8w2g-rqmx` and a browser screenshot path `/private/tmp` unavailable on Linux; this change does not claim those failures are resolved. The screenshot path now uses Python’s temporary directory and the seven plan-resumption browser checks pass locally. The [advisory](https://github.com/advisories/GHSA-3qf3-8w2g-rqmx) lists no fixed release; it concerns DER public keys accepted as HMAC secrets when algorithms are not restricted. Local `app/core/security.py` explicitly pins HS256 with the application secret, so the described public-key confusion path is not used by that code. This is a code review, not a claim that the dependency advisory is fixed; keep dependency replacement/update as maintenance work.

### Stage 4d — receipt price hints

- [x] Implemented read-only previous-purchase lookup and explicit in-row comparison, paid-total ratio/cost difference, exact shop/currency/package/historical-variant isolation, date and edit exclusion, lazy loading, context invalidation, retry and stale-response guards. No schema migration or historical backfill.
- [x] Local validation: 727 non-E2E passed, two optional migration tests skipped (schema unchanged); four new API cases also passed on disposable PostgreSQL 15. All 46 receipt/catalog browser cases and seven plan-resumption cases passed; three final hint cases separately verify plan dates, request cancellation/context invalidation, exact discount ratios, retry and draft preservation at 320/390/1440 px. Final 320 px screenshot reviewed; JavaScript syntax/Python compilation/diff checks pass.
- [x] Deployed on 2026-10-13 from GitHub `main` at `50b7da7` through server fast-forward pull; assets `20261013-receipt-hints1`, unchanged schema `20261013_0049`. Exact isolated Linux image: 43 selected checks passed (one existing anyio deprecation warning). Pre/post fingerprints match all fields in eight tables. Read-only production sample: all 30 sampled historical rows have unknown measurements and correctly return that status; comparable-price cases are covered by API/PostgreSQL/browser tests, not inferred from that sample. Readiness, seven served assets and app/bot image IDs verified. All six containers healthy with zero restarts at the final short check; only app/bot recreated. Rollback tags: `financialassistant-app:before-receipt-hints-20261013`, `financialassistant-bot:before-receipt-hints-20261013`. No data/schema rollback is needed. CI remained manual; neither the workflow-policy commit nor the release triggered a GitHub run.
- [x] Remaining stage 4 package replacement relations delivered in stage 4e below. OCR, retailer matching/polling/notifications and analytics consolidation remain subsequent stages.

### Stage 4e — confirmed package replacements

- [x] Implemented explicit old→new links, frozen snapshots, date/order/cycle/branch/stale-choice guards, revoke audit and merge/cleanup integrity. Product locks serialize variant saves, confirmations and merges. Paid and recorded-regular comparisons use actual identified receipts with exact units/shops/currencies; unknown observations are not inferred. UI loads lazily and preserves drafts, retries errors and rejects delayed cross-product responses.
- [x] Local validation: 733 non-E2E checks passed (two optional earlier migration checks skipped); final focused API/migration/identity/linkage run: 20 passed, concurrency scenario skipped on SQLite. All 11 replacement/identity API tests passed on disposable PostgreSQL 15, including competing branch/cycle confirmations. Fresh PostgreSQL migration upgrade/downgrade/upgrade passed. All 29 catalog/workspace/history/identity browser scenarios passed. Three final replacement cases separately passed at 320/390/1440 px, including confirmation reset, draft retention, nested receipt focus, retry and stale responses. The 320 px screenshot was reviewed; syntax, compilation and diff checks pass.
- [x] Deployed on 2026-10-13 through GitHub `main` at `6227e39` and server fast-forward pull; revision `20261013_0050`, assets `20261013-replacements1`. Fresh encrypted local backup `20261012T230936Z` restored to isolated PostgreSQL 16; new-image migration preserved all fields in eight existing tables and created an empty replacement table. Exact isolated Linux image: 38 selected checks passed; one PostgreSQL-only concurrency check skipped there (passed on PostgreSQL 15), one existing anyio deprecation warning. Production pre/post fingerprints match all eight tables. Read-only registry lookup succeeds on 25 products; no automatic links exist. Readiness, six asset hashes and app/bot image IDs verified; all six containers healthy with zero restarts at the final short check, including poopbot. Only app/bot recreated. Rollback image tags: `financialassistant-app:before-replacements-20261013`, `financialassistant-bot:before-replacements-20261013`. Keep the additive schema on rollback; after confirmations exist, prefer a forward fix because older merge code does not move them. Manual CI policy retained; no automatic GitHub runs triggered.


### Daily lists simplification — 2026-10-13

- [x] Operations: flat period/filter/sort controls, compact labelled totals, direct icon actions for operations and money-flow sources, icon add/batch actions. All existing source/currency/search/period filters retained.
- [x] Plans: labelled current result / active plans / projected result, flat records, one deadline with overdue status, direct confirm/edit/skip/journal/delete icons. Preview is opt-in and survives ordinary editor updates.
- [x] Debts: compact totals and counterparty groups, direct repayment/issuance/history/edit/journal/forgiveness/delete icons; bulk delete moved below the list. No time-progress bars or duplicated mobile action menus. At laptop widths the list prioritizes direction, outstanding amount, deadline and actions; full movements remain available.
- [x] Loading buttons preserve SVG/accessibility state, dynamic idle-label updates and editor resets. Regression covers failed action/retry and asynchronous completed-plan resumption.
- [x] Local validation: 733 non-E2E passed, 3 existing skips; 72 selected browser scenarios passed (10 plans, 12 money-flow operations, 20 debts, 2 action geometry, 21 editor/line-discount, 7 plan-resumption). Filled lists and plan editor inspected at 320/390/1024/1100/1440 px with local API fixtures; page overflow absent. The initial combined browser invocation exposed incompatible Playwright fixture lifetimes; affected suites were rerun separately. Financial API and schema unchanged.
- [x] Released `d00f21a` through GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261013-daily-lists1`: all 13 served file hashes match; ready on unchanged schema `20261013_0050`; all fields in 13 financial/catalog/debt tables match pre-release fingerprints. All six containers healthy. App recreated at `2026-10-13T16:20:14Z`; other service start times unchanged, including poopbot (its pre-existing restart count was already 1 before this deployment). Initial asset request hit startup connection reset; post-readiness retry passed. Rollback image `financialassistant-app:before-daily-lists-20261013`; CI remains manual.
- [x] Timesheet iteration implemented below. Next: analytics/dashboard/currency, remaining directories/settings/admin. OCR and retailer integration remain deferred.


### Timesheet simplification — 2026-10-13

- [x] Open Timesheet by default, place navigation first and remove the shared KPI wall from other views. Calendar follows compact hours/days; the salary cycle sits alongside on wide desktops and after the calendar on narrower screens. Earnings rates retain their original period/basis and forecast labels.
- [x] Give actual payments a separate Payments view, retaining operation linking/unlinking. Flatten settings, statistics and employment records; use direct accessible icon actions. Confirm employment-period deletion explicitly, and retain drafts across tabs.
- [x] Local validation: 733 non-E2E passed, 3 existing skips; 20 browser scenarios passed (19 work KPI/statistics/layout/draft/confirmation cases and the existing complete work flow). Full-month views inspected at 320/390/1024/1100/1440 px; fixed hour-chip overflow and icon sizing. Final settings render inspected after layout refinement. Financial calculations, API and schema unchanged.
- [x] Released `e8ea34f` through GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261013-work-compact1`: all eight served file hashes match. Ready on unchanged schema `20261013_0050`; all fields in 17 financial/catalog/debt/work tables match pre-release fingerprints. All six containers healthy. Only app recreated (`2026-10-13T16:39:05Z`); all other start times unchanged, including poopbot with its pre-existing restart count of 1. Rollback image `financialassistant-app:before-work-compact-20261013`; CI remains manual.
- [x] Analytics/dashboard/currency delivered below. Company suggestions replaced in the directories/settings iteration; remaining source/brand/editor polish is tracked there.


### Analytics, dashboard and currency consolidation — 2026-10-13

- [x] Analytics navigation contains only Structure and Calendar. Structure keeps category/group/brand filters, visibility controls and operation drilldown; income/expense/cash-flow chart shares its period beneath the breakdown. Calendar retains month/year, date navigation, totals and exact-date/range drilldown.
- [x] Destination map: Positions → Catalog / Purchases (all separate quantity metrics, currencies, sources, ranking, selected-item timeline and date matrix); Discounts → Catalog / Discounts (promo/coupon/points, savings metrics, period and operation drilldown); legacy price-increase averages → existing Catalog / Price changes and product price history with explicit comparability flags; Currency analytics → Currency / Rates and trades (bank/NBRB comparison, series controls, backfill, filtered trade history). The portfolio retains result history and position accounting; duplicate KPI/balance blocks are hidden in the rates view. Old reporting APIs remain compatible.
- [x] Dashboard DOM order is period totals, plans, debts, structure, frequent purchases and optional currency overview. Flatten KPI styling and convert actions to accessible icons. Preserve display preferences, result/cash-flow distinctions and destructive confirmations. Smaller charts and compact category rows; calendar navigation grouped in one row.
- [x] Preserve return-to-report state, discount custom periods and icon loading/retry. Guard delayed report responses; a trend outage leaves Structure available and clears its stale graph. Existing analytical module/element names remain for compatibility although their owning sections changed. Global period controls move with the owning report rather than duplicating IDs/listeners.
- [x] Local validation: 733 non-E2E passed, 3 existing skips; 52 distinct browser scenarios passed (33 analytics/report navigation/geometry/late-response cases, 8 currency pagination/digest, 1 cash-flow semantics, 8 product workspace/price changes, 2 trade-entry cases). Final geometry subset and currency suite rerun after visual refinements. Inspected seven views at 320/390/1024/1100/1440 px with local API fixtures; no horizontal page overflow or uncaught browser errors. Later refinements of dashboard/portfolio empty states inspected at 320/390/1440 px. Updated legacy selectors/contracts to the new report destinations; tests remain manual in GitHub.
- [x] Released `2f3984a` through GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261013-insights-compact1`: all 22 served file hashes match. Ready on unchanged schema `20261013_0050`; all fields in 18 financial/catalog/debt/work/FX-trade tables match pre-release fingerprints. All six containers healthy. Only app recreated (`2026-10-13T20:28:13Z`); all other start times unchanged, including poopbot with its pre-existing restart count of 1. Rollback image `financialassistant-app:before-insights-compact-20261013`; CI remains manual.
- [x] Categories/settings/admin and company picker delivered below. Evaluate the reorganized dashboard with real usage before adding another recent-operations block. OCR and retailer integrations remain deferred.

### Directories, settings and administration — 2026-10-13–14

- [x] Settings now have direct pages: General, Dashboard, Currencies/banks, Reminders, Rate thresholds, Data. Desktop side navigation and compact mobile grid share the original form controls; switching pages preserves drafts, saving includes all pages, and native invalid fields reveal their owning page. Account deletion remains separate with its explicit consequence and typed confirmation.
- [x] Categories: compact counters (including corrected filtered counts), direct category/group icons, compact header actions and bulk deletion below the list. Keep grouping, search/layout correction, sorting, create/edit/usage/journal flows and protected system categories.
- [x] Admin: Access and Rate diagnostics are separate, loaded on demand, with Russian labels, direct icons and unchanged deletion confirmation. Late user-list responses cannot overwrite the selected filter. Bind diagnostics refresh through the runtime module; the previous action facade did not export that command.
- [x] Company suggestions in work settings/history now reuse the application's store picker with company data, keyboard/layout-aware search and manual text entry. Close portalled suggestions when the owning view/section hides; preserve both form drafts. No financial calculation, API or schema changes.
- [x] Local validation: 733 non-E2E passed, 3 existing skips; 60 distinct targeted browser cases passed (19 category/session, 24 work including five company-picker widths, 12 settings/admin/draft/validation/error-retry cases, four store-picker regressions, one complete work flow). Final frontend contracts: 38 passed. Inspected 45 settings/category/admin states and company suggestions at 320/390/1024/1100/1440 px; final sequential preview has no page overflow, failed asset requests or uncaught browser errors. A parallel preview hit local HTTP-server connection resets; final checks ran sequentially.
- [x] Released `fbbe7bc` on 2026-10-14 (Minsk) via GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261013-directories1`: all 17 served hashes match; ready on unchanged schema `20261013_0050`. All fields in 20 financial/catalog/debt/work/FX/category tables match pre-release fingerprints. All six containers healthy. App recreated at `2026-10-13T21:02:20Z`; every other service start time is unchanged, including poopbot with its pre-existing restart count of 1. Rollback image: `financialassistant-app:before-directories-20261014`. CI remains manual.
- [x] Test maintenance completed in the secondary-editor pass below: all 29 receipt/catalog cases and eight bulk-import cases now pass across scoped runs. Hidden fields and opt-in previews are opened through their controls; bulk tests use their own ephemeral server instead of a fixed local port.
- [ ] Remaining UX pass: source/brand directories delivered below; continue secondary editors, consistent modal action icons, and final cross-section review with long real-world data. Do not treat this iteration as a claim that every old screen already satisfies the contract. OCR and retailer integrations remain deferred until the agreed UX priority is finished.

### KPI presentation correction — 2026-10-14

- [x] User feedback: the compact-layout passes removed KPI surfaces across multiple sections. Restore distinct backgrounds, borders, radii and inner padding for dashboard, operation/debt summaries, plan result items, catalog/report counts, calendar, currency, work and admin KPIs. Keep result colors and compact typography; align card content at the top.
- [x] Remove section-level surface resets and centralize the shared KPI surface in `kpi-cards.css`. Mobile debt/balance grids use two columns and wrap long amounts. The plan summary container stays unframed around its three individual KPI cards. Preserve all data, calculations, API endpoints and navigation.
- [x] Clarify the visual contract: compactness must preserve the visual grouping of each KPI.
- [x] Validation: 38 frontend contract checks and seven existing adaptive browser cases passed. Reviewed KPI states at 320/390/1024/1100/1440 px across the affected sections; final mobile dashboard/currency refinements checked again. No horizontal page overflow in the exercised states. Work actual-payment gradients and result colors retained. The existing compressed mobile source-group heading remains part of the pending source-directory pass, outside this KPI fix.
- [x] Released `cdae02b` through GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261014-kpi1`: all nine served hashes match. Ready on unchanged schema `20261013_0050`; all six containers healthy. Only app recreated (`2026-10-13T21:19:58Z`, 14 October in Minsk); bot and poopbot start times/restart counts unchanged. Rollback image `financialassistant-app:before-kpi-surfaces-20261014`. CSS and cache versions only; no data migration or financial logic changes. CI stays manual.

### Desktop structure size correction — 2026-10-14

- [x] Restore a large structure block on Dashboard and Analytics: 560 px chart/list height (previous compact value 330 px), equal columns, responsive circular donut up to 520 px (previous cap 280 px). Preserve mobile layout at widths up to 640 px: 185 px donut and list capped at 330 px. No data, API or calculation changes.
- [x] Record desktop/mobile sizing in the visual contract. Validate Dashboard and Analytics at 320/390/640/768/1024/1100/1440/1920 px, including a 29-category fixture: no page overflow or uncaught browser errors. Three existing browser cases pass: desktop geometry/hover containment, mobile all-time structure, category drilldown.
- [x] Released `86cf0c6` through GitHub main → server fast-forward pull → app-only rebuild. Assets `20261014-structure1`: all four served file hashes match. Ready on unchanged schema `20261013_0050`; all six containers healthy. Only app recreated (`2026-10-13T21:29:23Z`, 14 October in Minsk); bot and poopbot start times/restart counts unchanged. Rollback image `financialassistant-app:before-structure-size-20261014`. CI remains manual.

### Timesheet day editor modal — 2026-10-14

- [x] Replace the expanding editor beneath the calendar with the shared modal surface: centered 640 px dialog on desktop, bottom sheet on mobile. Keep the same day status, planned/actual/credited hours, comment, range end date and reset-to-schedule action. Calendar geometry and financial calculations remain unchanged.
- [x] Close via icon, Escape or backdrop; retain the current day's draft across close/reopen and work tabs, until another day is opened or the page reloads. Keep keyboard focus in the dialog and return it to the day cell. Block duplicate writes and closing during submission; failed requests retain inputs for retry.
- [x] Validation: 26 work browser scenarios and 51 frontend contract checks pass. Inspected 320/390/1024/1100/1440 px previews with a full month: no page/form overflow or browser errors. Range-save payload, reset, request failure/retry, pending-write guard, keyboard focus and unchanged calendar height covered. Existing static refresh-count assertion updated for the shared save/reset helper.
- [x] Released `e42525d` via GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261014-work-day1`: all seven served hashes match. Ready on unchanged schema `20261013_0050`; all six containers healthy (app health confirmed after the startup check). Only app recreated (`2026-10-13T21:40:33Z`, 14 October in Minsk); bot and poopbot start times/restart counts unchanged. Rollback image `financialassistant-app:before-work-day-modal-20261014`. CI remains manual.

### Source and brand directory consistency — 2026-10-14

- [x] Show source add/edit/delete and brand edit/delete as direct accessible SVG icons. Preserve confirmation before deletion, grouping/search, bulk brand assignment and record drilldown. Move delete-all positions below the source list.
- [x] Fix mobile source heading geometry: separate chevron/logo/name columns, remove space reserved for the old menu, wrap long source/product/brand names. Brand actions use a regular action cell instead of inherited kebab positioning; search keeps its normal input height. Keep KPI surfaces and values.
- [x] Simplify source/brand modals: icon actions, compact logo area, labelled source name, source counters instead of the preview table. Remove the mixed-product average price from source summaries; retain position/use counts and last-used date. Preserve brand color preview, detail KPIs, operations and item navigation, and logo editing.
- [x] Validation: 24 distinct browser cases (brand CRUD/detail/assignment, source/category/item actions, live catalog updates/selection/sorting, four source/brand image framing cases); 46 frontend contracts. Reviewed 25 list/editor/detail states at 320/390/1024/1100/1440 px with long names: no page/modal overflow or uncaught browser errors in the final pass. Migrated assertions from old brand menus to direct actions. Financial API and schema unchanged; CI stays manual.
- [x] Released `57b83a6` via GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261014-source-brand1`: all nine served hashes match. Ready on unchanged schema `20261013_0050`; all six containers healthy (app health confirmed after startup). Only app recreated (`2026-10-13T22:10:53Z`, 14 October in Minsk); bot and poopbot start times/restart counts unchanged. Rollback image `financialassistant-app:before-source-brand-20261014`. CI remains manual.
- [x] Secondary catalog editors and outdated receipt-picker selectors addressed below. Final cross-section review remains; OCR/retailer integrations stay deferred until the UX pass is finished.


### Secondary catalog editors — 2026-10-14

- [x] Compact the position editor into labelled desktop columns and a single mobile column. Journal, purchases, history, preview, close and save use shared SVG icons. Preview opens on request; source/brand/category pickers and submitted fields remain unchanged. Reserve date-input padding for navigation buttons.
- [x] Use shared icons in price history and batch-position import. Preserve validation/preview before import, row counts in accessible button names, deletion confirmations, and image editing.
- [x] Fix an actual receipt regression discovered during browser-test maintenance: opening Details on an empty draft previously normalized the list and recreated that draft, immediately closing Details. The toggle now only redraws visibility, preserving the draft id and payload.
- [x] Visual review: 20 editor/preview/history/import states at 320/390/1024/1100/1440 px; no page/modal overflow or uncaught browser errors. Date padding and 42/44 px action heights checked in the final pass.
- [x] Validation: 733 non-E2E passed, three existing skips; 59 distinct browser cases passed across scoped runs (29 receipt/catalog, 20 operation-editor, eight bulk-import, two position-image framing). Migrated hidden-field, preview, direct-action and discount-container selectors; mobile geometry checks assert visible, non-overlapping fields. One bulk-mobile run failed to find the form; its isolated retry and the five-width preview passed. JS syntax and diff checks pass.
- [ ] Final cross-section review remains. OCR/retailer work stays deferred until UX is finished.

- [x] Released `cf15a74` via GitHub main → clean server fast-forward pull → app-only rebuild. Assets `20261014-secondary1`: all 12 served hashes match. Ready on unchanged schema `20261013_0050`; all six containers healthy. Only app recreated (`2026-10-13T23:06:32Z`, 14 October in Minsk); bot, poopbot, databases and Redis start times/restart counts unchanged. Rollback image `financialassistant-app:before-secondary-editors-20261014`. No API/schema changes; CI stays manual.
