// اسکریپت صفحه: departments/list.html

    (function () {
        'use strict';

        // ============================================
        // پالت ۱۰ رنگی هماهنگ با سایر صفحات
        // ============================================
        const DEPT_COLORS = [
            {base: '#1b698b', light: '#3d8bb5'}, // آبی اقیانوسی
            {base: '#167a5c', light: '#2aa07a'}, // سبز زمردی
            {base: '#d69e2e', light: '#e8b94a'}, // طلایی
            {base: '#c05621', light: '#dd7a3d'}, // نارنجی سوخته
            {base: '#4a5568', light: '#6b7a8f'}, // خاکستری تیره
            {base: '#2b6cb0', light: '#3d8ad4'}, // آبی روشن
            {base: '#319795', light: '#4fc3c0'}, // فیروزه‌ای
            {base: '#805ad5', light: '#9f7ae8'}, // بنفش
            {base: '#718096', light: '#8fa0b5'}, // خاکستری متوسط
            {base: '#2f855a', light: '#4aa876'}  // سبز جنگلی
        ];

        // ============================================
        // اعمال رنگ اختصاصی به هر کارت
        // ============================================
        function applyDepartmentColors() {
            const cards = document.querySelectorAll('#departmentsGrid .dp-card');

            cards.forEach(function (card, index) {
                const color = DEPT_COLORS[index % DEPT_COLORS.length];
                card.style.setProperty('--dept-color', color.base);
                card.style.setProperty('--dept-color-light', color.light);
            });
        }

        // ============================================
        // اجرا بعد از لود DOM
        // ============================================
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', applyDepartmentColors);
        } else {
            applyDepartmentColors();
        }

    })();
