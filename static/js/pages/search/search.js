// اسکریپت صفحه: search/search.html

    // ============================================================
    // ★ State
    // ============================================================
    const searchState = {
        query: '',
        page: 1,
        perPage: 20,
        isLoading: false,
        hasMore: false,
        total: 0,
        hasSearched: false,
        liveSearchTimeout: null,
        suggestTimeout: null,
    };

    // ★ mode جستجوی کلیدواژه (پیش‌فرض: OR)
    let keywordsMode = 'OR';

    const $ = id => document.getElementById(id);
    const esc = v => v == null ? '' : String(v).replace(/[&<>"']/g, m => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[m]));

    // ============================================================
    // ★ URL Templates
    // ============================================================
    const URL_TEMPLATES = (() => {
        try {
            const el = document.getElementById('url-templates');
            return el ? JSON.parse(el.textContent) : {};
        } catch (e) {
            console.error('URL templates parse error:', e);
            return {};
        }
    })();

    function buildUrl(template, id) {
        if (!template) return `/documents/view/${id}`;
        return template.replace(/\/0(\?|$)/, `/${id}$1`).replace(/\/0$/, `/${id}`);
    }

    // ============================================================
    // ★ تعریف فیلترها — ترتیب جدید
    // ============================================================
    const FILTER_DEFINITIONS = [
        {id: 'filterContractor',      key: 'contractor',       label: 'پیمانکار'},
        {id: 'filterProject',         key: 'project',          label: 'پروژه'},
        {id: 'filterArea',            key: 'area',             label: 'ناحیه'},
        {id: 'filterDepartment',      key: 'department',       label: 'دپارتمان'},
        {id: 'filterGroup',           key: 'group',            label: 'گروه سند'},
        {id: 'filterSubgroup',        key: 'subgroup',         label: 'زیرگروه'},
        {id: 'filterStatus',          key: 'status',           label: 'وضعیت'},
        {id: 'filterUser',            key: 'user',             label: 'کاربر'},
        {id: 'filterDateFrom',        key: 'date_from',        label: 'از تاریخ'},
        {id: 'filterDateTo',          key: 'date_to',          label: 'تا تاریخ'},
        {id: 'filterSubjectKeywords', key: 'subject_keywords', label: 'کلیدواژه موضوع'},
    ];

    // ============================================================
    // ★ ستون تاریخ
    // ============================================================
    const DATE_COLUMN_LABELS = {
        'date_letter': 'تاریخ نامه',
        'date_received': 'تاریخ دریافت',
        'date_referral': 'تاریخ ارجاع',
        'deadline': 'مهلت پاسخ',
        'response_announce_date': 'تاریخ اعلام پاسخ',
        'final_send_date': 'تاریخ ارسال نهایی',
    };

    function getDateColumnValue() {
        const el = $('filterDateColumn');
        return el ? (el.value || 'date_letter') : 'date_letter';
    }

    function updateDateLabels() {
        const col = getDateColumnValue();
        const label = DATE_COLUMN_LABELS[col] || 'تاریخ نامه';
        const fromLabel = $('dateFromLabel');
        const toLabel = $('dateToLabel');
        if (fromLabel) fromLabel.textContent = label;
        if (toLabel) toLabel.textContent = label;
    }

    // ============================================================
    // ★ به‌روزرسانی متن راهنما بر اساس mode کلیدواژه
    // ============================================================
    function __updateKeywordsModeHint(mode) {
        const hint = $('keywordsModeHint');
        if (!hint) return;

        if (mode === 'AND') {
            hint.innerHTML = 'فقط اسنادی نمایش داده می‌شوند که <strong>همه</strong> کلیدواژه‌ها را در موضوع دارند';
        } else {
            hint.innerHTML = 'نمایش اسنادی که <strong>حداقل یکی</strong> از کلیدواژه‌ها در موضوع دارند';
        }
    }

    function __applyKeywordsModeToUI(mode) {
        const kwModeToggle = $('keywordsModeToggle');
        if (kwModeToggle) {
            kwModeToggle.querySelectorAll('.kw-mode-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.mode === mode);
            });
        }
        __updateKeywordsModeHint(mode);
    }

    // ============================================================
    // ★ ساخت پارامترها
    // ============================================================
    function buildParams() {
        const params = new URLSearchParams();

        const q = $('searchQuery').value.trim();
        if (q) params.set('q', q);

        FILTER_DEFINITIONS.forEach(({id, key}) => {
            const el = $(id);
            if (el && el.value) params.set(key, el.value);
        });

        // ★ اگر کلیدواژه پر بود، mode را هم بفرست
        const kwEl = $('filterSubjectKeywords');
        if (kwEl && kwEl.value.trim()) {
            params.set('keywords_mode', keywordsMode);
        }

        const dateColumn = getDateColumnValue();
        if (dateColumn && dateColumn !== 'date_letter') {
            params.set('date_column', dateColumn);
        }

        const sortBy = $('filterSortBy').value;
        if (sortBy) params.set('sort_by', sortBy);

        return params;
    }

    // ============================================================
    // ★ خواندن مقدار نمایشی
    // ============================================================
    function getFilterDisplayValue(filterId) {
        const el = $(filterId);
        if (!el || !el.value) return '';

        if (el.tagName === 'SELECT') {
            const opt = el.options[el.selectedIndex];
            return opt ? opt.textContent.trim() : el.value;
        }
        return el.value;
    }

    // ============================================================
    // ★ چیپ‌های فیلتر فعال
    // ============================================================
    function updateFilterChips() {
        const container = $('chipsContainer');
        const wrapper = $('activeFiltersChips');
        const chips = [];

        FILTER_DEFINITIONS.forEach(({id, label}) => {
            const val = $(id)?.value;
            if (val) {
                const display = getFilterDisplayValue(id);
                chips.push(`
                <span class="filter-chip" data-filter-id="${id}">
                    <span class="chip-label">${esc(label)}:</span>
                    <span class="chip-value">${esc(display)}</span>
                    <button type="button" class="chip-remove" data-filter-id="${id}" aria-label="حذف فیلتر">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </span>
            `);
            }
        });

        container.innerHTML = chips.join('');
        wrapper.classList.toggle('visible', chips.length > 0);

        container.querySelectorAll('.chip-remove').forEach(btn => {
            btn.addEventListener('click', async () => {
                const filterId = btn.dataset.filterId;
                const el = $(filterId);
                if (!el) return;

                el.value = '';

                // ★ اگر چیپ «گروه» حذف شد → زیرگروه‌ها را ریست کن
                if (filterId === 'filterGroup') {
                    await __refreshSubgroups('');
                }

                // ★ اگر چیپ «پیمانکار» حذف شد → پروژه‌ها را ریست کن
                if (filterId === 'filterContractor') {
                    await __refreshProjectsByContractor('');
                }

                countActiveFilters();
            });
        });
    }

    // ============================================================
    // ★ شمارش فیلترهای فعال
    // ============================================================
    function countActiveFilters() {
        let count = 0;
        FILTER_DEFINITIONS.forEach(({id}) => {
            if ($(id)?.value) count++;
        });

        const badge = $('filtersBadge');
        if (badge) {
            badge.textContent = count > 0 ? count : '';
            badge.classList.toggle('visible', count > 0);
        }

        const toggle = $('filtersToggle');
        if (toggle) toggle.classList.toggle('active', count > 0);

        const hint = $('searchFilterHint');
        const hintCount = $('activeFilterCountHint');
        if (hint && hintCount) {
            hintCount.textContent = count.toLocaleString('fa-IR');
            hint.classList.toggle('visible', count > 0);
        }

        updateFilterChips();
    }

    // ============================================================
    // ★ Custom Dropdown — مرتب‌سازی سریع
    // ============================================================
    function initQuickSort() {
        const wrapper = $('quickSortWrapper');
        const trigger = $('quickSortTrigger');
        const menu = $('quickSortMenu');
        const label = $('quickSortLabel');

        if (!wrapper || !trigger || !menu || !label) return;

        function open() {
            wrapper.classList.add('open');
            trigger.setAttribute('aria-expanded', 'true');
        }

        function close() {
            wrapper.classList.remove('open');
            trigger.setAttribute('aria-expanded', 'false');
        }

        function setValue(value) {
            $('filterSortBy').value = value;
            menu.querySelectorAll('.quick-sort-option').forEach(opt => {
                const isSelected = opt.dataset.value === value;
                opt.classList.toggle('selected', isSelected);
                if (isSelected) {
                    label.textContent = opt.querySelector('span').textContent;
                }
            });
        }

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            if (wrapper.classList.contains('open')) close();
            else open();
        });

        menu.querySelectorAll('.quick-sort-option').forEach(opt => {
            opt.addEventListener('click', () => {
                setValue(opt.dataset.value);
                close();
            });
        });

        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) close();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && wrapper.classList.contains('open')) {
                close();
            }
        });

        window.__setQuickSortValue = setValue;
    }

    // ============================================================
    // ★ فیلتر پویای زیرگروه — فقط زیرگروه‌های گروه انتخاب‌شده
    // ============================================================
    let __allSubgroupOptions = [];

    async function __refreshSubgroups(groupId) {
        const subgroupEl = $('filterSubgroup');
        if (!subgroupEl) return;

        const currentValue = subgroupEl.value;

        if (!__allSubgroupOptions.length) {
            __allSubgroupOptions = Array.from(subgroupEl.options)
                .filter(opt => opt.value)
                .map(opt => opt.cloneNode(true));
        }

        subgroupEl.innerHTML = '<option value="">همه زیرگروه‌ها</option>';

        if (!groupId) {
            __allSubgroupOptions.forEach(opt => {
                subgroupEl.appendChild(opt.cloneNode(true));
            });
            if (currentValue) subgroupEl.value = currentValue;
            return;
        }

        const loadingOpt = document.createElement('option');
        loadingOpt.value = '';
        loadingOpt.textContent = 'در حال بارگذاری...';
        loadingOpt.disabled = true;
        subgroupEl.appendChild(loadingOpt);

        try {
            const res = await fetch(
                `/search/api/subgroups?group_id=${encodeURIComponent(groupId)}`,
                {headers: {'X-Requested-With': 'XMLHttpRequest'}}
            );
            const data = await res.json();

            subgroupEl.innerHTML = '<option value="">همه زیرگروه‌ها</option>';

            if (data.success && data.subgroups && data.subgroups.length) {
                data.subgroups.forEach(sg => {
                    const opt = document.createElement('option');
                    opt.value = sg.id;
                    opt.textContent = sg.title;
                    subgroupEl.appendChild(opt);
                });

                if (currentValue && data.subgroups.some(sg => String(sg.id) === String(currentValue))) {
                    subgroupEl.value = currentValue;
                }
            } else {
                const emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.textContent = 'زیرگروهی برای این گروه تعریف نشده';
                emptyOpt.disabled = true;
                subgroupEl.appendChild(emptyOpt);
            }
        } catch (err) {
            console.error('خطا در بارگذاری زیرگروه‌ها:', err);
            subgroupEl.innerHTML = '<option value="">همه زیرگروه‌ها</option>';
        }

        countActiveFilters();
    }

    // ============================================================
    // ★ فیلتر پویای پروژه ↔ پیمانکار (دو طرفه)
    // ============================================================
    let __allProjectOptions = [];
    let __isSyncingProjectContractor = false;

    async function __refreshProjectsByContractor(contractorId, preserveProjectId = null) {
        const projectEl = $('filterProject');
        if (!projectEl) return;

        const currentValue = preserveProjectId || projectEl.value;

        if (!__allProjectOptions.length) {
            __allProjectOptions = Array.from(projectEl.options)
                .filter(opt => opt.value)
                .map(opt => opt.cloneNode(true));
        }

        projectEl.innerHTML = '<option value="">همه پروژه‌ها</option>';

        if (!contractorId) {
            __allProjectOptions.forEach(opt => {
                projectEl.appendChild(opt.cloneNode(true));
            });
            if (currentValue) projectEl.value = currentValue;
            return;
        }

        const loadingOpt = document.createElement('option');
        loadingOpt.value = '';
        loadingOpt.textContent = 'در حال بارگذاری...';
        loadingOpt.disabled = true;
        projectEl.appendChild(loadingOpt);

        try {
            const res = await fetch(
                `/search/api/contractor-projects?contractor_id=${encodeURIComponent(contractorId)}`,
                {headers: {'X-Requested-With': 'XMLHttpRequest'}}
            );
            const data = await res.json();

            projectEl.innerHTML = '<option value="">همه پروژه‌ها</option>';

            if (data.success && data.projects && data.projects.length) {
                data.projects.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = p.name;
                    projectEl.appendChild(opt);
                });

                if (currentValue && data.projects.some(p => String(p.id) === String(currentValue))) {
                    projectEl.value = currentValue;
                }
            } else {
                const emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.textContent = 'پروژه‌ای برای این پیمانکار تعریف نشده';
                emptyOpt.disabled = true;
                projectEl.appendChild(emptyOpt);
            }
        } catch (err) {
            console.error('خطا در بارگذاری پروژه‌ها:', err);
            projectEl.innerHTML = '<option value="">همه پروژه‌ها</option>';
        }

        countActiveFilters();
    }

    async function __syncContractorFromProject(projectId) {
        if (!projectId) return;

        const contractorEl = $('filterContractor');
        if (!contractorEl) return;

        try {
            const res = await fetch(
                `/search/api/contractor-projects?project_id=${encodeURIComponent(projectId)}`,
                {headers: {'X-Requested-With': 'XMLHttpRequest'}}
            );
            const data = await res.json();

            if (data.success && data.contractor_id) {
                const currentContractorId = contractorEl.value;
                const newContractorId = String(data.contractor_id);

                if (currentContractorId !== newContractorId) {
                    contractorEl.value = newContractorId;
                    await __refreshProjectsByContractor(newContractorId, projectId);
                    countActiveFilters();
                }
            }
        } catch (err) {
            console.error('خطا در دریافت پیمانکار پروژه:', err);
        }
    }

    // ============================================================
    // ★ ذخیره/بازیابی state در URL
    // ============================================================
    function saveStateToUrl() {
        const params = buildParams();
        const qs = params.toString();
        const newUrl = qs ? `${location.pathname}?${qs}` : location.pathname;
        history.replaceState(null, '', newUrl);
    }

    async function restoreStateFromUrl() {
        const params = new URLSearchParams(location.search);
        if (![...params.keys()].length) return false;

        const q = params.get('q');
        if (q) $('searchQuery').value = q;

        // ★ بازیابی mode کلیدواژه
        const kwModeParam = params.get('keywords_mode');
        if (kwModeParam && (kwModeParam === 'AND' || kwModeParam === 'OR')) {
            keywordsMode = kwModeParam;
        }
        __applyKeywordsModeToUI(keywordsMode);

        // ★ ۱. اول پیمانکار (چون پروژه به آن وابسته است)
        const contractorVal = params.get('contractor');
        if (contractorVal && $('filterContractor')) {
            $('filterContractor').value = contractorVal;
        }

        // ★ ۲. سپس گروه (چون زیرگروه به آن وابسته است)
        const groupVal = params.get('group');
        if (groupVal && $('filterGroup')) {
            $('filterGroup').value = groupVal;
        }

        // ★ ۳. بقیه فیلترها (به جز فیلترهای وابسته)
        FILTER_DEFINITIONS.forEach(({id, key}) => {
            if (key === 'contractor' || key === 'project' ||
                key === 'group' || key === 'subgroup') return;
            const val = params.get(key);
            if (val) $(id).value = val;
        });

        // ★ ۴. بارگذاری زیرگروه‌ها بر اساس گروه
        if (groupVal) {
            await __refreshSubgroups(groupVal);
        }

        // ★ ۵. بارگذاری پروژه‌ها بر اساس پیمانکار
        if (contractorVal) {
            await __refreshProjectsByContractor(contractorVal);
        }

        // ★ ۶. حالا زیرگروه و پروژه را ست کن
        const subgroupVal = params.get('subgroup');
        if (subgroupVal && $('filterSubgroup')) {
            $('filterSubgroup').value = subgroupVal;
        }

        const projectVal = params.get('project');
        if (projectVal && $('filterProject')) {
            $('filterProject').value = projectVal;
        }

        const dateCol = params.get('date_column');
        if (dateCol && $('filterDateColumn')) {
            $('filterDateColumn').value = dateCol;
        }
        updateDateLabels();

        const sortBy = params.get('sort_by');
        if (sortBy) {
            $('filterSortBy').value = sortBy;
            if (window.__setQuickSortValue) {
                window.__setQuickSortValue(sortBy);
            }
        }

        if (FILTER_DEFINITIONS.some(({id}) => $(id)?.value)) {
            $('filtersPanel').classList.add('open');
            $('filtersToggle').classList.add('open');
            $('filtersToggle').setAttribute('aria-expanded', 'true');
        }

        countActiveFilters();
        return true;
    }

    // ============================================================
    // ★ اجرای جستجو
    // ============================================================
    async function performSearch(page = 1, append = false, options = {}) {
        if (searchState.isLoading) return;

        const {silent = false} = options;
        const query = $('searchQuery').value.trim();
        const hasFilters = FILTER_DEFINITIONS.some(({id}) => $(id)?.value);

        if (!query && !hasFilters) {
            showInitial();
            saveStateToUrl();
            return;
        }

        searchState.isLoading = true;
        searchState.hasSearched = true;
        searchState.query = query;

        $('resultsInitial').style.display = 'none';
        $('resultsEmpty').style.display = 'none';

        if (page === 1 && !append) {
            $('resultsGrid').innerHTML = '';
            if (!silent) showSkeletonLoader();
            $('resultsHeader').style.display = 'none';
            $('resultsPagination').style.display = 'none';
        } else {
            const btn = $('btnLoadMore');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> در حال بارگذاری...';
        }

        $('inputSpinner').classList.add('visible');

        const applyBtn = $('btnApplyFilters');
        if (applyBtn) {
            applyBtn.disabled = true;
            applyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> در حال اعمال...';
        }

        try {
            const params = buildParams();
            params.set('page', page);
            params.set('per_page', searchState.perPage);

            const res = await fetch(`/search/api/search?${params}`, {
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            });

            if (!res.ok) throw new Error('خطا در جستجو');
            const data = await res.json();

            hideSkeletonLoader();

            if (!data.success) throw new Error(data.message || 'خطا در جستجو');

            searchState.total = data.total;
            searchState.page = data.page;
            searchState.hasMore = data.has_more;

            $('resultsHeader').style.display = 'flex';
            $('resultsCount').textContent = data.total.toLocaleString('fa-IR');
            $('resultsQueryLabel').textContent = query ? `— «${query}»` : '';

            if (!data.records || data.records.length === 0) {
                if (page === 1) showEmptyState();
                $('resultsPagination').style.display = 'none';
                saveStateToUrl();
                return;
            }

            const html = data.records.map((r, i) => renderResultCard(r, i)).join('');
            if (append) {
                $('resultsGrid').insertAdjacentHTML('beforeend', html);
            } else {
                $('resultsGrid').innerHTML = html;
            }

            if (data.has_more) {
                $('resultsPagination').style.display = 'block';
                const shown = $('resultsGrid').children.length;
                $('loadMoreInfo').textContent = `${shown.toLocaleString('fa-IR')} از ${data.total.toLocaleString('fa-IR')} سند نمایش داده شده`;
            } else {
                $('resultsPagination').style.display = 'none';
            }

            if (page === 1 && !append && !silent) {
                $('resultsSection').scrollIntoView({behavior: 'smooth', block: 'start'});
            }

            saveStateToUrl();

        } catch (err) {
            console.error(err);
            hideSkeletonLoader();
            showEmptyState('خطا در جستجو', err.message);
        } finally {
            searchState.isLoading = false;
            $('inputSpinner').classList.remove('visible');
            const btn = $('btnLoadMore');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-arrow-down"></i> نمایش بیشتر';
            }
            if (applyBtn) {
                applyBtn.disabled = false;
                applyBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i> اعمال فیلتر';
            }
        }
    }

    // ============================================================
    // ★ Skeleton Loader
    // ============================================================
    function showSkeletonLoader() {
        $('resultsLoader').style.display = 'block';
        const container = $('skeletonContainer');
        let html = '';
        for (let i = 0; i < 3; i++) {
            html += `
            <div class="skeleton-card">
                <div class="skeleton-line w-60"></div>
                <div class="skeleton-line w-30"></div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;">
                    <div class="skeleton-line w-80"></div>
                    <div class="skeleton-line w-60"></div>
                    <div class="skeleton-line w-80"></div>
                </div>
            </div>
        `;
        }
        container.innerHTML = html;
    }

    function hideSkeletonLoader() {
        $('resultsLoader').style.display = 'none';
        $('skeletonContainer').innerHTML = '';
    }

    // ============================================================
    // ★ حالت خالی
    // ============================================================
    function showEmptyState(title, message) {
        const box = $('resultsEmpty');
        box.style.display = 'block';
        $('resultsGrid').innerHTML = '';
        $('resultsPagination').style.display = 'none';

        if (title) box.querySelector('h3').textContent = title;
        else box.querySelector('h3').textContent = 'نتیجه‌ای یافت نشد';

        if (message) $('emptyMessage').textContent = message;
        else $('emptyMessage').textContent = 'لطفاً عبارت جستجو یا فیلترها را تغییر دهید';

        const suggestions = [];
        if (FILTER_DEFINITIONS.some(({id}) => $(id)?.value)) {
            suggestions.push({
                icon: 'fa-filter-circle-xmark',
                text: 'حذف همه فیلترها',
                action: 'clear-filters'
            });
        }
        if ($('searchQuery').value.trim()) {
            suggestions.push({
                icon: 'fa-eraser',
                text: 'پاک کردن متن جستجو',
                action: 'clear-query'
            });
        }

        const box2 = $('emptySuggestions');
        box2.innerHTML = suggestions.map(s => `
        <button type="button" class="empty-suggestion-btn" data-action="${s.action}">
            <i class="fa-solid ${s.icon}"></i>
            ${s.text}
        </button>
    `).join('');

        box2.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', async () => {
                const action = btn.dataset.action;
                if (action === 'clear-filters') {
                    await resetFilters();
                    performSearch(1, false);
                } else if (action === 'clear-query') {
                    $('searchQuery').value = '';
                    $('clearInputBtn').classList.remove('visible');
                    performSearch(1, false);
                }
            });
        });
    }

    // ============================================================
    // ★ رندر کارت نتیجه
    // ============================================================
    function renderResultCard(record, index = 0) {
        const statusColor = record.status_color || '#3D8499';
        const statusCode = record.status_code || '';
        const subject = record.subject || 'بدون موضوع';
        const docId = record.id || '';

        let deadlineBadge = '';
        if (statusCode === 'in_progress' && record.days_left != null && record.days_left !== '') {
            const dl = Number(record.days_left);
            if (dl < 0) {
                deadlineBadge = `<span class="doc-deadline-badge badge-overdue"><i class="fa-solid fa-triangle-exclamation"></i> ${Math.abs(dl)} روز گذشته</span>`;
            } else if (dl <= 2) {
                const text = dl === 0 ? 'امروز' : (dl === 1 ? 'فردا' : `${dl} روز مانده`);
                deadlineBadge = `<span class="doc-deadline-badge badge-near"><i class="fa-solid fa-hourglass-half"></i> ${text}</span>`;
            } else {
                deadlineBadge = `<span class="doc-deadline-badge badge-normal"><i class="fa-solid fa-clock"></i> ${dl} روز مانده</span>`;
            }
        }

        const responseStatus = (record.doc_response_status || '').toString().trim();
        const approvalBadge = ['در انتظار امضاي مديريت', 'در انتظار امضای مدیریت', 'در انتظار تایید مدیریت'].includes(responseStatus)
            ? `<span class="doc-approval-badge"><i class="fa-solid fa-user-shield"></i> در انتظار تایید مدیریت</span>`
            : '';

        const mainFields = [
            ['date_letter_jalali', 'fa-calendar-day', 'تاریخ نامه', true],
            ['automation_number', 'fa-barcode', 'شماره اتوماسیون', true],
            ['contractor_letter_number', 'fa-envelope', 'شماره نامه پیمانکار', true],
            ['contract_number', 'fa-file-contract', 'شماره قرارداد', true],
            ['deadline_jalali', 'fa-hourglass-half', 'مهلت پاسخ', true, 'color:rgb(220,38,38);']
        ];

        const mainFieldsHtml = mainFields.map(([key, icon, label, ltr, extraStyle = '']) => {
            const val = record[key];
            if (!val) return '';
            const styleAttr = extraStyle ? ` style="${extraStyle}"` : '';
            return `<div class="doc-field">
                <span class="field-label"${styleAttr}><i class="fa-solid ${icon}"></i> ${label}</span>
                <span class="field-value${ltr ? ' ltr' : ''}"${styleAttr}>${esc(val)}</span>
            </div>`;
        }).join('');

        const expandFields1 = [
            [['contractor_name', 'contractor'], 'fa-building', 'پیمانکار'],
            [['area_title', 'area'], 'fa-location-dot', 'ناحیه'],
            ['date_received_jalali', 'fa-calendar-plus', 'تاریخ دریافت', true],
            ['date_referral_jalali', 'fa-share-from-square', 'تاریخ ارجاع', true],
            ['unit', 'fa-building-columns', 'واحد']
        ];
        const expandFields2 = [
            ['department_title', 'fa-sitemap', 'دپارتمان'],
            [['group_title', 'document_group'], 'fa-folder', 'گروه مدرک'],
            [['subgroup_title', 'sub_group'], 'fa-diagram-project', 'زیرگروه']
        ];
        const expandFields3 = [
            ['doc_response_status', 'fa-clipboard-check', 'وضعیت پاسخ مدرک', false, 'color:rgb(22,163,74); font-weight:700;'],
            ['final_send_date_jalali', 'fa-paper-plane', 'تاریخ ارسال نهایی', true, 'color:rgb(27,105,139); font-weight:700;'],
            ['final_letter_number', 'fa-file-signature', 'شماره نامه نهایی', true],
            ['final_delay', 'fa-hourglass-end', 'تاخیر نهایی', true]
        ];

        const buildField = ([key, icon, label, ltr = false, extraStyle = '']) => {
            let val;
            if (Array.isArray(key)) {
                val = key.map(k => record[k]).find(Boolean);
            } else {
                val = record[key];
            }
            if (!val) return '';
            const styleAttr = extraStyle ? ` style="${extraStyle}"` : '';
            return `<div class="doc-field">
                <span class="field-label"><i class="fa-solid ${icon}"></i> ${label}</span>
                <span class="field-value${ltr ? ' ltr' : ''}"${styleAttr}>${esc(val)}</span>
            </div>`;
        };

        const projectNameText = record.project_title || record.project_name;
        const projectName = projectNameText
            ? `<div class="doc-project">
                   <div class="doc-project-content">
                       <span class="doc-project-label">پروژه:</span>
                       <span class="doc-project-name" title="${esc(projectNameText)}">${esc(projectNameText)}</span>
                   </div>
               </div>`
            : '';

        const statusBadge = record.status_title
            ? `<span class="doc-status-badge"><i class="fa-solid fa-circle"></i> ${esc(record.status_title)}</span>`
            : '';

        const metaParts = [
            record.code_dfc ? `<span style="color:#16a34a;font-weight:700;"><i class="fa-solid fa-hashtag" style="color:#16a34a;"></i> DFC:${esc(record.code_dfc)}</span>` : '',
            (record.contractor_name || record.contractor) ? `<span><i class="fa-solid fa-building"></i> ${esc(record.contractor_name || record.contractor)}</span>` : '',
            record.user_full_name ? `<span><i class="fa-solid fa-user-tie"></i> ${esc(record.user_full_name)}</span>` : '',
            (record.subgroup_title || record.sub_group) ? `<span><i class="fa-solid fa-diagram-project"></i> ${esc(record.subgroup_title || record.sub_group)}</span>` : ''
        ].filter(Boolean).join('');

        const viewUrl = buildUrl(URL_TEMPLATES.documentView, docId);

        const actionsHtml = `
            <div class="doc-card-actions" onclick="event.stopPropagation();">
                <button type="button" class="doc-expand-btn" onclick="toggleExpand(this)" aria-expanded="false">
                    <span class="btn-text">جزئیات</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </button>
                <a href="${viewUrl}" class="doc-card-action-btn view-btn" title="تاریخچه یادداشت‌ها">
                    <i class="fa-solid fa-clock-rotate-left"></i>
                    <span>تاریخچه یادداشت‌ها</span>
                </a>
            </div>`;

        const delay = Math.min(index * 0.04, 0.4);

        return `
        <div class="document-card"
             data-status="${esc(statusCode)}"
             data-doc-id="${esc(docId)}"
             style="--status-color:${esc(statusColor)};animation-delay:${delay}s;">
            <div class="doc-header">
                <div class="doc-title-group">
                    <div class="doc-subject">
                        <i class="fa-solid fa-file-pen"></i>
                        <span>${esc(subject)}</span>
                    </div>
                </div>
                ${actionsHtml}
            </div>

            <div class="doc-expand-content">
                <div class="doc-expand-content-inner">
                    <div class="doc-details-summary">
                        ${projectName}
                        <div class="doc-meta">${metaParts}</div>
                        <div class="doc-badges-row">
                            ${statusBadge}
                            ${approvalBadge}
                            ${deadlineBadge}
                        </div>
                    </div>
                    <div class="doc-body-row">${mainFieldsHtml}</div>
                    <div class="doc-body-row">${expandFields1.map(buildField).join('')}</div>
                    <div class="doc-body-row">${expandFields2.map(buildField).join('')}</div>
                    <div class="doc-body-row">${expandFields3.map(buildField).join('')}</div>
                </div>
            </div>

        </div>`;
    }

    // ============================================================
    // ★ Toggle Expand
    // ============================================================
    function toggleExpand(btn) {
        const content = btn.closest('.document-card').querySelector('.doc-expand-content');
        const text = btn.querySelector('.btn-text');
        content.classList.toggle('open');
        btn.classList.toggle('expanded');
        const isOpen = content.classList.contains('open');
        text.textContent = isOpen ? 'بستن جزئیات' : 'جزئیات';
        btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }

    // ============================================================
    // ★ UI Helpers
    // ============================================================
    function showInitial() {
        $('resultsInitial').style.display = 'block';
        $('resultsEmpty').style.display = 'none';
        $('resultsHeader').style.display = 'none';
        $('resultsPagination').style.display = 'none';
        $('resultsGrid').innerHTML = '';
        hideSkeletonLoader();
    }

    async function resetFilters() {
        FILTER_DEFINITIONS.forEach(({id}) => {
            const el = $(id);
            if (el) el.value = '';
        });

        // ★ ریست زیرگروه‌ها به همه
        await __refreshSubgroups('');

        // ★ ریست پروژه‌ها به همه
        await __refreshProjectsByContractor('');

        // ★ ریست mode کلیدواژه به OR
        keywordsMode = 'OR';
        __applyKeywordsModeToUI('OR');

        if ($('filterDateColumn')) $('filterDateColumn').value = 'date_letter';
        updateDateLabels();

        $('filterSortBy').value = 'id';
        if (window.__setQuickSortValue) window.__setQuickSortValue('id');
        countActiveFilters();
    }

    // ============================================================
    // ★ Autocomplete
    // ============================================================
    async function fetchSuggestions(q) {
        if (!q || q.length < 2) {
            $('suggestionsBox').classList.remove('visible');
            return;
        }

        try {
            const res = await fetch(`/search/api/suggestions?q=${encodeURIComponent(q)}`);
            const data = await res.json();
            if (!data.success) return;

            const groups = [];
            if (data.subjects?.length) {
                groups.push({
                    title: 'موضوعات',
                    icon: 'fa-file-lines',
                    items: data.subjects.map(s => s.value)
                });
            }
            if (data.codes?.length) {
                groups.push({
                    title: 'کدهای DFC',
                    icon: 'fa-hashtag',
                    items: data.codes.map(s => s.value)
                });
            }
            if (data.contractors?.length) {
                groups.push({
                    title: 'پیمانکاران',
                    icon: 'fa-helmet-safety',
                    items: data.contractors.map(s => s.value)
                });
            }

            if (!groups.length) {
                $('suggestionsBox').classList.remove('visible');
                return;
            }

            const highlight = (text) => {
                const escaped = esc(text);
                const qEsc = esc(q);
                const regex = new RegExp(`(${qEsc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                return escaped.replace(regex, '<mark>$1</mark>');
            };

            $('suggestionsBox').innerHTML = groups.map(g => `
            <div class="suggestion-group">
                <div class="suggestion-group-title">${g.title}</div>
                ${g.items.map(item => `
                    <div class="suggestion-item" data-value="${esc(item)}" role="option">
                        <i class="fa-solid ${g.icon}"></i>
                        <span>${highlight(item)}</span>
                    </div>
                `).join('')}
            </div>
        `).join('');

            $('suggestionsBox').querySelectorAll('.suggestion-item').forEach(el => {
                el.addEventListener('click', () => {
                    selectSuggestion(el.dataset.value);
                });
            });

            $('suggestionsBox').classList.add('visible');
        } catch (e) {
            console.error(e);
        }
    }

    function selectSuggestion(value) {
        $('searchQuery').value = value;
        $('suggestionsBox').classList.remove('visible');
        $('clearInputBtn').classList.add('visible');
        performSearch(1, false);
    }

    // ============================================================
    // ★ Live Search
    // ============================================================
    function scheduleLiveSearch() {
        clearTimeout(searchState.liveSearchTimeout);
        searchState.liveSearchTimeout = setTimeout(() => {
            const query = $('searchQuery').value.trim();
            const hasFilters = FILTER_DEFINITIONS.some(({id}) => $(id)?.value);

            if (query.length >= 3 || hasFilters || searchState.hasSearched) {
                performSearch(1, false, {silent: true});
            }
        }, 500);
    }

    // ============================================================
    // ★ Init
    // ============================================================
    document.addEventListener('DOMContentLoaded', async () => {

        initQuickSort();
        updateDateLabels();
        __applyKeywordsModeToUI(keywordsMode);

        const hasState = await restoreStateFromUrl();

        // ---- دکمه جستجو ----
        $('btnSearch').addEventListener('click', () => performSearch(1, false));

        // ---- دکمه اعمال فیلتر ----
        const applyBtn = $('btnApplyFilters');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => performSearch(1, false));
        }

        // ---- Enter در input جستجو ----
        $('searchQuery').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                $('suggestionsBox').classList.remove('visible');
                performSearch(1, false);
            }
            if (e.key === 'Escape') {
                $('suggestionsBox').classList.remove('visible');
            }
        });

        // ---- نمایش/مخفی دکمه پاک کردن ----
        $('searchQuery').addEventListener('input', function () {
            $('clearInputBtn').classList.toggle('visible', this.value.length > 0);
        });

        // ---- دکمه پاک کردن input ----
        $('clearInputBtn').addEventListener('click', () => {
            $('searchQuery').value = '';
            $('clearInputBtn').classList.remove('visible');
            $('searchQuery').focus();
            performSearch(1, false);
        });

        // ---- Autocomplete + Live Search ----
        $('searchQuery').addEventListener('input', function () {
            clearTimeout(searchState.suggestTimeout);
            const val = this.value.trim();
            searchState.suggestTimeout = setTimeout(() => fetchSuggestions(val), 250);
            scheduleLiveSearch();
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-input-wrapper')) {
                $('suggestionsBox').classList.remove('visible');
            }
        });

        // ---- Toggle فیلترها ----
        $('filtersToggle').addEventListener('click', function () {
            const isOpen = this.classList.toggle('open');
            $('filtersPanel').classList.toggle('open');
            this.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        // ---- باز و بسته کردن کرکره‌ای گروه‌های فیلتر ----
        document.querySelectorAll('.filter-group-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const group = btn.closest('.filter-group');
                if (!group) return;
                const collapsed = group.classList.toggle('collapsed');
                btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
                btn.title = collapsed ? 'نمایش فیلترها' : 'بستن فیلترها';
                const label = btn.querySelector('span');
                if (label) label.textContent = collapsed ? 'نمایش' : 'بستن';
            });
        });

        // ---- ریست ----
        $('btnResetFilters').addEventListener('click', async () => {
            await resetFilters();
            performSearch(1, false);
        });

        // ---- پاک کردن همه چیپ‌ها ----
        $('chipClearAll').addEventListener('click', async () => {
            await resetFilters();
            performSearch(1, false);
        });

        // ---- جستجوی جدید ----
        $('btnNewSearch').addEventListener('click', async () => {
            $('searchQuery').value = '';
            $('clearInputBtn').classList.remove('visible');
            await resetFilters();
            showInitial();
            searchState.hasSearched = false;
            history.replaceState(null, '', location.pathname);
        });

        // ---- Load More ----
        $('btnLoadMore').addEventListener('click', () => {
            if (searchState.hasMore && !searchState.isLoading) {
                performSearch(searchState.page + 1, true);
            }
        });

        // ---- Export ----
        $('btnExport').addEventListener('click', () => {
            const params = buildParams();
            window.location.href = `/search/api/export?${params}`;
        });

        // ---- تغییر فیلترها (شمارش) ----
        ['filterStatus', 'filterDepartment', 'filterArea', 'filterGroup',
            'filterSubgroup', 'filterContractor', 'filterProject', 'filterUser'].forEach(id => {
                const el = $(id);
                if (el) {
                    el.addEventListener('change', () => {
                        countActiveFilters();
                    });
                }
            });

        // ============================================================
        // ★ فیلتر پویای زیرگروه
        // ============================================================
        const groupEl = $('filterGroup');
        if (groupEl) {
            groupEl.addEventListener('change', function () {
                __refreshSubgroups(this.value);
            });
        }

        if (groupEl && groupEl.value) {
            await __refreshSubgroups(groupEl.value);
        }

        // ============================================================
        // ★ فیلتر پویای پروژه ↔ پیمانکار (دو طرفه)
        // ============================================================
        const contractorEl = $('filterContractor');
        const projectEl = $('filterProject');

        if (contractorEl && projectEl) {
            contractorEl.addEventListener('change', function () {
                if (__isSyncingProjectContractor) return;

                __isSyncingProjectContractor = true;
                __refreshProjectsByContractor(this.value).finally(() => {
                    __isSyncingProjectContractor = false;
                    countActiveFilters();
                });
            });
        }

        if (projectEl && contractorEl) {
            projectEl.addEventListener('change', function () {
                if (__isSyncingProjectContractor) return;

                const projectId = this.value;
                if (projectId) {
                    __isSyncingProjectContractor = true;
                    __syncContractorFromProject(projectId).finally(() => {
                        __isSyncingProjectContractor = false;
                    });
                }
            });
        }

        if (contractorEl && contractorEl.value) {
            await __refreshProjectsByContractor(contractorEl.value);
        }

        // ============================================================
        // ★ Toggle AND/OR برای کلیدواژه‌ها
        // ============================================================
        const kwModeToggle = $('keywordsModeToggle');
        if (kwModeToggle) {
            kwModeToggle.querySelectorAll('.kw-mode-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    keywordsMode = this.dataset.mode;
                    __applyKeywordsModeToUI(keywordsMode);

                    // اگر قبلاً جستجو شده و کلیدواژه پر است، دوباره جستجو کن
                    const kwEl = $('filterSubjectKeywords');
                    if (kwEl && kwEl.value.trim() && searchState.hasSearched) {
                        performSearch(1, false, {silent: true});
                    }
                });
            });
        }

        // ---- sync مرتب‌سازی ----
        $('filterSortBy').addEventListener('change', function () {
            if (window.__setQuickSortValue) {
                window.__setQuickSortValue(this.value);
            }
            countActiveFilters();
        });

        // ---- تاریخ‌ها ----
        ['filterDateFrom', 'filterDateTo'].forEach(id => {
            const el = $(id);
            if (el) {
                el.addEventListener('change', countActiveFilters);
                el.addEventListener('input', countActiveFilters);
            }
        });

        // ---- ستون تاریخ ----
        const dateColEl = $('filterDateColumn');
        if (dateColEl) {
            dateColEl.addEventListener('change', () => {
                updateDateLabels();
            });
        }

        // ---- کلیدواژه‌های موضوع ----
        const kwEl = $('filterSubjectKeywords');
        if (kwEl) {
            kwEl.addEventListener('input', () => {
                countActiveFilters();
            });
        }

        // ---- Ctrl+K ----
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                $('searchQuery').focus();
                $('searchQuery').select();
            }
        });

        // ---- Scroll to top ----
        const scrollTopBtn = $('scrollTopBtn');
        window.addEventListener('scroll', () => {
            scrollTopBtn.classList.toggle('visible', window.scrollY > 400);
        }, {passive: true});
        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({top: 0, behavior: 'smooth'});
        });

        // ---- شمارش اولیه ----
        countActiveFilters();

        // ---- اگه state از URL داشتیم، جستجو کن ----
        if (hasState && (searchState.query || FILTER_DEFINITIONS.some(({id}) => $(id)?.value))) {
            performSearch(1, false, {silent: true});
        }
    });
