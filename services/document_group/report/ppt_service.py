"""
PowerPoint Service - ساخت گزارش پاورپوینت گروه‌ها
====================================================
★ نسخه Registry-based (independent)
★ خروجی: فایل .pptx
"""
import io
from datetime import datetime

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

from database.connection import get_connection
from helpers.date_helper import DateHelper


class PowerPointService:
    """سرویس ساخت گزارش پاورپوینت"""

    # ============================================================
    # ★ رنگ‌ها
    # ============================================================
    PRIMARY = RGBColor(0x1B, 0x69, 0x8B)
    PRIMARY_LIGHT = RGBColor(0x16, 0x7A, 0x5C)
    ACCENT = RGBColor(0x66, 0x7E, 0xEA)
    WARNING = RGBColor(0xF5, 0x9E, 0x0B)
    DANGER = RGBColor(0xDC, 0x26, 0x26)
    SUCCESS = RGBColor(0x10, 0xB9, 0x81)
    PURPLE = RGBColor(0x80, 0x5A, 0xD5)
    TEXT_DARK = RGBColor(0x2D, 0x34, 0x36)
    TEXT_LIGHT = RGBColor(0x63, 0x6E, 0x72)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    BG_LIGHT = RGBColor(0xF8, 0xFA, 0xFC)

    FONT_NAME = "B Nazanin"

    # ============================================================
    # ★ متد اصلی
    # ============================================================
    @classmethod
    def build_classification_report(cls):
        """ساخت گزارش پاورپوینت طبقه‌بندی اسناد"""
        if not PPTX_AVAILABLE:
            raise RuntimeError(
                "python-pptx نصب نیست. لطفاً 'pip install python-pptx' رو اجرا کن."
            )

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        stats = cls._collect_stats()

        cls._add_title_slide(prs, "گزارش طبقه‌بندی اسناد", stats)
        cls._add_summary_slide(prs, stats)
        cls._add_groups_slide(prs, stats)
        cls._add_departments_slide(prs, stats)
        cls._add_subgroups_slide(prs, stats)
        cls._add_status_slide(prs, stats)
        cls._add_thanks_slide(prs)

        output = io.BytesIO()
        prs.save(output)
        output.seek(0)
        return output

    # ============================================================
    # ★ جمع‌آوری آمار
    # ============================================================
    @staticmethod
    def _collect_stats():
        conn = get_connection()
        try:
            total_docs = conn.execute(
                "SELECT COUNT(*) AS c FROM documents"
            ).fetchone()["c"]

            total_users = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE is_active = 1"
            ).fetchone()["c"]

            total_groups = conn.execute(
                "SELECT COUNT(*) AS c FROM document_groups WHERE is_active = 1"
            ).fetchone()["c"]

            total_subgroups = conn.execute(
                "SELECT COUNT(*) AS c FROM document_subgroups WHERE is_active = 1"
            ).fetchone()["c"]

            total_departments = conn.execute(
                "SELECT COUNT(*) AS c FROM departments WHERE is_active = 1"
            ).fetchone()["c"]

            by_status = [
                dict(r) for r in conn.execute("""
                    SELECT s.title, s.color, COUNT(d.id) AS c
                    FROM document_statuses s
                    LEFT JOIN documents d ON d.status_id = s.id
                    GROUP BY s.id
                    HAVING c > 0
                    ORDER BY s.sort_order
                """).fetchall()
            ]

            by_group = [
                dict(r) for r in conn.execute("""
                    SELECT g.title, g.color, COUNT(d.id) AS c
                    FROM document_groups g
                    LEFT JOIN documents d ON d.group_id = g.id
                    GROUP BY g.id
                    HAVING c > 0
                    ORDER BY c DESC
                    LIMIT 12
                """).fetchall()
            ]

            by_department = [
                dict(r) for r in conn.execute("""
                    SELECT dep.title, COUNT(d.id) AS c
                    FROM departments dep
                    LEFT JOIN documents d ON d.department_id = dep.id
                    GROUP BY dep.id
                    HAVING c > 0
                    ORDER BY c DESC
                    LIMIT 10
                """).fetchall()
            ]

            top_subgroups = [
                dict(r) for r in conn.execute("""
                    SELECT sg.title, sg.color, COUNT(d.id) AS c
                    FROM document_subgroups sg
                    LEFT JOIN documents d ON d.subgroup_id = sg.id
                    GROUP BY sg.id
                    HAVING c > 0
                    ORDER BY c DESC
                    LIMIT 10
                """).fetchall()
            ]

            return {
                "total_docs": total_docs,
                "total_users": total_users,
                "total_groups": total_groups,
                "total_subgroups": total_subgroups,
                "total_departments": total_departments,
                "by_status": by_status,
                "by_group": by_group,
                "by_department": by_department,
                "top_subgroups": top_subgroups,
                "generated_at": DateHelper.format_jalali_datetime(
                    datetime.now(), show_time=True
                ),
            }
        finally:
            conn.close()

    # ============================================================
    # ★ Helper: اضافه کردن متن
    # ============================================================
    @classmethod
    def _add_text(cls, slide, left, top, width, height,
                  text, size=14, bold=False,
                  color=None, align=PP_ALIGN.RIGHT):
        color = color or cls.TEXT_DARK
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.text = str(text)
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.runs[0]
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = cls.FONT_NAME
        return txBox

    # ============================================================
    # ★ Helper: عنوان اسلاید
    # ============================================================
    @classmethod
    def _add_slide_title(cls, slide, title, subtitle=None):
        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, 0,
            Inches(13.333), Inches(0.15)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = cls.PRIMARY
        bar.line.fill.background()

        cls._add_text(
            slide,
            Inches(0.5), Inches(0.4),
            Inches(12.3), Inches(0.8),
            title, size=28, bold=True,
            color=cls.PRIMARY,
            align=PP_ALIGN.RIGHT
        )

        if subtitle:
            cls._add_text(
                slide,
                Inches(0.5), Inches(1.15),
                Inches(12.3), Inches(0.5),
                subtitle, size=14, bold=False,
                color=cls.TEXT_LIGHT,
                align=PP_ALIGN.RIGHT
            )

        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0.5), Inches(1.55),
            Inches(12.3), Inches(0.02)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = cls.BG_LIGHT
        line.line.fill.background()

    # ============================================================
    # ★ Helper: کارت آماری
    # ============================================================
    @classmethod
    def _add_stat_card(cls, slide, left, top, width, height,
                       label, value, color):
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            left, top, width, height
        )
        card.fill.solid()
        card.fill.fore_color.rgb = cls.WHITE
        card.line.color.rgb = color
        card.line.width = Pt(1.5)

        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            left, top, Inches(0.08), height
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = color
        bar.line.fill.background()

        cls._add_text(
            slide,
            left, top + Inches(0.3),
            width, Inches(0.8),
            str(value), size=42, bold=True,
            color=color,
            align=PP_ALIGN.CENTER
        )

        cls._add_text(
            slide,
            left, top + height - Inches(0.55),
            width, Inches(0.4),
            label, size=13, bold=False,
            color=cls.TEXT_LIGHT,
            align=PP_ALIGN.CENTER
        )

    # ============================================================
    # ★ اسلاید ۱: عنوان
    # ============================================================
    @classmethod
    def _add_title_slide(cls, prs, title, stats):
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, 0, prs.slide_width, prs.slide_height
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = cls.PRIMARY
        bg.line.fill.background()

        deco = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(-2), Inches(-2),
            Inches(8), Inches(8)
        )
        deco.fill.solid()
        deco.fill.fore_color.rgb = cls.PRIMARY_LIGHT
        deco.line.fill.background()

        cls._add_text(
            slide,
            Inches(1), Inches(1.8),
            Inches(11.3), Inches(1),
            "📊", size=72, bold=True,
            color=cls.WHITE,
            align=PP_ALIGN.CENTER
        )

        cls._add_text(
            slide,
            Inches(1), Inches(3.2),
            Inches(11.3), Inches(1.2),
            title, size=52, bold=True,
            color=cls.WHITE,
            align=PP_ALIGN.CENTER
        )

        cls._add_text(
            slide,
            Inches(1), Inches(4.5),
            Inches(11.3), Inches(0.6),
            "سامانه مدیریت اسناد مهندسی",
            size=22, bold=False,
            color=cls.WHITE,
            align=PP_ALIGN.CENTER
        )

        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(5), Inches(5.4),
            Inches(3.3), Inches(0.03)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = cls.WHITE
        line.line.fill.background()

        cls._add_text(
            slide,
            Inches(1), Inches(5.8),
            Inches(11.3), Inches(0.5),
            f"تاریخ تهیه: {stats['generated_at']}",
            size=16, bold=False,
            color=cls.WHITE,
            align=PP_ALIGN.CENTER
        )

    # ============================================================
    # ★ اسلاید ۲: خلاصه آماری
    # ============================================================
    @classmethod
    def _add_summary_slide(cls, prs, stats):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        cls._add_slide_title(
            slide,
            "خلاصه آماری سیستم",
            "نمای کلی از داده‌های موجود"
        )

        cards = [
            ("کل اسناد", stats["total_docs"], cls.PRIMARY),
            ("کاربران فعال", stats["total_users"], cls.ACCENT),
            ("گروه‌های سند", stats["total_groups"], cls.SUCCESS),
            ("زیرگروه‌ها", stats["total_subgroups"], cls.WARNING),
        ]

        card_width = Inches(2.9)
        card_height = Inches(2.2)
        gap = Inches(0.25)
        total_width = card_width * 4 + gap * 3
        start_left = (prs.slide_width - total_width) / 2

        for i, (label, value, color) in enumerate(cards):
            left = start_left + (card_width + gap) * i
            cls._add_stat_card(
                slide,
                left, Inches(2.2),
                card_width, card_height,
                label, value, color
            )

        cls._add_text(
            slide,
            Inches(0.5), Inches(5),
            Inches(12.3), Inches(0.5),
            f"دپارتمان‌های فعال: {stats['total_departments']}",
            size=16, bold=True,
            color=cls.TEXT_DARK,
            align=PP_ALIGN.CENTER
        )

    # ============================================================
    # ★ اسلاید ۳: توزیع گروه‌ها
    # ============================================================
    @classmethod
    def _add_groups_slide(cls, prs, stats):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        cls._add_slide_title(
            slide,
            "توزیع اسناد بر اساس گروه",
            f"{len(stats['by_group'])} گروه با سند"
        )

        by_group = stats["by_group"]
        if not by_group:
            cls._add_text(
                slide,
                Inches(0.5), Inches(3),
                Inches(12.3), Inches(1),
                "داده‌ای موجود نیست",
                size=18, color=cls.TEXT_LIGHT,
                align=PP_ALIGN.CENTER
            )
            return

        max_count = max(g["c"] for g in by_group) or 1
        bar_area_left = Inches(2.5)
        bar_area_width = Inches(8.5)
        top_start = Inches(2)

        for i, g in enumerate(by_group[:10]):
            top = top_start + Inches(0.5 + i * 0.42)

            cls._add_text(
                slide,
                Inches(0.3), top,
                Inches(2), Inches(0.4),
                g["title"][:30],
                size=12, bold=False,
                color=cls.TEXT_DARK,
                align=PP_ALIGN.RIGHT
            )

            bar_width = bar_area_width * (g["c"] / max_count)
            bar = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                bar_area_left, top + Inches(0.05),
                bar_width, Inches(0.3)
            )
            bar.fill.solid()
            bar.fill.fore_color.rgb = cls.PRIMARY
            bar.line.fill.background()

            cls._add_text(
                slide,
                bar_area_left + bar_width + Inches(0.1),
                top + Inches(0.05),
                Inches(0.8), Inches(0.3),
                str(g["c"]),
                size=12, bold=True,
                color=cls.PRIMARY,
                align=PP_ALIGN.LEFT
            )

    # ============================================================
    # ★ اسلاید ۴: توزیع دپارتمان‌ها
    # ============================================================
    @classmethod
    def _add_departments_slide(cls, prs, stats):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        cls._add_slide_title(
            slide,
            "توزیع اسناد بر اساس دپارتمان",
            "برترین دپارتمان‌ها"
        )

        by_dept = stats["by_department"]
        if not by_dept:
            cls._add_text(
                slide,
                Inches(0.5), Inches(3),
                Inches(12.3), Inches(1),
                "داده‌ای موجود نیست",
                size=18, color=cls.TEXT_LIGHT,
                align=PP_ALIGN.CENTER
            )
            return

        rows = len(by_dept) + 1
        cols = 3
        table_shape = slide.shapes.add_table(
            rows, cols,
            Inches(1.5), Inches(2),
            Inches(10), Inches(0.45 * rows)
        )
        table = table_shape.table

        table.columns[0].width = Inches(1)
        table.columns[1].width = Inches(6)
        table.columns[2].width = Inches(3)

        headers = ["#", "دپارتمان", "تعداد اسناد"]
        for c, h in enumerate(headers):
            cell = table.cell(0, c)
            cell.text = h
            cell.fill.solid()
            cell.fill.fore_color.rgb = cls.PRIMARY
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            p.runs[0].font.name = cls.FONT_NAME
            p.runs[0].font.size = Pt(13)
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = cls.WHITE

        for i, dep in enumerate(by_dept, start=1):
            cell = table.cell(i, 0)
            cell.text = str(i)
            cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

            cell = table.cell(i, 1)
            cell.text = dep["title"]
            cell.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

            cell = table.cell(i, 2)
            cell.text = str(dep["c"])
            cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

            for c in range(cols):
                cell = table.cell(i, c)
                p = cell.text_frame.paragraphs[0]
                p.runs[0].font.name = cls.FONT_NAME
                p.runs[0].font.size = Pt(12)
                p.runs[0].font.color.rgb = cls.TEXT_DARK
                if i % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = cls.BG_LIGHT

    # ============================================================
    # ★ اسلاید ۵: زیرگروه‌های پرتکرار
    # ============================================================
    @classmethod
    def _add_subgroups_slide(cls, prs, stats):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        cls._add_slide_title(
            slide,
            "پرتکرارترین زیرگروه‌ها",
            "Top 10 زیرگروه بر اساس تعداد اسناد"
        )

        top = stats["top_subgroups"]
        if not top:
            cls._add_text(
                slide,
                Inches(0.5), Inches(3),
                Inches(12.3), Inches(1),
                "داده‌ای موجود نیست",
                size=18, color=cls.TEXT_LIGHT,
                align=PP_ALIGN.CENTER
            )
            return

        for i, sg in enumerate(top):
            col = i % 2
            row = i // 2

            left = Inches(0.5 + col * 6.2)
            top_pos = Inches(2 + row * 0.9)

            cls._add_text(
                slide,
                left, top_pos,
                Inches(0.5), Inches(0.7),
                f"{i+1}", size=20, bold=True,
                color=cls.WARNING,
                align=PP_ALIGN.CENTER
            )

            cls._add_text(
                slide,
                left + Inches(0.6), top_pos,
                Inches(4), Inches(0.4),
                sg["title"][:40],
                size=13, bold=True,
                color=cls.TEXT_DARK,
                align=PP_ALIGN.RIGHT
            )

            cls._add_text(
                slide,
                left + Inches(4.7), top_pos,
                Inches(1.3), Inches(0.4),
                f"{sg['c']} سند",
                size=12, bold=False,
                color=cls.TEXT_LIGHT,
                align=PP_ALIGN.LEFT
            )

    # ============================================================
    # ★ اسلاید ۶: توزیع وضعیت‌ها
    # ============================================================
    @classmethod
    def _add_status_slide(cls, prs, stats):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        cls._add_slide_title(
            slide,
            "توزیع اسناد بر اساس وضعیت",
            "نمای کلی از وضعیت‌های اسناد"
        )

        by_status = stats["by_status"]
        if not by_status:
            cls._add_text(
                slide,
                Inches(0.5), Inches(3),
                Inches(12.3), Inches(1),
                "داده‌ای موجود نیست",
                size=18, color=cls.TEXT_LIGHT,
                align=PP_ALIGN.CENTER
            )
            return

        total = sum(s["c"] for s in by_status)
        card_width = Inches(2.4)
        card_height = Inches(2.5)
        gap = Inches(0.3)
        total_width = card_width * len(by_status[:5]) + gap * (len(by_status[:5]) - 1)
        start_left = (prs.slide_width - total_width) / 2

        for i, s in enumerate(by_status[:5]):
            left = start_left + (card_width + gap) * i

            color = cls._hex_to_rgb(s.get("color") or "#3D8499")

            card = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                left, Inches(2.2),
                card_width, card_height
            )
            card.fill.solid()
            card.fill.fore_color.rgb = cls.WHITE
            card.line.color.rgb = color
            card.line.width = Pt(2)

            bar = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                left, Inches(2.2),
                card_width, Inches(0.1)
            )
            bar.fill.solid()
            bar.fill.fore_color.rgb = color
            bar.line.fill.background()

            cls._add_text(
                slide,
                left, Inches(2.8),
                card_width, Inches(1),
                str(s["c"]),
                size=48, bold=True,
                color=color,
                align=PP_ALIGN.CENTER
            )

            percent = round(s["c"] / total * 100, 1) if total else 0
            cls._add_text(
                slide,
                left, Inches(3.9),
                card_width, Inches(0.4),
                f"{percent}٪",
                size=16, bold=False,
                color=cls.TEXT_LIGHT,
                align=PP_ALIGN.CENTER
            )

            cls._add_text(
                slide,
                left, Inches(4.4),
                card_width, Inches(0.4),
                s["title"],
                size=14, bold=True,
                color=cls.TEXT_DARK,
                align=PP_ALIGN.CENTER
            )

    # ============================================================
    # ★ اسلاید ۷: تشکر
    # ============================================================
    @classmethod
    def _add_thanks_slide(cls, prs):
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0, 0, prs.slide_width, prs.slide_height
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = cls.PRIMARY
        bg.line.fill.background()

        cls._add_text(
            slide,
            Inches(1), Inches(2.5),
            Inches(11.3), Inches(1),
            "🙏",
            size=72, bold=True,
            color=cls.WHITE,
            align=PP_ALIGN.CENTER
        )

        cls._add_text(
            slide,
            Inches(1), Inches(4),
            Inches(11.3), Inches(1),
            "با تشکر از توجه شما",
            size=40, bold=True,
            color=cls.WHITE,
            align=PP_ALIGN.CENTER
        )

    # ============================================================
    # ★ Helper: hex → RGBColor
    # ============================================================
    @staticmethod
    def _hex_to_rgb(hex_color):
        try:
            hex_color = hex_color.lstrip("#")
            return RGBColor(
                int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16),
            )
        except Exception:
            return RGBColor(0x3D, 0x84, 0x99)