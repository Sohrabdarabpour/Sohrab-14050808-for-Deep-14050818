// اسکریپت صفحه: projects/list.html

    (function () {
        'use strict';

        window.openImportModal = function () {
            document.getElementById('importModal').classList.add('show');
        };

        window.closeImportModal = function () {
            document.getElementById('importModal').classList.remove('show');
        };

        const modal = document.getElementById('importModal');
        if (modal) {
            modal.addEventListener('click', function (e) {
                if (e.target === this) closeImportModal();
            });
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') closeImportModal();
            });
        }
    })();
