"""Accept host measurements via stdin, without exposing credentials or Docker socket."""
import json
import sys
from app.core.config import get_settings
from app.core.security_observation import SecurityJournal
from app.services.security_alert_service import SecurityAlerts
from app.services.operations_alert_service import observe

if __name__ == '__main__':
    settings = get_settings()
    if not settings.security_alerts_enabled or not settings.security_event_log_path:
        raise SystemExit('Operational notifications require configured security alerts')
    alerts = SecurityAlerts(settings, SecurityJournal(settings.security_event_log_path))
    observe(alerts, json.loads(sys.stdin.read(4096)))
    print('operational_sample=recorded')
