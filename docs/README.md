# Documentation Index

This folder keeps durable product, architecture, engineering, and operations contracts. Completed one-off TODOs should be deleted or folded into the current docs.

## Source Of Truth

- `PRODUCT_CONTEXT.md` - product scope, domain semantics, and current MVP behavior.
- `ARCHITECTURE.md` - backend/frontend architecture, runtime boundaries, and cache contracts.
- `UI_SYSTEM.md` - layout, component, modal, mobile, and Telegram Mini App UI rules.
- `UX_PATTERNS.md` - persisted state, controls, navigation, and interaction patterns.
- `ENGINEERING_PRINCIPLES.md` - engineering guardrails, cache strategy, testing and release expectations.
- `ROADMAP.md` - active roadmap and current execution status.

## Active Notes

Keep this list short. If an item is implemented, promote durable decisions into source-of-truth docs and remove the note.

- `CURRENCY_FEATURE_PLAN.md` - compact current currency feature contract and backlog.
- `RESULT_AND_CASHFLOW_SEMANTICS_PLAN.md` - pending naming/semantics guardrails for result and cashflow surfaces.

## Operations

- `RELEASE_CHECKLIST.md` - pre-release test and deploy checks.
- `VPS_UPDATE_CHECKLIST.md` - VPS update and Telegram/BotFather checks.
- `REQUEST_BUDGETS.md` - request-count budget source consumed by tests.

## Historical And Local

- `archive/` stores historical plans, investigations, worklogs, and completed execution notes.
- Archived files are useful for rationale, but they are not active source of truth unless a current doc explicitly links to them.
- `_local/` is ignored by git.
- Use it for temporary Codex investigations, local backlogs, drafts, and one-off working notes.
- Do not place durable product or architecture decisions only in `_local/`; promote them to a tracked doc when they become real project policy.
