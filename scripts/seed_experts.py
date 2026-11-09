"""
اسکریپت افزودن کارشناسان به دیتابیس
اجرا: python scripts/seed_experts.py
"""

import os
import sys

# ★ اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection
from database.users import create_user


# ============================================================
# ★ لیست کارشناسان (75 نفر) ★
# ============================================================
EXPERTS_LIST = [
    ("e.khoshoei",        "احسان خشوعی"),
    ("e.safavi",          "احسان صفوی"),
    ("e.veisizadeh",      "احسان ویسی زاده"),
    ("a.damenpak",        "احمد دامن پاک"),
    ("e.khosravi",        "اسکندر خسروی"),
    ("a.sawaedi",         "امل سواعدی"),
    ("o.farajadi",        "امید فرجادی"),
    ("a.hajipour",        "امیر محمد حاجی پور"),
    ("a.azhdarizadeh",    "امیرحسین اژدری زاده"),
    ("a.jahangiribabadi", "امین جهانگیری بابادی"),
    ("a.torabizadeh",     "آتیا ترابی زاده"),
    ("a.amani",           "آرش امانی"),
    ("a.javadibabaahmadi","آرش جوادی بابااحمدی"),
    ("a.limochi",         "آرش لیموچی"),
    ("b.meridian",        "بهنام مریدیان"),
    ("h.bahoosh",         "حسین باهوش"),
    ("h.faraji",          "حسین فرجی"),
    ("kh.rezaei",         "خسرو رضائی"),
    ("kh.hemmatian",      "خسرو همتیان"),
    ("r.alizadeh",        "رحمان علیزاده"),
    ("r.moeini",          "رحمن معینی"),
    ("r.ahmadi",          "رضا احمدی"),
    ("r.azizizadeh",      "رضا عزیزی زاده"),
    ("r.ghanbari",        "رضا قنبری"),
    ("r.kiani",           "رضا کیانی"),
    ("r.eslami",          "رکاب اسلامی"),
    ("r.etemadzadeh",     "رویا اعتماد زاده"),
    ("z.alizadeh",        "زهرا علیزاده"),
    ("z.fazlipour",       "زهرا فضلی پور"),
    ("s.hemmatian",       "سارا همتیان"),
    ("s.salehi",          "ساقی صالحی"),
    ("s.mousavi",         "سامان موسوی"),
    ("s.navi",            "ساناز نوی"),
    ("s.sarlak",          "سجاد سرلک"),
    ("s.najafitabar",     "سعید نجفی تبار"),
    ("s.golestan",        "سیاوش گلستان"),
    ("s.ghofrani",        "سید رضا غفرانی"),
    ("s.fatemizadeh",     "سید علی اصغر فاطمی زاده"),
    ("sh.hosseinnezhad",  "شاهرخ حسین نژاد"),
    ("sh.sspe",           "شهرام حسین نژاد"),
    ("s.rashidian",       "صابر رشیدیان"),
    ("s.rezaei",          "صادق رضایی"),
    ("t.khalili",         "طاهر خلیلی"),
    ("t.khalilizadeh",    "طاهر خلیلی زاده"),
    ("a.khalifzadeh",     "عباس خلیف زاده"),
    ("a.golchinnezhad",   "عبدالامیر گلچین نژاد"),
    ("a.albootaher",      "عبدالرضا آلبوطاهر"),
    ("f.kamroafar",       "فاطمه کامروافر"),
    ("k.hardani",         "کاظم حردانی"),
    ("k.kazemi",          "کاظم کاظمی"),
    ("k.sadeghipour",     "کوثر صادقی پور"),
    ("m.zangeneh",        "مجتبی زنگنه"),
    ("m.shahniyani",      "مجتبی شهنیانی"),
    ("m.ghanbari",        "مجتبی قنبری"),
    ("m.dehdashti",       "مجید دهدشتی"),
    ("m.afshinfar",       "محسن افشین فر"),
    ("m.hajipour",        "محمد حاجی پور"),
    ("m.behnam",          "محمد حسین بهنام"),
    ("m.koochaktondro",   "محمد کوچک تندرو"),
    ("m.saghalarzadeh",   "محمد محسن سقالرزاده"),
    ("m.mahavi",          "محمد مهاوی"),
    ("m.mohsenpour",      "محمود محسن پور"),
    ("m.bahmani",         "مرتضی بهمنی"),
    ("m.rezaei",          "مریم رضایی"),
    ("m.saffar",          "مسعود صفار"),
    ("m.mansouri",        "مطهره منصوری"),
    ("m.darivandpour",    "مهیار داریوند پور"),
    ("m.saeb",            "میلاد صائب"),
    ("m.jahanbakhsh",     "مینا جهانبخش"),
    ("n.fard",            "ناصری فرد"),
    ("n.pourmahmoud",     "ندا پورمحمود"),
    ("n.jadbabaee",       "نگین جدبابایی"),
    ("n.jafari",          "نوید جعفری"),
    ("n.norouzi",         "نیما نوروزی"),
    ("y.goli",            "یوسف گلی"),
]


DEFAULT_PASSWORD = "123456"


def seed_experts():
    """افزودن کارشناسان به دیتابیس (بدون دست زدن به کاربران موجود)"""

    print("=" * 60)
    print("👥 شروع افزودن کارشناسان")
    print("=" * 60)

    # ★ همه یوزرنیم‌های موجود رو یک‌جا می‌گیریم
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT username FROM users"
        ).fetchall()
        existing_usernames = {row["username"] for row in rows}
    finally:
        connection.close()

    print(f"📊 کاربران موجود در دیتابیس: {len(existing_usernames)}")
    print(f"📋 تعداد در لیست: {len(EXPERTS_LIST)}\n")

    # ★ افزودن کارشناسان جدید
    created = []
    skipped = []
    failed = []

    for username, full_name in EXPERTS_LIST:
        if username in existing_usernames:
            skipped.append((username, full_name))
            continue

        success = create_user(
            username=username,
            password=DEFAULT_PASSWORD,
            full_name=full_name,
            role="expert"
        )

        if success:
            created.append((username, full_name))
            print(f"  ✅ {full_name}  →  {username}")
        else:
            failed.append((username, full_name))
            print(f"  ❌ خطا: {full_name}  ({username})")

    # ============================================================
    # 📊 گزارش نهایی
    # ============================================================
    print("\n" + "=" * 60)
    print("📊 گزارش نهایی")
    print("=" * 60)
    print(f"  ✅ ایجاد شده:        {len(created)}")
    print(f"  ⏭️  رد شده (تکراری): {len(skipped)}")
    print(f"  ❌ خطا:             {len(failed)}")
    print(f"  ─────────────────────────")
    print(f"  📋 کل لیست:         {len(EXPERTS_LIST)}")

    if skipped:
        print(f"\n⏭️  کاربران تکراری (قبلاً موجود بودند):")
        for username, full_name in skipped:
            print(f"     • {full_name}  ({username})")

    if failed:
        print(f"\n❌ کاربرانی که ایجاد نشدند:")
        for username, full_name in failed:
            print(f"     • {full_name}  ({username})")

    print("\n✅ تمام!")


if __name__ == "__main__":
    seed_experts()