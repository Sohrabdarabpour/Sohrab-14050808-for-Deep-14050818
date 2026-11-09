// اسکریپت صفحه: departments/view.html

    (function () {
        'use strict';

        document.addEventListener('DOMContentLoaded', function () {

            const searchInput = document.getElementById('expertSearch');
            const statusFilter = document.getElementById('expertStatusFilter');
            const activeStatusFilter = document.getElementById('activeStatusFilter');
            const yearFilter = document.getElementById('yearFilter');
            const monthFilter = document.getElementById('monthFilter');
            const clearButton = document.getElementById('clearExpertFilters');
            const cards = Array.from(document.querySelectorAll('.dv-expert-card'));
            const visibleExperts = document.getElementById('visibleExperts');
            const noFilterResult = document.getElementById('noFilterResult');

            const showAllToggle = document.getElementById('showAllExpertsToggle');
            const showAllCheckbox = document.getElementById('showAllExpertsCheckbox');

            const expertsData = JSON.parse(document.getElementById('expertsDataJson').textContent);

            // ============================================
            // پالت رنگ
            // ============================================
            const EXPERT_COLORS = [
                {base: '#1b698b', light: '#3d8bb5'},
                {base: '#167a5c', light: '#2aa07a'},
                {base: '#d69e2e', light: '#e8b94a'},
                {base: '#c05621', light: '#dd7a3d'},
                {base: '#4a5568', light: '#6b7a8f'},
                {base: '#2b6cb0', light: '#3d8ad4'},
                {base: '#319795', light: '#4fc3c0'},
                {base: '#805ad5', light: '#9f7ae8'},
                {base: '#718096', light: '#8fa0b5'},
                {base: '#2f855a', light: '#4aa876'}
            ];

            cards.forEach(function (card, index) {
                const color = EXPERT_COLORS[index % EXPERT_COLORS.length];
                card.style.setProperty('--ex-color', color.base);
                card.style.setProperty('--ex-color-light', color.light);
            });

            // ============================================
            // فیلتر سال
            // ============================================
            if (yearFilter) {
                yearFilter.addEventListener('change', function () {
                    const url = new URL(window.location.href);
                    const yearVal = this.value;

                    if (yearVal === 'all') {
                        url.searchParams.delete('year');
                        url.searchParams.delete('month');
                    } else {
                        url.searchParams.set('year', yearVal);
                        url.searchParams.delete('month');
                    }
                    window.location.href = url.toString();
                });
            }

            // ============================================
            // فیلتر ماه
            // ============================================
            if (monthFilter) {
                monthFilter.addEventListener('change', function () {
                    const url = new URL(window.location.href);
                    const yearVal = yearFilter?.value || 'all';
                    const monthVal = this.value;

                    if (yearVal !== 'all') {
                        url.searchParams.set('year', yearVal);
                    }

                    if (monthVal === 'all') {
                        url.searchParams.delete('month');
                    } else {
                        url.searchParams.set('month', monthVal);
                    }
                    window.location.href = url.toString();
                });
            }

            // ============================================
            // فیلتر کارشناسان
            // ============================================
            function filterExperts() {
                const search = (searchInput?.value || '').trim().toLowerCase();
                const status = statusFilter?.value || 'all';
                const activeStatus = activeStatusFilter?.value || 'all';
                let visibleCount = 0;
                let activeCount = 0;
                let inactiveCount = 0;

                cards.forEach(function (card) {
                    const name = card.dataset.name || '';
                    const cardStatus = card.dataset.status || '';
                    const cardActive = card.dataset.active || '';

                    const matchesSearch = !search || name.includes(search);
                    const matchesStatus = status === 'all' || cardStatus === status;
                    const matchesActive = activeStatus === 'all' || cardActive === activeStatus;
                    const visible = matchesSearch && matchesStatus && matchesActive;

                    card.style.display = visible ? 'flex' : 'none';
                    if (visible) {
                        visibleCount++;
                        if (cardActive === 'active') activeCount++;
                        else if (cardActive === 'inactive') inactiveCount++;
                    }
                });

                if (visibleExperts) visibleExperts.textContent = visibleCount;
                if (noFilterResult) {
                    noFilterResult.style.display = visibleCount ? 'none' : 'block';
                }

                const activeEl = document.getElementById('activeCount');
                const inactiveEl = document.getElementById('inactiveCount');
                if (activeEl) activeEl.textContent = activeCount;
                if (inactiveEl) inactiveEl.textContent = inactiveCount;
            }

            searchInput?.addEventListener('input', filterExperts);
            statusFilter?.addEventListener('change', filterExperts);
            activeStatusFilter?.addEventListener('change', filterExperts);

            // ============================================
            // پاک کردن فیلترها
            // ============================================
            clearButton?.addEventListener('click', function () {
                if (searchInput) searchInput.value = '';
                if (statusFilter) statusFilter.value = 'all';
                if (activeStatusFilter) activeStatusFilter.value = 'all';
                if (yearFilter) yearFilter.value = 'all';
                if (monthFilter) monthFilter.value = 'all';
                filterExperts();

                const url = new URL(window.location.href);
                let changed = false;
                if (url.searchParams.has('year')) {
                    url.searchParams.delete('year');
                    changed = true;
                }
                if (url.searchParams.has('month')) {
                    url.searchParams.delete('month');
                    changed = true;
                }
                if (changed) {
                    window.location.href = url.toString();
                }
            });

            // ============================================
            // آپدیت خودکار وضعیت آنلاین
            // ============================================
            function updateOnlineStatus() {
                fetch('/panel/users/online-status', {
                    method: 'GET',
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                    .then(function (res) {
                        if (!res.ok) throw new Error('Network error');
                        return res.json();
                    })
                    .then(function (data) {
                        Object.keys(data).forEach(function (userId) {
                            const isOnline = data[userId];
                            const dot = document.querySelector(
                                '.dv-expert-status[data-user-id="' + userId + '"]'
                            );
                            if (dot) {
                                dot.classList.toggle('offline', !isOnline);
                            }

                            const card = document.querySelector(
                                '.dv-expert-card:has(.dv-expert-status[data-user-id="' + userId + '"])'
                            );
                            if (card) {
                                card.dataset.status = isOnline ? 'active' : 'inactive';
                            }
                        });

                        if (statusFilter?.value !== 'all') {
                            filterExperts();
                        }
                    })
                    .catch(function (err) {
                        console.warn('خطا در آپدیت وضعیت آنلاین:', err);
                    });
            }

            setTimeout(updateOnlineStatus, 800);
            setInterval(updateOnlineStatus, 5000);

            // ============================================
            // نمودار میله‌ای
            // ============================================
            let pendingChartInstance = null;

            function initializePendingChart() {
                const canvas = document.getElementById('pendingChart');
                if (!canvas || typeof Chart === 'undefined') return;

                const PENDING_STATUS_CODE = 'in_progress';
                const showAll = showAllCheckbox ? showAllCheckbox.checked : false;

                let chartData = expertsData.map(function (expert) {
                    const pendingItem = (expert.status_counts || [])
                        .find(function (st) { return st.code === PENDING_STATUS_CODE; });
                    return {
                        name: expert.full_name || 'بدون نام',
                        count: pendingItem ? Number(pendingItem.count || 0) : 0
                    };
                });

                if (!showAll) {
                    chartData = chartData.filter(function (item) { return item.count > 0; });
                }

                chartData.sort(function (a, b) { return b.count - a.count; });

                const totalPending = chartData.reduce(function (sum, item) {
                    return sum + item.count;
                }, 0);

                const totalEl = document.getElementById('pendingTotalCount');
                if (totalEl) totalEl.textContent = totalPending.toLocaleString('fa-IR');

                if (chartData.length === 0) {
                    const wrapper = canvas.parentElement;
                    if (wrapper) {
                        wrapper.innerHTML =
                            '<div style="display:flex;flex-direction:column;align-items:center;' +
                            'justify-content:center;height:100%;color:#a0aeb8;text-align:center;gap:8px;">' +
                            '<i class="fa-solid fa-mug-hot" style="font-size:2rem;opacity:.5;"></i>' +
                            '<span style="font-size:.85rem;">' +
                            (showAll ? 'هیچ کارشناسی در این دپارتمان وجود ندارد' : 'هیچ کار در دست بررسی‌ای وجود ندارد') +
                            '</span></div>';
                    }
                    return;
                }

                const wrapper = canvas.parentElement;
                if (wrapper && !wrapper.querySelector('canvas')) {
                    wrapper.innerHTML = '<canvas id="pendingChart"></canvas>';
                }
                const newCanvas = document.getElementById('pendingChart');

                if (wrapper) {
                    const perItemHeight = 42;
                    const dynamicHeight = Math.max(240, chartData.length * perItemHeight + 60);
                    wrapper.style.height = Math.min(dynamicHeight, 700) + 'px';
                }

                const maxCount = Math.max.apply(null, chartData.map(function (d) { return d.count; }));

                function getBarColor(value) {
                    const t = maxCount > 0 ? value / maxCount : 0;
                    const r = Math.round(214 + (1 - t) * 20);
                    const g = Math.round(158 - (1 - t) * 40);
                    const b = Math.round(46 + (1 - t) * 60);
                    return 'rgba(' + r + ', ' + g + ', ' + b + ', 0.9)';
                }

                if (pendingChartInstance) {
                    pendingChartInstance.destroy();
                    pendingChartInstance = null;
                }

                pendingChartInstance = new Chart(newCanvas, {
                    type: 'bar',
                    data: {
                        labels: chartData.map(function (d) { return d.name; }),
                        datasets: [{
                            label: 'کار در دست بررسی',
                            data: chartData.map(function (d) { return d.count; }),
                            backgroundColor: chartData.map(function (d) { return getBarColor(d.count); }),
                            borderColor: '#ffffff',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false,
                            barPercentage: 0.65,
                            categoryPercentage: 0.8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        layout: { padding: { top: 8, right: 20, bottom: 8, left: 8 } },
                        onClick: function (event, elements) {
                            if (elements.length === 0) return;
                            const idx = elements[0].index;
                            const expertName = chartData[idx].name;
                            const target = cards.find(function (c) {
                                return (c.dataset.name || '').includes(expertName.toLowerCase());
                            });
                            if (target) {
                                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                target.style.outline = '3px solid #d69e2e';
                                target.style.outlineOffset = '4px';
                                setTimeout(function () {
                                    target.style.outline = '';
                                    target.style.outlineOffset = '';
                                }, 1600);
                            }
                        },
                        scales: {
                            x: {
                                beginAtZero: true,
                                ticks: { precision: 0, font: { family: 'Vazirmatn', size: 11 }, color: '#6b7d8a' },
                                grid: { color: 'rgba(27, 105, 139, 0.06)' },
                                border: { display: false }
                            },
                            y: {
                                ticks: { font: { family: 'Vazirmatn', size: 12, weight: '600' }, color: '#2d3e4a', autoSkip: false },
                                grid: { display: false },
                                border: { display: false }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                rtl: true,
                                backgroundColor: 'rgba(45, 52, 54, 0.95)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                titleFont: { family: 'Vazirmatn', size: 13, weight: '700' },
                                bodyFont: { family: 'Vazirmatn', size: 12 },
                                padding: 12,
                                cornerRadius: 10,
                                displayColors: false,
                                callbacks: {
                                    label: function (context) {
                                        const value = context.raw || 0;
                                        const percent = totalPending > 0
                                            ? Math.round((value / totalPending) * 100)
                                            : 0;
                                        return '⏳ ' + value + ' کار در جریان  (' + percent + '%)';
                                    }
                                }
                            }
                        },
                        animation: { duration: 900, easing: 'easeOutQuart' }
                    }
                });
            }

            if (showAllCheckbox) {
                showAllCheckbox.addEventListener('change', function () {
                    if (showAllToggle) {
                        showAllToggle.classList.toggle('active', this.checked);
                    }
                    setTimeout(initializePendingChart, 50);
                });
            }

            setTimeout(initializePendingChart, 100);

        });
    })();
