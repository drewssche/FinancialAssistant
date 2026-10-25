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
    """Visual hierarchy: KPI, comparisons, trend, composition, changes, timeline."""
    c=ReportCanvas(); cur=report['current']; prev=report['previous']; currency=report['currency']
    colors=[CYAN,ORANGE,'#a99ded','#ee8da8','#84ace6','#4e627d']
    c.text(64,50,'Φ',55,ORANGE,True);c.draw.ellipse((98,103,110,115),fill=GREEN)
    c.text(130,73,'ФинАсист',29,TEXT,True);c.text(1016,81,'ЛИЧНЫЙ ОТЧЁТ',19,MUTED,right=True)
    c.y=151;c.paragraph(TITLES[report['kind']],size=48,color=TEXT,bold=True)
    c.paragraph(span(report['start'],report['end']),size=27);c.y+=20
    for i,(label,key,color) in enumerate([('Пришло','cashflow_income_total',GREEN),('Ушло','cashflow_expense_total',RED),('Разница','cashflow_total',GREEN if dec(cur['cashflow_total'])>=0 else RED)]):
        x=64+i*324;c.box((x,c.y,x+304,c.y+140))
        c.text(x+20,c.y+18,label,25,MUTED,width=264)
        c.text(x+20,c.y+65,money(cur[key],i==2),38,color,True,width=264)
        c.lines.append(f'{label}: {money(cur[key])} {currency}')
    c.y+=160;c.paragraph(f"{currency} · {cur['cashflow_events_count']} событий · {cur['operations_count']} операций",size=23)

    if int(prev.get('cashflow_events_count') or 0):
        c.heading('Ушло: сравнение периодов')
        maximum=max(dec(cur['cashflow_expense_total']),dec(prev['cashflow_expense_total']),Decimal(1))
        for label,data,color in [('Предыдущий',prev,'#526983'),('Текущий',cur,CYAN)]:
            value=dec(data['cashflow_expense_total'])
            c.text(64,c.y,f"{label} · {span(data['date_from'], data['date_to'])}",23,MUTED,width=690)
            c.text(1016,c.y,money(value),28,TEXT,True,right=True)
            c.draw.rounded_rectangle((64,c.y+43,1016,c.y+66),radius=10,fill='#1d2a3e')
            if value>0:c.draw.rounded_rectangle((64,c.y+43,64+max(3,float(value/maximum)*952),c.y+66),radius=10,fill=color)
            c.lines.append(f"{label}: {span(data['date_from'],data['date_to'])}, ушло {money(value)} {currency}");c.y+=86
        delta=dec(cur['cashflow_expense_total'])-dec(prev['cashflow_expense_total'])
        c.text(64,c.y,'Изменение оттока',24,MUTED);c.text(1016,c.y,money(delta,True)+' '+currency,31,ORANGE if delta>0 else GREEN,True,right=True)
        c.lines.append(f'Изменение оттока: {money(delta,True)} {currency}');c.y+=45

    yearly=report['kind']=='year'
    c.heading('Результат по месяцам' if yearly else 'Ушло по дням' if report['kind']=='week' else 'Динамика расходов и других списаний')
    series=report['series'];key='cashflow_total' if yearly else 'cashflow_expense_total'
    values=[dec(row[key]) for row in series];maximum=max([abs(v) for v in values]+[Decimal(1)])
    top=c.y+32;baseline=top+170;step=952/max(1,len(values))
    c.draw.line((64,baseline,1016,baseline),fill=EDGE,width=2)
    for i,(row,v) in enumerate(zip(series,values)):
        x=64+step*(i+.5);height=float(abs(v)/maximum)*148;col=GREEN if yearly and v>=0 else RED if yearly else CYAN
        if v:c.draw.rounded_rectangle((x-22,baseline-height if v>=0 else baseline,x+22,baseline if v>=0 else baseline+height),radius=min(7,height/2),fill=col)
        value=f'{v:,.0f}'.replace(',',' ') if yearly else money(v)
        size=20 if yearly else 23;length=c.draw.textlength(value,font=font(size,True))
        c.text(x-length/2,baseline-height-35 if v>=0 else baseline+height+9,value,size,col,True,width=step-8)
        label=MONTHS[day(row['date_from']).month-1] if yearly else short(row['date_from']) if report['kind']=='week' else f"{day(row['date_from']).day}–{day(row['date_to']).day}"
        length=c.draw.textlength(label,font=font(20));c.text(x-length/2,baseline+197 if yearly else baseline+22,label,20,MUTED,width=step-8)
        c.lines.append(f"{span(row['date_from'],row['date_to'])}: {money(v)} {currency}")
    c.y=baseline+(235 if yearly else 66)
    if yearly:c.paragraph('На графике — округлённые суммы в '+currency,size=20)

    c.heading('Движение денег')
    maximum=max(dec(cur['cashflow_income_total']),dec(cur['cashflow_expense_total']),Decimal(1))
    for label,total_key,operations_key,col in [('Пришло','cashflow_income_total','income_total',GREEN),('Ушло','cashflow_expense_total','expense_total',RED)]:
        total=dec(cur[total_key]);ops=dec(cur[operations_key]);other=total-ops
        c.text(64,c.y,label,24,MUTED);c.text(1016,c.y,money(total),28,col,True,right=True)
        left=64;c.draw.rounded_rectangle((64,c.y+40,1016,c.y+72),radius=8,fill='#1d2a3e')
        for value,color in [(ops,col),(other,ORANGE)]:
            width=max(0,float(value/maximum)*952)
            if width:c.draw.rectangle((left,c.y+40,left+width,c.y+72),fill=color)
            left+=width
        c.text(64,c.y+88,'Операции '+money(ops),21,col)
        c.text(1016,c.y+88,'Долги / валюта '+money(other),21,ORANGE,right=True)
        c.lines.append(f'{label}: операции {money(ops)}, долги / валюта {money(other)} {currency}');c.y+=132
    # Small signed component cards explain the net without paragraphs or duplicate KPIs.
    parts=[('Операции',dec(cur['income_total'])-dec(cur['expense_total'])),('Долги',dec(cur['debt_cashflow_total'])),('Валюта',dec(cur['fx_cashflow_total']))]
    for i,(label,value) in enumerate(parts):
        x=64+i*324;c.box((x,c.y,x+304,c.y+96));c.text(x+16,c.y+12,label+' · итог',21,MUTED,width=272)
        c.text(x+16,c.y+45,money(value,True),30,GREEN if value>0 else RED if value<0 else MUTED,True,width=272)
        c.lines.append(f'{label} · итог: {money(value,True)} {currency}')
    c.y+=110

    categories=cur.get('category_breakdown',[])
    c.heading('Структура расходов')
    c.paragraph('По операциям · '+money(cur['expense_total'])+' '+currency,size=24)
    if categories and dec(cur['expense_total'])>0:
        rows=[(x['category_name'] or 'Без категории',dec(x['total_amount'])) for x in categories[:5]]
        rest=sum(dec(x['total_amount']) for x in categories[5:])
        if rest:rows.append(('Остальные категории',rest))
        cy=c.y+18;start=-90
        for i,(label,value) in enumerate(rows):
            end=start+float(value/dec(cur['expense_total']))*360
            c.draw.pieslice((64,cy,444,cy+380),start,end,fill=colors[i]);start=end
        c.draw.ellipse((140,cy+76,368,cy+304),fill=SURFACE)
        total=money(cur['expense_total']);length=c.draw.textlength(total,font=font(31,True))
        c.text(254-length/2,cy+154,total,31,TEXT,True,width=220);c.text(231,cy+201,currency,23,MUTED)
        for i,(label,v) in enumerate(rows):
            y=cy+i*65;c.draw.ellipse((482,y+10,496,y+24),fill=colors[i])
            c.text(513,y,label,24,TEXT,width=503)
            share=float(v/dec(cur['expense_total']))*100
            c.text(513,y+31,f'{share:.1f}%'.replace('.',','),22,MUTED)
            c.text(1016,y+31,money(v),25,TEXT,True,right=True,width=330)
            c.lines.append(f'{label}: {money(v)} {currency} ({share:.1f}%)')
        c.y=cy+max(396,len(rows)*65)+15
    else:c.paragraph('За период расходов нет.')

    if int(prev.get('cashflow_events_count') or 0):
        before={x['category_id']:x for x in prev.get('category_breakdown',[])};after={x['category_id']:x for x in categories}
        changes=[]
        for key in before.keys()|after.keys():
            v=dec(after.get(key,{}).get('total_amount'));old=dec(before.get(key,{}).get('total_amount'))
            if v!=old:changes.append((v-old,(after.get(key) or before[key])['category_name'] or 'Без категории',old,v))
        if changes:
            c.heading('Что изменилось сильнее всего')
            for i,(delta,label,old,v) in enumerate(sorted(changes,key=lambda x:abs(x[0]),reverse=True)[:2]):
                x=64+i*486;y=c.y;c.box((x,y,x+466,y+195));col=ORANGE if delta>0 else GREEN
                c.text(x+20,y+16,label,24,TEXT,True,width=426);c.text(x+20,y+55,money(delta,True),36,col,True,width=426)
                mx=max(old,v,Decimal(1))
                for yy,value,color in [(y+112,old,'#526983'),(y+131,v,col)]:
                    c.draw.rounded_rectangle((x+20,yy,x+20+max(3,float(value/mx)*426),yy+10),radius=4,fill=color)
                c.text(x+20,y+157,money(old)+' → '+money(v),23,MUTED,width=426)
                c.lines.append(f'{label}: {money(old)} → {money(v)}, изменение {money(delta,True)} {currency}')
            c.y+=212

    operations=cur.get('top_operations',[])[:2]
    if operations:
        c.heading('Крупные траты')
        top=c.y;bottom=top
        for i,item in enumerate(operations):
            x=64+i*486;y=top;c.box((x,y,x+466,y+213))
            c.text(x+20,y+15,short(item['operation_date']),23,MUTED)
            c.text(x+446,y+15,money(item['amount']),31,RED,True,right=True,width=300)
            c.y=y+69
            c.paragraph(item.get('report_label') or item.get('note') or 'Расход без комментария',size=24,color=TEXT,max_lines=2,x=x+20,width=426)
            if item.get('receipt_summary'):
                c.paragraph(item['receipt_summary'],size=20,max_lines=2,x=x+20,width=426)
            c.lines.append(f"{short(item['operation_date'])}: {money(item['amount'])} {currency}")
            bottom=max(bottom,y+230)
        c.y=bottom

    plans=report['plans'];c.heading('Планы · '+short(plans['date_from'])+' — '+short(plans['date_to']))
    for i,(label,key,col) in enumerate([('Получить','income_total',GREEN),('Заплатить','expense_total',RED)]):
        x=64+i*486;c.box((x,c.y,x+466,c.y+100));c.text(x+20,c.y+12,label,23,MUTED)
        c.text(x+20,c.y+47,money(plans[key])+' '+currency,32,col,True,width=426)
        c.lines.append(f'{label} по планам: {money(plans[key])} {currency}')
    c.y+=125
    for item in plans['occurrences'][:3]:
        y=c.y;c.draw.ellipse((65,y+8,80,y+23),fill=GREEN if item['kind']=='income' else ORANGE)
        c.draw.line((72,y+25,72,y+103),fill=EDGE,width=2)
        c.text(99,y,short(item['scheduled_date']),25,MUTED)
        c.text(1016,y,money(item['original_amount'])+' '+item['currency'],30,GREEN if item['kind']=='income' else ORANGE,True,right=True,width=650)
        c.lines.append(f"{short(item['scheduled_date'])}: {money(item['original_amount'])} {item['currency']}")
        c.y+=43;c.paragraph(item['report_label'],size=27,color=TEXT,max_lines=2,x=99,width=917)
        if item['currency']!=currency:c.paragraph('≈ '+money(item['current_base_amount'])+' '+currency+' · прогноз',size=21,x=99,width=917)
        c.y+=19
    if not plans['occurrences']:c.paragraph('На ближайшие 7 дней платежей в планах нет.')
    if len(plans['occurrences'])>3:c.paragraph(f"Ещё платежей: {len(plans['occurrences'])-3} · подробнее в разделе «Планы»",size=23)
    if plans['unpriced_count']:c.paragraph('Итог неполный: для части платежей нет курса.',color=ORANGE,size=23)
    if plans['overdue_items']:
        item=plans['overdue_items'][0];c.y+=12
        c.paragraph(f"Проверить план · {short(item['scheduled_date'])} · {money(item['original_amount'])} {item['currency']}",color=ORANGE,bold=True,size=25)
        c.paragraph(item['report_label'],color=ORANGE,size=24,max_lines=2)
        c.paragraph(f"Неподтверждённых планов с прошедшей датой: {len(plans['overdue_items'])}",size=21)
    uncategorized=sum(dec(x['total_amount']) for x in categories if x['category_id'] is None)
    if uncategorized:c.paragraph(f'Без категории: {money(uncategorized)} {currency}',color=ORANGE)
    for extra in report.get('supplements',[]):
        data=extra['data'];c.heading(extra['label'])
        c.pair('Пришло / ушло',money(data['cashflow_income_total'])+' / '+money(data['cashflow_expense_total']))
        c.pair('Разница',money(data['cashflow_total'],True))
    return c.finish()
