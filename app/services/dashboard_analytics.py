from sqlalchemy.orm import Session

from app.repositories.currency_repo import CurrencyRepository
from app.repositories.debt_repo import DebtRepository
from app.repositories.operation_repo import OperationRepository
from app.services.dashboard_analytics_highlights import DashboardAnalyticsHighlightsService
from app.services.dashboard_analytics_timeline import DashboardAnalyticsTimelineService


class DashboardAnalyticsService:
    def __init__(self, db: Session, repo: OperationRepository):
        self.timeline = DashboardAnalyticsTimelineService(repo, CurrencyRepository(db), DebtRepository(db))
        self.highlights = DashboardAnalyticsHighlightsService(db, repo, self.timeline)

    def resolve_period_bounds(self, **kwargs) -> tuple:
        return self.timeline.resolve_period_bounds(**kwargs)

    def month_bounds(self, anchor):
        return self.timeline.month_bounds(anchor)

    def percent_change(self, current, previous):
        return self.timeline.percent_change(current, previous)

    def get_calendar(self, **kwargs) -> dict:
        return self.timeline.get_calendar(**kwargs)

    def get_calendar_year(self, **kwargs) -> dict:
        return self.timeline.get_calendar_year(**kwargs)

    def get_trend(self, **kwargs) -> dict:
        return self.timeline.get_trend(**kwargs)

    def get_highlights(self, **kwargs) -> dict:
        return self.highlights.get_highlights(**kwargs)
