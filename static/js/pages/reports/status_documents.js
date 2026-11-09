// اسکریپت صفحه: reports/status_documents.html

    let searchTimeout = null;
    document.addEventListener("DOMContentLoaded", function () {
        const searchInput = document.getElementById("searchInput");
        const searchClear = document.getElementById("searchClear");
        const yearFilter = document.getElementById("yearFilter");
        const clearFilters = document.getElementById("clearFilters");
        if (searchInput) {
            if (searchInput.value.trim() !== "") {
                if (searchClear) {
                    searchClear.classList.add("visible");
                }
            }
            searchInput.addEventListener("input", function () {
                if (searchClear) {
                    searchClear.classList.toggle("visible", searchInput.value.trim() !== "");
                }
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(function () {
                    const url = new URL(window.location.href);
                    const value = searchInput.value.trim();
                    if (value) {
                        url.searchParams.set("search", value);
                    } else {
                        url.searchParams.delete("search");
                    }
                    url.searchParams.delete("page");
                    window.location.href = url.toString();
                }, 600);
            });
        }
        if (searchClear) {
            searchClear.addEventListener("click", function () {
                if (searchInput) {
                    searchInput.value = "";
                }
                const url = new URL(window.location.href);
                url.searchParams.delete("search");
                url.searchParams.delete("page");
                window.location.href = url.toString();
            });
        }
        if (yearFilter) {
            yearFilter.addEventListener("change", function () {
                const url = new URL(window.location.href);
                url.searchParams.set("year", yearFilter.value);
                url.searchParams.delete("page");
                window.location.href = url.toString();
            });
        }
        if (clearFilters) {
            clearFilters.addEventListener("click", function () {
                const url = new URL(window.location.href);
                url.searchParams.delete("year");
                url.searchParams.delete("search");
                url.searchParams.delete("page");
                window.location.href = url.pathname;
            });
        }
        document.addEventListener("keydown", function (e) {
            if ((e.ctrlKey || e.metaKey) && e.key === "k") {
                e.preventDefault();
                if (searchInput) {
                    searchInput.focus();
                }
            }
        });
    });
    function toggleExpand(btn) {
        const content = btn.parentElement.querySelector(".doc-expand-content");
        const text = btn.querySelector(".btn-text");
        const icon = btn.querySelector("i");
        const isOpen = content.classList.contains("open");
        if (isOpen) {
            content.classList.remove("open");
            content.style.maxHeight = "0";
            content.style.opacity = "0";
            content.style.marginTop = "0";
            text.textContent = "نمایش جزئیات بیشتر";
            btn.classList.remove("expanded");
            icon.style.transform = "rotate(0deg)";
        } else {
            content.classList.add("open");
            content.style.maxHeight = "1200px";
            content.style.opacity = "1";
            content.style.marginTop = "16px";
            text.textContent = "بستن جزئیات";
            btn.classList.add("expanded");
            icon.style.transform = "rotate(45deg)";
        }
    }
