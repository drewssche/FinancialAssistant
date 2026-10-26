"""Validated report controls shared by settings API and scheduled delivery."""
from datetime import datetime, timedelta
from typing import Annotated
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from sqlalchemy import select
from app.db.models.auth_identity import AuthIdentity
from app.db.models.user import User
from app.db.models.financial_report_recipient import FinancialReportRecipient
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


def telegram_identity(db, user_id):
    identities=list(db.scalars(select(AuthIdentity).join(User,User.id==AuthIdentity.user_id).where(
        AuthIdentity.user_id==user_id,AuthIdentity.provider=='telegram',User.status.in_(['approved','active']))))
    if len(identities)!=1 or not identities[0].provider_user_id.isdecimal():
        return None
    return identities[0]


def legacy_owner(db,user_id,settings):
    identity=telegram_identity(db,user_id)
    return bool(identity and identity.provider_user_id==getattr(settings,'financial_reports_telegram_id',''))


def read_report_preferences(db,user_id,settings=None):
    row=db.get(UserPreference,user_id)
    raw=(row.data or {}).get('financial_reports') if row else None
    if raw is not None:
        return ReportPreferences.model_validate(raw)
    if settings is not None and legacy_owner(db,user_id,settings):
        return ReportPreferences()
    return ReportPreferences(enabled=False,email=False)


def configured_for(db,user_id,settings):
    return bool(settings.financial_reports_enabled and telegram_identity(db,user_id))


def report_recipients(db,user_id,settings):
    identity=telegram_identity(db,user_id)
    if identity is None:
        return {}
    row=db.get(FinancialReportRecipient,user_id)
    address=row.email_address if row else (getattr(settings,'financial_reports_email','') if legacy_owner(db,user_id,settings) else None)
    recipients={'telegram':identity.provider_user_id}
    if address:
        recipients['email']=address
    return recipients


def activation_date(db,user_id,settings):
    row=db.get(FinancialReportRecipient,user_id)
    start=row.activated_on if row else None
    if not start and legacy_owner(db,user_id,settings):
        start=settings.financial_reports_start_date
    if start and settings.financial_reports_start_date:
        start=max(start,settings.financial_reports_start_date)
    return start


def lock_recipient(db,user_id,settings):
    # Serialize creation and verification on a stable parent row too.
    db.execute(select(User.id).where(User.id==user_id).with_for_update()).scalar_one()
    row=db.scalar(select(FinancialReportRecipient).where(FinancialReportRecipient.user_id==user_id)
                  .with_for_update().execution_options(populate_existing=True))
    if row is None:
        legacy=legacy_owner(db,user_id,settings)
        row=FinancialReportRecipient(user_id=user_id,
            email_address=(getattr(settings,'financial_reports_email','') or None) if legacy else None,
            activated_on=settings.financial_reports_start_date if legacy else None,
            code_attempts=0,code_day_count=0)
        db.add(row);db.flush()
    return row


def view_report_preferences(db,user_id,settings,now=None):
    from app.services.financial_report_data import ZONE, scheduled_period
    available=configured_for(db,user_id,settings)
    prefs=read_report_preferences(db,user_id,settings) if available else ReportPreferences(enabled=False,email=False)
    recipients=report_recipients(db,user_id,settings) if available else {}
    identity=telegram_identity(db,user_id) if available else None
    recipient=db.get(FinancialReportRecipient,user_id) if available else None
    now=(now or datetime.now(ZONE)).astimezone(ZONE)
    next_send=None
    ledger=None
    state_dir=getattr(settings,'financial_reports_state_dir','')
    if available and state_dir and (Path(state_dir)/'deliveries.sqlite3').exists():
        from app.services.financial_report_delivery import ReportLedger
        ledger=ReportLedger(state_dir)
    start=activation_date(db,user_id,settings) if available else None
    if available and prefs.enabled and start:
        hour,minute=map(int,prefs.send_time.split(':'))
        for offset in range(367):
            d=now.date()+timedelta(days=offset)
            if d<start:continue
            moment=datetime(d.year,d.month,d.day,hour,minute,tzinfo=ZONE)
            if ledger and all(ledger.state(f'{user_id}-{d.isoformat()}',c) in {'sent','uncertain','sending'} for c in prefs.channels):
                continue
            if moment>now and scheduled_period(d,prefs.kinds):
                next_send=moment.isoformat();break
    username=getattr(settings,'normalized_telegram_bot_username','')
    return {'available':available,'settings':prefs.model_dump(),'timezone':'Europe/Minsk',
            'email_address':recipients.get('email'),'pending_email':recipient.pending_email if recipient else None,
            'telegram_account':('@'+identity.username if identity.username else 'Telegram текущего аккаунта') if identity else None,
            'telegram_bot_url':'https://t.me/'+username if username else None,'next_send':next_send}


def save_report_preferences(db,user_id,payload,settings=None,now=None):
    if settings is not None:
        from app.services.financial_report_data import ZONE
        if not configured_for(db,user_id,settings):
            raise ValueError('Войдите через Telegram в одобренный профиль')
        recipient=lock_recipient(db,user_id,settings)
        if payload.email and not recipient.email_address:
            raise ValueError('Сначала подтвердите почту для отчётов')
        if payload.enabled and recipient.activated_on is None:
            recipient.activated_on=(now or datetime.now(ZONE)).astimezone(ZONE).date()
    repo=PreferenceRepository(db)
    current=repo.get_fresh(user_id,for_update=True)
    data={**(current.data or {}),'financial_reports':payload.model_dump()}
    repo.update(user_id=user_id,preferences_version=current.preferences_version,data=data)
    db.commit()
