// اسکریپت صفحه: document_group/groups/import.html

    (function () {
        'use strict';

        document.addEventListener('DOMContentLoaded', function () {
            const fileInput = document.getElementById('fileInput');
            const fileInfo = document.getElementById('fileInfo');
            const fileName = document.getElementById('fileName');
            const removeFile = document.getElementById('removeFile');
            const submitBtn = document.getElementById('submitBtn');
            const importForm = document.getElementById('importForm');

            // ★ نمایش فایل انتخاب‌شده
            fileInput?.addEventListener('change', function () {
                if (this.files && this.files.length > 0) {
                    const file = this.files[0];

                    // ★ چک فرمت
                    const ext = file.name.split('.').pop().toLowerCase();
                    if (!['xlsx', 'xls'].includes(ext)) {
                        alert('فرمت فایل باید Excel باشد (.xlsx یا .xls)');
                        this.value = '';
                        return;
                    }

                    fileName.textContent = file.name +
                        ' (' + (file.size / 1024).toFixed(1) + ' KB)';
                    fileInfo.classList.add('visible');
                    submitBtn.disabled = false;
                } else {
                    fileInfo.classList.remove('visible');
                    submitBtn.disabled = true;
                }
            });

            // ★ حذف فایل
            removeFile?.addEventListener('click', function () {
                fileInput.value = '';
                fileInfo.classList.remove('visible');
                submitBtn.disabled = true;
            });

            // ★ تأیید در حالت replace
            importForm?.addEventListener('submit', function (e) {
                const mode = document.querySelector(
                    'input[name="mode"]:checked'
                )?.value;

                if (mode === 'replace') {
                    const confirmed = confirm(
                        'هشدار!\n\n' +
                        'در حالت جایگزینی کامل، تمام گروه‌های قبلی حذف خواهند شد.\n' +
                        'آیا مطمئن هستید؟'
                    );

                    if (!confirmed) {
                        e.preventDefault();
                        return false;
                    }
                }

                // ★ نمایش وضعیت بارگذاری
                submitBtn.disabled = true;
                submitBtn.innerHTML =
                    '<i class="fa-solid fa-spinner fa-spin"></i> در حال پردازش...';
            });
        });
    })();
