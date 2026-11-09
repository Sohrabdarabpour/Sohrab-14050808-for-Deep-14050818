"""
دستیار هوشمند - روت‌های کامل
================================
- صفحه چت
- API پرسش/پاسخ
- جزئیات سند (مودال) ★ با تاریخ شمسی
- تاریخچه گفتگو
- بازخورد کاربر (👍/👎)
- پیشنهادات هوشمند
- پاک کردن گفتگو
- آمار استفاده
- Health check
"""
from flask import (
    Blueprint, render_template, request, jsonify,
    session, redirect, url_for, current_app ,
    send_file,
)
from functools import wraps
from datetime import datetime, timedelta
from html import escape
import time

from services.ai import AssistantService, Cache, ConversationContext
from database.connection import get_connection
from helpers.date_helper import DateHelper


assistant_bp = Blueprint("assistant", __name__, url_prefix="/assistant")


# ============================================================
# ★ فیلدهای تاریخ که باید به شمسی تبدیل بشن
# ============================================================
DATE_FIELDS = [
    "date_letter",
    "date_received",
    "date_referral",
    "deadline",
    "response_announce_date",
    "created_at",
    "updated_at",
]


# ============================================================
# ★ Decorators
# ============================================================
def login_required(f):
    """بررسی احراز هویت"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.path.endswith("/api"):
                return jsonify({
                    "ok": False,
                    "error": "unauthorized",
                    "message": "لطفاً وارد سیستم شوید."
                }), 401
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """فقط برای ادمین/مدیر"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        role = session.get("role", "expert")
        if role not in ("admin", "manager"):
            return jsonify({
                "ok": False,
                "error": "forbidden",
                "message": "دسترسی محدود است."
            }), 403
        return f(*args, **kwargs)
    return wrapper


def json_error(message, code=400, error="bad_request"):
    """پاسخ خطای استاندارد JSON"""
    return jsonify({
        "ok": False,
        "error": error,
        "message": message
    }), code


# ============================================================
# ★ Helpers
# ============================================================
def get_user_context():
    """اطلاعات کاربر فعلی"""
    return {
        "user_id": session.get("user_id"),
        "role": session.get("role", "expert"),
        "is_admin": session.get("role") in ("admin", "manager"),
        "full_name": session.get("full_name", "کاربر"),
    }


def convert_dates_to_jalali(doc, fields=None):
    """
    تبدیل فیلدهای تاریخ یک سند به شمسی

    Args:
        doc: dict سند
        fields: لیست فیلدهای تاریخ (پیش‌فرض DATE_FIELDS)

    Returns:
        dict با تاریخ‌های شمسی
    """
    if not doc:
        return doc

    fields = fields or DATE_FIELDS

    for field in fields:
        if doc.get(field):
            try:
                doc[field] = DateHelper.format_jalali(doc[field])
            except Exception:
                # اگه خطا داد، مقدار خام رو نگه دار
                pass

    return doc


def log_query(user_id, question, intent, elapsed_ms, status="ok"):
    """ثبت لاگ کوئری (اختیاری - اگر جدول داشته باشی)"""
    try:
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO assistant_logs
                (user_id, question, intent, elapsed_ms, status, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, question[:500], intent, elapsed_ms, status))
            conn.commit()
        except Exception:
            # جدول assistant_logs باید در init_db ساخته شود؛ اگر نشد،
            # حداقل خطا را برای عیب‌یابی ثبت کن (قبلاً بی‌صدا دور ریخته می‌شد).
            current_app.logger.debug("assistant log insert failed", exc_info=True)
        finally:
            conn.close()
    except Exception:
        pass


# ============================================================
# ★ صفحه اصلی چت
# ============================================================
@assistant_bp.route("/", methods=["GET"])
@login_required
def index():
    """صفحه چت دستیار"""
    ctx = get_user_context()
    return render_template(
        "ai/assistant/index.html",
        user=ctx,
        now=datetime.now()
    )


# ============================================================
# ★ API اصلی: پرسش و پاسخ
# ============================================================
@assistant_bp.route("/ask", methods=["POST"])
@login_required
def ask():
    """
    دریافت سوال کاربر و بازگشت پاسخ

    Body:
        {
            "question": "...",
            "debug": false
        }

    Response:
        {
            "answer": "...",
            "type": "text|count|list|stats|chart|help|error",
            "data": [...],
            "suggestions": [...],
            "meta": {...}
        }
    """
    start_time = time.time()

    # ---- Parse JSON ----
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    debug = bool(data.get("debug", False))

    # ---- Validate ----
    if not question:
        return json_error(
            '<i class="fa-solid fa-circle-question" style="color:#3D8499"></i> '
            'سوالی وارد نکردید.',
            code=400,
            error="empty_question"
        )

    if len(question) > 500:
        question = question[:500]

    # ---- Context ----
    ctx = get_user_context()

    # ---- Execute ----
    try:
        result = AssistantService.ask(
            question,
            user_id=ctx["user_id"],
            is_admin=ctx["is_admin"],
            debug=debug or current_app.debug
        )

        # ---- Log ----
        elapsed_ms = int((time.time() - start_time) * 1000)
        intent = result.get("meta", {}).get("intent", "unknown")
        log_query(ctx["user_id"], question, intent, elapsed_ms)

        return jsonify(result)

    except Exception as e:
        current_app.logger.exception("Assistant error")
        return json_error(
            f'<i class="fa-solid fa-bug" style="color:#ef4444"></i> '
            f'خطای داخلی سرور: {str(e) if current_app.debug else "لطفاً دوباره تلاش کنید."}',
            code=500,
            error="internal_error"
        )


# ============================================================
# ★ API: جزئیات کامل سند (برای مودال) ★ با تاریخ شمسی
# ============================================================
@assistant_bp.route("/document/<int:doc_id>", methods=["GET"])
@login_required
def document_details(doc_id):
    """
    دریافت جزئیات کامل یک سند برای نمایش در مودال
    ★ تاریخ‌ها به شمسی تبدیل می‌شن
    """
    ctx = get_user_context()

    try:
        conn = get_connection()
        try:
            sql = """
                SELECT d.*,
                       s.title AS status_title, s.color AS status_color,
                       a.title AS area_title,
                       dep.title AS department_title,
                       g.title AS group_title,
                       sg.title AS subgroup_title,
                       u.full_name AS user_full_name,
                       u.username AS user_username
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                LEFT JOIN areas a ON a.id = d.area_id
                LEFT JOIN departments dep ON dep.id = d.department_id
                LEFT JOIN document_groups g ON g.id = d.group_id
                LEFT JOIN document_subgroups sg ON sg.id = d.subgroup_id
                LEFT JOIN users u ON u.id = d.user_id
                WHERE d.id = ?
            """
            row = conn.execute(sql, (doc_id,)).fetchone()

            if not row:
                return jsonify({
                    "ok": False,
                    "error": "not_found",
                    "message": "سند پیدا نشد."
                }), 404

            doc = dict(row)

            # ---- چک دسترسی ----
            if not ctx["is_admin"] and doc.get("user_id") != ctx["user_id"]:
                return jsonify({
                    "ok": False,
                    "error": "forbidden",
                    "message": "دسترسی به این سند ندارید."
                }), 403

            # ★★★ تبدیل تاریخ‌های میلادی به شمسی ★★★
            doc = convert_dates_to_jalali(doc)

            # ---- عملیات مجاز بر اساس نقش ----
            doc["permissions"] = {
                "can_edit": ctx["is_admin"] or doc.get("user_id") == ctx["user_id"],
                "can_delete": ctx["is_admin"],
                "can_change_status": ctx["is_admin"] or doc.get("user_id") == ctx["user_id"],
            }

            return jsonify({"ok": True, "document": doc})

        finally:
            conn.close()

    except Exception as e:
        current_app.logger.exception("Document details error")
        return json_error(
            f"خطا در دریافت اطلاعات سند: {str(e)}",
            code=500,
            error="internal_error"
        )


# ============================================================
# ★ API: تاریخچه گفتگو
# ============================================================
@assistant_bp.route("/history", methods=["GET"])
@login_required
def history():
    """
    دریافت تاریخچه گفتگوهای کاربر

    Query:
        limit: تعداد (پیش‌فرض 20)
    """
    ctx = get_user_context()

    try:
        limit = min(int(request.args.get("limit", 20)), 50)
    except (ValueError, TypeError):
        limit = 20

    try:
        # ★ استفاده از متد عمومی
        turns = ConversationContext.get_history(ctx["user_id"], limit=limit)

        formatted = []
        for t in turns:
            answer = t.get("answer", "") or ""
            formatted.append({
                "question": t.get("q", ""),
                "intent": t.get("intent", "unknown"),
                "answer": answer[:200] + ("..." if len(answer) > 200 else ""),
                "at": t.get("at").isoformat() if t.get("at") else None,
            })

        total = ConversationContext.count(ctx["user_id"])

        return jsonify({
            "ok": True,
            "history": formatted,
            "total": total,
        })
    except Exception as e:
        current_app.logger.exception("History error")
        return json_error(
            "خطا در دریافت تاریخچه.",
            code=500,
            error="internal_error"
        )


# ============================================================
# ★ API: پیشنهادات هوشمند بر اساس context
# ============================================================
@assistant_bp.route("/suggestions", methods=["GET"])
@login_required
def suggestions():
    """
    دریافت پیشنهادات شخصی‌سازی‌شده برای کاربر
    بر اساس نقش و activity قبلی
    """
    ctx = get_user_context()

    base = [
        {"icon": "fa-list-check", "text": "چند سند در حال بررسی دارم؟"},
        {"icon": "fa-chart-pie", "text": "آمار کلی اسناد"},
        {"icon": "fa-folder-open", "text": "کارهای من چیه؟"},
        {"icon": "fa-clock", "text": "اسناد دیرکرد"},
    ]

    # ★ ادمین‌ها پیشنهادات بیشتر
    if ctx["is_admin"]:
        base.extend([
            {"icon": "fa-trophy", "text": "پرمشغله‌ترین کارشناس کیست؟"},
            {"icon": "fa-arrow-trend-up", "text": "روند هفتگی اسناد"},
            {"icon": "fa-layer-group", "text": "توزیع گروه‌ها"},
            {"icon": "fa-gauge-high", "text": "خلاصه کلی سیستم"},
        ])

    # ★ بر اساس آخرین intent
    try:
        last = ConversationContext.get_last(ctx["user_id"])
        if last:
            last_intent = last.get("intent", "")
            if last_intent == "list_in_progress":
                base.insert(0, {"icon": "fa-file-lines", "text": "جزئیات اولین سند"})
            elif last_intent == "list_overdue":
                base.insert(0, {"icon": "fa-triangle-exclamation", "text": "اسناد بحرانی"})
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "suggestions": base[:8]
    })


# ============================================================
# ★ API: بازخورد کاربر (👍/👎)
# ============================================================
@assistant_bp.route("/feedback", methods=["POST"])
@login_required
def feedback():
    """
    ثبت بازخورد کاربر روی پاسخ

    Body:
        {
            "question": "...",
            "answer": "...",
            "rating": "up" | "down",
            "comment": "..."  # اختیاری
        }
    """
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")

    if rating not in ("up", "down"):
        return json_error("نوع بازخورد نامعتبر است.", 400, "invalid_rating")

    question = (data.get("question") or "")[:500]
    answer = (data.get("answer") or "")[:2000]
    comment = (data.get("comment") or "")[:500]

    ctx = get_user_context()

    try:
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO assistant_feedback
                (user_id, question, answer, rating, comment, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (ctx["user_id"], question, answer, rating, comment))
            conn.commit()
            return jsonify({
                "ok": True,
                "message": "بازخورد شما ثبت شد. ممنون!"
            })
        except Exception:
            current_app.logger.exception("Feedback insert failed")
            return json_error(
                "ثبت بازخورد ناموفق بود.",
                code=500,
                error="feedback_error",
            )
        finally:
            conn.close()
    except Exception as e:
        current_app.logger.exception("Feedback error")
        return json_error(
            "خطا در ثبت بازخورد.",
            code=500,
            error="internal_error"
        )


# ============================================================
# ★ API: پاک کردن گفتگو
# ============================================================
@assistant_bp.route("/clear", methods=["POST"])
@login_required
def clear():
    """پاک کردن تاریخچه گفتگو و کش کاربر"""
    ctx = get_user_context()

    try:
        ConversationContext.clear(ctx["user_id"])
        Cache.clear()
        return jsonify({
            "ok": True,
            "message": "گفتگو پاک شد."
        })
    except Exception as e:
        current_app.logger.exception("Clear error")
        return json_error(
            "خطا در پاک کردن گفتگو.",
            code=500,
            error="internal_error"
        )


# ============================================================
# ★ API: آمار استفاده (فقط ادمین)
# ============================================================
@assistant_bp.route("/stats", methods=["GET"])
@login_required
@admin_required
def stats():
    """آمار استفاده از دستیار (فقط admin/manager)"""
    try:
        conn = get_connection()
        try:
            total = 0
            top_intents = []
            daily = []
            feedback_stats = {"up": 0, "down": 0}

            # ---- کوئری لاگ‌ها ----
            try:
                total = conn.execute(
                    "SELECT COUNT(*) AS c FROM assistant_logs"
                ).fetchone()["c"]

                top_intents = [
                    dict(r) for r in conn.execute("""
                        SELECT intent, COUNT(*) AS c
                        FROM assistant_logs
                        WHERE intent IS NOT NULL
                        GROUP BY intent
                        ORDER BY c DESC
                        LIMIT 10
                    """).fetchall()
                ]

                daily = [
                    dict(r) for r in conn.execute("""
                        SELECT DATE(created_at) AS day, COUNT(*) AS c
                        FROM assistant_logs
                        WHERE created_at >= date('now', '-7 days')
                        GROUP BY DATE(created_at)
                        ORDER BY day DESC
                    """).fetchall()
                ]
            except Exception:
                pass

            # ---- آمار بازخورد ----
            try:
                rows = conn.execute("""
                    SELECT rating, COUNT(*) AS c
                    FROM assistant_feedback
                    GROUP BY rating
                """).fetchall()

                for r in rows:
                    feedback_stats[r["rating"]] = r["c"]
            except Exception:
                pass

            return jsonify({
                "ok": True,
                "stats": {
                    "total_queries": total,
                    "top_intents": top_intents,
                    "daily": daily,
                    "feedback": feedback_stats,
                }
            })
        finally:
            conn.close()
    except Exception as e:
        current_app.logger.exception("Stats error")
        return json_error(
            "خطا در دریافت آمار.",
            code=500,
            error="internal_error"
        )


# ============================================================
# ★ API: Health check
# ============================================================
@assistant_bp.route("/ping", methods=["GET"])
def ping():
    """بررسی سلامت سرویس"""
    return jsonify({
        "ok": True,
        "service": "assistant",
        "time": datetime.now().isoformat(),
    })


# ============================================================
# ★ API: بررسی سلامت LLM
# ============================================================
@assistant_bp.route("/llm-health", methods=["GET"])
@login_required
@admin_required
def llm_health():
    """بررسی وضعیت اتصال به LLM (فقط ادمین)"""
    try:
        from services.ai import LLMConfig, LLM_AVAILABLE

        if not LLM_AVAILABLE or not LLMConfig:
            return jsonify({
                "ok": False,
                "available": False,
                "message": "پکیج LLM نصب نیست."
            })

        if not LLMConfig.is_available():
            return jsonify({
                "ok": False,
                "available": False,
                "message": "LLM غیرفعال است یا کلید API تنظیم نشده."
            })

        # ★ تست ساده
        from services.ai import LLMService
        if hasattr(LLMService, "health_check"):
            result = LLMService.health_check()
        else:
            result = {"ok": True, "message": "کلاینت آماده است."}

        return jsonify({
            "ok": True,
            "available": True,
            "provider": LLMConfig.PROVIDER,
            "model": LLMConfig.OLLAMA_MODEL if LLMConfig.PROVIDER == "ollama" else "N/A",
            "details": result,
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "available": False,
            "message": f"خطا: {str(e)}"
        })


# ============================================================
# ★ Error Handlers (فقط برای این blueprint)
# ============================================================
@assistant_bp.errorhandler(404)
def not_found(e):
    if request.is_json:
        return jsonify({
            "ok": False,
            "error": "not_found",
            "message": "مسیر مورد نظر پیدا نشد."
        }), 404
    return redirect(url_for("assistant.index"))


@assistant_bp.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "ok": False,
        "error": "method_not_allowed",
        "message": "متد HTTP مجاز نیست."
    }), 405


@assistant_bp.errorhandler(500)
def internal_error(e):
    return jsonify({
        "ok": False,
        "error": "internal_error",
        "message": "خطای داخلی سرور."
    }), 500



# ============================================================
# ★ API: دانلود گزارش پاورپوینت طبقه‌بندی
# ============================================================
@assistant_bp.route("/export/summary-powerpoint", methods=["GET"])
@login_required
def export_summary_powerpoint():
    """دانلود گزارش پاورپوینت طبقه‌بندی"""
    try:
        from services.document_group.report import PowerPointService

        if PowerPointService is None:
            return json_error(
                "سرویس پاورپوینت در دسترس نیست.",
                500,
                "service_unavailable"
            )

        buffer = PowerPointService.build_classification_report()

        try:
            import jdatetime
            date_str = jdatetime.date.today().strftime("%Y%m%d")
        except Exception:
            date_str = datetime.now().strftime("%Y%m%d")

        filename = f"classification_report_{date_str}.pptx"

        return send_file(
            buffer,
            mimetype=(
                "application/vnd.openxmlformats-officedocument"
                ".presentationml.presentation"
            ),
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        current_app.logger.exception("PPT export error")
        return json_error(
            f"خطا در ساخت گزارش پاورپوینت: {str(e)}",
            500,
            "ppt_export_error"
        )


# ============================================================
# ★ API: دانلود گزارش اکسل زیرگروه‌ها (Flat)
# ============================================================
@assistant_bp.route("/export/subgroups-excel", methods=["GET"])
@login_required
def export_subgroups_excel():
    """دانلود گزارش اکسل زیرگروه‌ها (Flat)"""
    try:
        from services.document_group.report import (
            DocumentSubgroupExcelFlatService,
        )

        if DocumentSubgroupExcelFlatService is None:
            return json_error(
                "سرویس اکسل در دسترس نیست.",
                500,
                "service_unavailable"
            )

        group_id = request.args.get("group_id", type=int)
        department_id = request.args.get("department_id", type=int)

        buffer = DocumentSubgroupExcelFlatService.export_subgroups_flat(
            group_id=group_id,
            department_id=department_id,
        )

        filename = DocumentSubgroupExcelFlatService.build_flat_filename(
            group_id=group_id,
            department_id=department_id,
        )

        return send_file(
            buffer,
            mimetype=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        current_app.logger.exception("Excel export error")
        return json_error(
            f"خطا در ساخت گزارش اکسل: {str(e)}",
            500,
            "excel_export_error"
        )
    
