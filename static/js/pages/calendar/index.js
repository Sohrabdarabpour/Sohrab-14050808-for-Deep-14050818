(function () {
    "use strict";

    var reasonDialog = document.getElementById("holidayReasonDialog");
    var reasonForm = document.getElementById("holidayReasonForm");
    var reasonDate = document.getElementById("holidayReasonDate");
    var reasonDateLabel = document.getElementById("holidayReasonDateLabel");
    var reasonInput = document.getElementById("holidayReasonInput");
    var cancelButton = document.getElementById("holidayReasonCancel");

    document.querySelectorAll(".day-toggle-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (form.dataset.hasHoliday === "true" || !reasonDialog || !reasonForm) {
                return;
            }

            event.preventDefault();
            var dateInput = form.querySelector('input[name="date"]');
            if (!dateInput) {
                return;
            }

            reasonDate.value = dateInput.value;
            reasonDateLabel.textContent = "تاریخ انتخاب‌شده: " + dateInput.value;
            reasonInput.value = "";
            reasonDialog.showModal();
            reasonInput.focus();
        });
    });

    if (cancelButton && reasonDialog) {
        cancelButton.addEventListener("click", function () {
            reasonDialog.close();
        });
    }

    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.getAttribute("data-confirm"))) {
                event.preventDefault();
            }
        });
    });
})();
