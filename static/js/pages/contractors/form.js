// اسکریپت صفحه: contractors/form.html

    (function () {
        'use strict';

        // ============================================
        // اعتبارسنجی سمت کلاینت (سبک)
        // ============================================
        const form = document.getElementById('contractorForm');
        if (!form) return;

        const validators = {
            name: (v) => {
                v = (v || '').trim();
                if (!v) return 'نام پیمانکار الزامی است';
                if (v.length < 3) return 'نام باید حداقل ۳ کاراکتر باشد';
                return null;
            },
            mobile: (v) => {
                v = (v || '').trim();
                if (!v) return null;
                if (!/^\d+$/.test(v)) return 'موبایل باید فقط عدد باشد';
                if (!v.startsWith('09')) return 'موبایل باید با ۰۹ شروع شود';
                if (v.length !== 11) return 'موبایل باید ۱۱ رقم باشد';
                return null;
            },
            email: (v) => {
                v = (v || '').trim();
                if (!v) return null;
                if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return 'ایمیل نامعتبر است';
                return null;
            }
        };

        function showError(fieldName, message) {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            const fieldWrap = field.closest('.cf-field');
            const errorEl = form.querySelector(`[data-error-for="${fieldName}"]`);

            if (message) {
                fieldWrap?.classList.add('has-error');
                if (errorEl) {
                    errorEl.querySelector('span').textContent = message;
                    errorEl.classList.add('show');
                }
            } else {
                fieldWrap?.classList.remove('has-error');
                if (errorEl) {
                    errorEl.classList.remove('show');
                }
            }
        }

        function validateField(fieldName) {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field || !validators[fieldName]) return true;

            const error = validators[fieldName](field.value);
            showError(fieldName, error);
            return !error;
        }

        // اعتبارسنجی لحظه‌ای
        Object.keys(validators).forEach((fieldName) => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            field.addEventListener('blur', () => validateField(fieldName));
            field.addEventListener('input', () => {
                if (field.closest('.cf-field')?.classList.contains('has-error')) {
                    validateField(fieldName);
                }
            });
        });

        // اعتبارسنجی نهایی روی submit
        form.addEventListener('submit', (e) => {
            let hasError = false;
            Object.keys(validators).forEach((fieldName) => {
                if (!validateField(fieldName)) {
                    hasError = true;
                }
            });

            if (hasError) {
                e.preventDefault();
                // اسکرول به اولین خطا
                const firstError = form.querySelector('.cf-field.has-error');
                firstError?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });

        // ============================================
        // Ctrl+S برای ذخیره سریع
        // ============================================
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                form.requestSubmit();
            }
        });
    })();
