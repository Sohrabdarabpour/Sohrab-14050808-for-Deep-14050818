// اسکریپت صفحه: document_group/subgroups/form.html

    // ★ شمارنده گروه‌ها
    function updateGroupCounter(checkbox) {
        const counter = document.getElementById('groupCounter');
        const list = document.getElementById('groupsList');
        if (!list || !counter) return;
        const checked = list.querySelectorAll('input[type="checkbox"]:checked');
        counter.textContent = checked.length;

        const item = checkbox.closest('.sf-multi-item');
        if (item) {
            if (checkbox.checked) item.classList.add('selected');
            else item.classList.remove('selected');
        }
    }

    // ★ شمارنده دپارتمان‌ها
    function updateDeptCounter(checkbox) {
        const counter = document.getElementById('deptCounter');
        const list = document.getElementById('deptsList');
        if (!list || !counter) return;
        const checked = list.querySelectorAll('input[type="checkbox"]:checked');
        counter.textContent = checked.length;

        const item = checkbox.closest('.sf-multi-item');
        if (item) {
            if (checkbox.checked) item.classList.add('selected');
            else item.classList.remove('selected');
        }
    }

    // ★ جستجو
    document.addEventListener('DOMContentLoaded', function () {
        ['groups', 'depts'].forEach(function (name) {
            const input = document.getElementById(name + 'Search');
            const list = document.getElementById(name + 'List');
            if (!input || !list) return;

            input.addEventListener('input', function () {
                const query = this.value.trim().toLowerCase();
                list.querySelectorAll('.sf-multi-item').forEach(function (item) {
                    const title = item.dataset.title || '';
                    item.style.display = (query === '' || title.includes(query)) ? '' : 'none';
                });
            });
        });

        // ★ مقداردهی اولیه شمارنده‌ها
        ['groupCounter:groupsList', 'deptCounter:deptsList'].forEach(function (pair) {
            const [counterId, listId] = pair.split(':');
            const counter = document.getElementById(counterId);
            const list = document.getElementById(listId);
            if (counter && list) {
                const checked = list.querySelectorAll('input[type="checkbox"]:checked');
                counter.textContent = checked.length;
            }
        });
    });
