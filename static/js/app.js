document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;
    const sidebar = document.querySelector(".app-sidebar");
    const overlay = document.querySelector(".sidebar-overlay");
    const desktopToggle = document.getElementById("sidebarToggleBtn");
    const mobileToggle = document.getElementById("mobileMenuBtn");
    const dropdowns = document.querySelectorAll(".sidebar-dropdown");

    const MOBILE_BREAKPOINT = 992;

    /* ---------- helpers ---------- */
    function isMobile() {
        return window.innerWidth <= MOBILE_BREAKPOINT;
    }

    function closeMobileSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (overlay) overlay.classList.remove("show");
        body.classList.remove("sidebar-mobile-open");
    }

    function openMobileSidebar() {
        if (sidebar) sidebar.classList.add("open");
        if (overlay) overlay.classList.add("show");
        body.classList.add("sidebar-mobile-open");
    }

    /* ---------- desktop collapse ---------- */
    if (desktopToggle) {
        desktopToggle.addEventListener("click", function () {
            if (isMobile()) return;
            body.classList.toggle("sidebar-collapsed");
            const collapsed = body.classList.contains("sidebar-collapsed");
            localStorage.setItem("sidebarCollapsed", collapsed ? "1" : "0");
        });
    }

    /* ---------- mobile toggle ---------- */
    if (mobileToggle) {
        mobileToggle.addEventListener("click", function () {
            if (!sidebar) return;
            if (sidebar.classList.contains("open")) {
                closeMobileSidebar();
            } else {
                openMobileSidebar();
            }
        });
    }

    /* ---------- overlay click ---------- */
    if (overlay) {
        overlay.addEventListener("click", closeMobileSidebar);
    }

    /* ---------- dropdowns (فقط toggle می‌کنه، آیکون با CSS می‌چرخه) ---------- */
    dropdowns.forEach(function (dropdown) {
        const toggle = dropdown.querySelector(".sidebar-dropdown-toggle");
        if (!toggle) return;

        toggle.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();

            const isOpen = dropdown.classList.contains("open");

            /* ★ فقط هم‌سطح‌ها (siblings) رو می‌بندیم، نه والدها
               اینطوری وقتی روی «گزارش‌ها» کلیک می‌کنی،
               «منوی اصلی» باز می‌مونه */
            const parentList = dropdown.parentElement;
            if (parentList) {
                parentList.querySelectorAll(":scope > .sidebar-dropdown.open").forEach(function (sibling) {
                    if (sibling !== dropdown) sibling.classList.remove("open");
                });
            }

            /* toggle خودش */
            dropdown.classList.toggle("open", !isOpen);
        });
    });

    /* ★ جلوگیری از بسته شدن منوی اصلی وقتی روی لینک‌های داخلش کلیک می‌شه */
    if (sidebar) {
        sidebar.querySelectorAll(".sidebar-submenu .sidebar-link:not(.sidebar-dropdown-toggle)").forEach(function (link) {
            link.addEventListener("click", function (e) {
                e.stopPropagation();
            });
        });
    }

    /* ---------- restore desktop collapse ---------- */
    if (!isMobile() && localStorage.getItem("sidebarCollapsed") === "1") {
        body.classList.add("sidebar-collapsed");
    }

    /* ---------- resize (با debounce) ---------- */
    let resizeTimer;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            if (!isMobile()) {
                closeMobileSidebar();
                if (localStorage.getItem("sidebarCollapsed") === "1") {
                    body.classList.add("sidebar-collapsed");
                }
            } else {
                body.classList.remove("sidebar-collapsed");
            }
        }, 150);
    });

    /* ---------- close on ESC ---------- */
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeMobileSidebar();
    });
});