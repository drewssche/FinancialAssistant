"""Explicit operator smoke test; records delivery and respects cooldown/day caps."""
import argparse
from app.core.config import get_settings
from app.core.security_observation import SecurityJournal
from app.services.security_alert_service import SecurityAlerts

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', choices=['telegram', 'email'], required=True)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.security_alerts_enabled or not settings.security_event_log_path:
        raise SystemExit('Security alerts are disabled')
    if args.channel == 'telegram':
        settings = settings.model_copy(update={'security_alert_email': ''})
    else:
        settings = settings.model_copy(update={'admin_telegram_ids': ''})
    alerts = SecurityAlerts(settings, SecurityJournal(settings.security_event_log_path))
    alerts.record({'event': 'security_notification_test'})
    alerts.tick(force_batch=True)
    print('Test queued/processed. Verify security_notification_sent in security.jsonl; cooldowns still apply.')
