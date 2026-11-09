// اسکریپت صفحه: contractors/list.html

    (function () {
        'use strict';

        // ============================================
        // پالت ۱۰ رنگی هماهنگ با سایر صفحات
        // ============================================
        const CONTRACTOR_COLORS = [
            { base: '#1b698b', light: '#3d8bb5' },
            { base: '#167a5c', light: '#2aa07a' },
            { base: '#d69e2e', light: '#e8b94a' },
            { base: '#c05621', light: '#dd7a3d' },
            { base: '#4a5568', light: '#6b7a8f' },
            { base: '#2b6cb0', light: '#3d8ad4' },
            { base: '#319795', light: '#4fc3c0' },
            { base: '#805ad5', light: '#9f7ae8' },
            { base: '#718096', light: '#8fa0b5' },
            { base: '#2f855a', light: '#4aa876' }
        ];

        // ============================================
        // اعمال رنگ اختصاصی به هر کارت
        // ============================================
        function applyContractorColors() {
            const cards = document.querySelectorAll('#contractorsGrid .cn-card');
            cards.forEach(function (card, index) {
                const color = CONTRACTOR_COLORS[index % CONTRACTOR_COLORS.length];
                card.style.setProperty('--cn-color', color.base);
                card.style.setProperty('--cn-color-light', color.light);
            });
        }

        // ============================================
        // Modal Import
        // ============================================
        window.openImportModal = function () {
            document.getElementById('importModal').classList.add('show');
        };

        window.closeImportModal = function () {
            document.getElementById('importModal').classList.remove('show');
        };

        const modal = document.getElementById('importModal');
        if (modal) {
            modal.addEventListener('click', function (e) {
                if (e.target === this) {
                    closeImportModal();
                }
            });
            // بستن با کلید Esc
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') {
                    closeImportModal();
                }
            });
        }

        // ============================================
        // اجرا
        // ============================================
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', applyContractorColors);
        } else {
            applyContractorColors();
        }
    })();
