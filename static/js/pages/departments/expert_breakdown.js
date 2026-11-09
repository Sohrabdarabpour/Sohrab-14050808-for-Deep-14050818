// اسکریپت صفحه: departments/expert_breakdown.html

    (function () {
        'use strict';

        document.addEventListener('DOMContentLoaded', function () {

            if (typeof Chart === 'undefined') {
                console.warn('Chart.js لود نشده');
                return;
            }

            // ★ ثبت پلاگین DataLabels
            if (typeof ChartDataLabels !== 'undefined') {
                Chart.register(ChartDataLabels);
            }

            const dataEl = document.getElementById('breakdownDataJson');
            if (!dataEl) {
                console.warn('breakdownDataJson پیدا نشد');
                return;
            }

            const breakdownData = JSON.parse(dataEl.textContent);

            // ============================================
            // ★ پالت رنگی
            // ============================================
            const CHART_COLORS = [
                '#1b698b', '#167a5c', '#d69e2e', '#2b6cb0',
                '#319795', '#dd6b20', '#38a169', '#4299e1',
                '#b7791f', '#2c7a7b', '#c05621', '#4a5568',
                '#2f855a', '#90cdf4', '#e8b94a', '#4fd1c5',
            ];

            // ============================================
            // ★ تابع کمکی — پیدا کردن رنگ برای گروه
            // ============================================
            function getGroupColor(groupTitle) {
                const groups = breakdownData.groups || [];
                for (let i = 0; i < groups.length; i++) {
                    if (groups[i].title === groupTitle) {
                        if (groups[i].color) return groups[i].color;
                        return CHART_COLORS[i % CHART_COLORS.length];
                    }
                }
                return CHART_COLORS[0];
            }

            // ============================================
            // نمودار گروه‌ها (Doughnut)
            // ============================================
            function initGroupChart() {
                const canvas = document.getElementById('groupChart');
                if (!canvas) return;

                const labels = [];
                const values = [];
                const colors = [];

                (breakdownData.groups || []).forEach(function (g, idx) {
                    if (g.count > 0) {
                        labels.push(g.title);
                        values.push(g.count);
                        colors.push(
                            g.color || CHART_COLORS[idx % CHART_COLORS.length]
                        );
                    }
                });

                if (breakdownData.ungrouped && breakdownData.ungrouped.count > 0) {
                    labels.push(breakdownData.ungrouped.title);
                    values.push(breakdownData.ungrouped.count);
                    colors.push('#94a3b8');
                }

                if (values.length === 0) {
                    canvas.parentElement.innerHTML =
                        '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#94a3b8;gap:8px;">' +
                        '<i class="fa-solid fa-chart-pie" style="font-size:2rem;opacity:.4;"></i>' +
                        '<span style="font-size:.85rem;">داده‌ای برای نمایش نیست</span></div>';
                    return;
                }

                const total = values.reduce(function (a, b) { return a + b; }, 0);

                new Chart(canvas, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors,
                            borderColor: '#ffffff',
                            borderWidth: 3,
                            hoverOffset: 10,
                            hoverBorderWidth: 3,
                            hoverBorderColor: '#ffffff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '58%',
                        layout: {
                            padding: { top: 10, bottom: 10, left: 10, right: 10 }
                        },
                        plugins: {
                            legend: {
                                position: 'bottom',
                                rtl: true,
                                labels: {
                                    font: {
                                        family: 'Vazirmatn',
                                        size: 12,
                                        weight: '600'
                                    },
                                    color: '#334155',
                                    padding: 14,
                                    usePointStyle: true,
                                    pointStyle: 'circle',
                                    boxWidth: 10,
                                    boxHeight: 10
                                }
                            },

                            datalabels: {
                                color: '#ffffff',
                                textShadowColor: 'rgba(0, 0, 0, 0.35)',
                                textShadowBlur: 4,
                                font: {
                                    family: 'Vazirmatn',
                                    size: 13,
                                    weight: '800'
                                },
                                formatter: function (value) {
                                    const percent = total > 0
                                        ? Math.round((value / total) * 100)
                                        : 0;
                                    if (percent < 5) return '';
                                    return value;
                                },
                                anchor: 'center',
                                align: 'center',
                                display: function (context) {
                                    const value = context.dataset.data[context.dataIndex];
                                    const percent = total > 0
                                        ? (value / total) * 100
                                        : 0;
                                    return percent >= 5;
                                }
                            },

                            tooltip: {
                                rtl: true,
                                backgroundColor: 'rgba(15, 23, 42, 0.96)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                titleFont: {
                                    family: 'Vazirmatn',
                                    size: 13,
                                    weight: '700'
                                },
                                bodyFont: {
                                    family: 'Vazirmatn',
                                    size: 12
                                },
                                padding: 14,
                                cornerRadius: 12,
                                displayColors: true,
                                boxPadding: 6,
                                borderColor: 'rgba(255, 255, 255, 0.1)',
                                borderWidth: 1,
                                callbacks: {
                                    label: function (context) {
                                        const value = context.raw || 0;
                                        const percent = total > 0
                                            ? ((value / total) * 100).toFixed(1)
                                            : 0;
                                        return ' ' + context.label + ': ' + value +
                                               ' کار (' + percent + '%)';
                                    }
                                }
                            }
                        },
                        animation: {
                            duration: 1000,
                            easing: 'easeOutQuart'
                        }
                    }
                });
            }

            // ============================================
            // ★★ نمودار زیرگروه‌ها (Bar افقی) — تجمیع‌شده ★★
            // ============================================
            function initSubgroupChart() {
                const canvas = document.getElementById('subgroupChart');
                if (!canvas) return;

                // ★ ساختار تجمیع
                // کلید = نام زیرگروه
                // مقدار = { title, total, groups: [{title, color, count}] }
                const subgroupMap = {};

                (breakdownData.groups || []).forEach(function (g) {
                    (g.subgroups || []).forEach(function (sg) {
                        if (sg.count > 0) {
                            const key = sg.title;

                            if (!subgroupMap[key]) {
                                subgroupMap[key] = {
                                    title: sg.title,
                                    total: 0,
                                    groups: [],
                                    color: g.color || getGroupColor(g.title)
                                };
                            }

                            subgroupMap[key].total += sg.count;
                            subgroupMap[key].groups.push({
                                title: g.title,
                                color: g.color || getGroupColor(g.title),
                                count: sg.count
                            });
                        }
                    });
                });

                // ★ تبدیل به آرایه و مرتب‌سازی نزولی
                const aggregated = Object.values(subgroupMap)
                    .sort(function (a, b) { return b.total - a.total; });

                if (aggregated.length === 0) {
                    canvas.parentElement.innerHTML =
                        '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#94a3b8;gap:8px;">' +
                        '<i class="fa-solid fa-chart-bar" style="font-size:2rem;opacity:.4;"></i>' +
                        '<span style="font-size:.85rem;">داده‌ای برای زیرگروه‌ها نیست</span></div>';
                    return;
                }

                // ★ برچسب‌ها — با نشانگر ● اگه چند گروه داشت
                const labels = aggregated.map(function (item) {
                    let title = item.title.length > 30
                        ? item.title.substring(0, 28) + '…'
                        : item.title;

                    if (item.groups.length > 1) {
                        title += ' ●';
                    }

                    return title;
                });

                const values = aggregated.map(function (item) {
                    return item.total;
                });

                // ★ رنگ هر میله
                const colors = aggregated.map(function (item, idx) {
                    return item.color || CHART_COLORS[idx % CHART_COLORS.length];
                });

                // ★ ارتفاع داینامیک
                const wrapper = canvas.parentElement;
                if (wrapper) {
                    const perItemHeight = 44;
                    const minHeight = 280;
                    const dynamicHeight = Math.max(
                        minHeight,
                        values.length * perItemHeight + 60
                    );
                    const maxHeight = 700;
                    wrapper.style.height = Math.min(dynamicHeight, maxHeight) + 'px';
                }

                new Chart(canvas, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors,
                            borderColor: colors,
                            borderWidth: 0,
                            borderRadius: 8,
                            borderSkipped: false,
                            barPercentage: 0.7,
                            categoryPercentage: 0.85,
                            hoverBackgroundColor: colors
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        layout: {
                            padding: {
                                top: 8,
                                right: 50,
                                bottom: 8,
                                left: 8
                            }
                        },
                        plugins: {
                            legend: { display: false },

                            // ★★ نمایش اعداد در انتهای میله‌ها ★★
                            datalabels: {
                                color: '#1e293b',
                                font: {
                                    family: 'Vazirmatn',
                                    size: 12,
                                    weight: '800'
                                },
                                anchor: 'end',
                                align: 'right',
                                offset: 6,
                                formatter: function (value) {
                                    return value;
                                },
                                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                                borderColor: 'rgba(148, 163, 184, 0.3)',
                                borderWidth: 1,
                                borderRadius: 6,
                                padding: {
                                    top: 3,
                                    bottom: 3,
                                    left: 8,
                                    right: 8
                                }
                            },

                            // ★★ Tooltip حرفه‌ای — نمایش گروه‌های دخیل ★★
                            tooltip: {
                                rtl: true,
                                backgroundColor: 'rgba(15, 23, 42, 0.96)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                titleFont: {
                                    family: 'Vazirmatn',
                                    size: 13,
                                    weight: '700'
                                },
                                bodyFont: {
                                    family: 'Vazirmatn',
                                    size: 11
                                },
                                padding: 14,
                                cornerRadius: 10,
                                displayColors: true,
                                callbacks: {
                                    title: function (context) {
                                        const idx = context[0].dataIndex;
                                        return aggregated[idx].title;
                                    },
                                    label: function (context) {
                                        const idx = context.dataIndex;
                                        const item = aggregated[idx];

                                        // ★ یه گروه
                                        if (item.groups.length === 1) {
                                            return [
                                                ' گروه: ' + item.groups[0].title,
                                                ' تعداد: ' + item.total + ' کار در جریان'
                                            ];
                                        }

                                        // ★ چند گروه
                                        const lines = [
                                            ' مجموع: ' + item.total + ' کار در جریان',
                                            '─────────────'
                                        ];

                                        item.groups
                                            .slice()
                                            .sort(function (a, b) { return b.count - a.count; })
                                            .forEach(function (grp) {
                                                lines.push(
                                                    ' ◾ ' + grp.title + ': ' + grp.count
                                                );
                                            });

                                        return lines;
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0,
                                    font: {
                                        family: 'Vazirmatn',
                                        size: 11,
                                        weight: '600'
                                    },
                                    color: '#64748b',
                                    padding: 8
                                },
                                grid: {
                                    color: 'rgba(148, 163, 184, 0.12)',
                                    drawBorder: false
                                },
                                border: {
                                    display: false
                                }
                            },
                            y: {
                                ticks: {
                                    font: {
                                        family: 'Vazirmatn',
                                        size: 11,
                                        weight: '600'
                                    },
                                    color: '#334155',
                                    autoSkip: false,
                                    padding: 6
                                },
                                grid: {
                                    display: false,
                                    drawBorder: false
                                },
                                border: {
                                    display: false
                                }
                            }
                        },
                        animation: {
                            duration: 1000,
                            easing: 'easeOutQuart'
                        }
                    }
                });
            }

            setTimeout(function () {
                initGroupChart();
                initSubgroupChart();
            }, 100);

        });
    })();
