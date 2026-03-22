from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

SERVICES_DIR = REPO_ROOT / "app" / "services"
REPOSITORIES_DIR = REPO_ROOT / "app" / "repositories"
API_DIR = REPO_ROOT / "app" / "api"
TELEGRAM_BOT_SCRIPT = REPO_ROOT / "scripts" / "run_telegram_admin_bot.py"

API_REPOSITORY_IMPORT_ALLOWLIST = set()


def _iter_py_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.name != "__init__.py")


def _imported_module_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_services_and_repositories_do_not_depend_on_api_layer():
    violations: list[str] = []

    for directory in (SERVICES_DIR, REPOSITORIES_DIR):
        for path in _iter_py_files(directory):
            imported = _imported_module_names(path)
            banned = [
                module
                for module in imported
                if module.startswith("app.api")
                or module.startswith("fastapi")
                or module.startswith("starlette")
            ]
            if banned:
                violations.append(f"{path.relative_to(REPO_ROOT)} -> {', '.join(sorted(set(banned)))}")

    assert not violations, "backend layer violation(s):\n" + "\n".join(f"- {item}" for item in violations)


def test_api_repository_imports_are_limited_to_known_boundary_exceptions():
    violations: list[str] = []

    for path in _iter_py_files(API_DIR):
        relative_path = path.relative_to(REPO_ROOT)
        imported = _imported_module_names(path)
        repo_imports = [module for module in imported if module.startswith("app.repositories")]
        if not repo_imports:
            continue
        if relative_path in API_REPOSITORY_IMPORT_ALLOWLIST:
            continue
        violations.append(f"{relative_path} -> {', '.join(sorted(set(repo_imports)))}")

    assert not violations, "unexpected direct repository imports in api layer:\n" + "\n".join(
        f"- {item}" for item in violations
    )


def test_telegram_bot_shell_depends_on_services_not_repositories_or_models():
    imported = _imported_module_names(TELEGRAM_BOT_SCRIPT)
    banned = [
        module
        for module in imported
        if module.startswith("app.repositories")
        or module.startswith("app.db.models")
        or module.startswith("app.api")
        or module.startswith("fastapi")
        or module.startswith("starlette")
    ]

    assert not banned, (
        "telegram bot shell must stay thin and avoid direct repository/model/api imports:\n"
        f"- {TELEGRAM_BOT_SCRIPT.relative_to(REPO_ROOT)} -> {', '.join(sorted(set(banned)))}"
    )

    assert "app.services.plan_reminder_service" not in imported, (
        "telegram bot shell should use telegram-specific reminder adapter service instead of "
        "importing PlanReminderService directly"
    )
