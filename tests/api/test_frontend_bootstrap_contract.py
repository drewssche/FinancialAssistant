from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "static" / "index.html"
MANIFEST_JS = REPO_ROOT / "static" / "js" / "app-manifest.js"


def test_index_html_uses_manifest_bootstrap_pair():
    html = INDEX_HTML.read_text(encoding="utf-8")

    script_sources = re.findall(r'<script[^>]+src="([^"]+)"', html)

    assert "/static/js/app-manifest.js?v=20260809a" in script_sources
    assert "/static/js/app-bootstrap.js?v=20260818a" in script_sources
    assert "/static/js/app-init.js" not in script_sources


def test_manifest_lists_bootstrap_scripts_in_stable_order():
    manifest = MANIFEST_JS.read_text(encoding="utf-8")
    script_sources = re.findall(r'"(/static/js/[^"]+\.js)"', manifest)

    assert script_sources, "frontend script manifest must not be empty"
    assert script_sources[0] == "/static/js/templates/shell-sections-primary.js"
    assert script_sources[-1] == "/static/js/app-init.js"
    assert len(script_sources) == len(set(script_sources)), "frontend script manifest must not contain duplicates"
    assert "/static/js/app-init-registry.js" in script_sources
    assert script_sources.index("/static/js/app-init-registry.js") < script_sources.index("/static/js/app-init-core.js")
    assert script_sources.index("/static/js/app-features-operation-modal-debt-counterparty.js") < script_sources.index(
        "/static/js/app-features-operation-modal-debt.js"
    )
    assert script_sources.index("/static/js/app-features-operation-modal-debt.js") < script_sources.index(
        "/static/js/app-features-operation-modal.js"
    )
    assert script_sources.index("/static/js/app-features-operation-modal-fx-settlement.js") < script_sources.index(
        "/static/js/app-features-operation-modal-currency.js"
    )
    assert script_sources.index("/static/js/app-features-operation-modal-currency.js") < script_sources.index(
        "/static/js/app-features-operation-modal.js"
    )
    assert script_sources.index("/static/js/app-features-plans-recurrence.js") < script_sources.index(
        "/static/js/app-features-plans.js"
    )
    assert script_sources.index("/static/js/app-features-plans-render.js") < script_sources.index(
        "/static/js/app-features-plans.js"
    )
    assert script_sources.index("/static/js/app-features-plans-dashboard.js") < script_sources.index(
        "/static/js/app-features-plans.js"
    )
    assert script_sources.index("/static/js/app-period-control-utils.js") < script_sources.index(
        "/static/js/app-features-plans-dashboard.js"
    )
    assert script_sources.index("/static/js/app-period-control-utils.js") < script_sources.index(
        "/static/js/app-init-features-analytics-period-controls.js"
    )
    assert script_sources.index("/static/js/app-period-control-utils.js") < script_sources.index(
        "/static/js/app-init-features-operations-period-controls.js"
    )
    assert script_sources.index("/static/js/app-init-features-analytics-period-controls.js") < script_sources.index(
        "/static/js/app-init-features-analytics.js"
    )
    assert script_sources.index("/static/js/app-init-features-operations-period-controls.js") < script_sources.index(
        "/static/js/app-init-features.js"
    )


def test_bootstrap_fetches_manifest_scripts_in_parallel_with_ordered_execution():
    bootstrap = (REPO_ROOT / "static" / "js" / "app-bootstrap.js").read_text(encoding="utf-8")

    assert 'const assetVersion = "20260818a"' in bootstrap
    assert "script.async = false" in bootstrap
    assert "Promise.all(manifest.map((src) => loadScript(src)))" in bootstrap


def test_app_init_uses_bootstrap_registry_with_global_fallback():
    app_init = (REPO_ROOT / "static" / "js" / "app-init.js").read_text(encoding="utf-8")

    assert 'getBootstrapModule?.("core")' in app_init
    assert 'getBootstrapModule?.("features")' in app_init
    assert 'getBootstrapModule?.("startup")' in app_init
    assert "|| window.App.initCore" in app_init


def test_runtime_registry_is_loaded_before_feature_modules():
    manifest = MANIFEST_JS.read_text(encoding="utf-8")
    script_sources = re.findall(r'"(/static/js/[^"]+\.js)"', manifest)

    registry_index = script_sources.index("/static/js/app-runtime-registry.js")
    assert registry_index < script_sources.index("/static/js/app-activity.js")
    assert registry_index < script_sources.index("/static/js/app-usage.js")
    assert registry_index < script_sources.index("/static/js/app-features-dashboard.js")
    assert registry_index < script_sources.index("/static/js/app-features-session-auth.js")
    assert registry_index < script_sources.index("/static/js/app-features-session.js")
    assert registry_index < script_sources.index("/static/js/app-features.js")
    assert script_sources.index("/static/js/app-categories-ui-coordinator.js") < script_sources.index(
        "/static/js/app-categories-table-ui.js"
    )
    assert script_sources.index("/static/js/app-categories-section-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-catalog.js"
    )
    assert script_sources.index("/static/js/app-debts-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-debts.js"
    )
    assert script_sources.index("/static/js/app-analytics-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-analytics.js"
    )
    assert script_sources.index("/static/js/app-picker-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-pickers.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-ui-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-catalog.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-section-coordinator.js") < script_sources.index(
        "/static/js/app-features-item-catalog.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-render-coordinator.js") < script_sources.index(
        "/static/js/app-features-item-catalog.js"
    )
    assert script_sources.index("/static/js/app-item-catalog-section-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-catalog.js"
    )
    assert script_sources.index("/static/js/app-analytics-hover-coordinator.js") < script_sources.index(
        "/static/js/app-init-features-analytics.js"
    )
    assert script_sources.index("/static/js/app-analytics-hover-state-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )
    assert script_sources.index("/static/js/app-analytics-breakdown-ui-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )
    assert script_sources.index("/static/js/app-analytics-breakdown-visibility-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )
    assert script_sources.index("/static/js/app-analytics-breakdown-snapshot-coordinator.js") < script_sources.index(
        "/static/js/app-features-analytics-highlights-ui.js"
    )


def test_runtime_registry_registrations_exist_for_key_modules():
    runtime_files = [
        REPO_ROOT / "static" / "js" / "app-activity.js",
        REPO_ROOT / "static" / "js" / "app-features-session-preferences.js",
        REPO_ROOT / "static" / "js" / "app-features-session-auth.js",
        REPO_ROOT / "static" / "js" / "app-features-session.js",
        REPO_ROOT / "static" / "js" / "app-features-dashboard.js",
        REPO_ROOT / "static" / "js" / "app-features-admin.js",
        REPO_ROOT / "static" / "js" / "app-features-debts.js",
        REPO_ROOT / "static" / "js" / "app-features-analytics.js",
        REPO_ROOT / "static" / "js" / "app-features-plans.js",
        REPO_ROOT / "static" / "js" / "app-features-item-catalog.js",
        REPO_ROOT / "static" / "js" / "app-features-operations.js",
        REPO_ROOT / "static" / "js" / "app-features-operation-modal.js",
    ]

    contents = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)

    assert 'registerRuntimeModule?.("activity"' in contents
    assert 'registerRuntimeModule?.("session-preferences"' in contents
    assert 'registerRuntimeModule?.("session-auth"' in contents
    assert 'registerRuntimeModule?.("session"' in contents
    assert 'registerRuntimeModule?.("dashboard"' in contents
    assert 'registerRuntimeModule?.("admin"' in contents
    assert 'registerRuntimeModule?.("debts"' in contents
    assert 'registerRuntimeModule?.("analytics"' in contents
    assert 'registerRuntimeModule?.("plans"' in contents
    assert 'registerRuntimeModule?.("item-catalog"' in contents
    assert 'registerRuntimeModule?.("operations"' in contents
    assert 'registerRuntimeModule?.("operation-modal"' in contents
