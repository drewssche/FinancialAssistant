"""Validated report controls shared by settings API and scheduled delivery."""
from datetime import datetime, timedelta
from typing import Annotated
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from sqlalchemy import select
from app.db.models.auth_identity import AuthIdentity
from app.db.models.user_preference import UserPreference
from app.repositories.preference_repo import PreferenceRepository


class ReportPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: StrictBool = True
    weekly: StrictBool = True
    monthly: StrictBool = True
    yearly: StrictBool = True
    telegram: StrictBool = True
    email: StrictBool = True
    send_time: Annotated[str, Field(pattern=r'^([01]\d|2[0-3]):(00|15|30|45)$')] = '09:00'

    @model_validator(mode='after')
    def validate_enabled(self):
        if self.enabled and not any((self.weekly,self.monthly,self.yearly)):
            raise ValueError('Выберите хотя бы один период отчёта')
        if self.enabled and not any((self.telegram,self.email)):
            raise ValueError('Выберите хотя бы один канал доставки')
        return self

    @property
    def kinds(self):
        return {kind for kind, enabled in [('week',self.weekly),('month',self.monthly),('year',self.yearly)] if enabled}

    @property
    def channels(self):
        return [c for c in ('telegram','email') if getattr(self,c)]


def read_report_preferences(db, user_id):
    row=db.get(UserPreference,user_id)
    raw=(row.data or {}).get('financial_reports',{}) if row else {}
    return ReportPreferences.model_validate(raw)


def configured_for(db,user_id,settings):
    return bool(settings.financial_reports_enabled and db.scalar(select(AuthIdentity.id).where(
        AuthIdentity.user_id==user_id,AuthIdentity.provider=='telegram',
        AuthIdentity.provider_user_id==settings.financial_reports_telegram_id)))


def view_report_preferences(db,user_id,settings,now=None):
    from app.services.financial_report_data import ZONE, scheduled_period
    available=configured_for(db,user_id,settings)
    prefs=read_report_preferences(db,user_id) if available else ReportPreferences(enabled=False)
    now=(now or datetime.now(ZONE)).astimezone(ZONE)
    next_send=None
    ledger=None
    state_dir=getattr(settings,'financial_reports_state_dir','')
    if available and state_dir and (Path(state_dir)/'deliveries.sqlite3').exists():
        from app.services.financial_report_delivery import ReportLedger
        ledger=ReportLedger(state_dir)
    if available and prefs.enabled:
        hour,minute=map(int,prefs.send_time.split(':'))
        for offset in range(367):
            d=now.date()+timedelta(days=offset)
            if settings.financial_reports_start_date and d<settings.financial_reports_start_date:continue
            moment=datetime(d.year,d.month,d.day,hour,minute,tzinfo=ZONE)
            if ledger and all(ledger.state(f'{user_id}-{d.isoformat()}',c) in {'sent','uncertain','sending'} for c in prefs.channels):
                continue
            if moment>now and scheduled_period(d,prefs.kinds):
                next_send=moment.isoformat();break
    return {'available':available,'settings':prefs.model_dump(),'timezone':'Europe/Minsk',
            'email_address':settings.financial_reports_email if available else None,'next_send':next_send}


def save_report_preferences(db,user_id,payload):
    repo=PreferenceRepository(db)
    current=repo.get_fresh(user_id,for_update=True)
    data={**(current.data or {}),'financial_reports':payload.model_dump()}
    repo.update(user_id=user_id,preferences_version=current.preferences_version,data=data)
    db.commit()
