"""User-bound, expiring email codes; never expose codes or digests through APIs."""
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from hashlib import sha256
import hmac
import re
import secrets
import smtplib
import ssl

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.services.financial_report_preferences import lock_recipient, read_report_preferences
from app.repositories.preference_repo import PreferenceRepository


class EmailRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email_address: str=Field(max_length=254)

    @field_validator('email_address')
    @classmethod
    def valid_address(cls,value):
        value=value.strip()
        if any(x in value for x in ('\r','\n','\t')) or value.count('@')!=1:
            raise ValueError('Укажите один адрес почты')
        local,domain=value.rsplit('@',1)
        try:domain=domain.encode('idna').decode('ascii').lower()
        except UnicodeError:raise ValueError('Некорректный домен почты')
        if (not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}",local)
            or local.startswith('.') or local.endswith('.') or '..' in local
            or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',domain)):
            raise ValueError('Укажите корректный адрес почты')
        address=local+'@'+domain
        if len(address)>254:raise ValueError('Слишком длинный адрес почты')
        return address


class EmailConfirmation(EmailRequest):
    code: str=Field(pattern=r'^[0-9]{6}$')


class EmailVerificationError(ValueError):
    def __init__(self,message,status=400):
        super().__init__(message);self.status=status


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def digest(settings,user_id,address,code):
    return hmac.new(settings.app_secret_key.encode(),f'{user_id}|{address}|{code}'.encode(),sha256).hexdigest()


def send_code(settings,address,code):
    message=EmailMessage()
    message['From']=settings.smtp_from;message['To']=address
    message['Subject']='ФинАсист — подтверждение почты для отчётов'
    message.set_content(f'Код подтверждения: {code}\n\nВведите его в настройках ФинАсист в течение 15 минут.\nЕсли вы не запрашивали код, ничего делать не нужно. Финансовых данных в этом письме нет.')
    context=ssl.create_default_context()
    client=smtplib.SMTP_SSL(settings.smtp_host,settings.smtp_port,timeout=20,context=context) if settings.smtp_security=='ssl' else smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=20)
    with client:
        if settings.smtp_security=='starttls':client.ehlo();client.starttls(context=context);client.ehlo()
        client.login(settings.smtp_username,settings.smtp_password)
        if client.send_message(message):raise RuntimeError('Email refused')


def request_code(db,user_id,address,settings,now=None,sender=None):
    address=EmailRequest(email_address=address).email_address
    if not all(getattr(settings,k,'') for k in ('smtp_host','smtp_from','smtp_username','smtp_password')):
        raise EmailVerificationError('Отправка почты временно недоступна',503)
    now=utc(now or datetime.now(timezone.utc))
    row=lock_recipient(db,user_id,settings)
    if row.email_address==address:raise EmailVerificationError('Этот адрес уже подтверждён')
    if row.last_code_at and (now-utc(row.last_code_at)).total_seconds()<60:
        raise EmailVerificationError('Повторный код можно запросить через минуту',429)
    count=row.code_day_count if row.code_day==now.date() else 0
    if count>=5:raise EmailVerificationError('Достигнут лимит: 5 писем с кодом в сутки',429)
    code=f'{secrets.randbelow(1_000_000):06d}'
    row.pending_email=address;row.code_digest=digest(settings,user_id,address,code)
    row.code_expires_at=now+timedelta(minutes=15);row.code_attempts=0
    row.last_code_at=now;row.code_day=now.date();row.code_day_count=count+1
    db.commit()  # Reserve rate limit before SMTP; ambiguous sends are never replayed.
    try:(sender or send_code)(settings,address,code)
    except Exception:raise EmailVerificationError('Не удалось подтвердить отправку письма. Проверьте почту; повторный запрос доступен через минуту.',502) from None


def confirm_code(db,user_id,address,code,settings,now=None):
    now=utc(now or datetime.now(timezone.utc))
    row=lock_recipient(db,user_id,settings)
    if not row.code_digest or not row.code_expires_at or now>=utc(row.code_expires_at) or row.code_attempts>=5:
        raise EmailVerificationError('Код истёк или недействителен. Запросите новый.')
    row.code_attempts+=1
    valid=address==row.pending_email and hmac.compare_digest(row.code_digest,digest(settings,user_id,address,code))
    if not valid:
        db.commit()
        raise EmailVerificationError('Неверный код или адрес почты')
    row.email_address=row.pending_email;row.pending_email=None;row.code_digest=None;row.code_expires_at=None
    db.commit()


def remove_email(db,user_id,settings):
    row=lock_recipient(db,user_id,settings)
    row.email_address=None;row.pending_email=None;row.code_digest=None;row.code_expires_at=None
    prefs=read_report_preferences(db,user_id,settings).model_dump()
    prefs['email']=False
    if not prefs['telegram']:prefs['enabled']=False
    repo=PreferenceRepository(db);current=repo.get_fresh(user_id,for_update=True)
    repo.update(user_id,current.preferences_version,{**(current.data or {}),'financial_reports':prefs})
    db.commit()
