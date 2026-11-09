// اسکریپت صفحه: panel/users.html

    (function () {
        'use strict';

        document.addEventListener('DOMContentLoaded', function () {

            const userCards = document.querySelectorAll('.usr-card');

            // ============================================
            // جستجوی کاربران
            // ============================================
            const searchInput = document.getElementById('userSearchInput');
            const searchClear = document.getElementById('userSearchClear');
            const searchInfo = document.getElementById('userSearchInfo');
            const searchCount = document.getElementById('userSearchCount');
            const searchQuery = document.getElementById('userSearchQuery');

            if (searchInput && searchClear) {
                let searchTimeout = null;
                const cardTextCache = new Map();

                userCards.forEach(function (card) {
                    const extra = card.getAttribute('data-search') || '';
                    const fullText = (card.textContent + ' ' + extra).toLowerCase();
                    cardTextCache.set(card, fullText);
                });

                function performSearch() {
                    const query = searchInput.value.trim().toLowerCase();
                    let visibleCount = 0;

                    userCards.forEach(function (card) {
                        const cardText = cardTextCache.get(card) || '';
                        const matches = query === '' || cardText.includes(query);

                        if (matches) {
                            card.style.display = '';
                            visibleCount++;
                        } else {
                            card.style.display = 'none';
                        }
                    });

                    if (query !== '') {
                        searchInfo.classList.add('visible');
                        searchCount.textContent = visibleCount;
                        searchQuery.textContent = query;
                        searchClear.classList.add('visible');
                    } else {
                        searchInfo.classList.remove('visible');
                        searchClear.classList.remove('visible');
                    }
                }

                searchInput.addEventListener('input', function () {
                    clearTimeout(searchTimeout);
                    searchTimeout = setTimeout(performSearch, 180);
                });

                searchClear.addEventListener('click', function () {
                    searchInput.value = '';
                    performSearch();
                    searchInput.focus();
                });

                document.addEventListener('keydown', function (e) {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                        e.preventDefault();
                        searchInput.focus();
                        searchInput.select();
                    }
                    if (e.key === 'Escape' && document.activeElement === searchInput) {
                        searchInput.blur();
                    }
                });
            }

            // ============================================
            // ★★★ کلیک روی کل کارت → صفحه جزئیات ★★★
            // ============================================
            userCards.forEach(function (card) {
                const href = card.getAttribute('data-href');
                if (!href) return;

                card.addEventListener('click', function (e) {
                    if (e.target.closest('.usr-btn') ||
                        e.target.closest('form') ||
                        e.target.closest('a')) {
                        return;
                    }
                    window.location.href = href;
                });

                card.setAttribute('tabindex', '0');
                card.setAttribute('role', 'link');
                card.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        window.location.href = href;
                    }
                });
            });

            // ============================================
            // ★★★ آپدیت خودکار وضعیت آنلاین/آفلاین ★★★
            // ============================================
            function updateOnlineStatus() {
                fetch('/panel/users/online-status', {
                    method: 'GET',
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                    .then(function (res) {
                        if (!res.ok) throw new Error('Network error');
                        return res.json();
                    })
                    .then(function (data) {
                        Object.keys(data).forEach(function (userId) {
                            const dot = document.querySelector(
                                `.usr-status-dot[data-user-id="${userId}"]`
                            );
                            if (!dot) return;

                            const isOnline = data[userId];
                            dot.classList.toggle('online', isOnline);
                            dot.classList.toggle('offline', !isOnline);
                            dot.setAttribute('title', isOnline ? 'آنلاین' : 'آفلاین');
                        });
                    })
                    .catch(function (err) {
                        console.warn('خطا در آپدیت وضعیت آنلاین:', err);
                    });
            }

            setTimeout(updateOnlineStatus, 800);
            setInterval(updateOnlineStatus, 5000);

            // ============================================
            // ★★★ ورود از اکسل (Import) ★★★
            // ============================================
            const importBtn = document.getElementById('usrImportBtn');
            const importForm = document.getElementById('usrImportForm');
            const importFile = document.getElementById('usrImportFile');

            if (importBtn && importForm && importFile) {
                // ★ کلیک روی دکمه → باز شدن پنجره انتخاب فایل
                importBtn.addEventListener('click', function () {
                    importFile.click();
                });

                // ★ انتخاب فایل → تأیید و ارسال
                importFile.addEventListener('change', function () {
                    if (this.files && this.files.length > 0) {
                        const fileName = this.files[0].name;

                        const confirmed = confirm(
                            `فایل «${fileName}» پردازش شود؟\n\n` +
                            `• ردیف‌هایی که «شناسه» دارند → بروزرسانی می‌شوند\n` +
                            `• ردیف‌های بدون «شناسه» → کاربر جدید ایجاد می‌کنند\n\n` +
                            `آیا مطمئن هستید؟`
                        );

                        if (confirmed) {
                            // ★ نمایش وضعیت بارگذاری روی دکمه
                            importBtn.disabled = true;
                            importBtn.innerHTML =
                                '<i class="fa-solid fa-spinner fa-spin"></i> در حال پردازش...';
                            importForm.submit();
                        } else {
                            this.value = ''; // ★ ریست ورودی
                        }
                    }
                });
            }

        });
    })();
