// اسکریپت صفحه: project_roles/list.html

    (function () {
        'use strict';

        // ============================================
        // تولید رنگ روشن از رنگ اصلی
        // ============================================
        function lightenColor(hex, percent) {
            hex = hex.replace('#', '');
            let r = parseInt(hex.substring(0, 2), 16);
            let g = parseInt(hex.substring(2, 4), 16);
            let b = parseInt(hex.substring(4, 6), 16);
            r = Math.min(255, Math.round(r + (255 - r) * percent));
            g = Math.min(255, Math.round(g + (255 - g) * percent));
            b = Math.min(255, Math.round(b + (255 - b) * percent));
            return '#' +
                r.toString(16).padStart(2, '0') +
                g.toString(16).padStart(2, '0') +
                b.toString(16).padStart(2, '0');
        }

        function applyLightColors() {
            const cards = document.querySelectorAll('#rolesGrid .pr-card');
            cards.forEach(function (card) {
                const mainColor = card.style.getPropertyValue('--pr-color').trim();
                if (mainColor) {
                    const lightColor = lightenColor(mainColor, 0.25);
                    card.style.setProperty('--pr-color-light', lightColor);
                }
            });
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', applyLightColors);
        } else {
            applyLightColors();
        }
    })();
