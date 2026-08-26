(() => {
  function createAnalyticsCurrencyChartFeature(deps) {
    const {
      el,
      core,
      escapeHtml,
    } = deps;
    const seriesColors = ["#ff8a2b", "#6ea8ff", "#62d39a", "#f7c65b", "#d78cff", "#ff7c98"];
    const minZoom = 1;
    const maxZoom = 2.8;
    const formatRate = (value) => core.formatRateDisplay?.(value || 0, 4, 6) || Number(value || 0).toFixed(6);

    function renderSeriesMarker(series, x, y, size = 3.5) {
      const color = escapeHtml(series.color || "#6ea8ff");
      if (series.markerShape === "diamond") {
        const side = size * 1.75;
        return `<rect x="${x - side / 2}" y="${y - side / 2}" width="${side}" height="${side}" rx="0.7" fill="rgba(17,29,48,0.96)" stroke="${color}" stroke-width="2" transform="rotate(45 ${x} ${y})"></rect>`;
      }
      const fill = series.markerFill === "hollow" ? "rgba(17,29,48,0.96)" : color;
      return `<circle cx="${x}" cy="${y}" r="${size}" fill="${fill}" stroke="${series.markerFill === "hollow" ? color : "rgba(255,255,255,0.9)"}" stroke-width="${series.markerFill === "hollow" ? "2" : "1.5"}"></circle>`;
    }

    function formatQuotedAt(value) {
      if (!value) {
        return "";
      }
      const parsed = new Date(value);
      return Number.isNaN(parsed.getTime())
        ? ""
        : parsed.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
    }

    function createTooltipHost(svgNode, variant = "default") {
      const wrapper = svgNode?.parentElement;
      if (!wrapper) {
        return null;
      }
      let tooltip = wrapper.querySelector(".analytics-chart-tooltip");
      if (!tooltip) {
        tooltip = document.createElement("div");
        tooltip.className = "analytics-chart-tooltip hidden";
        wrapper.appendChild(tooltip);
      }
      tooltip.classList.toggle(
        "analytics-chart-tooltip-currency-comparison",
        variant === "comparison",
      );
      return tooltip;
    }

    function positionTooltip(svgNode, tooltip, clientX, clientY) {
      if (!svgNode || !tooltip) {
        return;
      }
      const rect = svgNode.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      const left = Math.max(8, Math.min(rect.width - tooltipRect.width - 8, clientX - rect.left + 12));
      const top = Math.max(8, Math.min(rect.height - tooltipRect.height - 8, clientY - rect.top - tooltipRect.height - 10));
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
    }

    function clampZoom(value) {
      return Math.max(minZoom, Math.min(maxZoom, Number(value) || 1));
    }

    function getBaseWidth(wrapper) {
      const rootFontSize = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
      return Math.max(wrapper?.clientWidth || 0, rootFontSize * 46);
    }

    function applyZoom(wrapper, zoom, focusRatio = 0.5) {
      const chart = el.analyticsCurrencyChart;
      if (!wrapper || !chart) {
        return;
      }
      const nextZoom = clampZoom(zoom);
      const baseWidth = getBaseWidth(wrapper);
      const previousScrollWidth = wrapper.scrollWidth || baseWidth;
      const previousLeft = wrapper.scrollLeft;
      chart.dataset.chartZoom = String(nextZoom);
      chart.style.setProperty("--currency-chart-mobile-width", `${Math.round(baseWidth * nextZoom)}px`);
      requestAnimationFrame(() => {
        const nextScrollWidth = wrapper.scrollWidth || baseWidth;
        const focusX = previousLeft + (wrapper.clientWidth || 0) * focusRatio;
        const ratio = previousScrollWidth > 0 ? focusX / previousScrollWidth : focusRatio;
        wrapper.scrollLeft = Math.max(0, ratio * nextScrollWidth - (wrapper.clientWidth || 0) * focusRatio);
      });
    }

    function ensureZoom() {
      const chart = el.analyticsCurrencyChart;
      const wrapper = chart?.closest?.(".analytics-trend-chart-wrap");
      if (!chart || !wrapper) {
        return;
      }
      if (!chart.dataset.chartZoom) {
        applyZoom(wrapper, 1, 0);
      }
      if (wrapper.dataset.currencyChartZoomBound === "1") {
        return;
      }
      wrapper.dataset.currencyChartZoomBound = "1";
      let pinchStartDistance = 0;
      let pinchStartZoom = 1;
      const getTouchDistance = (event) => {
        if (!event.touches || event.touches.length < 2) {
          return 0;
        }
        const [first, second] = event.touches;
        return Math.hypot(first.clientX - second.clientX, first.clientY - second.clientY);
      };
      wrapper.addEventListener("touchstart", (event) => {
        if (event.touches.length !== 2) {
          return;
        }
        pinchStartDistance = getTouchDistance(event);
        pinchStartZoom = clampZoom(chart.dataset.chartZoom || 1);
        wrapper.classList.add("is-pinch-zooming");
      }, { passive: true });
      wrapper.addEventListener("touchmove", (event) => {
        if (event.touches.length !== 2 || !pinchStartDistance) {
          return;
        }
        event.preventDefault();
        const nextDistance = getTouchDistance(event);
        const wrapperRect = wrapper.getBoundingClientRect();
        const focusX = (event.touches[0].clientX + event.touches[1].clientX) / 2 - wrapperRect.left;
        const focusRatio = Math.max(0, Math.min(1, focusX / Math.max(1, wrapper.clientWidth)));
        applyZoom(wrapper, pinchStartZoom * (nextDistance / pinchStartDistance), focusRatio);
      }, { passive: false });
      const stopPinch = (event) => {
        if (!event.touches || event.touches.length < 2) {
          wrapper.classList.remove("is-pinch-zooming");
          pinchStartDistance = 0;
        }
      };
      wrapper.addEventListener("touchend", stopPinch, { passive: true });
      wrapper.addEventListener("touchcancel", stopPinch, { passive: true });
      wrapper.addEventListener("wheel", (event) => {
        if (!event.ctrlKey && !event.metaKey) {
          return;
        }
        event.preventDefault();
        const currentZoom = clampZoom(chart.dataset.chartZoom || 1);
        const nextZoom = currentZoom * (event.deltaY < 0 ? 1.08 : 0.92);
        const focusRatio = Math.max(
          0,
          Math.min(1, (event.clientX - wrapper.getBoundingClientRect().left) / Math.max(1, wrapper.clientWidth)),
        );
        applyZoom(wrapper, nextZoom, focusRatio);
      }, { passive: false });
    }

    function renderEmpty(message) {
      if (!el.analyticsCurrencyChart) {
        return;
      }
      ensureZoom();
      el.analyticsCurrencyChart.innerHTML = `
        <text x="490" y="140" text-anchor="middle" class="analytics-chart-empty">${escapeHtml(message)}</text>
      `;
    }

    function bindSingleTooltip(svgNode, points, helpers) {
      const tooltip = createTooltipHost(svgNode);
      if (!svgNode || !tooltip) {
        return;
      }
      const hoverGroup = svgNode.querySelector(".currency-chart-hover");
      const hoverXLine = svgNode.querySelector(".currency-chart-hover-x");
      const hoverYLine = svgNode.querySelector(".currency-chart-hover-y");
      const hoverDot = svgNode.querySelector(".currency-chart-hover-dot");
      const hoverXLabel = svgNode.querySelector(".currency-chart-hover-x-label");
      const hoverYLabel = svgNode.querySelector(".currency-chart-hover-y-label");
      const { toX, toY, width, height, padX, padY, metadata = {} } = helpers;
      svgNode.onmousemove = (event) => {
        const index = Number(event.target.closest(".trend-bucket")?.dataset.analyticsBucketIndex ?? -1);
        const point = points[index];
        if (!point) {
          tooltip.classList.add("hidden");
          hoverGroup?.classList.add("hidden");
          return;
        }
        const x = toX(index);
        const y = toY(Number(point.rate || 0));
        hoverGroup?.classList.remove("hidden");
        hoverXLine?.setAttribute("x1", String(padX));
        hoverXLine?.setAttribute("x2", String(width - padX));
        hoverXLine?.setAttribute("y1", String(y));
        hoverXLine?.setAttribute("y2", String(y));
        hoverYLine?.setAttribute("x1", String(x));
        hoverYLine?.setAttribute("x2", String(x));
        hoverYLine?.setAttribute("y1", String(padY));
        hoverYLine?.setAttribute("y2", String(height - padY));
        hoverDot?.setAttribute("cx", String(x));
        hoverDot?.setAttribute("cy", String(y));
        hoverXLabel?.setAttribute("x", String(x));
        hoverXLabel?.setAttribute("y", String(height - 10));
        if (hoverXLabel) {
          hoverXLabel.textContent = core.formatDateRu(point.rate_date);
        }
        hoverYLabel?.setAttribute("x", String(width - padX));
        hoverYLabel?.setAttribute("y", String(Math.max(padY + 12, y - 8)));
        if (hoverYLabel) {
          hoverYLabel.textContent = formatRate(point.rate || 0);
        }
        tooltip.innerHTML = `
          <div class="analytics-chart-tooltip-title">${escapeHtml(core.formatDateRu(point.rate_date))}</div>
          <div class="analytics-chart-tooltip-grid analytics-chart-tooltip-grid-compact">
            <span class="analytics-chart-tooltip-balance">${escapeHtml(metadata.label || "Курс")}: ${escapeHtml(formatRate(point.rate || 0))} ${escapeHtml(metadata.valueSuffix || "BYN")}</span>
          </div>
        `;
        tooltip.classList.remove("hidden");
        positionTooltip(svgNode, tooltip, event.clientX, event.clientY);
      };
      svgNode.onmouseleave = () => {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
      };
    }

    function bindMultiTooltip(svgNode, seriesList, orderedDates, helpers) {
      const tooltip = createTooltipHost(svgNode);
      if (!svgNode || !tooltip) {
        return;
      }
      const hoverGroup = svgNode.querySelector(".currency-chart-hover");
      const hoverYLine = svgNode.querySelector(".currency-chart-hover-y");
      const hoverDotsGroup = svgNode.querySelector(".currency-chart-hover-dots");
      const hoverXLabel = svgNode.querySelector(".currency-chart-hover-x-label");
      const { toX, toY, height, padY } = helpers;
      svgNode.onmousemove = (event) => {
        const index = Number(event.target.closest(".trend-bucket")?.dataset.analyticsBucketIndex ?? -1);
        const rateDate = orderedDates[index];
        const rows = rateDate
          ? seriesList.map((series) => {
            const point = series.pointsByDate.get(rateDate);
            return point ? {
              currency: series.currency,
              label: series.legendLabel || core.formatCurrencyLabel(series.currency),
              valueSuffix: series.valueSuffix || "BYN",
              color: series.color,
              rate: Number(point.rate || 0),
            } : null;
          }).filter(Boolean).sort((left, right) => right.rate - left.rate)
          : [];
        if (!rows.length) {
          tooltip.classList.add("hidden");
          hoverGroup?.classList.add("hidden");
          return;
        }
        const x = toX(index);
        hoverGroup?.classList.remove("hidden");
        hoverYLine?.setAttribute("x1", String(x));
        hoverYLine?.setAttribute("x2", String(x));
        hoverYLine?.setAttribute("y1", String(padY));
        hoverYLine?.setAttribute("y2", String(height - padY));
        hoverXLabel?.setAttribute("x", String(x));
        hoverXLabel?.setAttribute("y", String(height - 10));
        if (hoverXLabel) {
          hoverXLabel.textContent = core.formatDateRu(rateDate);
        }
        if (hoverDotsGroup) {
          hoverDotsGroup.innerHTML = rows.map((row) => `
            <circle cx="${x}" cy="${toY(row.rate)}" r="5" fill="${row.color}" stroke="#fff" stroke-width="2"></circle>
          `).join("");
        }
        tooltip.innerHTML = `
          <div class="analytics-chart-tooltip-title">${escapeHtml(core.formatDateRu(rateDate))}</div>
          <div class="analytics-chart-tooltip-grid">
            ${rows.map((row) => `
              <span class="analytics-chart-tooltip-balance">
                <span style="color:${escapeHtml(row.color)}">●</span> ${escapeHtml(row.label)}: ${escapeHtml(formatRate(row.rate))} ${escapeHtml(row.valueSuffix)}
              </span>
            `).join("")}
          </div>
        `;
        tooltip.classList.remove("hidden");
        positionTooltip(svgNode, tooltip, event.clientX, event.clientY);
      };
      svgNode.onmouseleave = () => {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
      };
    }

    function bindComparisonTooltip(svgNode, seriesList, orderedDates, helpers) {
      const tooltip = createTooltipHost(svgNode, "comparison");
      if (!svgNode || !tooltip) {
        return;
      }
      const hoverGroup = svgNode.querySelector(".currency-chart-hover");
      const hoverYLine = svgNode.querySelector(".currency-chart-hover-y");
      const hoverDotsGroup = svgNode.querySelector(".currency-chart-hover-dots");
      const hoverXLabel = svgNode.querySelector(".currency-chart-hover-x-label");
      const { toX, toY, height, padY } = helpers;
      svgNode.onmousemove = (event) => {
        const index = Number(event.target.closest(".trend-bucket")?.dataset.analyticsBucketIndex ?? -1);
        const rateDate = orderedDates[index];
        const rows = rateDate
          ? seriesList.map((series) => {
            const point = series.pointsByDate.get(rateDate);
            return point ? {
              id: series.id,
              label: series.label,
              color: series.color,
              dashArray: series.dashArray,
              markerShape: series.markerShape,
              markerFill: series.markerFill,
              channelLabel: series.channelLabel || "",
              valueSuffix: series.valueSuffix || "BYN",
              quotedAt: point.quoted_at || "",
              rate: Number(point.rate || 0),
            } : null;
          }).filter(Boolean)
          : [];
        if (!rows.length) {
          tooltip.classList.add("hidden");
          hoverGroup?.classList.add("hidden");
          return;
        }
        const x = toX(index);
        hoverGroup?.classList.remove("hidden");
        hoverYLine?.setAttribute("x1", String(x));
        hoverYLine?.setAttribute("x2", String(x));
        hoverYLine?.setAttribute("y1", String(padY));
        hoverYLine?.setAttribute("y2", String(height - padY));
        hoverXLabel?.setAttribute("x", String(x));
        hoverXLabel?.setAttribute("y", String(height - 10));
        if (hoverXLabel) {
          hoverXLabel.textContent = core.formatDateRu(rateDate);
        }
        if (hoverDotsGroup) {
          hoverDotsGroup.innerHTML = rows.map((row) => renderSeriesMarker(row, x, toY(row.rate), 5)).join("");
        }
        tooltip.innerHTML = `
          <div class="analytics-chart-tooltip-title">${escapeHtml(core.formatDateRu(rateDate))}</div>
          <div class="analytics-chart-tooltip-grid currency-chart-comparison-tooltip">
            ${rows.map((row) => `
              <span class="analytics-chart-tooltip-balance">
                <i class="currency-chart-tooltip-line" style="--series-color:${escapeHtml(row.color)};--series-dash:${row.dashArray ? "dashed" : "solid"}"></i>
                <span>${escapeHtml(row.label)}${row.channelLabel ? ` · ${escapeHtml(row.channelLabel)}` : ""}: <strong>${escapeHtml(formatRate(row.rate))}</strong> ${escapeHtml(row.valueSuffix)}${row.quotedAt ? ` · котировка ${escapeHtml(formatQuotedAt(row.quotedAt))}` : ""}</span>
              </span>
            `).join("")}
          </div>
        `;
        tooltip.classList.remove("hidden");
        positionTooltip(svgNode, tooltip, event.clientX, event.clientY);
      };
      svgNode.onmouseleave = () => {
        tooltip.classList.add("hidden");
        hoverGroup?.classList.add("hidden");
      };
    }

    function getSeriesColor(index) {
      return seriesColors[index % seriesColors.length];
    }

    function renderMulti(seriesList) {
      const chart = el.analyticsCurrencyChart;
      if (!chart) {
        return;
      }
      ensureZoom();
      const visibleSeries = Array.isArray(seriesList)
        ? seriesList.filter((item) => Array.isArray(item.points) && item.points.length >= 2)
        : [];
      if (!visibleSeries.length) {
        renderEmpty("Недостаточно истории курса по отслеживаемым валютам");
        return;
      }
      const width = 980;
      const height = 280;
      const padX = 56;
      const padY = 28;
      const orderedDates = Array.from(new Set(
        visibleSeries.flatMap((series) => series.points.map((point) => point.rate_date)),
      )).sort();
      if (orderedDates.length < 2) {
        renderEmpty("Недостаточно истории курса по отслеживаемым валютам");
        return;
      }
      const allRates = visibleSeries.flatMap((series) => (
        series.points.map((point) => Number(point.rate || 0))
      )).filter(Number.isFinite);
      const minRate = Math.min(...allRates);
      const maxRate = Math.max(...allRates);
      const yRange = maxRate - minRate || 1;
      const xStep = (width - padX * 2) / Math.max(1, orderedDates.length - 1);
      const toX = (index) => padX + index * xStep;
      const toY = (value) => height - padY - ((value - minRate) / yRange) * (height - padY * 2);
      const bucketWidth = orderedDates.length > 1 ? xStep : width - padX * 2;
      const seriesMarkup = visibleSeries.map((series) => {
        const polyline = orderedDates.filter((date) => series.pointsByDate.has(date)).map((date) => {
          const point = series.pointsByDate.get(date);
          return `${toX(orderedDates.indexOf(date))},${toY(Number(point.rate || 0))}`;
        }).join(" ");
        const dots = series.points.map((point) => `
          <circle cx="${toX(orderedDates.indexOf(point.rate_date))}" cy="${toY(Number(point.rate || 0))}" r="3.2" fill="${series.color}" stroke="rgba(255,255,255,0.88)" stroke-width="1.6"></circle>
        `).join("");
        return `<g class="currency-chart-series"><polyline fill="none" stroke="${series.color}" stroke-width="3.25" stroke-linejoin="round" stroke-linecap="round" points="${polyline}"></polyline>${dots}</g>`;
      }).join("");
      const xTickIndexes = [0, Math.floor(orderedDates.length / 2), orderedDates.length - 1]
        .filter((value, index, items) => items.indexOf(value) === index);
      const xTicks = xTickIndexes.map((index) => `
        <line x1="${toX(index)}" y1="${height - padY}" x2="${toX(index)}" y2="${height - padY + 6}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
        <text x="${toX(index)}" y="${height - 8}" text-anchor="${index === 0 ? "start" : index === orderedDates.length - 1 ? "end" : "middle"}" class="analytics-chart-empty">${core.formatDateRu(orderedDates[index])}</text>
      `).join("");
      const midRate = minRate + yRange / 2;
      const yMarks = [minRate, midRate, maxRate].map((value) => `
        <line x1="${width - padX - 8}" y1="${toY(value)}" x2="${width - padX}" y2="${toY(value)}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
        <text x="${width - padX}" y="${Math.max(padY + 10, toY(value) - 8)}" text-anchor="end" class="analytics-chart-empty">${formatRate(value)}</text>
      `).join("");
      const hitboxes = orderedDates.map((rateDate, index) => `
        <g class="trend-bucket" data-analytics-bucket-index="${index}" data-analytics-rate-date="${rateDate}">
          <rect class="analytics-trend-hitbox" x="${Math.max(0, toX(index) - bucketWidth / 2).toFixed(2)}" y="0" width="${Math.max(bucketWidth, 24).toFixed(2)}" height="${height}" fill="transparent"></rect>
        </g>
      `).join("");
      chart.innerHTML = `
        <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        ${seriesMarkup}${xTicks}${yMarks}${hitboxes}
        <g class="currency-chart-hover hidden">
          <line class="currency-chart-hover-y" x1="0" y1="0" x2="0" y2="0" stroke="rgba(255,255,255,0.28)" stroke-dasharray="4 4" stroke-width="1"></line>
          <g class="currency-chart-hover-dots"></g>
          <text class="analytics-chart-empty currency-chart-hover-x-label" x="0" y="0" text-anchor="middle"></text>
        </g>
      `;
      bindMultiTooltip(chart, visibleSeries, orderedDates, { toX, toY, height, padY });
    }

    function renderComparison(seriesList) {
      const chart = el.analyticsCurrencyChart;
      if (!chart) {
        return;
      }
      ensureZoom();
      const visibleSeries = Array.isArray(seriesList)
        ? seriesList.filter((item) => Array.isArray(item.points) && item.points.length >= 1)
        : [];
      if (!visibleSeries.length) {
        renderEmpty("История банковских курсов начнёт собираться после обновления данных");
        return;
      }
      const width = 980;
      const height = 280;
      const padX = 56;
      const padY = 28;
      const orderedDates = Array.from(new Set(
        visibleSeries.flatMap((series) => series.points.map((point) => point.rate_date)),
      )).sort();
      if (!orderedDates.length) {
        renderEmpty("История банковских курсов начнёт собираться после обновления данных");
        return;
      }
      const allRates = visibleSeries.flatMap((series) => (
        series.points.map((point) => Number(point.rate || 0))
      )).filter((value) => Number.isFinite(value) && value > 0);
      if (!allRates.length) {
        renderEmpty("Нет банковских котировок за выбранный период");
        return;
      }
      const rawMinRate = Math.min(...allRates);
      const rawMaxRate = Math.max(...allRates);
      const rawRange = rawMaxRate - rawMinRate;
      const margin = rawRange > 0 ? rawRange * 0.08 : Math.max(rawMaxRate * 0.006, 0.0001);
      const minRate = Math.max(0, rawMinRate - margin);
      const maxRate = rawMaxRate + margin;
      const yRange = maxRate - minRate || 1;
      const xStep = orderedDates.length > 1
        ? (width - padX * 2) / (orderedDates.length - 1)
        : 0;
      const toX = (index) => orderedDates.length > 1 ? padX + index * xStep : width / 2;
      const toY = (value) => height - padY - ((value - minRate) / yRange) * (height - padY * 2);
      const bucketWidth = orderedDates.length > 1 ? xStep : width - padX * 2;
      const seriesMarkup = visibleSeries.map((series) => {
        const datedPoints = orderedDates.filter((date) => series.pointsByDate.has(date)).map((date) => {
          const point = series.pointsByDate.get(date);
          return {
            date,
            x: toX(orderedDates.indexOf(date)),
            y: toY(Number(point.rate || 0)),
          };
        });
        const polyline = datedPoints.map((point) => `${point.x},${point.y}`).join(" ");
        const dash = series.dashArray ? ` stroke-dasharray="${escapeHtml(series.dashArray)}"` : "";
        const line = datedPoints.length >= 2
          ? `<polyline fill="none" stroke="${series.color}" stroke-width="3"${dash} stroke-linejoin="round" stroke-linecap="round" points="${polyline}"></polyline>`
          : "";
        const dots = datedPoints.map((point) => renderSeriesMarker(series, point.x, point.y)).join("");
        return `<g class="currency-chart-series currency-chart-bank-series" data-series-id="${escapeHtml(series.id || "")}" data-marker-shape="${escapeHtml(series.markerShape || "circle")}">${line}${dots}</g>`;
      }).join("");
      const xTickIndexes = [0, Math.floor(orderedDates.length / 2), orderedDates.length - 1]
        .filter((value, index, items) => items.indexOf(value) === index);
      const xTicks = xTickIndexes.map((index) => `
        <line x1="${toX(index)}" y1="${height - padY}" x2="${toX(index)}" y2="${height - padY + 6}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
        <text x="${toX(index)}" y="${height - 8}" text-anchor="${orderedDates.length === 1 ? "middle" : index === 0 ? "start" : index === orderedDates.length - 1 ? "end" : "middle"}" class="analytics-chart-empty">${core.formatDateRu(orderedDates[index])}</text>
      `).join("");
      const midRate = minRate + yRange / 2;
      const yMarks = [minRate, midRate, maxRate].map((value) => `
        <line x1="${width - padX - 8}" y1="${toY(value)}" x2="${width - padX}" y2="${toY(value)}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
        <text x="${width - padX}" y="${Math.max(padY + 10, toY(value) - 8)}" text-anchor="end" class="analytics-chart-empty">${formatRate(value)}</text>
      `).join("");
      const hitboxes = orderedDates.map((rateDate, index) => `
        <g class="trend-bucket" data-analytics-bucket-index="${index}" data-analytics-rate-date="${rateDate}">
          <rect class="analytics-trend-hitbox" x="${Math.max(0, toX(index) - bucketWidth / 2).toFixed(2)}" y="0" width="${Math.max(bucketWidth, 24).toFixed(2)}" height="${height}" fill="transparent"></rect>
        </g>
      `).join("");
      chart.innerHTML = `
        <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        ${seriesMarkup}${xTicks}${yMarks}${hitboxes}
        <g class="currency-chart-hover hidden">
          <line class="currency-chart-hover-y" x1="0" y1="0" x2="0" y2="0" stroke="rgba(255,255,255,0.28)" stroke-dasharray="4 4" stroke-width="1"></line>
          <g class="currency-chart-hover-dots"></g>
          <text class="analytics-chart-empty currency-chart-hover-x-label" x="0" y="0" text-anchor="middle"></text>
        </g>
      `;
      bindComparisonTooltip(chart, visibleSeries, orderedDates, { toX, toY, height, padY });
    }

    function renderSingle(points, metadata = {}) {
      const chart = el.analyticsCurrencyChart;
      if (!chart) {
        return;
      }
      ensureZoom();
      if (!Array.isArray(points) || points.length < 2) {
        renderEmpty("Недостаточно истории курса");
        return;
      }
      const width = 980;
      const height = 280;
      const padX = 56;
      const padY = 28;
      const rates = points.map((item) => Number(item.rate || 0)).filter(Number.isFinite);
      if (rates.length < 2) {
        renderEmpty("Недостаточно истории курса");
        return;
      }
      const minRate = Math.min(...rates);
      const maxRate = Math.max(...rates);
      const yRange = maxRate - minRate || 1;
      const xStep = (width - padX * 2) / Math.max(1, points.length - 1);
      const toX = (index) => padX + index * xStep;
      const toY = (value) => height - padY - ((value - minRate) / yRange) * (height - padY * 2);
      const last = points[points.length - 1];
      const first = points[0];
      const middle = points[Math.floor(points.length / 2)];
      const midRate = minRate + yRange / 2;
      const bucketWidth = points.length > 1 ? xStep : width - padX * 2;
      const polyline = points.map((item, index) => `${toX(index)},${toY(Number(item.rate || 0))}`).join(" ");
      const pointDots = points.map((item, index) => `
        <circle cx="${toX(index)}" cy="${toY(Number(item.rate || 0))}" r="2.8" fill="rgba(255,255,255,0.82)"></circle>
      `).join("");
      const xTicks = [0, Math.floor(points.length / 2), points.length - 1]
        .filter((value, index, items) => items.indexOf(value) === index)
        .map((index) => `<line x1="${toX(index)}" y1="${height - padY}" x2="${toX(index)}" y2="${height - padY + 6}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>`)
        .join("");
      const yTicks = [minRate, midRate, maxRate].map((value) => `
        <line x1="${width - padX - 8}" y1="${toY(value)}" x2="${width - padX}" y2="${toY(value)}" stroke="rgba(207, 219, 245, 0.28)" stroke-width="1"></line>
      `).join("");
      const hitboxes = points.map((item, index) => `
        <g class="trend-bucket" data-analytics-bucket-index="${index}">
          <rect class="analytics-trend-hitbox" x="${Math.max(0, toX(index) - bucketWidth / 2).toFixed(2)}" y="0" width="${Math.max(bucketWidth, 24).toFixed(2)}" height="${height}" fill="transparent"></rect>
        </g>
      `).join("");
      chart.innerHTML = `
        <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" class="analytics-axis-line"></line>
        <polyline fill="none" stroke="var(--accent, #6ea8ff)" stroke-width="4" points="${polyline}"></polyline>
        ${pointDots}
        <circle cx="${toX(points.length - 1)}" cy="${toY(Number(last.rate || 0))}" r="5" fill="var(--accent, #6ea8ff)"></circle>
        ${xTicks}${yTicks}${hitboxes}
        <g class="currency-chart-hover hidden">
          <line class="currency-chart-hover-x" x1="0" y1="0" x2="0" y2="0" stroke="rgba(255,255,255,0.28)" stroke-dasharray="4 4" stroke-width="1"></line>
          <line class="currency-chart-hover-y" x1="0" y1="0" x2="0" y2="0" stroke="rgba(255,255,255,0.28)" stroke-dasharray="4 4" stroke-width="1"></line>
          <circle class="currency-chart-hover-dot" cx="0" cy="0" r="5.5" fill="var(--accent, #6ea8ff)" stroke="#fff" stroke-width="2"></circle>
          <text class="analytics-chart-empty currency-chart-hover-x-label" x="0" y="0" text-anchor="middle">${core.formatDateRu(last.rate_date)}</text>
          <text class="analytics-chart-empty currency-chart-hover-y-label" x="0" y="0" text-anchor="end">${formatRate(last.rate || 0)}</text>
        </g>
        <text x="${padX}" y="${height - 8}" class="analytics-chart-empty">${core.formatDateRu(first.rate_date)}</text>
        <text x="${toX(Math.floor(points.length / 2))}" y="${height - 8}" text-anchor="middle" class="analytics-chart-empty">${core.formatDateRu(middle.rate_date)}</text>
        <text x="${width - padX}" y="${height - 8}" text-anchor="end" class="analytics-chart-empty">${core.formatDateRu(last.rate_date)}</text>
        <text x="${width - padX}" y="${padY + 4}" text-anchor="end" class="analytics-chart-empty">${formatRate(maxRate)}</text>
        <text x="${width - padX}" y="${height / 2}" text-anchor="end" class="analytics-chart-empty">${formatRate(midRate)}</text>
        <text x="${width - padX}" y="${height - padY - 8}" text-anchor="end" class="analytics-chart-empty">${formatRate(minRate)}</text>
      `;
      bindSingleTooltip(chart, points, { toX, toY, width, height, padX, padY, metadata });
    }

    return {
      getSeriesColor,
      renderEmpty,
      renderMulti,
      renderComparison,
      renderSingle,
    };
  }

  window.App.registerRuntimeModule?.(
    "analytics-currency-chart-factory",
    createAnalyticsCurrencyChartFeature,
  );
})();
