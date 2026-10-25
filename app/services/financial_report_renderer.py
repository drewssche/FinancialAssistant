"""Offline PNG layouts: Express weekly, Ring monthly, Pulse yearly."""
from datetime import date
from decimal import Decimal
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw
from app.services.incident_infographic import font

BG, SURFACE, EDGE = '#0e1726', '#19263b', '#2a3b53'
TEXT, MUTED = '#f0f5fe', '#a8b8cf'
GREEN, RED, ORANGE, BLUE, PURPLE = '#7addb4', '#ff8b9e', '#ffab52', '#8eaff5', '#c1a1e6'
MONTHS = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
TITLES = {'week': 'Итоги недели', 'month': 'Итоги месяца', 'year': 'Итоги года'}
REPORT_STYLES = {'week': 'Экспресс', 'month': 'Кольцо', 'year': 'Пульс'}
ICON_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'report_icons'
COLORS = [ORANGE, BLUE, PURPLE, GREEN, RED, EDGE]


def dec(value):
    return Decimal(str(value or 0))


def money(value, signed=False):
    value = dec(value)
    return ('+' if signed and value > 0 else '') + f'{value:,.2f}'.replace(',', ' ').replace('.', ',')


def day(value):
    return date.fromisoformat(str(value)[:10])


def span(start, end):
    return f'{day(start):%d.%m.%Y} — {day(end):%d.%m.%Y}'


def short(value):
    return f'{day(value):%d.%m}'


def category_icon(label):
    """Known meanings get a pictogram; unfamiliar categories keep a neutral tag."""
    label = str(label).casefold()
    for terms, name in [
        (('баня', 'сауна'), 'bath'), (('ставки',), 'dice-5'),
        (('праздник', 'костюм'), 'party-popper'), (('кофе',), 'coffee'),
        (('подписк',), 'repeat-2'), (('одежд', 'обувь'), 'shirt'),
        (('сигарет', 'табак'), 'cigarette'), (('сыр', 'молоч'), 'milk'),
        (('перевод', 'валют'), 'arrow-left-right'), (('аптек', 'лекар'), 'pill'),
        (('такси', 'транспорт', 'авто'), 'car'), (('ремонт', 'сервис'), 'wrench'),
        (('жиль', 'коммун', 'недвиж'), 'house'), (('путешеств', 'отдых'), 'plane'),
        (('еда', 'продукт', 'ресторан'), 'utensils'), (('долг',), 'handshake'),
    ]:
        if any(term in label for term in terms):
            return name
    return 'tag'


@lru_cache(maxsize=128)
def icon_image(name, size, color):
    with Image.open(ICON_DIR / f'{name}.png') as source:
        alpha = source.getchannel('A').resize((size, size), Image.Resampling.LANCZOS)
    image = Image.new('RGBA', (size, size), color)
    image.putalpha(alpha)
    return image


def top_categories(report, count):
    rows = report['current'].get('category_breakdown', [])
    return sorted((r for r in rows if dec(r['total_amount']) > 0),
                  key=lambda r: dec(r['total_amount']), reverse=True)[:count]


class ReportCanvas:
    def __init__(self, report):
        self.image = Image.new('RGB', (1080, 5000), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.lines = [TITLES[report['kind']], span(report['start'], report['end']), report['currency']]
        self.y = 200
        self.text(62, 40, 'Φ', 69, ORANGE, True)
        self.text(143, 67, 'ФинАсист', 34, bold=True, width=300)
        self.text(1018, 57, span(report['start'], report['end']), 27, MUTED, right=True, width=570)
        self.text(1018, 101, TITLES[report['kind']]+' · '+report['currency'], 27, MUTED, right=True, width=570)

    def text(self, x, y, value, size=30, color=TEXT, bold=False, *, right=False, center=False, width=956):
        value = ' '.join(str(value).split())
        while size > 22 and self.draw.textlength(value, font=font(size, bold)) > width:
            size -= 1
        if self.draw.textlength(value, font=font(size, bold)) > width:
            while value and self.draw.textlength(value+'…', font=font(size, bold)) > width:
                value = value[:-1]
            value += '…'
        length = self.draw.textlength(value, font=font(size, bold))
        x -= length if right else length/2 if center else 0
        self.draw.text((x, y), value, font=font(size, bold), fill=color)

    def paragraph(self, value, *, x=62, width=956, size=27, color=MUTED, max_lines=2, bold=False):
        original = ' '.join(str(value).split())
        rows, row = [], ''
        for word in original.split():
            for piece in textwrap.wrap(word, max(10, int(width/size*1.6))) or ['']:
                candidate = (row+' '+piece).strip()
                if row and self.draw.textlength(candidate, font=font(size, bold)) > width:
                    rows.append(row); row = piece
                else:
                    row = candidate
        if row:
            rows.append(row)
        visible = rows[:max_lines]
        if len(rows) > max_lines:
            visible[-1] += '…'
        for row in visible:
            self.text(x, self.y, row, size, color, bold, width=width)
            self.y += size+10
        self.lines.append(original)

    def box(self, rect, color=SURFACE, radius=36):
        self.draw.rounded_rectangle(rect, radius=radius, fill=color)

    def icon(self, name, x, y, *, color=ORANGE, size=50, tile=False):
        if tile:
            self.box((x-14, y-14, x+size+14, y+size+14), radius=24)
        image = icon_image(name, size, color)
        self.image.paste(image, (int(x), int(y)), image)

    def heading(self, label, right=''):
        self.y += 30
        self.text(62, self.y, label, 29, MUTED, width=730)
        self.text(1018, self.y, right, 26, MUTED, right=True, width=215)
        self.y += 65

    def hero(self, current, label):
        value = dec(current['cashflow_total'])
        self.icon('equal', 80, self.y+47, color=GREEN if value >= 0 else RED, size=60, tile=True)
        self.text(187, self.y, label, 28, MUTED)
        self.text(187, self.y+47, money(value, True), 88, GREEN if value >= 0 else RED, True, width=830)
        self.lines.append('Разница: '+money(value, True))
        self.y += 185

    def totals(self, current, *, bars=False):
        maximum = max(dec(current['cashflow_income_total']), dec(current['cashflow_expense_total']), Decimal(1))
        for i, (label, key, color, icon) in enumerate([
            ('Пришло', 'cashflow_income_total', GREEN, 'arrow-down-left'),
            ('Ушло', 'cashflow_expense_total', RED, 'arrow-up-right'),
        ]):
            value = dec(current[key])
            if bars:
                y = self.y+i*128
                self.icon(icon, 66, y+6, color=color, size=42)
                self.text(144, y+3, label, 36)
                self.text(1018, y, money(value), 48, TEXT, True, right=True, width=560)
                self.box((144, y+78, 1018, y+94), radius=8)
                if value > 0:
                    self.box((144, y+78, 144+float(value/maximum)*874, y+94), color, radius=8)
            else:
                x = 62+i*490
                self.box((x, self.y, x+466, self.y+180))
                self.icon(icon, x+28, self.y+30, color=MUTED, size=34)
                self.text(x+78, self.y+28, label, 29, MUTED, width=350)
                self.text(x+30, self.y+88, money(value), 55, color, True, width=406)
            self.lines.append(label+': '+money(value))
        self.y += 256 if bars else 200

    def net_strip(self, value):
        self.box((62, self.y, 1018, self.y+124))
        self.icon('equal', 90, self.y+40, color=GREEN if dec(value) >= 0 else RED, size=40)
        self.text(162, self.y+40, 'Разница', 32, width=250)
        self.text(988, self.y+28, money(value, True), 59, GREEN if dec(value) >= 0 else RED, True, right=True, width=560)
        self.lines.append('Разница: '+money(value, True))
        self.y += 150

    def finish(self):
        self.y += 22
        self.paragraph('Пришло / ушло — с долгами и валютой.', size=25)
        self.paragraph('Разница — итог периода, не остаток на счетах.', size=25)
        bottom = self.y+55
        if bottom > 4900:
            raise ValueError('Financial report exceeds safe image height')
        image = self.image.crop((0, 0, 1080, bottom))
        ImageDraw.Draw(image).rounded_rectangle((1, 1, 1078, bottom-2), radius=55, outline=EDGE, width=3)
        out = BytesIO(); image.save(out, format='PNG', optimize=True)
        if len(out.getvalue()) > 8_000_000:
            raise ValueError('Financial report exceeds photo size limit')
        return out.getvalue(), '\n'.join(self.lines)


def draw_top_categories(c, report, *, tiles=False):
    rows = top_categories(report, 3)
    c.heading('Топ расходов', f"{report['current']['operations_count']} операций" if tiles else report['currency'])
    if not rows:
        c.paragraph('За период расходов нет.')
        return
    maximum = dec(rows[0]['total_amount'])
    for i, row in enumerate(rows):
        name = row['category_name'] or 'Без категории'
        value = dec(row['total_amount'])
        if tiles:
            x = 62+i*326
            c.box((x, c.y, x+304, c.y+260))
            c.icon(category_icon(name), x+125, c.y+33, color=COLORS[i], size=54)
            c.text(x+152, c.y+111, money(value), 43, TEXT, True, center=True, width=278)
            saved = c.y; c.y += 178
            c.paragraph(name, x=x+18, width=268, size=25, max_lines=2)
            c.y = saved
        else:
            y = c.y+i*115
            c.icon(category_icon(name), 78, y+9, size=45, tile=True)
            c.text(165, y, name, 34, width=620)
            c.text(1018, y+5, money(value), 43, TEXT, True, right=True, width=215)
            c.box((165, y+66, 790, y+79), radius=6)
            c.box((165, y+66, 165+float(value/maximum)*625, y+79), ORANGE, radius=6)
        c.lines.append(name+': '+money(value))
    c.y += 280 if tiles else len(rows)*115


def draw_express(c, report):
    current, previous = report['current'], report['previous']
    c.hero(current, 'Разница за неделю')
    c.totals(current, bars=True)
    draw_top_categories(c, report)
    if int(previous.get('cashflow_events_count') or 0):
        delta = dec(current['cashflow_expense_total'])-dec(previous['cashflow_expense_total'])
        c.box((62, c.y, 1018, c.y+104))
        c.icon('trending-up' if delta >= 0 else 'trending-down', 86, c.y+32, color=RED if delta > 0 else GREEN, size=44)
        c.text(160, c.y+35, 'Ушло к прошлой неделе', 28, width=560)
        c.text(988, c.y+28, money(delta, True), 41, TEXT, True, right=True, width=260)
        c.lines.append('Ушло к прошлой неделе: '+money(delta, True))
        c.y += 128


def draw_ring(c, report):
    c.totals(report['current'])
    total = dec(report['current']['expense_total'])
    rows = [(r['category_name'] or 'Без категории', dec(r['total_amount'])) for r in top_categories(report, 5)]
    rest = total-sum(value for _, value in rows)
    if rest > 0:
        rows.append(('Остальные категории', rest))
    top = c.y+30
    c.draw.ellipse((295, top, 785, top+490), fill=EDGE)
    start = -90
    for i, (_, value) in enumerate(rows):
        end = start+float(value/total)*360 if total > 0 else start
        c.draw.pieslice((295, top, 785, top+490), start, end, fill=COLORS[i])
        start = end
    c.draw.ellipse((352, top+57, 728, top+433), fill=BG)
    c.text(540, top+136, 'Расходы', 31, MUTED, center=True, width=350)
    c.text(540, top+192, money(total), 60, TEXT, True, center=True, width=350)
    c.text(540, top+276, 'по операциям · '+report['currency'], 26, MUTED, center=True, width=350)
    c.lines.append('Расходы по операциям: '+money(total))
    c.y = top+540
    for i, (name, value) in enumerate(rows):
        c.icon('ellipsis' if name == 'Остальные категории' else category_icon(name), 66, c.y, color=COLORS[i] if i<5 else MUTED, size=40)
        c.text(132, c.y, name, 31, width=610)
        c.text(1018, c.y, money(value), 35, TEXT, True, right=True, width=250)
        c.lines.append(name+': '+money(value)); c.y += 73
    if not rows:
        c.paragraph('За период расходов нет.')
    c.y += 18
    c.net_strip(report['current']['cashflow_total'])


def draw_pulse(c, report):
    c.hero(report['current'], 'Разница за период')
    c.totals(report['current'])
    c.heading('Разница по месяцам', report['currency'])
    series = report['series']
    if series:
        values = [dec(row['cashflow_total']) for row in series]
        maximum = max([abs(v) for v in values]+[Decimal(1)])
        step = 956/len(series); baseline = c.y+155
        c.draw.line((62, baseline, 1018, baseline), fill=EDGE, width=2)
        for i, (row, value) in enumerate(zip(series, values)):
            x = 62+step*(i+.5); height = float(abs(value)/maximum)*145
            if value:
                rect = (x-step*.34, baseline-height if value>0 else baseline, x+step*.34, baseline if value>0 else baseline+height)
                c.box(rect, GREEN if value>0 else RED, radius=min(7, height/2))
            label = MONTHS[day(row['date_from']).month-1]
            c.text(x, baseline+170, label, 25, MUTED, center=True, width=step-6)
            c.lines.append(label+': '+money(value, True))
        c.y = baseline+235
        # Actual extrema, not hardcoded January/October from the approved preview.
        for i, index in enumerate(dict.fromkeys((values.index(min(values)), values.index(max(values))))):
            value = values[index]; label = MONTHS[day(series[index]['date_from']).month-1]
            c.text(62 if i==0 else 1018, c.y, label+' '+money(value, True), 29, GREEN if value>=0 else RED,
                   right=i>0, width=465)
        c.y += 50
    draw_top_categories(c, report, tiles=True)


def draw_plans(c, report):
    plans = report['plans']
    c.y += 22
    c.draw.line((62, c.y, 1018, c.y), fill=EDGE, width=2)
    c.y += 45
    items = sorted(plans.get('occurrences', []), key=lambda item: day(item['scheduled_date']))
    if items:
        item = items[0]
        c.icon('calendar-clock', 78, c.y+8, color=BLUE, tile=True)
        c.text(1018, c.y+8, money(item['original_amount'])+' '+item['currency'], 38, TEXT, True, right=True, width=280)
        c.paragraph(item['report_label'], x=166, width=550, size=32, color=TEXT, bold=True)
        direction = 'получить' if item['kind']=='income' else 'заплатить'
        c.paragraph(short(item['scheduled_date'])+' · '+direction, x=166, width=550, size=27)
        if len(items)>1:
            c.paragraph(f'Ещё в ближайшие 7 дней: {len(items)-1}', x=166, width=850, size=25)
        c.lines.append(f"{short(item['scheduled_date'])}: {direction} {money(item['original_amount'])} {item['currency']}")
    else:
        c.icon('calendar-clock', 78, c.y+8, color=BLUE, tile=True)
        c.paragraph('На ближайшие 7 дней платежей в планах нет.', x=166, width=850, size=28)
    if plans.get('unpriced_count'):
        c.paragraph('Для части планов нет курса.', color=ORANGE, size=25)
    overdue = plans.get('overdue_items', [])
    if overdue:
        c.y += 15
        c.paragraph(f'Проверить планы: {len(overdue)} с прошедшей датой', color=ORANGE, size=25)
        # Keep full detail accessible without expanding the compact graphic.
        for item in overdue:
            c.lines.append(f"Проверить {short(item['scheduled_date'])}: {item['report_label']} · {money(item['original_amount'])} {item['currency']}")
    for extra in report.get('supplements', []):
        c.y += 18
        c.box((62, c.y, 1018, c.y+153))
        c.text(88, c.y+18, extra['label'], 29, MUTED, width=550)
        data = extra['data']
        c.text(988, c.y+16, money(data['cashflow_total'], True), 37, GREEN if dec(data['cashflow_total'])>=0 else RED,
               True, right=True, width=370)
        c.text(88, c.y+77, 'Пришло '+money(data['cashflow_income_total']), 28, width=430)
        c.text(988, c.y+77, 'Ушло '+money(data['cashflow_expense_total']), 28, right=True, width=430)
        c.lines.append(extra['label']+': пришло '+money(data['cashflow_income_total'])+', ушло '+money(data['cashflow_expense_total'])+', разница '+money(data['cashflow_total'], True))
        c.y += 168


def render_report(report):
    """Only presentation varies; dates, snapshot, recipients and ledger stay upstream."""
    renderers = {'week': draw_express, 'month': draw_ring, 'year': draw_pulse}
    renderer = renderers[report['kind']]
    c = ReportCanvas(report)
    renderer(c, report)
    draw_plans(c, report)
    return c.finish()
