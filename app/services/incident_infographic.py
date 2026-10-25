"""Incident PNGs from bounded observation snapshots; never synthesize measurements."""
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

BG, SURFACE, EDGE = '#080e18', '#111c2d', '#29394f'
TEXT, MUTED, RED, ORANGE, CYAN = '#f1f5fc', '#a5b7ce', '#ff8b9e', '#ffab52', '#75d1d8'
SIZE = (1080, 1260)
MAX_BYTES = 5_000_000
ZONE = ZoneInfo('Europe/Minsk')
FONT_PAIRS = (
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
)


@lru_cache(maxsize=32)
def font(size, bold=False):
    for pair in FONT_PAIRS:
        if all(Path(p).is_file() for p in pair):
            return ImageFont.truetype(pair[int(bold)], size)
    raise RuntimeError('Cyrillic notification font is unavailable')


def stamp(value):
    return datetime.fromtimestamp(value, ZONE).strftime('%d.%m %H:%M')


class Card:
    def __init__(self, *, test=False):
        self.image = Image.new('RGB', SIZE, BG)
        self.draw = ImageDraw.Draw(self.image)
        self.box((20, 20, 1060, 1240), SURFACE, EDGE, 32)
        self.text(62, 61, 'Φ', 53, ORANGE, True)
        self.draw.ellipse((96, 107, 108, 119), fill='#5ac9af')
        self.text(129, 75, 'ФинАсист', 30, bold=True)
        self.box((790, 70, 1018, 110), '#202f44', radius=12)
        self.text(904, 81, 'ТЕСТ ДОСТАВКИ' if test else 'УВЕДОМЛЕНИЕ', 17, MUTED, True, center=True)

    def text(self, x, y, text, size=28, color=TEXT, bold=False, *, center=False, width=None):
        text = str(text).replace('\n', ' ').replace('\r', ' ')
        face = font(size, bold)
        if width is not None:
            while text and self.draw.textlength(text, font=face) > width:
                text = text[:-2].rstrip('…') + '…'
        if center:
            x -= self.draw.textlength(text, font=face) / 2
        self.draw.text((x, y), text, font=face, fill=color)

    def box(self, rect, fill, outline=None, radius=20):
        self.draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=2)

    def line(self, coords, color, width=3):
        self.draw.line(coords, fill=color, width=width)

    def circle(self, x, y, radius, fill, outline=None):
        self.draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill, outline=outline, width=2)

    def cross(self, x, y, radius=11):
        self.line((x-radius, y-radius, x+radius, y+radius), RED, 4)
        self.line((x-radius, y+radius, x+radius, y-radius), RED, 4)

    def footer(self, value):
        self.line((62, 1158, 1018, 1158), EDGE, 2)
        self.text(62, 1182, f'{stamp(value)} · время Минска', 22, MUTED)

    def finish(self):
        output = BytesIO()
        self.image.save(output, format='PNG', optimize=True)
        result = output.getvalue()
        if len(result) > MAX_BYTES:
            raise ValueError('Notification image too large')
        return result


def security_card(payload):
    test = payload.get('kinds') == ['security_notification_test']
    c = Card(test=test)
    if test:
        c.text(62, 177, 'Проверка доставки', 56, bold=True)
        c.text(62, 256, 'Это тест, а не сообщение об инциденте.', 28, MUTED)
        c.box((62, 360, 1018, 830), '#152238', EDGE, 24)
        c.circle(540, 565, 100, '#1b3545', CYAN)
        c.box((476, 525, 604, 605), None, CYAN, 10)
        c.line((479, 529, 540, 576, 601, 529), CYAN, 4)
        c.text(540, 714, 'Инфографика уведомлений', 34, center=True, bold=True)
        c.text(62, 964, 'Каналы: Telegram и почта', 32, bold=True)
        c.text(62, 1034, 'Лимиты и защита от повторов сохранены.', 26, MUTED)
        c.footer(payload['last'])
        return c.finish(), 'ФинАсист — проверка доставки инфографики. Это тест, реального инцидента нет.'

    c.text(62, 162, 'Подозрительные', 56, bold=True)
    c.text(62, 230, 'попытки входа', 56, bold=True)
    snapshot = payload.get('login_snapshot') or {}
    count = snapshot.get('count')
    c.text(62, 345, str(count) if count is not None else '≥50', 100, RED, True, width=280)
    c.text(365, 374, 'отказов входа', 34, bold=True)
    c.text(365, 428, 'окно наблюдения — до 5 минут', 24, MUTED, width=650)
    c.box((62, 513, 1018, 893), '#152238', EDGE, 24)
    c.text(91, 541, 'ОТКАЗЫ ПО МИНУТАМ ОКНА', 21, MUTED, True)
    buckets = snapshot.get('buckets') or []
    if buckets:
        maximum = max(1, max(buckets))
        for index in range(5):
            x, base = 158 + index * 190, 815
            if index < len(buckets):
                value = buckets[index]
                height = round(value / maximum * 180)
                if height:
                    c.box((x-36, base-height, x+36, base), RED if value == maximum else '#b8607a', radius=min(9, height//2))
                c.text(x, base-height-40, str(value), 26, bold=True, center=True, width=150)
            else:
                c.text(x, 773, '—', 26, MUTED, center=True)
            c.text(x, 839, f'{index+1}-я мин', 23, MUTED, center=True)
    else:
        c.circle(540, 701, 60, '#482739', '#a65069')
        c.text(540, 661, '!', 68, RED, True, center=True)
        c.text(540, 806, 'Детализация по минутам недоступна', 27, MUTED, center=True)
    c.text(62, 930, 'Максимальный срез с одного адреса', 27, bold=True)
    c.text(62, 978, f"IP {snapshot.get('source', '—')} · {stamp(snapshot.get('at', payload['last']))}", 25, MUTED, width=950)
    c.text(62, 1044, 'Проверить журнал входов', 29, bold=True)
    c.text(62, 1092, 'Эти отказы не подтверждают успешный взлом.', 23, MUTED, width=950)
    c.footer(payload['last'])
    caption = (f"ФинАсист — массовые попытки входа. {count if count is not None else 'Не менее 50'} отказов в окне до 5 минут.\n"
               f"Срез: {stamp(snapshot.get('at', payload['last']))} (Минск). IP: {snapshot.get('source', 'см. журнал')}.\n"
               'Это не подтверждение взлома. Подробности: security.jsonl. Повторы остаются в журнале.')
    return c.finish(), caption


OP_TITLES = {
    'bot_unhealthy': ('Telegram-бот', 'Работоспособность не подтверждена'),
    'bot_restarts': ('Telegram-бот', 'Серия перезапусков: ≥3 за 30 минут'),
    'backup_unknown': ('Резервная копия', 'Свежая внешняя копия не подтверждена'),
    'backup_stale': ('Резервная копия', 'Внешняя копия устарела'),
}


def operations_card(payload):
    items = payload['operations']
    if not 1 <= len(items) <= 2 or any(item['reason'] not in OP_TITLES for item in items):
        raise ValueError('Unsupported operational image payload')
    c = Card()
    c.text(62, 169, 'Требуется внимание', 56, bold=True)
    c.text(62, 252, 'Подтверждённое состояние сервисов', 28, MUTED)
    for index, item in enumerate(items):
        top = 334 + index * 332
        label, reason = OP_TITLES[item['reason']]
        c.box((62, top, 1018, top+308), '#152238', EDGE, 24)
        c.circle(132, top+62, 30, '#482739', '#a65069')
        c.text(132, top+35, '!', 43, RED, True, center=True)
        c.text(188, top+34, label, 32, bold=True)
        c.text(92, top+109, reason, 26, MUTED, width=900)
        # Only observation timestamps, never invented downtime or probe counts.
        c.line((114, top+206, 934, top+206), '#624152', 4)
        c.circle(114, top+206, 12, '#482739', RED)
        c.circle(934, top+206, 12, ORANGE)
        c.text(92, top+235, stamp(item['changed']) + ' · инцидент', 22, MUTED)
        c.text(580, top+235, stamp(item.get('last_seen', item['changed'])) + ' · проверка', 22, ORANGE, width=400)
    if len(items) == 1:
        c.text(62, 720, 'Проверить сервис и его журнал', 34, bold=True)
        c.text(62, 782, 'Кратковременные сбои не уведомляют.', 25, MUTED)
    c.text(62, 1044, 'Один инцидент — одно уведомление', 29, bold=True, width=950)
    c.text(62, 1092, 'Повторы состояния остаются в журнале.', 23, MUTED)
    c.footer(max(item.get('last_seen', item['changed']) for item in items))
    caption = 'ФинАсист — состояние сервисов\n' + '\n'.join(
        f"{OP_TITLES[item['reason']][0]}: {OP_TITLES[item['reason']][1]}. {stamp(item['changed'])} (Минск)." for item in items)
    return c.finish(), caption + '\nПроверьте серверный журнал. Повторы состояния не отправляются.'


def render_notification(payload):
    return operations_card(payload) if payload.get('operations') else security_card(payload)
