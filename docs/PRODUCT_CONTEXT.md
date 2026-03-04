# Product Context

## Product Idea
Financial Assistant is a web-first personal finance tracker for income and expenses. The same backend API is designed to support both:
- Web application (primary UI)
- Telegram Mini App client (secondary UI)

## Core Jobs To Be Done
- Track income and expense operations quickly
- Keep a clean category structure
- View simple but actionable dashboard totals
- Preserve user-selected display preferences between sessions

## Authentication Scope
MVP-1 uses Telegram-only sign in. Google auth is planned as provider #2 without changing core user model.

## Data Minimization
We store only the minimum profile data required for product operation:
- internal user id
- provider identity ids
- display name/avatar optional
- account status and timestamps

No password storage in MVP-1.
