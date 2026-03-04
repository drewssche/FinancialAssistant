# UX Patterns

## Persisted View State (Required)
User display settings must persist until user changes them.

MVP-1 persisted items:
- dashboard period (`30d`, `month`, custom later)
- operations filters
- operations sorting

Persistence strategy:
- Source of truth: server-side `user_preferences`
- Fast fallback cache: local storage

Behavior:
- Save changes with debounce to avoid noisy writes
- Restore last state on next open/session
- Provide clear `Reset filters` action

## Action Hierarchy
- One primary CTA per screen (for example, `Add operation`)
- Secondary actions grouped nearby
- Destructive actions require explicit confirmation

## Responsive Behavior
- Desktop: sidebar visible
- Mobile: sidebar collapses, priority actions remain accessible
