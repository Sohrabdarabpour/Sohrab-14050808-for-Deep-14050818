// اسکریپت صفحه: documents/view.html

        (async function () {
            const container = document.getElementById('workflowHistory');
            if (!container) return;
            const docId = container.dataset.documentId;

            try {
                const res = await fetch(`/workflow/history/${docId}`);
                const data = await res.json();

                if (!data.success || !data.history || data.history.length === 0) {
                    container.innerHTML = `
                        <div class="dv-timeline-loading" style="color:#94a3b8;">
                            <i class="fa-solid fa-note-sticky" style="font-size:2rem;opacity:.4;"></i>
                            هنوز یادداشتی برای این سند ثبت نشده
                        </div>
                    `;
                    return;
                }

                const badge = document.getElementById('historyCount');
                if (badge) {
                    badge.textContent = data.history.length + ' رخداد';
                    badge.style.display = 'inline-block';
                }

                // ★ نگاشت event_type به رنگ و آیکن
                const eventConfig = {
                    'submit':  { color: '#1b698b', icon: 'fa-paper-plane',    label: 'ثبت یادداشت' },
                    'comment': { color: '#7c3aed', icon: 'fa-comment',        label: 'کامنت' },
                    'approve': { color: '#16a34a', icon: 'fa-circle-check',   label: 'تایید' },
                    'reject':  { color: '#dc2626', icon: 'fa-circle-xmark',   label: 'رد' },
                    'return':  { color: '#0891b2', icon: 'fa-rotate-left',    label: 'برگشت' },
                    'forward': { color: '#6366f1', icon: 'fa-share',          label: 'ارجاع' },
                    'close':   { color: '#059669', icon: 'fa-flag-checkered', label: 'خاتمه' },
                    'reopen':  { color: '#f59e0b', icon: 'fa-lock-open',      label: 'بازگشایی' },
                    'edit':    { color: '#a855f7', icon: 'fa-pen',            label: 'ویرایش' },
                };

                const items = data.history.map(function (item) {
                    const evType = item.event_type || 'comment';
                    const cfg = eventConfig[evType] || eventConfig['comment'];

                    const senderName = item.user_full_name || 'کاربر';
                    const time = item.created_at_jalali || (item.created_at || '').substring(0, 16);

                    // ساخت label بر اساس نوع رخداد
                    let label = senderName + ' — ' + cfg.label;
                    if (evType === 'approve' && item.to_user_name) {
                        label = senderName + ' تایید و ارسال به ' + item.to_user_name;
                    } else if (evType === 'return' && item.to_user_name) {
                        label = senderName + ' برگشت به ' + item.to_user_name;
                    } else if (evType === 'forward' && item.to_user_name) {
                        label = senderName + ' ارجاع به ' + item.to_user_name;
                    }

                    // مسیر مرحله‌ها
                    let stepsHtml = '';
                    if (item.from_step_title || item.to_step_title) {
                        const from = item.from_step_title || '';
                        const to = item.to_step_title || '';
                        let path = '';
                        if (from && to && from !== to) {
                            path = `<strong>${from}</strong> <i class="fa-solid fa-arrow-left" style="font-size:.6rem;color:#94a3b8;"></i> <strong>${to}</strong>`;
                        } else if (to) {
                            path = `<strong>${to}</strong>`;
                        } else if (from) {
                            path = `<strong>${from}</strong>`;
                        }
                        if (path) {
                            stepsHtml = `<div class="wl-steps">${path}</div>`;
                        }
                    }

                    // پیام
                    let msgHtml = '';
                    if (item.message) {
                        msgHtml = `<div class="wl-comment" style="border-color: ${cfg.color}40; background: ${cfg.color}08;">
                            <i class="fa-solid fa-comment-dots" style="color: ${cfg.color};"></i>
                            <span>${item.message}</span>
                        </div>`;
                    }

                    return `
                        <div class="wl-item" style="--tl-color: ${cfg.color};">
                            <div class="wl-dot">
                                <i class="fa-solid ${cfg.icon}"></i>
                            </div>
                            <div class="wl-body">
                                <div class="wl-head">
                                    <span class="wl-action-badge"
                                          style="background: ${cfg.color}15; color: ${cfg.color}; border-color: ${cfg.color}30;">
                                        <i class="fa-solid ${cfg.icon}"></i>
                                        ${label}
                                    </span>
                                    <span class="wl-time">${time}</span>
                                </div>
                                ${stepsHtml}
                                ${msgHtml}
                            </div>
                        </div>
                    `;
                }).join('');

                container.innerHTML = '<div class="wl-timeline">' + items + '</div>';

            } catch (err) {
                console.error(err);
                container.innerHTML =
                    '<p style="text-align:center;color:#dc2626;padding:20px;">خطا در دریافت تاریخچه</p>';
            }
        })();
    
