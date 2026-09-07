from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_JS = REPO_ROOT / "static" / "js" / "app-features-work.js"
WORK_TEMPLATE_JS = REPO_ROOT / "static" / "js" / "templates" / "shell-sections-secondary.js"
ACTIVITY_JS = REPO_ROOT / "static" / "js" / "app-activity.js"


def test_work_clock_rollover_keeps_watching_and_only_advances_the_current_month():
    source = WORK_JS.read_text(encoding="utf-8")

    assert "function handleLocalDateRollover(now)" in source
    assert "if (handleLocalDateRollover(now)) return;" in source
    assert "snapshotMonth === isoMonth(previousDate)" in source
    assert "anchor = new Date(now.getFullYear(), now.getMonth(), 1);" in source
    assert "midnightReloadPending = true;" in source
    assert 'nodes.workSection?.classList.contains("hidden")' in source

    rollover = source.split("function handleLocalDateRollover(now)", 1)[1].split(
        "function updateLiveWorkday", 1
    )[0]
    assert "clearInterval" not in rollover
    assert "liveTimerId = null" not in rollover
    assert "loadWorkSection()" in rollover
    assert "if (!midnightReloadPending) return didRollOver;" in rollover


def test_work_clock_checks_rollover_before_requiring_a_live_day():
    source = WORK_JS.read_text(encoding="utf-8")
    update = source.split("function updateLiveWorkday", 1)[1].split(
        "function startLiveTimer", 1
    )[0]

    rollover_check = update.index("handleLocalDateRollover(now)")
    live_baseline_guard = update.index("!liveBaseline || !snapshot?.summary")
    assert rollover_check < live_baseline_guard


def test_work_section_loads_are_single_flight_and_keep_the_latest_anchor():
    source = WORK_JS.read_text(encoding="utf-8")

    assert 'let workLoadPromise = null;' in source
    assert 'let activeWorkLoadKey = "";' in source
    assert "let queuedWorkLoad = null;" in source
    assert "function createWorkLoadRequest({ refresh = false } = {})" in source
    assert "async function performWorkSectionLoad(request)" in source
    assert "async function drainWorkSectionLoads()" in source
    assert "function loadWorkSection({ refresh = false } = {})" in source

    loader = source.split("function loadWorkSection({ refresh = false } = {})", 1)[1].split(
        "function openDayEditor", 1
    )[0]
    assert "if (workLoadPromise)" in loader
    assert "activeWorkLoadKey === request.key" in loader
    assert "queuedWorkLoad?.key === request.key && queuedWorkLoad.refresh" in loader
    assert "if (!keepsQueuedRefresh) queuedWorkLoad = null;" in loader
    assert "queuedWorkLoad?.key === request.key" in loader
    assert "queuedWorkLoad = request;" in loader
    assert ".then(drainWorkSectionLoads)" in loader

    performer = source.split("async function performWorkSectionLoad(request)", 1)[1].split(
        "async function drainWorkSectionLoads", 1
    )[0]
    assert "request.anchor.getFullYear()" in performer
    assert "request.anchor.getMonth() + 1" in performer
    assert "if (request.key !== currentWorkLoadKey()) return;" in performer

    drain = source.split("async function drainWorkSectionLoads()", 1)[1].split(
        "function loadWorkSection", 1
    )[0]
    assert "while (queuedWorkLoad)" in drain
    assert "await performWorkSectionLoad(request)" in drain

    # A mutation during an in-flight read must schedule another pass for the same month.
    assert source.count("loadWorkSection({ refresh: true })") >= 6


def test_work_payment_history_range_is_limited_to_ten_years():
    source = WORK_JS.read_text(encoding="utf-8")
    history_loader = source.split("async function loadPaymentHistory()", 1)[1].split(
        "function statisticsQuery", 1
    )[0]

    assert "profileStart < fallbackFrom ? fallbackFrom : profileStart" in history_loader


def test_role_cards_use_salary_cycle_and_keep_operation_and_plan_actions():
    source = WORK_JS.read_text(encoding="utf-8")
    render = source.split("function renderPayments()", 1)[1].split("function renderCalendar", 1)[0]
    assert "snapshot?.salary_cycle?.components" in render
    assert "snapshot?.salary_cycle?.extras" in render
    assert "snapshot?.payments" not in render
    assert 'componentsByRole.get("advance")' in render
    assert 'componentsByRole.get("salary")' in render
    component = source.split("function renderSalaryCycleComponent(", 1)[1].split("function renderSalaryCycleCard", 1)[0]
    assert 'data-work-operation-id=' in component
    assert 'data-work-open-plan-picker=' in component
    assert 'paymentSourceLabel(row.source)' in component
    assert 'activeSalaryCycleOperations(component)' in component


def test_money_kpis_and_rates_use_only_salary_cycle():
    source = WORK_JS.read_text(encoding="utf-8")
    template = WORK_TEMPLATE_JS.read_text(encoding="utf-8")
    assert 'id="workMoneySummaryGrid"' in template
    assert 'aria-live="polite"' in template
    assert "monthSnapshotPaymentOperations" not in source
    assert "monthVisibleForecasts" not in source
    assert "Получено за месяц" not in source
    for field in ["actual_amount", "forecast_amount", "expected_amount"]:
        assert f'cycle.totals, "{field}"' in source
    assert "Получено за период" in source
    assert "Итого за период" in source
    assert "Недостаточно данных" in source
    assert "Неполный итог" in source
    assert "cycle.earnings_estimate" in source
    assert "без разовых доплат" in source
    assert "snapshot?.summary" not in source.split("function renderEarningsEstimate", 1)[1].split("function renderMoneySummary", 1)[0]
    live_update = source.split("function updateLiveWorkday", 1)[1].split("function startLiveTimer", 1)[0]
    assert "renderMoneySummary();" not in live_update
    month_load = source.split("async function performWorkSectionLoad", 1)[1].split("async function drainWorkSectionLoads", 1)[0]
    assert "renderMoneySummary();" in month_load


def test_time_summary_separates_days_and_hours_without_extra_kpis():
    source = WORK_JS.read_text(encoding="utf-8")
    summary = source.split("function renderSummary()", 1)[1].split("function groupedMoney", 1)[0]
    assert "Отработано часов" in summary
    assert "Отработано дней" in summary
    assert "summary.completed_days" in summary
    assert "summary.planned_days" in summary
    assert "сегодня в процессе" in summary
    assert "К оплате" not in summary
    assert "Исключения" not in summary


def test_payment_link_controls_and_activity_label_have_consistent_accessibility():
    source = WORK_JS.read_text(encoding="utf-8")
    template = WORK_TEMPLATE_JS.read_text(encoding="utf-8")
    activity = ACTIVITY_JS.read_text(encoding="utf-8")

    assert 'id="workPaymentLinkRole" class="segmented work-payment-link-role" role="group"' in template
    assert 'data-work-payment-link-role="salary" type="button" aria-pressed="true"' in template
    assert 'data-work-payment-link-role="advance" type="button" aria-pressed="false"' in template
    assert 'button.setAttribute("aria-pressed"' in source
    assert "nodes.workPaymentLinkToggle.focus();" in source
    assert 'work_payment_link: "связи выплаты"' in activity
