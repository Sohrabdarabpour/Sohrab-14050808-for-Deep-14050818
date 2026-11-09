// اسکریپت صفحه: excel/import.html

    (function () {
        'use strict';

        const fileInput = document.getElementById('excelFile');
        const fileLabel = document.getElementById('xlFileLabel');
        const fileSelected = document.getElementById('xlFileSelected');
        const fileNameEl = document.getElementById('xlFileName');
        const fileSizeEl = document.getElementById('xlFileSize');
        const fileRemove = document.getElementById('xlFileRemove');
        const submitBtn = document.getElementById('xlSubmitBtn');

        if (!fileInput || !fileLabel || !fileSelected) return;

        // ============================================
        // فرمت حجم فایل
        // ============================================
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' بایت';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' کیلوبایت';
            return (bytes / (1024 * 1024)).toFixed(2) + ' مگابایت';
        }

        // ============================================
        // نمایش فایل
        // ============================================
        function showFile(file) {
            if (!file) return;

            const name = file.name || '';
            const validExt = /\.(xlsx|xls)$/i.test(name);

            if (!validExt) {
                alert('فقط فایل‌های Excel با پسوند xlsx یا xls مجاز هستند.');
                resetFile();
                return;
            }

            fileNameEl.textContent = name;
            fileSizeEl.textContent = formatSize(file.size);

            fileSelected.classList.add('show');
            fileLabel.style.display = 'none';
            submitBtn.disabled = false;
        }

        // ============================================
        // پاک کردن فایل
        // ============================================
        function resetFile() {
            fileInput.value = '';
            fileSelected.classList.remove('show');
            fileLabel.style.display = 'flex';
            fileNameEl.textContent = '';
            fileSizeEl.textContent = '';
            submitBtn.disabled = true;
        }

        // ============================================
        // انتخاب از طریق input
        // ============================================
        fileInput.addEventListener('change', function () {
            if (this.files && this.files.length > 0) {
                showFile(this.files[0]);
            } else {
                resetFile();
            }
        });

        // ============================================
        // حذف فایل
        // ============================================
        fileRemove.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            resetFile();
        });

        // ============================================
        // Drag & Drop
        // ============================================
        let dragCounter = 0;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function (eventName) {
            fileLabel.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        fileLabel.addEventListener('dragenter', function () {
            dragCounter++;
            fileLabel.classList.add('xl-dragover');
        });

        fileLabel.addEventListener('dragover', function () {
            fileLabel.classList.add('xl-dragover');
        });

        fileLabel.addEventListener('dragleave', function () {
            dragCounter--;
            if (dragCounter <= 0) {
                dragCounter = 0;
                fileLabel.classList.remove('xl-dragover');
            }
        });

        fileLabel.addEventListener('drop', function (e) {
            dragCounter = 0;
            fileLabel.classList.remove('xl-dragover');

            const dt = e.dataTransfer;
            if (!dt) return;

            const files = dt.files;
            if (files && files.length > 0) {
                try {
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(files[0]);
                    fileInput.files = dataTransfer.files;
                } catch (err) {
                    console.warn('DataTransfer not supported:', err);
                }
                showFile(files[0]);
            }
        });

    })();
