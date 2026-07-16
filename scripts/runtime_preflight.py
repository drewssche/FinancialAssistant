#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Report non-secret FinancialAssistant runtime configuration safety checks.")
    parser.add_argument("--strict", action="store_true", help="Return a non-zero status when warnings are found.")
    args = parser.parse_args()

    settings = get_settings()
    normalized_env = settings.app_env.strip().lower()
    warnings: list[str] = []
    if normalized_env not in {"development", "test", "production"}:
        warnings.append("APP_ENV is not one of: development, test, production")
    if normalized_env == "production":
        warnings.extend(settings.production_config_errors())

    print(f"APP_ENV={normalized_env or '<empty>'}")
    print(f"production_checks_enabled={'yes' if settings.is_production else 'no'}")
    print(f"cors_origin_count={len(settings.cors_origins)}")
    print(f"admin_id_count={len(settings.admin_telegram_id_set)}")
    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1 if args.strict else 0
    print("runtime_preflight=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
