"""Readable financial PNGs and equivalent plain text, with no invented insights."""
from datetime import date
from decimal import Decimal
from io import BytesIO
import textwrap

from PIL import Image, ImageDraw
from app.services.incident_infographic import font, BG, SURFACE, EDGE, TEXT, MUTED, RED, ORANGE, CYAN

GREEN = '#7addb4'
MONTHS = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
TITLES = {'week': 'Итоги недели', 'month': 'Итоги месяца', 'year': 'Итоги года'}


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


class ReportCanvas:
    def __init__(self):
        self.image = Image.new('RGB', (1080, 6500), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.draw.rectangle((24, 24, 1056, 6476), fill=SURFACE)
        self.lines = []
        self.y = 52

    def box(self, rect, color='#152238'):
        self.draw.rounded_rectangle(rect, radius=20, fill=color, outline=EDGE, width=2)

    def text(self, x, y, value, size=26, color=TEXT, bold=False, *, right=False, width=952):
        value = ' '.join(str(value).split())
        while size > 16 and self.draw.textlength(value, font=font(size, bold)) > width:
            size -= 1
        if self.draw.textlength(value, font=font(size, bold)) > width:
            while value and self.draw.textlength(value + '…', font=font(size, bold)) > width:
                value = value[:-1]
            value += '…'
        if right:
            x -= self.draw.textlength(value, font=font(size, bold))
        self.draw.text((x, y), value, font=font(size, bold), fill=color)

    def paragraph(self, value, *, size=25, color=MUTED, bold=False, max_lines=4, x=64, width=952):
        original = ' '.join(str(value).split())
        words = original.split()
        rows, row = [], ''
        for word in words:
            # Split unbroken URLs/identifiers too; never draw beyond a card.
            for piece in textwrap.wrap(word, max(10, int(width / size * 1.6))) or ['']:
                next_row = (row + ' ' + piece).strip()
                if self.draw.textlength(next_row, font=font(size, bold)) > width and row:
                    rows.append(row); row = piece
                else:
                    row = next_row
        if row:
            rows.append(row)
        if len(rows) > max_lines:
            rows = rows[:max_lines]; rows[-1] += '…'
        for row in rows:
            self.text(x, self.y, row, size, color, bold, width=width)
            self.y += size + 9
        self.lines.append(original)

    def heading(self, value):
        self.y += 24
        self.paragraph(value, size=31, color=TEXT, bold=True, max_lines=2)
        self.y += 12

    def pair(self, label, value, *, color=TEXT, note=None):
        self.text(64, self.y, label, 26, width=640)
        self.text(1016, self.y, value, 28, color, True, right=True, width=294)
        self.lines.append(f'{label}: {value}')
        self.y += 43
        if note:
            self.paragraph(note, size=22, max_lines=2)
        self.y += 7

    def finish(self):
        self.y += 22
        self.draw.line((64, self.y, 1016, self.y), fill=EDGE, width=2)
        self.y += 22
        self.paragraph('Категории — расходы по операциям. «Пришло» и «Ушло» включают движения по долгам и валюте.', size=21)
        self.paragraph('Разница — результат периода, не остаток на счетах. Даты и время — Минск.', size=21)
        bottom = self.y + 32
        if bottom > 6400:
            raise ValueError('Financial report exceeds safe image height')
        image = self.image.crop((0, 0, 1080, bottom))
        out = BytesIO(); image.save(out, format='PNG', optimize=True)
        if len(out.getvalue()) > 8_000_000:
            raise ValueError('Financial report exceeds photo size limit')
        return out.getvalue(), '\n'.join(self.lines)


def render_report(report):
    c = ReportCanvas(); cur = report['current']; prev = report['previous']; currency = report['currency']
    title = TITLES[report['kind']]
    c.text(64, 50, 'Φ', 55, ORANGE, True); c.draw.ellipse((98, 103, 110, 115), fill=GREEN)
    c.text(130, 73, 'ФинАсист', 29, TEXT, True)
    c.text(1016, 81, 'ЛИЧНЫЙ ОТЧЁТ', 19, MUTED, right=True)
    c.y = 155; c.paragraph(title, size=49, color=TEXT, bold=True)
    c.paragraph(span(report['start'], report['end']), size=27)
    c.y += 25
    for index, (label, key, color) in enumerate([
        ('Пришло', 'cashflow_income_total', GREEN), ('Ушло', 'cashflow_expense_total', RED),
        ('Разница', 'cashflow_total', GREEN if dec(cur['cashflow_total']) >= 0 else RED),
    ]):
        x = 64 + index * 324
        c.box((x, c.y, x + 304, c.y + 130))
        c.text(x + 20, c.y + 18, label, 25, MUTED, width=264)
        c.text(x + 20, c.y + 62, money(cur[key], index == 2), 37, color, True, width=264)
        c.lines.append(f'{label}: {money(cur[key])} {currency}')
    c.y += 153
    c.paragraph(f"{cur['cashflow_events_count']} событий · {cur['operations_count']} операций · суммы в {currency}", size=24)

    if int(prev.get('cashflow_events_count') or 0) > 0:
        change = dec(cur['cashflow_expense_total']) - dec(prev['cashflow_expense_total'])
        relation = 'больше' if change >= 0 else 'меньше'
        c.heading(f'Ушло на {money(abs(change))} {relation}')
        c.paragraph(f"Сравнение: {span(prev['date_from'], prev['date_to'])}.", size=23)
        op_change = dec(cur['expense_total']) - dec(prev['expense_total'])
        c.paragraph(f'Изменение расходов по операциям: {money(op_change, True)} {currency}. Остальное изменение оттока связано с долгами и валютой.', max_lines=3)
    else:
        c.y += 14
        c.paragraph('За предыдущий период нет записей для сравнения.', size=24)

    c.heading('Как сложилась разница')
    balance = dec(cur['income_total']) - dec(cur['expense_total'])
    c.pair('Доходы минус расходы по операциям', money(balance, True), color=GREEN if balance >= 0 else RED,
           note=f"Доходы {money(cur['income_total'])} − расходы {money(cur['expense_total'])} {currency}.")
    for label, key in [('Движения по долгам', 'debt_cashflow_total'), ('Валютные операции', 'fx_cashflow_total')]:
        value = dec(cur[key])
        c.pair(label, money(value, True), color=GREEN if value > 0 else RED if value < 0 else MUTED)
    if dec(cur['fx_cashflow_total']):
        c.paragraph('Покупка валюты влияет на денежный поток, но не входит в расходы по категориям.', size=23)

    yearly = report['kind'] == 'year'
    c.heading('Результат по месяцам' if yearly else 'Ушло по дням' if report['kind'] == 'week' else 'Ушло по отрезкам месяца')
    series = report['series']; key = 'cashflow_total' if yearly else 'cashflow_expense_total'
    values = [dec(item[key]) for item in series]; maximum = max([abs(v) for v in values] + [Decimal(1)])
    top = c.y + 38; baseline = top + 130; step = 952 / max(1, len(values))
    c.draw.line((64, baseline, 1016, baseline), fill=EDGE, width=2)
    for i, (row, value) in enumerate(zip(series, values)):
        x = 64 + step * (i + .5); height = float(abs(value) / maximum) * 115
        color = GREEN if yearly and value >= 0 else RED if yearly else CYAN
        if abs(value) > 0:
            c.draw.rectangle((x-19, baseline-height if value >= 0 else baseline, x+19, baseline if value >= 0 else baseline+height), fill=color)
        label = f'{value:,.0f}'.replace(',', ' ') if yearly else money(value)
        c.text(x + step/2 - 7, baseline-height-31 if value >= 0 else baseline+height+7, label, 20, color, True, right=True, width=step-12)
        label = MONTHS[day(row['date_from']).month-1] if yearly else short(row['date_from']) if report['kind']=='week' else f"{day(row['date_from']).day}–{day(row['date_to']).day}"
        c.text(x + step/2 - 7, baseline+160 if yearly else baseline+20, label, 20, MUTED, right=True, width=step-12)
        c.lines.append(f"{span(row['date_from'], row['date_to'])}: {money(value)} {currency}")
    c.y = baseline + (205 if yearly else 70)
    if yearly:
        c.paragraph('Подписи графика округлены до целого; итоговые суммы — до копейки.', size=21)

    categories = cur.get('category_breakdown', [])
    c.heading('Крупнейшие категории расходов')
    c.paragraph(f"Всего по операциям: {money(cur['expense_total'])} {currency}. Доли ниже рассчитаны от этой суммы.", size=23)
    for i, item in enumerate(categories[:3 if report['kind']=='week' else 5]):
        amount = dec(item['total_amount']); total = dec(cur['expense_total'])
        share = float(amount / total * 100) if total else 0
        c.pair(item['category_name'] or 'Без категории', money(amount), note=f'{share:.1f}% расходов'.replace('.', ','))
        width = float(amount / dec(categories[0]['total_amount'])) * 952 if dec(categories[0]['total_amount']) else 0
        c.draw.rounded_rectangle((64, c.y-4, 64+max(3,width), c.y+2), radius=3, fill=[CYAN, ORANGE, '#9e98ed', RED, '#8bb9f3'][i])
        c.y += 14
    if not categories:
        c.paragraph('За период расходов нет.')

    if int(prev.get('cashflow_events_count') or 0):
        before = {x['category_id']: x for x in prev.get('category_breakdown', [])}
        after = {x['category_id']: x for x in categories}
        changes = []
        for key in before.keys() | after.keys():
            delta = dec(after.get(key, {}).get('total_amount')) - dec(before.get(key, {}).get('total_amount'))
            if delta:
                changes.append((delta, (after.get(key) or before[key])['category_name']))
        if changes:
            c.heading('Заметные изменения категорий')
            c.paragraph(f"К {span(prev['date_from'], prev['date_to'])}.", size=23)
            for delta, label in sorted(changes, key=lambda x: abs(x[0]), reverse=True)[:2]:
                c.pair(label or 'Без категории', money(delta, True), color=ORANGE if delta>0 else GREEN)

    top_operations = cur.get('top_operations', [])[:2]
    if top_operations:
        c.heading('Крупные траты')
        for item in top_operations:
            c.pair(short(item['operation_date']), money(item['amount']), color=RED)
            c.paragraph(item.get('report_label') or item.get('note') or 'Расход без комментария', color=TEXT, max_lines=2)
            if item.get('receipt_summary'):
                c.paragraph(f"{item['receipt_summary']} · позиций: {item['receipt_count']}", size=22, max_lines=2)
            c.y += 12

    plans = report['plans']
    c.heading('Ближайшие планы')
    c.paragraph(span(plans['date_from'], plans['date_to']), size=24)
    c.pair('Ожидается получить', money(plans['income_total']), color=GREEN)
    c.pair('Ожидается заплатить', money(plans['expense_total']), color=RED)
    if plans['unpriced_count']:
        c.paragraph(f"Нет курса для {plans['unpriced_count']} платежей. Итог требует уточнения.", color=ORANGE)
    if not plans['occurrences']:
        c.paragraph('На ближайшие 7 дней платежей в планах нет.')
    for item in plans['occurrences'][:3]:
        c.y += 13
        c.pair(f"{short(item['scheduled_date'])} · {'Получить' if item['kind']=='income' else 'Заплатить'}",
               f"{money(item['original_amount'])} {item['currency']}", color=GREEN if item['kind']=='income' else ORANGE)
        c.paragraph(item['report_label'], color=TEXT, max_lines=2)
        if item['currency'] != currency:
            c.paragraph(f"≈ {money(item['current_base_amount'])} {currency} · оценка на {short(report['generated_on'])}, не факт оплаты.", size=22)
    if len(plans['occurrences']) > 3:
        c.paragraph(f"Ещё платежей: {len(plans['occurrences'])-3}. Подробности — в разделе «Планы».", size=23)
    if plans['overdue_items']:
        c.y += 16
        item = plans['overdue_items'][0]
        c.paragraph(f"Проверить подтверждение: {item['report_label']} · {money(item['original_amount'])} {item['currency']} · {short(item['scheduled_date'])}.", color=ORANGE, max_lines=3)
        c.paragraph(f"Планов с прошедшей датой: {len(plans['overdue_items'])}. Это не подтверждение задолженности; проверьте факт оплаты.", size=22)
    uncategorized = sum(dec(x['total_amount']) for x in categories if x['category_id'] is None)
    if uncategorized:
        c.heading('Нужно уточнить категории')
        c.paragraph(f'{money(uncategorized)} {currency} расходов не распределено по категориям.', color=ORANGE)
    for supplement in report.get('supplements', []):
        data = supplement['data']
        c.heading(supplement['label'])
        c.paragraph(f"{span(data['date_from'], data['date_to'])}: пришло {money(data['cashflow_income_total'])}, ушло {money(data['cashflow_expense_total'])}, разница {money(data['cashflow_total'], True)} {currency}.")
    return c.finish()
