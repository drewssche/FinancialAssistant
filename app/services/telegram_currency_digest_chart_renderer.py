from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Literal, Sequence

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


__all__ = [
    "CurrencyDigestChartPanel",
    "CurrencyDigestChartPoint",
    "CurrencyDigestChartSeries",
    "TelegramCurrencyDigestChartPayload",
    "TelegramCurrencyDigestChartRenderer",
]


CurrencyDigestChartSeriesKind = Literal["nbrb", "bank_buy", "bank_sell"]


@dataclass(frozen=True, slots=True)
class CurrencyDigestChartPoint:
    day: date
    value: Decimal | None
    source_label: str | None = None


@dataclass(frozen=True, slots=True)
class CurrencyDigestChartSeries:
    kind: CurrencyDigestChartSeriesKind
    label: str
    points: Sequence[CurrencyDigestChartPoint]


@dataclass(frozen=True, slots=True)
class CurrencyDigestChartPanel:
    currency: str
    display_label: str
    series: Sequence[CurrencyDigestChartSeries]
    position_summary: str | None = None


@dataclass(frozen=True, slots=True)
class TelegramCurrencyDigestChartPayload:
    as_of: date
    panels: Sequence[CurrencyDigestChartPanel]
    base_currency: str = "BYN"
    total_current_value: Decimal | None = None
    total_result_value: Decimal | None = None


@dataclass(frozen=True, slots=True)
class _SeriesStyle:
    color: str
    dashed: bool = False


class TelegramCurrencyDigestChartRenderer:
    """Render a Telegram-ready seven-day currency infographic as an in-memory PNG."""

    IMAGE_SIZE = (1080, 1350)
    MAX_OUTPUT_BYTES = 5_000_000
    MAX_PANELS = 4
    _BACKGROUND = "#07111F"
    _CARD = "#101C2F"
    _CARD_BORDER = "#263852"
    _TEXT = "#F1F5F9"
    _MUTED = "#91A4BF"
    _GRID = "#24344B"
    _POSITIVE = "#58D6A2"
    _NEGATIVE = "#FB7185"
    _SERIES_STYLES: dict[CurrencyDigestChartSeriesKind, _SeriesStyle] = {
        "nbrb": _SeriesStyle(color="#A7B7D3", dashed=True),
        "bank_buy": _SeriesStyle(color="#5EEAD4"),
        "bank_sell": _SeriesStyle(color="#FB923C"),
    }
    _FONT_PAIRS = (
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        ("/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/SFNS.ttf"),
        (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    )

    def __init__(self, font_path: str | Path | None = None):
        regular_path, bold_path = self._resolve_font_paths(font_path)
        self._fonts = {
            "title": self._load_font(bold_path, 44, bold=True),
            "subtitle": self._load_font(regular_path, 23),
            "summary_label": self._load_font(regular_path, 18),
            "summary_value": self._load_font(bold_path, 30, bold=True),
            "panel_title": self._load_font(bold_path, 28, bold=True),
            "metric_label": self._load_font(regular_path, 16),
            "metric_value": self._load_font(bold_path, 21, bold=True),
            "small": self._load_font(regular_path, 14),
            "small_bold": self._load_font(bold_path, 14, bold=True),
            "empty": self._load_font(regular_path, 25),
        }

    def render(self, payload: TelegramCurrencyDigestChartPayload) -> bytes:
        self._validate_payload(payload)
        canvas = Image.new("RGB", self.IMAGE_SIZE, self._BACKGROUND)
        draw = ImageDraw.Draw(canvas)
        period_start = payload.as_of - timedelta(days=6)

        self._draw_header(draw, payload=payload, period_start=period_start)
        self._draw_summary(draw, payload=payload)
        self._draw_panels(draw, payload=payload, period_start=period_start)
        self._draw_footer(draw, payload=payload, period_start=period_start)

        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Title", "Курсы валют за 7 дней")
        metadata.add_text("Period", f"{period_start.isoformat()}..{payload.as_of.isoformat()}")
        metadata.add_text("MissingData", "Values are not interpolated")
        output = BytesIO()
        canvas.save(output, format="PNG", optimize=True, compress_level=9, pnginfo=metadata)
        content = output.getvalue()
        if len(content) > self.MAX_OUTPUT_BYTES:
            raise RuntimeError("Currency digest chart unexpectedly exceeds the safe Telegram photo size")
        return content

    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        payload: TelegramCurrencyDigestChartPayload,
        period_start: date,
    ) -> None:
        draw.text((56, 46), "Курсы валют за 7 дней", font=self._fonts["title"], fill=self._TEXT)
        draw.text(
            (56, 106),
            "НБРБ и лучшие курсы выбранных банков",
            font=self._fonts["subtitle"],
            fill=self._MUTED,
        )
        period = f"{period_start:%d.%m} — {payload.as_of:%d.%m.%Y}"
        period_width = self._text_width(draw, period, self._fonts["small_bold"])
        badge_box = (994 - period_width - 32, 58, 1024, 104)
        draw.rounded_rectangle(badge_box, radius=18, fill="#17263D", outline="#314865", width=2)
        draw.text(
            (badge_box[0] + 16, badge_box[1] + 13),
            period,
            font=self._fonts["small_bold"],
            fill="#C8D6EA",
        )

    def _draw_summary(self, draw: ImageDraw.ImageDraw, *, payload: TelegramCurrencyDigestChartPayload) -> None:
        draw.rounded_rectangle(
            (56, 158, 1024, 274),
            radius=24,
            fill=self._CARD,
            outline=self._CARD_BORDER,
            width=2,
        )
        self._draw_summary_metric(
            draw,
            x=84,
            label="Текущая оценка портфеля",
            value=payload.total_current_value,
            suffix=payload.base_currency,
            color=self._TEXT,
        )
        draw.line((540, 181, 540, 250), fill=self._CARD_BORDER, width=2)
        result = self._decimal(payload.total_result_value)
        result_color = self._POSITIVE if result is not None and result >= 0 else self._NEGATIVE
        self._draw_summary_metric(
            draw,
            x=574,
            label="Итоговый результат",
            value=result,
            suffix=payload.base_currency,
            color=result_color,
            signed=True,
        )

    def _draw_summary_metric(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        x: int,
        label: str,
        value: Decimal | None,
        suffix: str,
        color: str,
        signed: bool = False,
    ) -> None:
        draw.text((x, 181), label, font=self._fonts["summary_label"], fill=self._MUTED)
        numeric = self._decimal(value)
        if numeric is None:
            value_text = "Нет данных"
            color = self._MUTED
        else:
            value_text = self._format_decimal(numeric, places=2, signed=signed) + f" {suffix}"
        draw.text((x, 216), value_text, font=self._fonts["summary_value"], fill=color)

    def _draw_panels(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        payload: TelegramCurrencyDigestChartPayload,
        period_start: date,
    ) -> None:
        panels = list(payload.panels)
        if not panels:
            self._draw_empty_state(draw)
            return
        available_height = 916
        gap = 18
        panel_height = min(292, int((available_height - gap * (len(panels) - 1)) / len(panels)))
        top = 296
        for panel in panels:
            self._draw_panel(
                draw,
                panel=panel,
                period_start=period_start,
                period_end=payload.as_of,
                box=(56, top, 1024, top + panel_height),
            )
            top += panel_height + gap

    def _draw_empty_state(self, draw: ImageDraw.ImageDraw) -> None:
        box = (56, 296, 1024, 596)
        draw.rounded_rectangle(box, radius=24, fill=self._CARD, outline=self._CARD_BORDER, width=2)
        text = "За выбранный период данных о курсах пока нет"
        width = self._text_width(draw, text, self._fonts["empty"])
        draw.text(((1080 - width) / 2, 418), text, font=self._fonts["empty"], fill=self._MUTED)

    def _draw_panel(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        panel: CurrencyDigestChartPanel,
        period_start: date,
        period_end: date,
        box: tuple[int, int, int, int],
    ) -> None:
        left, top, right, bottom = box
        draw.rounded_rectangle(box, radius=24, fill=self._CARD, outline=self._CARD_BORDER, width=2)
        draw.text((left + 26, top + 18), panel.display_label, font=self._fonts["panel_title"], fill=self._TEXT)
        if panel.position_summary:
            available = right - (left + 250) - 26
            summary = self._ellipsize(draw, panel.position_summary, self._fonts["small"], available)
            summary_width = self._text_width(draw, summary, self._fonts["small"])
            draw.text(
                (right - 26 - summary_width, top + 28),
                summary,
                font=self._fonts["small"],
                fill=self._MUTED,
            )

        series_by_kind = {series.kind: series for series in panel.series}
        metric_top = top + 63
        metric_left = left + 26
        metric_width = int((right - left - 52) / 3)
        for index, kind in enumerate(("nbrb", "bank_buy", "bank_sell")):
            series = series_by_kind.get(kind)
            self._draw_series_metric(
                draw,
                series=series,
                kind=kind,
                x=metric_left + index * metric_width,
                y=metric_top,
                width=metric_width - 12,
                period_start=period_start,
                period_end=period_end,
            )

        chart_top = top + 136
        chart_bottom = bottom - 34
        if chart_bottom - chart_top >= 38:
            self._draw_chart(
                draw,
                series=list(series_by_kind.values()),
                period_start=period_start,
                period_end=period_end,
                box=(left + 34, chart_top, right - 34, chart_bottom),
            )

    def _draw_series_metric(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        series: CurrencyDigestChartSeries | None,
        kind: CurrencyDigestChartSeriesKind,
        x: int,
        y: int,
        width: int,
        period_start: date,
        period_end: date,
    ) -> None:
        style = self._SERIES_STYLES[kind]
        label = series.label if series else self._default_series_label(kind)
        label = self._ellipsize(draw, label, self._fonts["metric_label"], width - 30)
        self._draw_legend_line(draw, (x, y + 10), (x + 20, y + 10), style)
        draw.text((x + 29, y), label, font=self._fonts["metric_label"], fill=self._MUTED)

        points = self._window_points(series, period_start=period_start, period_end=period_end)
        available = [(day, value, source) for day, value, source in points if value is not None]
        if not available:
            draw.text((x, y + 26), "нет данных", font=self._fonts["metric_value"], fill="#7387A5")
            return
        latest_day, latest_value, latest_source = available[-1]
        assert latest_value is not None
        value_text = self._format_decimal(latest_value, places=4)
        draw.text((x, y + 25), value_text, font=self._fonts["metric_value"], fill=style.color)

        detail_parts: list[str] = []
        if latest_source:
            detail_parts.append(latest_source)
        if latest_day != period_end:
            detail_parts.append(f"на {latest_day:%d.%m}")
        if len(available) >= 2:
            delta = latest_value - available[0][1]  # type: ignore[operator]
            detail_parts.append(self._format_decimal(delta, places=4, signed=True))
        if detail_parts:
            detail = self._ellipsize(draw, " · ".join(detail_parts), self._fonts["small"], width)
            draw.text((x, y + 53), detail, font=self._fonts["small"], fill=self._MUTED)

    def _draw_chart(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        series: list[CurrencyDigestChartSeries],
        period_start: date,
        period_end: date,
        box: tuple[int, int, int, int],
    ) -> None:
        left, top, right, bottom = box
        series_points = {
            item.kind: self._window_points(item, period_start=period_start, period_end=period_end)
            for item in series
        }
        values = [value for points in series_points.values() for _, value, _ in points if value is not None]
        if not values:
            message = "Нет значений — пропуски не заполняются"
            message_width = self._text_width(draw, message, self._fonts["small"])
            draw.text(
                ((left + right - message_width) / 2, top + max(0, (bottom - top - 14) / 2)),
                message,
                font=self._fonts["small"],
                fill="#7387A5",
            )
            return

        minimum = min(values)
        maximum = max(values)
        spread = maximum - minimum
        padding = spread * Decimal("0.12") if spread else max(abs(maximum) * Decimal("0.01"), Decimal("0.01"))
        chart_min = minimum - padding
        chart_max = maximum + padding
        chart_range = chart_max - chart_min
        for fraction in (Decimal("0"), Decimal("0.5"), Decimal("1")):
            y = bottom - int(Decimal(bottom - top) * fraction)
            draw.line((left, y, right, y), fill=self._GRID, width=1)

        day_count = (period_end - period_start).days

        def coordinates(day: date, value: Decimal) -> tuple[int, int]:
            x = left + round(((day - period_start).days / day_count) * (right - left)) if day_count else left
            ratio = (value - chart_min) / chart_range
            y = bottom - round(float(ratio) * (bottom - top))
            return x, y

        for kind in ("nbrb", "bank_buy", "bank_sell"):
            style = self._SERIES_STYLES[kind]
            plotted = [(day, value) for day, value, _ in series_points.get(kind, []) if value is not None]
            previous: tuple[date, Decimal] | None = None
            for day, value in plotted:
                assert value is not None
                current = (day, value)
                if previous and (day - previous[0]).days == 1:
                    start = coordinates(*previous)
                    end = coordinates(*current)
                    if style.dashed:
                        self._draw_dashed_line(draw, start, end, fill=style.color, width=3)
                    else:
                        draw.line((start, end), fill=style.color, width=3)
                x, y = coordinates(day, value)
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=style.color, outline=self._CARD, width=2)
                previous = current

        start_label = f"{period_start:%d.%m}"
        end_label = f"{period_end:%d.%m}"
        draw.text((left, bottom + 8), start_label, font=self._fonts["small"], fill=self._MUTED)
        end_width = self._text_width(draw, end_label, self._fonts["small"])
        draw.text((right - end_width, bottom + 8), end_label, font=self._fonts["small"], fill=self._MUTED)

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        payload: TelegramCurrencyDigestChartPayload,
        period_start: date,
    ) -> None:
        draw.text(
            (56, 1282),
            "Точки отсутствующих дней не интерполируются",
            font=self._fonts["small"],
            fill="#7186A4",
        )
        generated = f"Данные: {period_start:%d.%m.%Y}–{payload.as_of:%d.%m.%Y}"
        generated_width = self._text_width(draw, generated, self._fonts["small"])
        draw.text((1024 - generated_width, 1282), generated, font=self._fonts["small"], fill="#7186A4")

    def _window_points(
        self,
        series: CurrencyDigestChartSeries | None,
        *,
        period_start: date,
        period_end: date,
    ) -> list[tuple[date, Decimal | None, str | None]]:
        rows: dict[date, tuple[Decimal | None, str | None]] = {}
        if series:
            for point in series.points:
                if period_start <= point.day <= period_end:
                    rows[point.day] = (self._decimal(point.value), self._clean_label(point.source_label))
        return [
            (day, *rows.get(day, (None, None)))
            for day in (period_start + timedelta(days=offset) for offset in range(7))
        ]

    def _draw_legend_line(
        self,
        draw: ImageDraw.ImageDraw,
        start: tuple[int, int],
        end: tuple[int, int],
        style: _SeriesStyle,
    ) -> None:
        if style.dashed:
            self._draw_dashed_line(draw, start, end, fill=style.color, width=3, dash=5, gap=4)
        else:
            draw.line((start, end), fill=style.color, width=3)

    @staticmethod
    def _draw_dashed_line(
        draw: ImageDraw.ImageDraw,
        start: tuple[int, int],
        end: tuple[int, int],
        *,
        fill: str,
        width: int,
        dash: int = 8,
        gap: int = 5,
    ) -> None:
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length <= 0:
            return
        cursor = 0.0
        while cursor < length:
            segment_end = min(cursor + dash, length)
            draw.line(
                (
                    x1 + dx * cursor / length,
                    y1 + dy * cursor / length,
                    x1 + dx * segment_end / length,
                    y1 + dy * segment_end / length,
                ),
                fill=fill,
                width=width,
            )
            cursor += dash + gap

    def _validate_payload(self, payload: TelegramCurrencyDigestChartPayload) -> None:
        if len(payload.panels) > self.MAX_PANELS:
            raise ValueError(f"Currency digest chart supports at most {self.MAX_PANELS} panels")
        for panel in payload.panels:
            if not str(panel.display_label or "").strip():
                raise ValueError("Currency digest chart panel display_label cannot be empty")
            kinds = [series.kind for series in panel.series]
            unknown = [kind for kind in kinds if kind not in self._SERIES_STYLES]
            if unknown:
                raise ValueError(f"Unsupported currency digest chart series: {unknown[0]}")
            if len(set(kinds)) != len(kinds):
                raise ValueError(f"Duplicate series in currency digest chart panel {panel.currency}")

    @classmethod
    def _resolve_font_paths(cls, font_path: str | Path | None) -> tuple[Path, Path]:
        if font_path is not None:
            candidate = Path(font_path)
            if not candidate.is_file():
                raise RuntimeError(f"Currency digest chart font does not exist: {candidate}")
            if not cls._font_supports_required_glyphs(candidate):
                raise RuntimeError(f"Currency digest chart font lacks Cyrillic or currency glyphs: {candidate}")
            return candidate, candidate
        for regular_value, bold_value in cls._FONT_PAIRS:
            regular = Path(regular_value)
            bold = Path(bold_value)
            if (
                regular.is_file()
                and bold.is_file()
                and cls._font_supports_required_glyphs(regular)
                and cls._font_supports_required_glyphs(bold)
            ):
                return regular, bold
        raise RuntimeError(
            "No Cyrillic-capable font found for the currency digest chart; "
            "install fonts-dejavu-core or pass font_path"
        )

    @staticmethod
    def _font_supports_required_glyphs(path: Path) -> bool:
        font = ImageFont.truetype(str(path), 32)
        missing_glyph = bytes(font.getmask("\u0378"))
        return all(bytes(font.getmask(character)) != missing_glyph for character in "Курс₽€")

    @staticmethod
    def _load_font(path: Path, size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
        font = ImageFont.truetype(str(path), size)
        if bold:
            try:
                if b"Bold" in font.get_variation_names():
                    font.set_variation_by_name("Bold")
            except (AttributeError, OSError):
                pass
        return font

    @staticmethod
    def _decimal(value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None
        return normalized if normalized.is_finite() else None

    @staticmethod
    def _clean_label(value: str | None) -> str | None:
        normalized = " ".join(str(value or "").split())
        return normalized or None

    @staticmethod
    def _format_decimal(value: Decimal, *, places: int, signed: bool = False) -> str:
        prefix = "+" if signed and value > 0 else ""
        return prefix + f"{value:,.{places}f}".replace(",", " ").replace(".", ",")

    @staticmethod
    def _default_series_label(kind: CurrencyDigestChartSeriesKind) -> str:
        return {
            "nbrb": "НБРБ",
            "bank_buy": "Покупка банком",
            "bank_sell": "Продажа банком",
        }[kind]

    @staticmethod
    def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
        return draw.textlength(text, font=font)

    def _ellipsize(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> str:
        normalized = " ".join(str(text or "").split())
        if self._text_width(draw, normalized, font) <= max_width:
            return normalized
        suffix = "…"
        lower = 0
        upper = len(normalized)
        while lower < upper:
            middle = (lower + upper + 1) // 2
            candidate = normalized[:middle].rstrip() + suffix
            if self._text_width(draw, candidate, font) <= max_width:
                lower = middle
            else:
                upper = middle - 1
        return normalized[:lower].rstrip() + suffix
