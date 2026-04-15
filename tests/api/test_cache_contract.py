from app.core.cache import (
    build_categories_cache_key,
    build_debts_cache_key,
    build_dashboard_analytics_cache_key,
    build_dashboard_summary_cache_key,
    build_item_templates_cache_key,
    build_operations_cache_key,
    build_plans_cache_key,
    build_user_scoped_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_user_scoped_cache,
    reset_cache_for_tests,
    set_json,
)


def test_dashboard_summary_wrapper_keeps_existing_key_shape():
    key = build_dashboard_summary_cache_key(
        user_id=7,
        period="month",
        date_from=None,
        date_to=None,
    )
    assert key == "dashsum:v1:u:7:p:month:from:-:to:-"


def test_user_scoped_cache_invalidation_is_namespace_specific():
    reset_cache_for_tests()
    summary_key = build_dashboard_summary_cache_key(
        user_id=7,
        period="month",
        date_from=None,
        date_to=None,
    )
    analytics_key = build_user_scoped_cache_key(
        namespace="dashboard_analytics",
        user_id=7,
        period="month",
        view="calendar",
    )
    other_user_summary_key = build_dashboard_summary_cache_key(
        user_id=8,
        period="month",
        date_from=None,
        date_to=None,
    )

    set_json(summary_key, {"scope": "summary"})
    set_json(analytics_key, {"scope": "analytics"})
    set_json(other_user_summary_key, {"scope": "other"})

    invalidate_user_scoped_cache(namespace="dashboard_summary", user_id=7)

    assert get_json(summary_key) is None
    assert get_json(analytics_key) == {"scope": "analytics"}
    assert get_json(other_user_summary_key) == {"scope": "other"}


def test_namespace_ttl_registry_exposes_current_backend_contract():
    assert get_namespace_ttl_seconds("dashboard_summary") == 60
    assert get_namespace_ttl_seconds("dashboard_analytics") == 60
    assert get_namespace_ttl_seconds("plans") == 60
    assert get_namespace_ttl_seconds("item_templates") == 60
    assert get_namespace_ttl_seconds("debts") == 60
    assert get_namespace_ttl_seconds("operations") == 60
    assert get_namespace_ttl_seconds("categories") == 60


def test_dashboard_analytics_key_shape_is_namespaced_and_parameterized():
    key = build_dashboard_analytics_cache_key(
        user_id=7,
        view="highlights",
        period="month",
        date_from=None,
        date_to=None,
        month_anchor=None,
        category_kind="expense",
        category_breakdown_level="group",
    )
    assert key == (
        "dashanalytics:v1:u:7:view:highlights:period:month:from:-:to:-:"
        "month:-:category_kind:expense:category_breakdown_level:group:granularity:-:year:-"
    )


def test_dashboard_analytics_trend_key_shape_is_parameterized_by_granularity():
    key = build_dashboard_analytics_cache_key(
        user_id=7,
        view="trend",
        period="custom",
        date_from="2026-03-01",
        date_to="2026-03-03",
        granularity="day",
    )
    assert key == (
        "dashanalytics:v1:u:7:view:trend:period:custom:from:2026-03-01:to:2026-03-03:"
        "month:-:category_kind:-:category_breakdown_level:-:granularity:day:year:-"
    )


def test_dashboard_analytics_calendar_key_shape_is_parameterized_by_month_anchor():
    key = build_dashboard_analytics_cache_key(
        user_id=7,
        view="calendar",
        period="month",
        date_from=None,
        date_to=None,
        month_anchor="2026-03-01",
    )
    assert key == (
        "dashanalytics:v1:u:7:view:calendar:period:month:from:-:to:-:"
        "month:2026-03-01:category_kind:-:category_breakdown_level:-:granularity:-:year:-"
    )


def test_dashboard_analytics_calendar_year_key_shape_is_parameterized_by_year_anchor():
    key = build_dashboard_analytics_cache_key(
        user_id=7,
        view="calendar_year",
        period="year",
        date_from=None,
        date_to=None,
        year_anchor=2026,
    )
    assert key == (
        "dashanalytics:v1:u:7:view:calendar_year:period:year:from:-:to:-:"
        "month:-:category_kind:-:category_breakdown_level:-:granularity:-:year:2026"
    )


def test_plans_cache_key_shape_is_namespaced_and_parameterized():
    key = build_plans_cache_key(
        user_id=7,
        view="history",
        q="коммуналка",
        kind="expense",
    )
    assert key == "plans:v1:u:7:view:history:q:коммуналка:kind:expense"


def test_item_templates_list_cache_key_shape_is_namespaced_and_parameterized():
    key = build_item_templates_cache_key(
        user_id=7,
        view="list",
        page=2,
        page_size=50,
        q="Ротманс",
    )
    assert key == "itemtpl:v1:u:7:view:list:page:2:page_size:50:q:Ротманс:template_id:-:limit:-"


def test_item_templates_prices_cache_key_shape_is_namespaced_and_parameterized():
    key = build_item_templates_cache_key(
        user_id=7,
        view="prices",
        template_id=13,
        limit=100,
    )
    assert key == "itemtpl:v1:u:7:view:prices:page:-:page_size:-:q:-:template_id:13:limit:100"


def test_debts_cards_cache_key_shape_is_namespaced_and_parameterized():
    key = build_debts_cache_key(
        user_id=7,
        view="cards",
        include_closed=True,
        q="олег",
    )
    assert key == "debts:v1:u:7:view:cards:include_closed:True:q:олег"


def test_operations_summary_cache_key_shape_is_namespaced_and_parameterized():
    key = build_operations_cache_key(
        user_id=7,
        view="summary",
        page=None,
        page_size=None,
        sort_by=None,
        sort_dir=None,
        kind="expense",
        date_from="2026-03-01",
        date_to="2026-03-31",
        category_id=5,
        q="еда",
        quick_view="large",
    )
    assert (
        key
        == "ops:v1:u:7:view:summary:page:-:page_size:-:sort_by:-:sort_dir:-:kind:expense:date_from:2026-03-01:date_to:2026-03-31:category_id:5:q:еда:quick_view:large:currency_scope:-"
    )


def test_operations_list_cache_key_shape_is_namespaced_and_parameterized():
    key = build_operations_cache_key(
        user_id=7,
        view="list",
        page=2,
        page_size=20,
        sort_by="operation_date",
        sort_dir="desc",
        kind="expense",
        date_from="2026-03-01",
        date_to="2026-03-31",
        category_id=5,
        q="еда",
        quick_view="receipt",
    )
    assert (
        key
        == "ops:v1:u:7:view:list:page:2:page_size:20:sort_by:operation_date:sort_dir:desc:kind:expense:date_from:2026-03-01:date_to:2026-03-31:category_id:5:q:еда:quick_view:receipt:currency_scope:-"
    )


def test_categories_groups_cache_key_shape_is_namespaced_and_parameterized():
    key = build_categories_cache_key(
        user_id=7,
        view="groups",
    )
    assert key == "cats:v1:u:7:view:groups:page:-:page_size:-:kind:-:q:-"


def test_categories_paginated_cache_key_shape_is_namespaced_and_parameterized():
    key = build_categories_cache_key(
        user_id=7,
        view="paginated",
        page=2,
        page_size=20,
        kind="expense",
        q="еда",
    )
    assert key == "cats:v1:u:7:view:paginated:page:2:page_size:20:kind:expense:q:еда"
