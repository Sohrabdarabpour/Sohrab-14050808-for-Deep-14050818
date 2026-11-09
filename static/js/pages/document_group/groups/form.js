// اسکریپت صفحه: document_group/groups/form.html

    // ★ شمارنده انتخاب‌شده‌ها
    function updateSelectedCounter(checkbox) {
        const counter = document.getElementById('selectedCounter');
        const list = document.getElementById('subgroupsList');
        if (!list || !counter) return;
        const checked = list.querySelectorAll('input[type="checkbox"]:checked');
        counter.textContent = checked.length;

        const item = checkbox.closest('.df-subgroup-item');
        if (item) {
            if (checkbox.checked) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        }
    }

    // ★ جستجو در زیرگروه‌ها
    document.addEventListener('DOMContentLoaded', function () {
        const searchInput = document.getElementById('subgroupsSearch');
        const list = document.getElementById('subgroupsList');

        if (searchInput && list) {
            searchInput.addEventListener('input', function () {
                const query = this.value.trim().toLowerCase();
                const items = list.querySelectorAll('.df-subgroup-item');
                items.forEach(item => {
                    const title = item.dataset.title || '';
                    item.style.display = (query === '' || title.includes(query)) ? '' : 'none';
                });
            });
        }

        // ★ مقداردهی اولیه
        const counter = document.getElementById('selectedCounter');
        if (list && counter) {
            const checked = list.querySelectorAll('input[type="checkbox"]:checked');
            counter.textContent = checked.length;
        }
    });
