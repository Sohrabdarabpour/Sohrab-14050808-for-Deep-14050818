// اسکریپت صفحه: profile/profile.html

    (function () {
        'use strict';

        document.addEventListener('DOMContentLoaded', function () {

            // ============================================
            // ★★★ آپلود آواتار ★★★
            // ============================================
            const avatarLabel = document.getElementById('pfAvatarLabel');
            const avatarInput = document.getElementById('avatarInput');
            const avatarBtn = document.getElementById('pfAvatarBtn');
            const avatarRemoveBtn = document.getElementById('pfAvatarRemove');
            const avatarImg = document.getElementById('pfAvatarImg');
            const avatarForm = document.getElementById('pfAvatarForm');
            const avatarFormInput = document.getElementById('pfAvatarFormInput');
            const avatarRemoveForm = document.getElementById('pfAvatarRemoveForm');
            const uploadProgress = document.getElementById('pfUploadProgress');
            const uploadProgressBar = document.getElementById('pfUploadProgressBar');

            function openFileDialog() {
                if (avatarInput) avatarInput.click();
            }

            if (avatarLabel && avatarInput) {
                avatarLabel.addEventListener('click', function (e) {
                    if (e.target === avatarInput) return;
                    e.preventDefault();
                    openFileDialog();
                });
            }

            if (avatarBtn) {
                avatarBtn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    openFileDialog();
                });
            }

            // ★ حذف آواتار
            if (avatarRemoveBtn && avatarRemoveForm) {
                avatarRemoveBtn.addEventListener('click', function (e) {
                    e.preventDefault();
                    if (confirm('تصویر پروفایل حذف شود؟')) {
                        avatarRemoveForm.submit();
                    }
                });
            }

            // ============================================
            // ★ اعتبارسنجی و آپلود فایل آواتار
            // ============================================
            function uploadAvatar(file) {
                if (!file) return;

                const validTypes = [
                    'image/png', 'image/jpeg', 'image/jpg',
                    'image/webp', 'image/gif'
                ];
                if (!validTypes.includes(file.type)) {
                    alert('فقط فایل‌های تصویری (PNG، JPG، WebP، GIF) مجاز هستند.');
                    return;
                }

                if (file.size > 5 * 1024 * 1024) {
                    alert('حجم فایل نباید بیشتر از ۵ مگابایت باشد.');
                    return;
                }

                // ★ پیش‌نمایش فوری
                const reader = new FileReader();
                reader.onload = function (ev) {
                    if (avatarImg) avatarImg.src = ev.target.result;
                };
                reader.readAsDataURL(file);

                // ★ آپلود با AJAX برای نمایش پیشرفت
                const formData = new FormData();
                formData.append('avatar', file);
                formData.append('action', 'avatar');

                const xhr = new XMLHttpRequest();
                xhr.open('POST', window.location.href, true);

                if (uploadProgress) {
                    uploadProgress.classList.add('active');
                    uploadProgressBar.style.width = '0%';
                }

                xhr.upload.addEventListener('progress', function (e) {
                    if (e.lengthComputable && uploadProgressBar) {
                        const percent = (e.loaded / e.total) * 100;
                        uploadProgressBar.style.width = percent + '%';
                    }
                });

                xhr.onload = function () {
                    if (uploadProgress) {
                        uploadProgressBar.style.width = '100%';
                        setTimeout(function () {
                            uploadProgress.classList.remove('active');
                        }, 400);
                    }

                    if (xhr.status >= 200 && xhr.status < 300) {
                        window.location.reload();
                    } else {
                        alert('خطا در آپلود تصویر. دوباره تلاش کنید.');
                        window.location.reload();
                    }
                };

                xhr.onerror = function () {
                    if (uploadProgress) {
                        uploadProgress.classList.remove('active');
                    }
                    alert('خطای شبکه. اتصال اینترنت خود را بررسی کنید.');
                };

                xhr.send(formData);
            }

            if (avatarInput) {
                avatarInput.addEventListener('change', function () {
                    if (this.files && this.files.length > 0) {
                        uploadAvatar(this.files[0]);
                    }
                });
            }

            // ============================================
            // ★ Drag & Drop روی آواتار
            // ============================================
            if (avatarLabel) {
                let dragCounter = 0;

                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function (eventName) {
                    avatarLabel.addEventListener(eventName, function (e) {
                        e.preventDefault();
                        e.stopPropagation();
                    });
                });

                avatarLabel.addEventListener('dragenter', function () {
                    dragCounter++;
                    avatarLabel.classList.add('pf-dragover');
                });

                avatarLabel.addEventListener('dragover', function () {
                    avatarLabel.classList.add('pf-dragover');
                });

                avatarLabel.addEventListener('dragleave', function () {
                    dragCounter--;
                    if (dragCounter <= 0) {
                        dragCounter = 0;
                        avatarLabel.classList.remove('pf-dragover');
                    }
                });

                avatarLabel.addEventListener('drop', function (e) {
                    dragCounter = 0;
                    avatarLabel.classList.remove('pf-dragover');

                    const dt = e.dataTransfer;
                    if (dt && dt.files && dt.files.length > 0) {
                        uploadAvatar(dt.files[0]);
                    }
                });
            }

            // ============================================
            // ★★★ نمایش/مخفی رمز عبور ★★★
            // ============================================
            document.querySelectorAll('.pf-toggle-password').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('data-target');
                    const input = document.getElementById(targetId);
                    if (!input) return;

                    const icon = this.querySelector('i');
                    if (input.type === 'password') {
                        input.type = 'text';
                        if (icon) {
                            icon.classList.remove('fa-eye');
                            icon.classList.add('fa-eye-slash');
                        }
                    } else {
                        input.type = 'password';
                        if (icon) {
                            icon.classList.remove('fa-eye-slash');
                            icon.classList.add('fa-eye');
                        }
                    }
                });
            });

            // ============================================
            // ★★★ نشانگر قدرت رمز ★★★
            // ============================================
            const newPassword = document.getElementById('new_password');
            const confirmPassword = document.getElementById('confirm_password');
            const oldPassword = document.getElementById('old_password');
            const passwordStrength = document.getElementById('pfPasswordStrength');
            const passwordStrengthText = document.getElementById('pfPasswordStrengthText');
            const passwordSubmit = document.getElementById('pfPasswordSubmit');

            function calcStrength(pass) {
                if (!pass) return '';
                let score = 0;
                if (pass.length >= 8) score++;
                if (/[a-z]/.test(pass) && /[A-Z]/.test(pass)) score++;
                if (/[0-9]/.test(pass)) score++;
                if (/[^a-zA-Z0-9]/.test(pass)) score++;

                if (pass.length < 8) return 'weak';
                if (score <= 2) return 'weak';
                if (score === 3) return 'medium';
                return 'strong';
            }

            function updateStrength() {
                if (!newPassword || !passwordStrength) return;
                const value = newPassword.value;
                const strength = calcStrength(value);

                passwordStrength.setAttribute('data-strength', strength);

                if (passwordStrengthText) {
                    if (!value) {
                        passwordStrengthText.textContent = 'حداقل ۸ کاراکتر شامل حرف و عدد';
                        passwordStrengthText.style.color = '';
                    } else if (strength === 'weak') {
                        passwordStrengthText.textContent = 'ضعیف';
                        passwordStrengthText.style.color = '#ef4444';
                    } else if (strength === 'medium') {
                        passwordStrengthText.textContent = 'متوسط';
                        passwordStrengthText.style.color = '#f59e0b';
                    } else if (strength === 'strong') {
                        passwordStrengthText.textContent = 'قوی';
                        passwordStrengthText.style.color = '#22c55e';
                    }
                }

                validatePasswordForm();
            }

            // ============================================
            // ★★★ اعتبارسنجی فرم رمز ★★★
            // ============================================
            function validatePasswordForm() {
                if (!passwordSubmit) return;
                let valid = true;

                if (!oldPassword || !oldPassword.value.trim()) {
                    valid = false;
                }

                if (!newPassword || newPassword.value.length < 8) {
                    valid = false;
                }

                if (!confirmPassword ||
                    confirmPassword.value !== newPassword.value ||
                    !confirmPassword.value) {
                    valid = false;
                }

                passwordSubmit.disabled = !valid;
            }

            if (newPassword) {
                newPassword.addEventListener('input', updateStrength);
            }

            if (confirmPassword) {
                confirmPassword.addEventListener('input', function () {
                    const errorEl = document.querySelector('[data-error="confirm_password"]');
                    if (this.value && this.value !== newPassword.value) {
                        this.classList.add('pf-invalid');
                        if (errorEl) errorEl.classList.add('visible');
                    } else {
                        this.classList.remove('pf-invalid');
                        if (errorEl) errorEl.classList.remove('visible');
                    }
                    validatePasswordForm();
                });
            }

            if (oldPassword) {
                oldPassword.addEventListener('input', validatePasswordForm);
            }

            // ============================================
            // ★★★ اعتبارسنجی فرم پروفایل ★★★
            // ============================================
            const profileForm = document.getElementById('pfProfileForm');
            const fullNameInput = document.getElementById('full_name');
            const emailInput = document.getElementById('email');
            const phoneInput = document.getElementById('phone');
            const nationalCodeInput = document.getElementById('national_code');

            function showError(fieldName, show) {
                const input = document.getElementById(fieldName);
                const errorEl = document.querySelector(`[data-error="${fieldName}"]`);
                if (show) {
                    if (input) input.classList.add('pf-invalid');
                    if (errorEl) errorEl.classList.add('visible');
                } else {
                    if (input) input.classList.remove('pf-invalid');
                    if (errorEl) errorEl.classList.remove('visible');
                }
            }

            function validateProfileField(field) {
                if (!field) return true;

                if (field === fullNameInput) {
                    const ok = field.value.trim().length >= 3;
                    showError('full_name', !ok);
                    return ok;
                }
                if (field === emailInput) {
                    const value = field.value.trim();
                    if (!value) {
                        showError('email', false);
                        return true;
                    }
                    const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                    showError('email', !ok);
                    return ok;
                }
                if (field === phoneInput) {
                    const value = field.value.trim();
                    if (!value) {
                        showError('phone', false);
                        return true;
                    }
                    const ok = /^09\d{9}$/.test(value);
                    showError('phone', !ok);
                    return ok;
                }
                if (field === nationalCodeInput) {
                    const value = field.value.trim();
                    if (!value) {
                        showError('national_code', false);
                        return true;
                    }
                    const ok = /^\d{10}$/.test(value);
                    showError('national_code', !ok);
                    return ok;
                }
                return true;
            }

            [fullNameInput, emailInput, phoneInput, nationalCodeInput].forEach(function (input) {
                if (!input) return;
                input.addEventListener('blur', function () {
                    validateProfileField(input);
                });
                input.addEventListener('input', function () {
                    if (input.classList.contains('pf-invalid')) {
                        validateProfileField(input);
                    }
                });
            });

            if (profileForm) {
                profileForm.addEventListener('submit', function (e) {
                    const ok = [fullNameInput, emailInput, phoneInput, nationalCodeInput]
                        .map(validateProfileField)
                        .every(Boolean);

                    if (!ok) {
                        e.preventDefault();
                        const firstInvalid = profileForm.querySelector('.pf-invalid');
                        if (firstInvalid) firstInvalid.focus();
                    }
                });
            }

        });
    })();
