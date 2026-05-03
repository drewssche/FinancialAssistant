# Documentation Index

This folder keeps the current product, architecture, engineering, and operations contracts.

## Current Source Of Truth

- `PRODUCT_CONTEXT.md` - product scope, domain semantics, and current MVP behavior.
- `ARCHITECTURE.md` - backend/frontend architecture, runtime boundaries, and cache contracts.
- `UI_SYSTEM.md` - layout, component, modal, mobile, and Telegram Mini App UI rules.
- `UX_PATTERNS.md` - persisted state, controls, navigation, and interaction patterns.
- `ENGINEERING_PRINCIPLES.md` - engineering guardrails, cache strategy, testing and release expectations.
- `ROADMAP.md` - active roadmap and current execution status.

## Operations And Release

- `RELEASE_CHECKLIST.md` - pre-release test and deploy checks.
- `VPS_UPDATE_CHECKLIST.md` - VPS update and Telegram/BotFather checks.
- `REQUEST_BUDGETS.md` - request-count budget source consumed by tests.

## Active / Semi-Active Plans

These still contain unresolved or forward-looking decisions. When implemented, promote durable decisions into the current source-of-truth docs and move the plan to `archive/`.

- `CURRENCY_FEATURE_PLAN.md`
- `CURRENCY_PNL_TIMELINE_PLAN.md`
- `RESULT_AND_CASHFLOW_SEMANTICS_PLAN.md`
- `PLANS_TODO.md`

## Archive

- `archive/` stores historical plans, investigations, worklogs, and completed execution notes.
- Archived files are useful for rationale, but they are not active source of truth unless a current doc explicitly links to them.

## Local Notes

- `_local/` is ignored by git.
- Use it for temporary Codex investigations, local backlogs, drafts, and one-off working notes.
- Do not place durable product or architecture decisions only in `_local/`; promote them to a tracked doc when they become real project policy.
