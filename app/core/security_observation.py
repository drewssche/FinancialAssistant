"""Passive request signals. Never changes a response or makes an access decision."""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from ipaddress import ip_address
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from time import monotonic, time
from uuid import uuid4

from starlette.requests import Request


# Exact, nonexistent routes only; ordinary missing pages/assets are not signals.
SIGNAL_PATHS = frozenset({
    "/login", "/signin", "/token", "/auth", "/admin", "/admin/login",
    "/api/auth", "/api/login", "/api/signin", "/api/token", "/api/auth/login",
    "/api/v1/login", "/api/v1/signin", "/api/v1/token", "/api/v1/auth",
    "/api/v1/auth/admin/login", "/api/v1/auth/admin", "/api/v1/auth/user/login",
    "/api/v1/auth/user", "/api/v1/auth/login", "/api/v1/auth/signin", "/api/v1/auth/token",
})
AUTH_PATHS = frozenset({"/api/v1/auth/telegram", "/api/v1/auth/telegram/browser", "/api/v1/auth/refresh"})
DOC_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"})
DRY_RUN_STATUSES = {"DELAYED_DRY_RUN", "REJECTED_DRY_RUN"}


def documentation_options(production: bool) -> dict:
    return {"docs_url": None, "redoc_url": None, "openapi_url": None} if production else {}


def normalized_path(request: Request) -> str:
    path = request.url.path.rstrip("/") or "/"
    if path in SIGNAL_PATHS | AUTH_PATHS | DOC_PATHS:
        return path
    # Templates hide IDs and arbitrary user-supplied path segments. They also
    # prevent unbounded cardinality in the existing request metrics.
    route = request.scope.get("route")
    return getattr(route, "path", None) or "<unmatched>"


def client_context(request: Request, trusted_proxy_ips: frozenset[str]) -> tuple[str, str | None]:
    peer = request.client.host if request.client else "unknown"
    # Uvicorn must preserve the socket peer (--no-proxy-headers). Only the exact
    # configured proxy may supply these headers; X-Forwarded-For is never read.
    if peer in trusted_proxy_ips:
        try:
            client = str(ip_address(request.headers.get("x-real-ip", "")))
        except ValueError:
            client = peer
        rate = request.headers.get("x-fa-rate-observation")
        return client, rate if rate in DRY_RUN_STATUSES else None
    try:
        return str(ip_address(peer)), None
    except ValueError:
        return "unknown", None


class SecurityJournal:
    """Private JSONL journal, <= 4 x 2 MiB, maximum seven days of idle retention.

    Retention is checked on writes/startup; an idle journal is pruned on its next
    use. The named Docker volume survives app replacement. No DB or network IO.
    """

    def __init__(self, filename: str):
        self.path = Path(filename)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.parent.chmod(0o700)
        self.lock_path = self.path.with_suffix('.lock')
        with self.lock_path.open('a') as lock_file:
            self.lock_path.chmod(0o600)
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            self.prune()
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        self.handler = RotatingFileHandler(filename, maxBytes=2 * 1024 * 1024, backupCount=3, delay=True)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.last_prune = monotonic()
        self.lock = Lock()

    def prune(self):
        for path in [self.path, *(Path(str(self.path) + f".{n}") for n in range(1, 4))]:
            if path.exists() and path.stat().st_mtime < time() - 7 * 86400:
                path.unlink()

    def __call__(self, event: dict):
        with self.lock:
            with self.lock_path.open('a') as lock_file:
                self.lock_path.chmod(0o600)
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    # Another process (the operator smoke test) may rotate the
                    # file. Reopen under the shared lock before every append.
                    if self.handler.stream:
                        self.handler.stream.close()
                        self.handler.stream = None
                    self.write(event)
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)

    def write(self, event: dict):
        if monotonic() - self.last_prune >= 3600:
            if self.handler.stream:
                self.handler.stream.close()
                self.handler.stream = None
            self.prune()
            self.last_prune = monotonic()
        self.handler.handle(logging.LogRecord(
            "security", logging.INFO, "", 0, json.dumps(event, ensure_ascii=True), (), None,
        ))
        if self.path.exists():
            self.path.chmod(0o600)


@dataclass
class SourceWindow:
    started: float
    requests: int = 0
    failures: int = 0
    paths: set[str] = field(default_factory=set)
    emitted: int = 0
    minute: int = -1
    last_events: dict[str, float] = field(default_factory=dict)


class SecurityObserver:
    MAX_SOURCES = 4096
    MAX_EVENTS_PER_MINUTE = 200
    MAX_SOURCE_EVENTS_PER_MINUTE = 10
    WINDOW_SECONDS = 300

    def __init__(self, sink, trusted_proxy_ips=(), clock=monotonic):
        self.sink = sink
        self.trusted_proxy_ips = frozenset(trusted_proxy_ips)
        self.clock = clock
        self.sources: OrderedDict[str, SourceWindow] = OrderedDict()
        self.lock = Lock()
        self.minute = -1
        self.emitted = 0
        self.suppressed = 0

    def observe(self, request: Request, status: int):
        path = normalized_path(request)
        probe = status == 404 and path in SIGNAL_PATHS | DOC_PATHS
        # A pending/rejected account trying to open the UI is not an attack.
        access_pending = getattr(request.state, "access_not_approved", False)
        failure = not access_pending and (
            status == 401 or (status == 403 and path.startswith("/api/"))
            or (path in AUTH_PATHS and status in {400, 422})
        )
        client, rate = client_context(request, self.trusted_proxy_ips)
        if not (probe or failure or rate):
            return
        now = self.clock()
        minute = int(now // 60)
        with self.lock:
            # Bound both source cardinality and stale-source retention.
            while self.sources and now - next(iter(self.sources.values())).started >= self.WINDOW_SECONDS:
                self.sources.popitem(last=False)
            source = self.sources.get(client)
            if source is None or now - source.started >= self.WINDOW_SECONDS:
                if len(self.sources) >= self.MAX_SOURCES:
                    self.sources.popitem(last=False)
                source = SourceWindow(now)
                self.sources[client] = source
            source.requests += 1
            source.failures += int(failure)
            if len(source.paths) < 32:
                source.paths.add(path)
            if self.minute != minute:
                self.minute, self.emitted = minute, 0
            if source.minute != minute:
                source.minute, source.emitted = minute, 0
            kind = "rate_would_limit" if rate else "signal_route" if probe else "repeated_access_failure"
            if failure and not probe and not rate and source.failures < 5:
                return
            # Log each probe path once/minute; repeated failures/rate hits are
            # summarized once/minute per source, without affecting traffic.
            key = path if kind == "signal_route" else kind
            if key in source.last_events and now - source.last_events[key] < 60:
                self.suppressed += 1
                return
            if self.emitted >= self.MAX_EVENTS_PER_MINUTE or source.emitted >= self.MAX_SOURCE_EVENTS_PER_MINUTE:
                self.suppressed += 1
                return
            source.last_events[key] = now
            self.emitted += 1
            source.emitted += 1
            user_id = getattr(request.state, "authenticated_user_id", None)
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(), "mode": "observe",
                "event": kind, "client_ip": client,
                "method": request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "OTHER",
                "path": path, "status": status,
                "request_id": getattr(request.state, "request_id", str(uuid4())),
                "user_id": user_id if isinstance(user_id, int) else None,
                "rate_status": rate, "signals_in_window": source.requests,
                "failures_in_window": source.failures, "distinct_paths": len(source.paths),
                "suppressed_since_last_event": self.suppressed,
            }
            self.suppressed = 0
            try:
                self.sink(event)
            except OSError:
                # Disk failures must not deny service or change authentication.
                logging.getLogger(__name__).error("security_journal_write_failed")
