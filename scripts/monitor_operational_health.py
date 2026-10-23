"""Host-only stdlib sampler. Does not contact Yandex or restart any service."""
import json
from pathlib import Path
import subprocess
from scripts.check_backup_health import check_backup_health


def backup_status(spool):
    healthy, message = check_backup_health(spool)
    if healthy:
        return 'ok'
    if 'stale' in message:
        return 'stale'
    if 'retention=failed' in message:
        return 'retention'
    return 'failed' if 'last_run=failed' in message else 'unknown'


def bot_status():
    # The inspect format deliberately excludes Config.Env (contains secrets).
    try:
        result = subprocess.run(['docker', 'inspect', '--format',
            '{{json .Id}} {{json .RestartCount}} {{json .State.Status}} {{json .State.Health.Status}}',
            'financial_assistant_bot'], capture_output=True, text=True, check=True, timeout=15)
        identity, restarts, status, health = result.stdout.strip().split()
        return {'id': json.loads(identity), 'restarts': int(restarts),
            'healthy': json.loads(status) == 'running' and json.loads(health) == 'healthy'}
    except (subprocess.SubprocessError, ValueError, OSError):
        return {'id': '', 'restarts': 0, 'healthy': False}


def main():
    sample = {'backup': backup_status(Path('/var/lib/financialassistant-backups')), 'bot': bot_status()}
    try:
        result = subprocess.run(['docker', 'compose', 'exec', '-T', 'app', 'python', '-m',
            'scripts.record_operational_health'], input=json.dumps(sample), capture_output=True, text=True, timeout=40)
        if result.returncode:
            raise RuntimeError('sample delivery failed')
    except (subprocess.SubprocessError, OSError, RuntimeError):
        print('operational_sample=failed')
        return 1
    print('operational_sample=recorded backup=' + sample['backup'] + ' bot=' + ('healthy' if sample['bot']['healthy'] else 'unhealthy'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
