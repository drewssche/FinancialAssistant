from app.core.worker_health import check_worker_health


if __name__ == "__main__":
    healthy = check_worker_health()
    print("telegram worker: healthy" if healthy else "telegram worker: no recent successful poll/progress")
    raise SystemExit(0 if healthy else 1)
