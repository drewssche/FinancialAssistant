# Plans TODO

## Active Fix Pass

- Align `Планы` kebab popover sizing and button sizing to the desktop `Операции` baseline.
- Remove remaining desktop `Долги` child-row clipping and inner scroll so the kebab popover renders above the row without a nested scrollbar.
- Tighten mobile `Операции` kebab inset so the trigger stays inside the card with a consistent top-right utility offset.
- Keep this pass covered by targeted mobile/desktop e2e checks for:
  - mobile kebab top-right inset
  - desktop debts wrapper overflow behavior
  - plans popover width consistency

## Next UX / Product Pass
- Keep this file scoped to `Планы` section fixes and regressions only.
- Currency / analytics / reminders roadmap lives in [docs/CURRENCY_FEATURE_PLAN.md](/Users/bitriks24/Downloads/FinancialAssistant/docs/CURRENCY_FEATURE_PLAN.md).
