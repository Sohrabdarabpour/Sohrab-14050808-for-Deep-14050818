// اسکریپت صفحه: login.html

    document.addEventListener('DOMContentLoaded', function () {
        const togglePassword = document.getElementById('togglePassword');
        const passwordInput = document.getElementById('passwordInput');
        let isPasswordVisible = false;

        if (togglePassword && passwordInput) {
            function togglePasswordVisibility(e) {
                if (e) { e.preventDefault(); e.stopPropagation(); }
                isPasswordVisible = !isPasswordVisible;
                passwordInput.setAttribute('type', isPasswordVisible ? 'text' : 'password');
                const icon = togglePassword.querySelector('i');
                if (icon) {
                    icon.classList.toggle('bi-eye', !isPasswordVisible);
                    icon.classList.toggle('bi-eye-slash', isPasswordVisible);
                }
                const pos = passwordInput.value.length;
                passwordInput.focus({ preventScroll: true });
                try { passwordInput.setSelectionRange(pos, pos); } catch (_) {}
            }
            togglePassword.addEventListener('click', togglePasswordVisibility);
            togglePassword.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    togglePasswordVisibility(e);
                }
            });
        }

        const usernameInput = document.getElementById('usernameInput');

        function validateField(field) {
            const value = field.value.trim();
            if (field.id === 'usernameInput') {
                if (value.length === 0 || value.length < 3) { field.classList.remove('is-valid'); field.classList.add('is-invalid'); }
                else { field.classList.remove('is-invalid'); field.classList.add('is-valid'); }
            } else if (field.id === 'passwordInput') {
                if (value.length === 0 || value.length < 6) { field.classList.remove('is-valid'); field.classList.add('is-invalid'); }
                else { field.classList.remove('is-invalid'); field.classList.add('is-valid'); }
            }
        }

        if (usernameInput) {
            usernameInput.addEventListener('blur', function () { validateField(this); });
            usernameInput.addEventListener('input', function () {
                if (this.classList.contains('is-invalid') || this.classList.contains('is-valid')) validateField(this);
            });
        }
        if (passwordInput) {
            passwordInput.addEventListener('blur', function () { validateField(this); });
            passwordInput.addEventListener('input', function () {
                if (this.classList.contains('is-invalid') || this.classList.contains('is-valid')) validateField(this);
            });
        }

        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', function (e) {
                const submitBtn = document.getElementById('loginButton');
                const username = document.getElementById('usernameInput');
                const password = document.getElementById('passwordInput');
                let isValid = true;

                if (!username || username.value.trim().length < 3) {
                    if (username) { username.classList.add('is-invalid'); username.classList.remove('is-valid'); }
                    isValid = false;
                }
                if (!password || password.value.trim().length < 6) {
                    if (password) { password.classList.add('is-invalid'); password.classList.remove('is-valid'); }
                    isValid = false;
                }

                if (!isValid) {
                    e.preventDefault();
                    if (username && username.classList.contains('is-invalid')) username.focus();
                    else if (password && password.classList.contains('is-invalid')) password.focus();
                    return;
                }

                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = 'در حال ورود <span class="button-spinner"></span>';
                }
            });
        }

        const rememberMe = document.getElementById('rememberMe');
        if (rememberMe) {
            const saved = localStorage.getItem('rememberMe');
            if (saved === 'true') {
                rememberMe.checked = true;
                if (usernameInput) {
                    const savedUsername = localStorage.getItem('savedUsername');
                    if (savedUsername) { usernameInput.value = savedUsername; usernameInput.dispatchEvent(new Event('blur')); }
                }
            }
            rememberMe.addEventListener('change', function () {
                localStorage.setItem('rememberMe', this.checked);
                if (this.checked && usernameInput) localStorage.setItem('savedUsername', usernameInput.value);
                else localStorage.removeItem('savedUsername');
            });
        }

        if (usernameInput && !usernameInput.value) {
            setTimeout(function () { usernameInput.focus(); }, 400);
        }

        function showAlert(type, message) {
            const container = document.querySelector('.flash-container');
            if (!container) {
                const form = document.querySelector('.login-form');
                if (!form) return;
                const newContainer = document.createElement('div');
                newContainer.className = 'flash-container';
                form.insertBefore(newContainer, form.firstChild);
                setTimeout(function () { showAlert(type, message); }, 100);
                return;
            }
            const existingAlerts = container.querySelectorAll('.alert-custom');
            existingAlerts.forEach(alert => {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.3s ease';
                setTimeout(() => { if (alert.parentNode) alert.remove(); }, 300);
            });
            setTimeout(() => {
                const alert = document.createElement('div');
                const iconMap = { 'success': 'bi-check-circle-fill', 'danger': 'bi-exclamation-circle-fill', 'warning': 'bi-exclamation-triangle-fill', 'info': 'bi-info-circle-fill' };
                alert.className = 'alert-custom alert-' + type + '-custom';
                alert.innerHTML = '<i class="bi ' + (iconMap[type] || 'bi-info-circle-fill') + '"></i> ' + message;
                container.appendChild(alert);
                setTimeout(() => {
                    alert.style.opacity = '0';
                    alert.style.transition = 'opacity 0.5s ease';
                    setTimeout(() => { if (alert.parentNode) alert.remove(); }, 500);
                }, 5000);
            }, 350);
        }

        document.getElementById('forgotPassword')?.addEventListener('click', function (e) {
            e.preventDefault();
            showAlert('info', 'لطفاً با پشتیبانی سیستم تماس بگیرید.');
        });
        document.getElementById('helpLink')?.addEventListener('click', function (e) {
            e.preventDefault();
            showAlert('info', 'راهنمای سامانه به زودی ارائه می‌شود.');
        });
    });
