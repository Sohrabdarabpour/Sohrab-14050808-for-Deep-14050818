// اسکریپت صفحه: reports/department_performance.html

    (function () {
        'use strict';

        if (typeof Chart !== 'undefined') {
            Chart.defaults.font.family = 'Vazirmatn, Tahoma, Arial, sans-serif';
            Chart.defaults.font.size = 12;
            Chart.defaults.color = '#2d3e4a';
        }

        // ============================================================
        // ★ متغیرهای سراسری
        // ============================================================
        let monthlyTrendChart = null;
        let activeTooltipChart = null;

        let currentData = JSON.parse(
            document.getElementById('dpInitialData').textContent
        );

        let brushState = {
            from: 0,
            to: 11,
            dragging: null,
            months: [],
            monthsShort: [],
            hasData: false,
            initialized: false
        };

        let previousRanks = {};

        const primaryColor = '#1b698b';
        const successColor = '#16a34a';
        const warningColor = '#d97706';

        const SCORE_COLORS = [
            {min: 80, color: '#16a34a'},
            {min: 60, color: '#22c55e'},
            {min: 40, color: '#f59e0b'},
            {min: 20, color: '#fb923c'},
            {min: 0, color: '#dc2626'}
        ];

        function getScoreColor(score) {
            for (const c of SCORE_COLORS) {
                if (score >= c.min) return c.color;
            }
            return '#dc2626';
        }

        // ============================================================
        // ★ Tooltip
        // ============================================================
        function getOrCreateTooltip() {
            let el = document.getElementById('dp-chart-tooltip');
            if (!el) {
                el = document.createElement('div');
                el.id = 'dp-chart-tooltip';
                document.body.appendChild(el);
            }
            return el;
        }

        function hideTooltip() {
            const el = document.getElementById('dp-chart-tooltip');
            if (el) {
                el.classList.remove('visible');
                el.style.opacity = '0';
                el.style.visibility = 'hidden';
                el.style.pointerEvents = 'none';
                el.innerHTML = '';
            }
            activeTooltipChart = null;

            document.querySelectorAll('.dp-rank-item.dp-rank-clicked').forEach(function (item) {
                item.classList.remove('dp-rank-clicked');
            });
        }

        function showTooltipAtPoint(chart, dataIndex, mouseEvent) {
            const tooltipEl = getOrCreateTooltip();
            const chartId = chart.canvas.id;

            let html = '';

            if (chartId === 'monthlyTrendChart' && dataIndex >= 0) {
                const monthLabel = chart.data.labels[dataIndex] || '';

                html = `
                    <button type="button" class="dp-tt-close" data-dp-close="1">
                        <i class="fa-solid fa-xmark" style="pointer-events:none;"></i>
                    </button>
                    <div class="dp-tt-title"><span>${monthLabel}</span></div>
                `;

                chart.data.datasets.forEach(function (ds) {
                    const label = ds.label || '';
                    const value = Number(ds.data[dataIndex] || 0).toLocaleString('fa-IR');

                    let iconName = 'fa-file-lines';
                    let iconClass = 'icon-doc';

                    if (label.includes('تکمیل')) {
                        iconName = 'fa-circle-check';
                        iconClass = 'icon-completed';
                    } else if (label.includes('باقی')) {
                        iconName = 'fa-hourglass-half';
                        iconClass = 'icon-pending';
                    } else if (label.includes('کل')) {
                        iconName = 'fa-layer-group';
                        iconClass = 'icon-total';
                    }

                    html += `
                        <div class="dp-tt-row">
                            <span class="dp-tt-label">
                                <i class="fa-solid ${iconName} ${iconClass}"></i>
                                <span>${label}</span>
                            </span>
                            <span class="dp-tt-value">${value}</span>
                        </div>
                    `;
                });

                html += `<span class="dp-tt-hint">برای بستن، دکمه ✕ یا کلیک بیرون</span>`;
            }

            if (!html) return;

            tooltipEl.innerHTML = html;
            tooltipEl.style.opacity = '0';
            tooltipEl.style.visibility = 'hidden';
            tooltipEl.style.pointerEvents = 'none';
            tooltipEl.classList.add('visible');

            const tw = tooltipEl.offsetWidth;
            const th = tooltipEl.offsetHeight;

            let clickX, clickY;
            if (mouseEvent && typeof mouseEvent.clientX === 'number') {
                clickX = mouseEvent.clientX;
                clickY = mouseEvent.clientY;
            } else {
                const rect = chart.canvas.getBoundingClientRect();
                clickX = rect.left + rect.width / 2;
                clickY = rect.top + rect.height / 2;
            }

            const OFFSET = 15;
            let finalLeft = clickX + OFFSET;
            let finalTop = clickY - th / 2;

            if (finalLeft + tw > window.innerWidth - 10) {
                finalLeft = clickX - tw - OFFSET;
            }
            if (finalLeft < 10) finalLeft = 10;
            if (finalTop < 10) finalTop = 10;
            if (finalTop + th > window.innerHeight - 10) {
                finalTop = window.innerHeight - th - 10;
            }

            tooltipEl.style.left = finalLeft + 'px';
            tooltipEl.style.top = finalTop + 'px';
            tooltipEl.style.opacity = '1';
            tooltipEl.style.visibility = 'visible';
            tooltipEl.style.pointerEvents = 'auto';

            activeTooltipChart = chart;
        }

        function showRankingTooltip(item, mouseEvent, rankElement) {
            const tooltipEl = getOrCreateTooltip();

            const score = Number(item.score || 0);
            const rate = Number(item.completion_rate || 0);
            const effective = Number(item.effective_total || 0);
            const completed = Number(item.completed || 0);
            const pending = Number(item.pending || 0);
            const excluded = Number(item.excluded || 0);
            const volume = Number(item.normalized_volume || 0);

            const color = getScoreColor(score);

            const html = `
                <button type="button" class="dp-tt-close" data-dp-close="1" aria-label="بستن">
                    <i class="fa-solid fa-xmark" style="pointer-events:none;"></i>
                </button>

                <div class="dp-tt-title">
                    <i class="fa-solid fa-building" style="color: ${color};"></i>
                    <span>${escapeHtml(item.department_title || 'نامشخص')}</span>
                </div>

                <div class="dp-tt-row">
                    <span class="dp-tt-label">
                        <i class="fa-solid fa-award icon-award"></i>
                        <span>امتیاز عملکرد</span>
                    </span>
                    <span class="dp-tt-value" style="color: ${color}; font-size: 15px; font-weight: 900;">
                        ${score.toFixed(1)}
                    </span>
                </div>

                <div class="dp-tt-divider"></div>

                <div class="dp-tt-row">
                    <span class="dp-tt-label">
                        <i class="fa-solid fa-percent icon-rate"></i>
                        <span>نرخ تکمیل</span>
                    </span>
                    <span class="dp-tt-value">${rate.toFixed(1)}٪</span>
                </div>

                <div class="dp-tt-row">
                    <span class="dp-tt-label">
                        <i class="fa-solid fa-chart-simple icon-effective"></i>
                        <span>حجم کار</span>
                    </span>
                    <span class="dp-tt-value">${volume.toFixed(1)}٪</span>
                </div>

                <div class="dp-tt-divider"></div>

                <div class="dp-tt-row">
                    <span class="dp-tt-label">
                        <i class="fa-solid fa-layer-group icon-effective"></i>
                        <span>اسناد مؤثر</span>
                    </span>
                    <span class="dp-tt-value">${effective.toLocaleString('fa-IR')}</span>
                </div>

                <div class="dp-tt-row">
                    <span class="dp-tt-label">
                        <i class="fa-solid fa-circle-check icon-completed"></i>
                        <span>تکمیل‌شده</span>
                    </span>
                    <span class="dp-tt-value" style="color: #86efac;">
                        ${completed.toLocaleString('fa-IR')}
                    </span>
                </div>

                <div class="dp-tt-row">
                    <span class="dp-tt-label">
                        <i class="fa-solid fa-hourglass-half icon-pending"></i>
                        <span>باقی‌مانده فعال</span>
                    </span>
                    <span class="dp-tt-value" style="color: #fcd34d;">
                        ${pending.toLocaleString('fa-IR')}
                    </span>
                </div>

                ${excluded > 0 ? `
                <div class="dp-tt-row">
                    <span class="dp-tt-label">
                        <i class="fa-solid fa-ban icon-excluded"></i>
                        <span>خارج از محاسبه</span>
                    </span>
                    <span class="dp-tt-value" style="color: #cbd5e1;">
                        ${excluded.toLocaleString('fa-IR')}
                    </span>
                </div>
                ` : ''}

                <span class="dp-tt-hint">
                    برای بستن، دکمه ✕ یا کلیک بیرون
                </span>
            `;

            tooltipEl.innerHTML = html;
            tooltipEl.style.opacity = '0';
            tooltipEl.style.visibility = 'hidden';
            tooltipEl.style.pointerEvents = 'none';
            tooltipEl.classList.add('visible');

            const tw = tooltipEl.offsetWidth;
            const th = tooltipEl.offsetHeight;

            let clickX, clickY;
            if (mouseEvent && typeof mouseEvent.clientX === 'number') {
                clickX = mouseEvent.clientX;
                clickY = mouseEvent.clientY;
            } else if (rankElement) {
                const rect = rankElement.getBoundingClientRect();
                clickX = rect.left + rect.width / 2;
                clickY = rect.top + rect.height / 2;
            } else {
                clickX = window.innerWidth / 2;
                clickY = window.innerHeight / 2;
            }

            const OFFSET = 15;
            let finalLeft = clickX + OFFSET;
            let finalTop = clickY - th / 2;

            if (finalLeft + tw > window.innerWidth - 10) {
                finalLeft = clickX - tw - OFFSET;
            }
            if (finalLeft < 10) finalLeft = 10;
            if (finalTop < 10) finalTop = 10;
            if (finalTop + th > window.innerHeight - 10) {
                finalTop = window.innerHeight - th - 10;
            }

            tooltipEl.style.left = finalLeft + 'px';
            tooltipEl.style.top = finalTop + 'px';
            tooltipEl.style.opacity = '1';
            tooltipEl.style.visibility = 'visible';
            tooltipEl.style.pointerEvents = 'auto';

            document.querySelectorAll('.dp-rank-item.dp-rank-clicked').forEach(function (el) {
                el.classList.remove('dp-rank-clicked');
            });
            if (rankElement) rankElement.classList.add('dp-rank-clicked');

            activeTooltipChart = null;
        }

        function setupGlobalTooltipHandlers() {
            document.addEventListener('pointerdown', function (e) {
                if (e.target.closest('[data-dp-close="1"]')) {
                    e.preventDefault();
                    e.stopPropagation();
                    hideTooltip();
                }
            }, true);

            document.addEventListener('click', function (e) {
                const el = document.getElementById('dp-chart-tooltip');
                if (!el || !el.classList.contains('visible')) return;
                if (e.target.closest('[data-dp-close="1"]')) return;
                if (el.contains(e.target)) return;
                if (e.target.tagName === 'CANVAS') return;
                if (e.target.closest('.dp-rank-item')) return;

                hideTooltip();
            });

            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') hideTooltip();
            });
        }

        // ============================================================
        // ★ راه‌اندازی
        // ============================================================
        document.addEventListener('DOMContentLoaded', function () {
            renderSummary(currentData.summary);
            renderMonthlyTrend(currentData.monthly_trend);
            renderRanking(currentData.ranking, true);

            initBrushFromData();

            bindFilterButtons();
            bindModals();
            setupGlobalTooltipHandlers();
        });

        // ============================================================
        // ★ فیلترها
        // ============================================================
        function bindFilterButtons() {
            const yearButtons = document.querySelectorAll('#yearButtons .dp-filter-btn');
            const deptButtons = document.querySelectorAll('#departmentButtons .dp-filter-btn');

            yearButtons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    setActiveButton(yearButtons, this);
                    fetchData({year: this.dataset.year});
                });
            });

            deptButtons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    setActiveButton(deptButtons, this);
                    fetchData({department_id: this.dataset.dept});
                });
            });
        }

        function setActiveButton(buttons, activeBtn) {
            buttons.forEach(b => b.classList.remove('active'));
            activeBtn.classList.add('active');
        }

        // ============================================================
        // ★ AJAX
        // ============================================================
        function fetchData(changes) {
            Object.assign(currentData.filters, changes);
            previousRanks = {};
            hideTooltip();

            const params = new URLSearchParams({
                year: currentData.filters.year || 'all',
                department_id: currentData.filters.department_id || 'all',
                area_id: currentData.filters.area_id || 'all'
            });

            fetch('/reports/department-performance/data.json?' + params.toString(), {
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            })
                .then(function (res) {
                    if (!res.ok) throw new Error('خطا');
                    return res.json();
                })
                .then(function (data) {
                    currentData.summary = data.summary;
                    currentData.monthly_trend = data.monthly_trend;
                    currentData.ranking = data.ranking;
                    if (data.departments) currentData.departments = data.departments;
                    if (data.monthly_per_department) {
                        currentData.monthly_per_department = data.monthly_per_department;
                    }

                    renderSummary(data.summary);
                    renderMonthlyTrend(data.monthly_trend);
                    renderRanking(data.ranking, true);

                    initBrushFromData();

                    const subtitle = document.getElementById('trendSubtitle');
                    if (subtitle) {
                        const y = currentData.filters.year;
                        subtitle.textContent = (y && y !== 'all')
                            ? 'سال ' + y
                            : 'همه سال‌ها';
                    }
                })
                .catch(function (err) {
                    console.error(err);
                    alert('خطا در بارگذاری داده‌ها');
                });
        }

        // ============================================================
        // ★ Summary
        // ============================================================
        function renderSummary(summary) {
            if (!summary) return;

            const fmt = function (n) {
                return Number(n || 0).toLocaleString('fa-IR');
            };

            document.getElementById('summaryTotal').textContent = fmt(summary.total);
            document.getElementById('summaryCompleted').textContent = fmt(summary.completed);
            document.getElementById('summaryPending').textContent = fmt(summary.pending);
            document.getElementById('summaryExcluded').textContent = fmt(summary.excluded || 0);

            const rateEl = document.getElementById('summaryRate');
            rateEl.innerHTML = Number(summary.completion_rate || 0).toFixed(1).toLocaleString('fa-IR') + '<small>%</small>';
        }

        // ============================================================
        // ★ نمودار خطی
        // ============================================================
        function renderMonthlyTrend(trend) {
            const canvas = document.getElementById('monthlyTrendChart');
            if (!canvas || !trend) return;

            if (monthlyTrendChart) {
                monthlyTrendChart.destroy();
                monthlyTrendChart = null;
            }

            if (!trend.labels || trend.labels.length === 0) {
                canvas.parentElement.innerHTML =
                    '<div class="dp-empty">' +
                    '<i class="fa-solid fa-chart-line"></i>' +
                    '<h3>داده‌ای برای نمایش وجود ندارد</h3>' +
                    '<p>با فیلترهای دیگر امتحان کنید</p>' +
                    '</div>';
                return;
            }

            const ctx = canvas.getContext('2d');

            const gradientTotal = ctx.createLinearGradient(0, 0, 0, 400);
            gradientTotal.addColorStop(0, 'rgba(27, 105, 139, .35)');
            gradientTotal.addColorStop(0.5, 'rgba(27, 105, 139, .10)');
            gradientTotal.addColorStop(1, 'rgba(27, 105, 139, 0)');

            const gradientCompleted = ctx.createLinearGradient(0, 0, 0, 400);
            gradientCompleted.addColorStop(0, 'rgba(22, 163, 74, .40)');
            gradientCompleted.addColorStop(0.5, 'rgba(22, 163, 74, .12)');
            gradientCompleted.addColorStop(1, 'rgba(22, 163, 74, 0)');

            const gradientPending = ctx.createLinearGradient(0, 0, 0, 400);
            gradientPending.addColorStop(0, 'rgba(217, 119, 6, .35)');
            gradientPending.addColorStop(0.5, 'rgba(217, 119, 6, .10)');
            gradientPending.addColorStop(1, 'rgba(217, 119, 6, 0)');

            const isSmall = window.innerWidth <= 576;
            const isTiny = window.innerWidth <= 380;

            monthlyTrendChart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: trend.labels,
                    datasets: [
                        {
                            label: 'کل اسناد مؤثر',
                            data: trend.total,
                            borderColor: primaryColor,
                            backgroundColor: gradientTotal,
                            borderWidth: isSmall ? 2 : 2.5,
                            tension: 0.4,
                            fill: true,
                            pointRadius: isTiny ? 2 : (isSmall ? 3 : 4),
                            pointHoverRadius: isTiny ? 4 : (isSmall ? 5 : 7),
                            pointBackgroundColor: '#fff',
                            pointBorderColor: primaryColor,
                            pointBorderWidth: 2,
                            pointHoverBackgroundColor: primaryColor
                        },
                        {
                            label: 'تکمیل‌شده',
                            data: trend.completed,
                            borderColor: successColor,
                            backgroundColor: gradientCompleted,
                            borderWidth: isSmall ? 2 : 2.5,
                            tension: 0.4,
                            fill: true,
                            pointRadius: isTiny ? 2 : (isSmall ? 3 : 4),
                            pointHoverRadius: isTiny ? 4 : (isSmall ? 5 : 7),
                            pointBackgroundColor: '#fff',
                            pointBorderColor: successColor,
                            pointBorderWidth: 2,
                            pointHoverBackgroundColor: successColor
                        },
                        {
                            label: 'باقی‌مانده فعال',
                            data: trend.pending,
                            borderColor: warningColor,
                            backgroundColor: gradientPending,
                            borderWidth: isSmall ? 2 : 2.5,
                            tension: 0.4,
                            fill: true,
                            pointRadius: isTiny ? 2 : (isSmall ? 3 : 4),
                            pointHoverRadius: isTiny ? 4 : (isSmall ? 5 : 7),
                            pointBackgroundColor: '#fff',
                            pointBorderColor: warningColor,
                            pointBorderWidth: 2,
                            pointHoverBackgroundColor: warningColor
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {mode: 'index', intersect: false},
                    layout: {
                        padding: {
                            top: 8,
                            right: isSmall ? 6 : 12,
                            bottom: 4,
                            left: isSmall ? 4 : 8
                        }
                    },
                    plugins: {
                        legend: {
                            position: isSmall ? 'bottom' : 'top',
                            rtl: true,
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                boxWidth: isSmall ? 8 : 10,
                                boxHeight: isSmall ? 8 : 10,
                                padding: isSmall ? 10 : 16,
                                color: '#2d3e4a',
                                font: {
                                    family: 'Vazirmatn, Tahoma, Arial, sans-serif',
                                    size: isTiny ? 10 : (isSmall ? 11 : 12),
                                    weight: '600'
                                }
                            }
                        },
                        tooltip: {enabled: false}
                    },
                    scales: {
                        x: {
                            grid: {display: false},
                            ticks: {
                                color: '#6b7d8a',
                                font: {
                                    family: 'Vazirmatn, Tahoma, Arial, sans-serif',
                                    size: isTiny ? 9 : (isSmall ? 10 : 11),
                                    weight: '600'
                                },
                                maxRotation: isSmall ? 45 : 0,
                                autoSkip: true,
                                maxTicksLimit: isSmall ? 7 : 14
                            },
                            border: {display: false}
                        },
                        y: {
                            beginAtZero: true,
                            grid: {color: 'rgba(27, 105, 139, 0.06)'},
                            ticks: {
                                color: '#6b7d8a',
                                font: {
                                    family: 'Vazirmatn, Tahoma, Arial, sans-serif',
                                    size: isTiny ? 9 : (isSmall ? 10 : 11)
                                },
                                precision: 0,
                                maxTicksLimit: 6,
                                callback: function (value) {
                                    return Number(value).toLocaleString('fa-IR');
                                }
                            },
                            border: {display: false}
                        }
                    },
                    animation: {duration: 1000, easing: 'easeOutQuart'}
                }
            });

            canvas.onclick = function (event) {
                const points = monthlyTrendChart.getElementsAtEventForMode(
                    event, 'index', {intersect: false}, true
                );

                if (points.length > 0) {
                    event.stopPropagation();
                    showTooltipAtPoint(monthlyTrendChart, points[0].index, event);
                } else {
                    hideTooltip();
                }
            };
        }

        // ============================================================
        // ★ TIME RANGE SLIDER (BRUSH)
        // ============================================================
        function initBrushFromData() {
            const perDept = currentData.monthly_per_department;
            let months = [];
            let monthsShort = [];

            if (perDept && perDept.months && perDept.months.length > 0) {
                months = perDept.months;
                monthsShort = perDept.months_short || perDept.months;
            } else if (currentData.monthly_trend && currentData.monthly_trend.labels) {
                months = currentData.monthly_trend.labels;
                monthsShort = months.map(function (m) {
                    return m.split(' ')[0].substring(0, 3);
                });
            }

            if (!months || months.length === 0) {
                const section = document.getElementById('timeRangeSection');
                if (section) section.style.display = 'none';
                return;
            }

            brushState.months = months.slice();
            brushState.monthsShort = monthsShort.slice();
            brushState.hasData = true;
            brushState.initialized = false;

            brushState.from = 0;
            brushState.to = months.length - 1;

            renderBrushLabels(monthsShort);
            renderBrushTicks(months.length);

            const section = document.getElementById('timeRangeSection');
            if (section) section.style.display = 'block';

            setTimeout(function () {
                updateBrushUI();
                if (!brushState.initialized) {
                    bindBrushEvents();
                    brushState.initialized = true;
                }
            }, 50);
        }

        function renderBrushLabels(months) {
            const labelsEl = document.getElementById('dpBrushLabels');
            if (!labelsEl) return;
            labelsEl.innerHTML = months.map((m, i) =>
                `<span class="dp-brush-label" data-idx="${i}">${m}</span>`
            ).join('');
        }

        function renderBrushTicks(count) {
            const ticksEl = document.getElementById('dpBrushTicks');
            if (!ticksEl) return;
            ticksEl.innerHTML = Array.from({length: count})
                .map(() => '<span class="dp-brush-tick"></span>')
                .join('');
        }

        function updateBrushUI() {
            const brush = document.getElementById('dpBrush');
            if (!brush) return;

            const total = brushState.months.length;
            if (total === 0) return;

            const brushWidth = brush.clientWidth;
            const stepWidth = brushWidth / Math.max(1, total - 1);

            const fromX = brushState.from * stepWidth;
            const toX = brushState.to * stepWidth;

            const thumbFrom = document.getElementById('dpBrushThumbFrom');
            if (thumbFrom) thumbFrom.style.left = fromX + 'px';

            const thumbTo = document.getElementById('dpBrushThumbTo');
            if (thumbTo) thumbTo.style.left = toX + 'px';

            const range = document.getElementById('dpBrushRange');
            if (range) {
                range.style.left = Math.min(fromX, toX) + 'px';
                range.style.width = Math.abs(toX - fromX) + 'px';
            }

            document.querySelectorAll('.dp-brush-label').forEach(function (el, i) {
                el.classList.toggle('in-range', i >= brushState.from && i <= brushState.to);
            });

            document.querySelectorAll('.dp-brush-tick').forEach(function (el, i) {
                el.classList.toggle('in-range', i >= brushState.from && i <= brushState.to);
            });

            const fromEl = document.getElementById('brushValueFrom');
            const toEl = document.getElementById('brushValueTo');
            if (fromEl) fromEl.textContent = brushState.months[brushState.from] || '—';
            if (toEl) toEl.textContent = brushState.months[brushState.to] || '—';

            const countText = document.getElementById('brushCountText');
            const count = brushState.to - brushState.from + 1;
            if (countText) {
                countText.textContent = count.toLocaleString('fa-IR') + ' ماه';
            }

            updateFilterRangeInfo();
        }

        function updateFilterRangeInfo() {
            const rangeItem = document.getElementById('trendFilterRangeItem');
            const rangeEl = document.getElementById('trendFilterRange');
            const infoBox = document.getElementById('trendFilterInfo');

            if (!rangeItem || !rangeEl) return;

            const totalMonths = brushState.months.length;
            const selected = brushState.to - brushState.from + 1;
            const isAll = (brushState.from === 0 && brushState.to === totalMonths - 1);

            if (!isAll && selected > 0) {
                const fromLabel = brushState.months[brushState.from] || '';
                const toLabel = brushState.months[brushState.to] || '';
                rangeEl.textContent = fromLabel + ' تا ' + toLabel;
                rangeItem.style.display = 'inline-flex';
                if (infoBox) infoBox.style.display = 'flex';
            } else {
                rangeItem.style.display = 'none';

                const yearItem = document.getElementById('trendFilterYearItem');
                const deptItem = document.getElementById('trendFilterDeptItem');
                const hasYear = yearItem && yearItem.style.display !== 'none';
                const hasDept = deptItem && deptItem.style.display !== 'none';
                if (!hasYear && !hasDept && infoBox) {
                    infoBox.style.display = 'none';
                }
            }
        }

        function bindBrushEvents() {
            const brush = document.getElementById('dpBrush');
            if (!brush) return;

            const thumbFrom = document.getElementById('dpBrushThumbFrom');
            const thumbTo = document.getElementById('dpBrushThumbTo');

            function getIndexFromX(clientX) {
                const rect = brush.getBoundingClientRect();
                const x = clientX - rect.left;
                const total = brushState.months.length;
                if (total < 2) return 0;
                const stepWidth = rect.width / (total - 1);
                let idx = Math.round(x / stepWidth);
                return Math.max(0, Math.min(total - 1, idx));
            }

            function onPointerMove(e) {
                if (!brushState.dragging) return;
                const idx = getIndexFromX(e.clientX);

                if (brushState.dragging === 'from') {
                    brushState.from = Math.min(idx, brushState.to);
                } else {
                    brushState.to = Math.max(idx, brushState.from);
                }

                updateBrushUI();
            }

            function onPointerUp() {
                if (!brushState.dragging) return;
                brushState.dragging = null;
                brush.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                window.removeEventListener('pointermove', onPointerMove);
                window.removeEventListener('pointerup', onPointerUp);

                applyTimeRangeFilter();
            }

            function startDrag(which) {
                return function (e) {
                    e.preventDefault();
                    brushState.dragging = which;
                    brush.classList.add('dragging');
                    document.body.style.cursor = 'grabbing';
                    document.body.style.userSelect = 'none';
                    window.addEventListener('pointermove', onPointerMove);
                    window.addEventListener('pointerup', onPointerUp);
                };
            }

            if (thumbFrom) thumbFrom.addEventListener('pointerdown', startDrag('from'));
            if (thumbTo) thumbTo.addEventListener('pointerdown', startDrag('to'));

            const track = brush.querySelector('.dp-brush-track');
            if (track) {
                track.addEventListener('click', function (e) {
                    const idx = getIndexFromX(e.clientX);
                    const distFrom = Math.abs(idx - brushState.from);
                    const distTo = Math.abs(idx - brushState.to);

                    if (distFrom < distTo) {
                        brushState.from = Math.min(idx, brushState.to);
                    } else {
                        brushState.to = Math.max(idx, brushState.from);
                    }
                    updateBrushUI();
                    applyTimeRangeFilter();
                });
            }

            const resetBtn = document.getElementById('brushResetBtn');
            if (resetBtn) {
                resetBtn.addEventListener('click', function () {
                    brushState.from = 0;
                    brushState.to = brushState.months.length - 1;
                    updateBrushUI();
                    applyTimeRangeFilter();
                });
            }
        }

        // ============================================================
        // ★ اعمال بازه روی رتبه‌بندی + نمودار
        // ============================================================
        function applyTimeRangeFilter() {
            const perDept = currentData.monthly_per_department;

            const from = brushState.from;
            const to = brushState.to;

            updateTrendChartForRange(from, to);

            if (perDept && perDept.departments && perDept.departments.length > 0) {
                const computed = perDept.departments.map(function (dept) {
                    let effective = 0;
                    let completed = 0;
                    let pending = 0;

                    for (let i = from; i <= to; i++) {
                        const m = dept.monthly && dept.monthly[i];
                        if (!m) continue;
                        effective += Number(m.effective || 0);
                        completed += Number(m.completed || 0);
                        pending += Number(m.pending || 0);
                    }

                    return {
                        department_id: dept.id,
                        department_title: dept.title,
                        effective_total: effective,
                        completed: completed,
                        pending: pending,
                        excluded: Number(dept.excluded_total || 0),
                        completion_rate: effective > 0 ? (completed / effective) * 100 : 0,
                        _volume: effective
                    };
                });

                const maxVolume = Math.max.apply(null, computed.map(function (c) {
                    return c._volume;
                }).concat([1]));

                computed.forEach(function (c) {
                    const volumeScore = (c._volume / maxVolume) * 100;
                    c.score = (c.completion_rate * 0.6) + (volumeScore * 0.4);
                    c.normalized_volume = volumeScore;
                });

                computed.sort(function (a, b) {
                    return b.score - a.score;
                });

                const filtered = computed.filter(function (c) {
                    return c.effective_total > 0;
                });

                animateRankingUpdate(filtered);

                const subtitle = document.getElementById('rankingSubtitle');
                if (subtitle) {
                    const totalMonths = brushState.months.length;
                    const isAll = (from === 0 && to === totalMonths - 1);
                    if (isAll) {
                        subtitle.textContent = 'بر اساس امتیاز عملکرد (کل دوره)';
                    } else {
                        subtitle.textContent = 'بازه: ' +
                            (brushState.months[from] || '') + ' تا ' +
                            (brushState.months[to] || '');
                    }
                }
            }
        }

        function updateTrendChartForRange(from, to) {
            if (!monthlyTrendChart) return;
            const trend = currentData.monthly_trend;
            if (!trend || !trend.labels) return;

            if (!monthlyTrendChart._fullData) {
                monthlyTrendChart._fullData = {
                    labels: trend.labels.slice(),
                    total: trend.total.slice(),
                    completed: trend.completed.slice(),
                    pending: trend.pending.slice()
                };
            }

            const full = monthlyTrendChart._fullData;

            const slicedLabels = full.labels.slice(from, to + 1);
            const slicedTotal = full.total.slice(from, to + 1);
            const slicedCompleted = full.completed.slice(from, to + 1);
            const slicedPending = full.pending.slice(from, to + 1);

            monthlyTrendChart.data.labels = slicedLabels;
            monthlyTrendChart.data.datasets[0].data = slicedTotal;
            monthlyTrendChart.data.datasets[1].data = slicedCompleted;
            monthlyTrendChart.data.datasets[2].data = slicedPending;

            const count = slicedLabels.length;
            const isSmall = window.innerWidth <= 576;
            const maxTicks = count <= 6 ? count : (isSmall ? 6 : 12);
            monthlyTrendChart.options.scales.x.ticks.maxTicksLimit = maxTicks;

            monthlyTrendChart.update('active');
        }

        // ============================================================
        // ★ FLIP Animation
        // ============================================================
        function animateRankingUpdate(newRanking) {
            const listEl = document.getElementById('rankingList');
            if (!listEl) return;

            const currentPositions = {};
            Array.from(listEl.children).forEach(function (el) {
                const key = el.dataset.key;
                if (key) {
                    currentPositions[key] = el.getBoundingClientRect();
                }
            });

            renderRankingList(newRanking, false);

            requestAnimationFrame(function () {
                Array.from(listEl.children).forEach(function (el) {
                    const key = el.dataset.key;
                    if (!key) return;

                    const oldRect = currentPositions[key];
                    const newRect = el.getBoundingClientRect();

                    if (oldRect) {
                        const deltaY = oldRect.top - newRect.top;
                        const deltaX = oldRect.left - newRect.left;

                        if (Math.abs(deltaY) > 1 || Math.abs(deltaX) > 1) {
                            el.style.transition = 'none';
                            el.style.transform = `translate(${deltaX}px, ${deltaY}px)`;

                            void el.offsetHeight;

                            requestAnimationFrame(function () {
                                el.style.transition = 'transform .75s cubic-bezier(.25, .46, .45, .94)';
                                el.style.transform = 'translate(0, 0)';
                            });
                        }
                    }
                });
            });
        }

        // ============================================================
        // ★ رسم لیست رتبه‌بندی
        // ============================================================
        function renderRanking(ranking, animate) {
            previousRanks = {};
            renderRankingList(ranking, animate);
        }

        function renderRankingList(ranking, animate) {
            const listEl = document.getElementById('rankingList');
            if (!listEl) return;

            if (!ranking || ranking.length === 0) {
                listEl.innerHTML =
                    '<div class="dp-empty">' +
                    '<i class="fa-solid fa-ranking-star"></i>' +
                    '<h3>داده‌ای برای رتبه‌بندی وجود ندارد</h3>' +
                    '<p>بازه زمانی بزرگ‌تری را انتخاب کنید</p>' +
                    '</div>';
                listEl._currentRanking = [];
                return;
            }

            const maxScore = Math.max.apply(null, ranking.map(function (r) {
                return r.score || 0;
            }).concat([1]));

            const items = ranking.map(function (item, idx) {
                const rank = idx + 1;
                const score = Number(item.score || 0);
                const rate = Number(item.completion_rate || 0);
                const effective = Number(item.effective_total || 0);
                const completed = Number(item.completed || 0);
                const pending = Number(item.pending || 0);

                const color = getScoreColor(score);
                const progressPercent = Math.min(100, (score / Math.max(1, maxScore)) * 100);

                let changeBadge = '';
                const key = item.department_title || ('dept-' + idx);

                if (previousRanks[key] !== undefined) {
                    const diff = previousRanks[key] - rank;
                    if (diff > 0) {
                        changeBadge = `<span class="dp-rank-change-badge up">
                            <i class="fa-solid fa-arrow-up"></i> ${diff.toLocaleString('fa-IR')}
                        </span>`;
                    } else if (diff < 0) {
                        changeBadge = `<span class="dp-rank-change-badge down">
                            <i class="fa-solid fa-arrow-down"></i> ${Math.abs(diff).toLocaleString('fa-IR')}
                        </span>`;
                    }
                }

                previousRanks[key] = rank;

                const medalIcon = rank === 1 ? '<i class="fa-solid fa-crown"></i>' :
                    rank === 2 ? '<i class="fa-solid fa-medal"></i>' :
                        rank === 3 ? '<i class="fa-solid fa-award"></i>' :
                            rank;

                return `
                    <div class="dp-rank-item"
                         data-rank="${rank}"
                         data-key="${escapeAttr(key)}"
                         style="--rank-color: ${color};">
                        ${changeBadge}
                        <div class="dp-rank-medal">${medalIcon}</div>
                        <div class="dp-rank-info">
                            <div class="dp-rank-name" title="${escapeAttr(item.department_title || '')}">
                                ${escapeHtml(item.department_title || 'نامشخص')}
                            </div>
                            <div class="dp-rank-meta">
                                <span class="dp-rank-meta-item">
                                    <i class="fa-solid fa-percent"></i>
                                    نرخ: <strong>${rate.toFixed(1)}٪</strong>
                                </span>
                                <span class="dp-rank-meta-item">
                                    <i class="fa-solid fa-layer-group"></i>
                                    مؤثر: <strong>${effective.toLocaleString('fa-IR')}</strong>
                                </span>
                                <span class="dp-rank-meta-item">
                                    <i class="fa-solid fa-circle-check"></i>
                                    تکمیل: <strong>${completed.toLocaleString('fa-IR')}</strong>
                                </span>
                            </div>
                            <div class="dp-rank-progress">
                                <div class="dp-rank-progress-bar" style="width: ${progressPercent}%;"></div>
                            </div>
                        </div>
                        <div class="dp-rank-score">
                            <span class="dp-rank-score-number">${score.toFixed(1)}</span>
                            <span class="dp-rank-score-label">امتیاز</span>
                        </div>
                    </div>
                `;
            }).join('');

            listEl.innerHTML = items;

            if (animate) {
                Array.from(listEl.children).forEach(function (el, i) {
                    el.style.animation = `dpRankEnter .5s cubic-bezier(.25, .46, .45, .94) ${Math.min(i * 40, 400)}ms both`;
                });
            }

            Array.from(listEl.children).forEach(function (el) {
                const idx = parseInt(el.dataset.rank, 10) - 1;
                el.addEventListener('click', function (e) {
                    if (e.target.closest('.dp-rank-change-badge')) return;

                    const currentRanking = listEl._currentRanking;
                    if (!currentRanking || !currentRanking[idx]) return;

                    e.stopPropagation();

                    const tooltipEl = document.getElementById('dp-chart-tooltip');
                    if (tooltipEl && tooltipEl.classList.contains('visible') &&
                        el.classList.contains('dp-rank-clicked')) {
                        hideTooltip();
                        el.classList.remove('dp-rank-clicked');
                        return;
                    }

                    showRankingTooltip(currentRanking[idx], e, el);
                });
            });

            listEl._currentRanking = ranking.slice();
        }

        function escapeHtml(str) {
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function escapeAttr(str) {
            return escapeHtml(str);
        }

        // ============================================================
        // ★ Modals
        // ============================================================
        function bindModals() {
            const pendingModal = document.getElementById('pendingModal');
            const pendingClose = document.getElementById('pendingModalClose');
            const pendingCard = document.getElementById('pendingCard');

            if (pendingCard && pendingModal) {
                pendingCard.addEventListener('click', function () {
                    pendingModal.classList.add('show');
                    renderStatusModal(currentData.summary, 'pending',
                        'pendingStatusList', 'pendingModalTotal');
                    document.body.style.overflow = 'hidden';
                });
            }

            if (pendingClose) {
                pendingClose.addEventListener('click', function () {
                    pendingModal.classList.remove('show');
                    document.body.style.overflow = '';
                });
            }

            if (pendingModal) {
                pendingModal.addEventListener('click', function (e) {
                    if (e.target === pendingModal) {
                        pendingModal.classList.remove('show');
                        document.body.style.overflow = '';
                    }
                });
            }

            const exclModal = document.getElementById('excludedModal');
            const exclClose = document.getElementById('excludedModalClose');
            const exclCard = document.getElementById('excludedCard');

            if (exclCard && exclModal) {
                exclCard.addEventListener('click', function () {
                    exclModal.classList.add('show');
                    renderStatusModal(currentData.summary, 'excluded',
                        'excludedStatusList', 'excludedModalTotal');
                    document.body.style.overflow = 'hidden';
                });
            }

            if (exclClose) {
                exclClose.addEventListener('click', function () {
                    exclModal.classList.remove('show');
                    document.body.style.overflow = '';
                });
            }

            if (exclModal) {
                exclModal.addEventListener('click', function (e) {
                    if (e.target === exclModal) {
                        exclModal.classList.remove('show');
                        document.body.style.overflow = '';
                    }
                });
            }

            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') {
                    pendingModal && pendingModal.classList.remove('show');
                    exclModal && exclModal.classList.remove('show');
                    document.body.style.overflow = '';
                }
            });
        }

        function renderStatusModal(summary, category, listId, totalId) {
            const list = document.getElementById(listId);
            const totalEl = document.getElementById(totalId);
            if (!list || !summary) return;

            const items = (summary.status_breakdown || []).filter(
                item => item.category === category
            );

            if (items.length === 0) {
                list.innerHTML =
                    '<div class="dp-empty" style="padding: 30px 20px;">' +
                    '<i class="fa-solid fa-inbox" style="color: #94a3b8;"></i>' +
                    '<h3>موردی یافت نشد</h3>' +
                    '</div>';
                if (totalEl) totalEl.textContent = '0';
                return;
            }

            const icons = {
                'in_progress': 'fa-spinner',
                'deleted': 'fa-trash',
                'stopped': 'fa-circle-pause',
                'informational': 'fa-circle-info',
                'unknown': 'fa-file'
            };

            list.innerHTML = items.map(function (item) {
                return `
                    <div class="dp-status-item" style="--item-color: ${item.color};">
                        <div class="dp-status-item-icon">
                            <i class="fa-solid ${icons[item.code] || 'fa-file'}"></i>
                        </div>
                        <div class="dp-status-item-content">
                            <span class="dp-status-item-title">${escapeHtml(item.title)}</span>
                        </div>
                        <div class="dp-status-item-count">
                            ${Number(item.count).toLocaleString('fa-IR')}
                        </div>
                    </div>
                `;
            }).join('');

            const total = items.reduce((sum, item) => sum + Number(item.count || 0), 0);
            if (totalEl) totalEl.textContent = total.toLocaleString('fa-IR');
        }

        // ============================================================
        // ★ Resize
        // ============================================================
        let resizeTimer = null;
        let lastWidth = window.innerWidth;

        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () {
                const newWidth = window.innerWidth;
                const modeChanged =
                    (lastWidth <= 576 && newWidth > 576) ||
                    (lastWidth > 576 && newWidth <= 576);

                lastWidth = newWidth;

                if (modeChanged && currentData.monthly_trend) {
                    hideTooltip();
                    renderMonthlyTrend(currentData.monthly_trend);
                    setTimeout(function () {
                        updateTrendChartForRange(brushState.from, brushState.to);
                    }, 100);
                }

                updateBrushUI();
            }, 250);
        });

    })();
