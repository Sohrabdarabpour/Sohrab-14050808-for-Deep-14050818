// اسکریپت صفحه: projects/form.html

    (function () {
        'use strict';
        const form = document.getElementById('projectForm');
        if (!form) return;

        // اعتبارسنجی سریع
        const validators = {
            name: (v) => {
                v = (v || '').trim();
                if (!v) return 'نام پروژه الزامی است';
                if (v.length < 3) return 'نام باید حداقل ۳ کاراکتر باشد';
                return null;
            },
            progress_percent: (v) => {
                v = (v || '').trim();
                if (!v) return null;
                const n = Number(v);
                if (isNaN(n) || n < 0 || n > 100)
                    return 'درصد باید بین ۰ تا ۱۰۰ باشد';
                return null;
            }
        };

        function showError(name, msg) {
            const field = form.querySelector(`[name="${name}"]`);
            if (!field) return;
            const wrap = field.closest('.pf-field');
            const el = form.querySelector(`[data-error-for="${name}"]`);
            if (msg) {
                wrap?.classList.add('has-error');
                if (el) {
                    el.querySelector('span').textContent = msg;
                    el.classList.add('show');
                }
            } else {
                wrap?.classList.remove('has-error');
                el?.classList.remove('show');
            }
        }

        Object.keys(validators).forEach((name) => {
            const field = form.querySelector(`[name="${name}"]`);
            if (!field) return;
            field.addEventListener('blur', () => {
                showError(name, validators[name](field.value));
            });
        });

        form.addEventListener('submit', (e) => {
            let hasError = false;
            Object.keys(validators).forEach((name) => {
                const field = form.querySelector(`[name="${name}"]`);
                if (!field) return;
                const err = validators[name](field.value);
                showError(name, err);
                if (err) hasError = true;
            });
            if (hasError) {
                e.preventDefault();
                form.querySelector('.pf-field.has-error')
                    ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });

        // Ctrl+S
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                form.requestSubmit();
            }
        });
    })();
