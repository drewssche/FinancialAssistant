# VPS Update Checklist

Updated: 2026-03-08

## What Changed in Telegram/Bot Terms

No new mandatory BotFather settings were introduced by the recent code changes.

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
- frontend relies on server `browser_login_available`

So after update, browser login still works only when:

- `TELEGRAM_BOT_USERNAME` is set correctly
- Telegram-side domain/widget configuration is still valid for your current public hostname

Mini App login via `initData` is unaffected by this change as long as the Mini App is opened from Telegram.

## VPS Update Steps

1. Pull changes on server.
2. Confirm production env still contains:
   - `APP_ENV=production`
   - valid `APP_SECRET_KEY`
   - valid `TELEGRAM_BOT_TOKEN`
   - valid `TELEGRAM_BOT_USERNAME` if browser login is needed
   - valid `ADMIN_TELEGRAM_IDS`
3. Rebuild and restart services:
   - `docker compose up --build -d`
   - add `--profile cache` if Redis-backed cache is desired
4. Check containers:
   - `docker compose ps`
   - `docker compose logs app --tail=100`
   - `docker compose logs bot --tail=100`
5. Run quick health check:
   - `/health`
   - login in Telegram Mini App
   - if browser login is used, verify widget is still shown and works on current domain

## Manual Smoke After Update

- open app from Telegram Mini App
- verify login works
- verify previously approved user still enters workspace
- verify `pending/rejected` handling still behaves correctly
- verify one long mobile modal and one batch modal on phone
- verify analytics calendar opens and scrolls normally
