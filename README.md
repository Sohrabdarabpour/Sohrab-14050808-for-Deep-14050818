# SSPE — سامانه مدیریت اسناد و گزارش‌ها

برنامه وب مبتنی بر **Flask** برای مدیریت اسناد سازمانی، پروژه‌ها، پیمانکاران، کارشناسان، دپارتمان‌ها، گردش‌کار تأیید یادداشت‌ها و دستیار هوش مصنوعی.

---

## پیش‌نیازها

- Python **3.11** یا بالاتر
- Windows / Linux
- (اختیاری) کلید API برای ماژول دستیار هوش مصنوعی

---

## راه‌اندازی

```bash
# ۱) محیط مجازی
python -m venv .venv
.venv\Scripts\activate        # ویندوز
# source .venv/bin/activate   # لینوکس

# ۲) نصب وابستگی‌ها
pip install -r requirements.txt
pip install -e ".[dev]"       # ابزارهای توسعه: pytest, black, ruff, isort

# ۳) متغیرهای محیطی
copy .env.example .env        # ویندوز
# cp .env.example .env        # لینوکس
#   سپس .env را باز کنید و کلیدهای واقعی را جایگذاری کنید

# ۴) اجرا
python run.py                  # فقط روی 127.0.0.1 و بدون debug
# برای توسعه (debug + auto-reload):
#   $env:FLASK_DEBUG = "1"   (ویندوز)
#   export FLASK_DEBUG=1     (لینوکس)
# یا برای production:
gunicorn "app:create_app()"

# ⚠️ محدودیت نرخ دستیار و تاریخچه گفتگو در حافظه‌ی هر پروسه نگه‌داری می‌شوند؛
# تا انتقال آن‌ها به دیتابیس/Redis، از یک worker با چند thread استفاده کنید:
#   gunicorn "app:create_app()" --workers 1 --threads 8
```

برنامه روی `http://127.0.0.1:5000` بالا می‌آید.

> ⚠️ فایل `.env` حاوی کلیدهای API است و در `.gitignore` قرار دارد.
> هیچ کلیدی نباید داخل کد پایتون نوشته شود — `tests/test_ai.py` این را بررسی می‌کند.

### متغیرهای محیطی

| متغیر | پیش‌فرض | توضیح |
|---|---|---|
| `SECRET_KEY` | مقدار توسعه‌ای | **در production حتماً ست شود** (وگرنه هشدار در لاگ) |
| `SSPE_DATABASE_PATH` | `instance/database.db` | مسیر فایل دیتابیس SQLite |
| `FLASK_DEBUG` | `0` | `1` فقط برای توسعه؛ در production خاموش بماند |
| `SSPE_HOST` | `127.0.0.1` | آدرس شنود؛ برای دسترسی شبکه `0.0.0.0` |
| `SSPE_PORT` | `5000` | پورت اجرا |
| `SESSION_COOKIE_SECURE` | `0` | پشت HTTPS مقدار `1` بدهید |
| `SSPE_WEEKEND_DAYS` | `4,5` | روزهای تعطیل هفتگی (ISO: دوشنبه=۱ … یکشنبه=۷)؛ پیش‌فرض پنجشنبه و جمعه |
| `SSPE_DEFAULT_SLA_DAYS` | `7` | مهلت پاسخ پیش‌فرض (روز کاری) وقتی گروه/زیرگروه مقدار ندارد |
| `SSPE_TRUSTED_ORIGINS` | — | میزبان‌های اضافی مجاز برای POST (پشت reverse proxy)، با کاما |
| `LLM_PROVIDER` | `deepseek` | `avalai` · `deepseek` · `ollama` · `groq` · `openai` |
| `LLM_ENABLED` | `true` | خاموش‌کردن کل مسیر LLM |
| `DEEPSEEK_API_KEY` | — | کلید DeepSeek |
| `AVALAI_API_KEY` | — | کلید AvalAI (بدون نیاز به VPN) |
| `LLM_MAX_TOKENS` | `1500` | سقف توکن پاسخ |
| `LLM_TEMPERATURE` | `0.3` | خلاقیت مدل |
| `LLM_TIMEOUT` | `60` | مهلت درخواست (ثانیه) |

اگر کلید provider فعال خالی باشد، دستیار بدون خطا به حالت **rule-based** (همان ۳۳ intent) برمی‌گردد.

---

## ساختار پروژه

```
SSPE/
├── app.py                  ← ساخت اپلیکیشن، ثبت Blueprintها، error handlerها
├── run.py                  ← اجرای ساده
├── config.py               ← تنظیمات (کلاس Config)
├── pyproject.toml          ← تنظیمات black / ruff / isort / pytest
├── requirements.txt        ← وابستگی‌های اجرا
│
├── routes/                 ← کنترلرها (۱۸ Blueprint)
│   ├── __init__.py         ← ثبت و صادرات همه Blueprintها
│   ├── auth.py  dashboard.py  documents.py  excel.py  main.py  panel.py
│   └── <module>/           ← هر ماژول: __init__.py + <module>_routes.py
│       ai/ contract_types/ contractors/ departments/ document_group/
│       profile/ project_roles/ projects/ reports/ search/ workflow/
│
├── services/               ← منطق کسب‌وکار، یک پوشه برای هر موجودیت
│   ├── users/              ← user_service, user_excel_service, avatar_service
│   ├── documents/          ← document_service
│   ├── departments/        ← department_service و ۴ سرویس دیگر
│   ├── reports/            ← سرویس‌های گزارش (area, status, …)
│   ├── projects/           ← project_service, project_member_service, …
│   ├── contractors/  contract_types/  project_roles/  document_group/
│   ├── workflow/  search/  dashboard/  profile/  excel/
│   └── ai/                 ← NLU, registry, LLM, handlers/
│
├── database/               ← دسترسی به داده (سه لایه مجزا)
│   ├── connection.py       ← اتصال SQLite
│   ├── init_db.py          ← فقط هماهنگ‌کننده (۳۸ خط)
│   ├── tables/             ← یک فایل برای هر جدول: DDL + ایندکس‌ها
│   │   └── users.py, documents.py, projects.py, notifications.py, …
│   ├── seeds/              ← داده‌های پیش‌فرض: statuses, areas, admin, …
│   ├── repositories/       ← توابع CRUD: users, projects, workflow, …
│   ├── users.py  documents.py  reports.py   ← کد قدیمی CRUD
│   └── migrations/
│
├── forms/                  ← اعتبارسنجی — یک پوشه برای هر موجودیت
│   └── auth/ departments/ documents/ users/ projects/ workflow/ …
├── helpers/                ← تاریخ جلالی، قواعد دسترسی گردش‌کار
├── security/               ← دکوراتورهای احراز هویت و مجوز
│
├── templates/              ← قالب‌های Jinja2 — آینه ساختار routes
│   ├── base.html           ← قالب پایه
│   └── components/         ← header, sidebar, footer
│
├── static/                 ← دارایی‌های سمت کلاینت
│   ├── css/
│   │   ├── core/           ← variables (توکن‌های طراحی), reset, utilities
│   │   ├── base/base.css
│   │   ├── app-ui.css      ← چیدمان اصلی (هدر، سایدبار، محتوا)
│   │   ├── components/     ← header, sidebar و کامپوننت‌های مشترک
│   │   └── pages/          ← یک فایل CSS برای هر صفحه (آینه ساختار templates)
│   ├── js/
│   │   ├── app.js          ← رفتار سراسری
│   │   └── pages/          ← یک فایل JS برای هر صفحه
│   ├── images/
│   └── uploads/            ← فایل‌های آپلودشده کاربران
│
├── docs/DESIGN.md          ← سند طراحی: قواعد معماری، ترتیب CSS، قراردادها
│
├── uploads/                ← خروجی‌های موقت Excel
├── instance/               ← دیتابیس SQLite (خارج از کنترل نسخه)
├── scripts/                ← اسکریپت‌های داده اولیه
├── tests/                  ← تست‌های pytest (دود + معماری)
└── _archive/               ← فایل‌های تکراری/زائد منتقل‌شده (خارج از کد فعال)
```

### لایه‌ها

```
app.py  →  routes/  →  services/  →  database/
                ↘  forms/            helpers/ · security/
                     ↕
              templates/ + static/
```

**قاعده:** فایل route نباید SQL بنویسد؛ کوئری در `database/`، منطق در `services/`، اعتبارسنجی در `forms/`، و نمایش در `templates/`.

### دسترسی به دیتابیس — کجا چه چیزی را اصلاح کنم؟

| می‌خواهم… | فایل |
|---|---|
| ستون یا جدولی را عوض کنم | `database/tables/<table>.py` |
| داده پیش‌فرض (وضعیت، ناحیه، دپارتمان…) را عوض کنم | `database/seeds/<entity>.py` |
| کوئری یا منطق خواندن/نوشتن را عوض کنم | `database/repositories/<entity>.py` |
| ترتیب ساخت جداول یا seedها را عوض کنم | `database/init_db.py` |
| کل ساختار جداول را یک‌جا ببینم | `database/tables/__init__.py` |

> توابع CRUD برای سازگاری از `database.init_db` هم قابل import هستند
> (`from database.init_db import get_note`)، ولی محل تعریفشان `database/repositories/` است.

---

## افزودن یک ماژول جدید

الگوی ثابت پروژه (نمونهٔ مرجع: ماژول `calendar`):

1. **`database/tables/<table>.py`** — DDL + ایندکس + در صورت نیاز `migrate()` برای ستون‌های جدید
2. **`database/repositories/<entity>.py`** — **تنها جای SQL**؛ بدون منطق کسب‌وکار و بدون پیام فارسی
3. **`database/seeds/<entity>.py`** — داده پیش‌فرض (در `seeds/__init__.py` ثبت شود)
4. **`services/<name>/<name>_service.py`** — منطق، اعتبارسنجی دامنه، پیام‌های فارسی
   (سرویس فقط repository را صدا می‌زند، نه `connection.execute`)
5. **`forms/<name>/forms.py`** — فرم‌های WTForms + `__init__.py` برای export
6. **`routes/<name>/__init__.py`** — ساخت Blueprint با `url_prefix` و import کردن routeها
   ```python
   from flask import Blueprint
   name_bp = Blueprint("name", __name__, url_prefix="/names")
   from . import name_routes  # noqa: E402,F401
   __all__ = ["name_bp"]
   ```
7. **`routes/<name>/<name>_routes.py`** — endpointها؛ **بدون SQL**، فقط سرویس/فرم
8. **`templates/<name>/`** — قالب‌های آینه‌ای (`index.html` / `form.html` / `view.html`)
9. **`static/css/pages/<name>.css`** (و در صورت نیاز `static/js/pages/<name>/`)
10. **ثبت Blueprint در دو جا**: `routes/__init__.py` و `app.py`
11. **`tests/test_<name>.py`** + به‌روزرسانی `test_smoke.py` (اگر Blueprint اضافه شده)

قواعد لایه‌ها:

| لایه | مجاز | ممنوع |
|---|---|---|
| `routes/` | request/response، فرم، فراخوانی سرویس | SQL، منطق دامنه |
| `services/` | منطق، هم‌آهنگی چند repository، پیام فارسی | SQL مستقیم، `request` |
| `database/repositories/` | SQL، تبدیل Row→dict | پیام کاربر، منطق گردش‌کار |
| `forms/` | اعتبارسنجی ورودی | دسترسی به دیتابیس |
| `templates/` | نمایش | کوئری/محاسبه |

سپس Blueprint را در **دو جا** ثبت کنید: `routes/__init__.py` و `app.py`.

> ⚠️ اگر ماژول route را در `routes/<name>/__init__.py` import نکنید، مسیرهایش ثبت نمی‌شوند
> و صفحه ۴۰۴ می‌دهد. تست `test_every_route_module_is_imported` این حالت را می‌گیرد.

---

## تست

```bash
pytest                      # همه تست‌ها
pytest tests/test_smoke.py -v
pytest tests/test_architecture.py -v
```

`tests/conftest.py` یک کپی موقت از دیتابیس می‌سازد؛ **تست‌ها به دیتابیس واقعی دست نمی‌زنند.**

- **تست دود** (`test_smoke.py`): ثبت ۱۸ Blueprint، حداقل ۱۵۰ مسیر، رندر صفحه ورود، ریدایرکت صفحات محافظت‌شده، خطای ۴۰۴، کامپایل همه قالب‌ها، نبود فایل تکراری «copy».
- **تست معماری** (`test_architecture.py`): import شدن همه ماژول‌های routes، نبود فایل تخت در `services/` و `forms/`، یک فایل برای هر جدول، و نازک ماندن `init_db.py`.

---

## استانداردهای کد

```bash
black .            # قالب‌بندی، طول خط ۱۰۰
isort .            # مرتب‌سازی importها (سازگار با black)
ruff check .       # لینت (E, F, W, I, UP, B)
```

- نام ماژول‌ها و فایل‌ها: `snake_case`
- نام Blueprintها: کوتاه و بدون پسوند (`projects`، `workflow`)
- فایل‌های آینه (route ↔ service ↔ form ↔ template) هم‌نام باشند
- مسیرهای فارسی/انکودینگ: همه فایل‌ها **UTF-8** (بدون BOM)

---

## پوشه `_archive/`

در بازآرایی ساختار، هیچ فایلی حذف نشد؛ موارد زیر به `_archive/` منتقل شدند:

| زیرپوشه | محتوا |
|---|---|
| `duplicates/` | ۲۴ فایل تکراری با نام «copy» |
| `dead_code/` | `routes/routes.py` و `routes/import_routes.py` (هیچ‌جا import نمی‌شدند) |
| `junk/` | فایل‌های بدون پسوند و خروجی‌های ابزار |
| `tools/` | ابزار تولید ساختار، طرح اولیه، اسکریپت بررسی موقت |
| `legacy_databases/` | دو دیتابیس بلااستفاده (`database all.db`، `database2.db`) |
| `refactor/` | نسخه اصلی `init_db.py` (۲۴۵۹ خط) + شواهد برابری schema |
| `migration/` | اسکریپت‌های یک‌بارمصرف تفکیک ساختار |

فهرست کامل انتقال‌ها: [`_archive/MOVED-FILES.tsv`](_archive/MOVED-FILES.tsv)

> نسخه پشتیبان با حفظ کامل ساختار پوشه‌ها در `_backup/SSPE-after-refactor-<timestamp>.zip`.
> برای بازگردانی، محتوای zip را روی ریشه پروژه استخراج کنید.

---

## نکات امنیتی

- **رمز عبور**: با `scrypt` نمک‌دار (Werkzeug) ذخیره می‌شود. رمزهای قدیمی
  `SHA-256` همچنان پذیرفته می‌شوند و **در اولین ورود موفق به‌طور خودکار ارتقا**
  می‌یابند؛ بنابراین مهاجرت بدون قفل‌شدن کاربران انجام می‌شود.
- **CSRF**: دو لایه — (۱) بررسی `Origin`/`Referer` برای همه‌ی
  `POST/PUT/PATCH/DELETE`؛ درخواست cross-site با `403` رد می‌شود.
  (۲) توکن Flask-WTF در تمام ۳۳ فرم و در هدر `X-CSRFToken` برای
  درخواست‌های AJAX (پچ خودکار `fetch`/`XHR` در `base.html`).
  اگر پشت reverse proxy هستید، `SSPE_TRUSTED_ORIGINS` را تنظیم کنید.
- **XSS**: خروجی مدل زبانی قبل از نمایش با allowlist پاک‌سازی می‌شود
  (`services/ai/sanitizer.py`) تا از طریق متن اسناد کد اجرا نشود.
- **هدرهای امنیتی**: `X-Frame-Options`، `X-Content-Type-Options`،
  `Referrer-Policy` و `Permissions-Policy` روی همه‌ی پاسخ‌ها ست می‌شوند.
- **نشست**: کوکی `HttpOnly` + `SameSite=Lax`، عمر ۱۲ ساعت
  (`PERMANENT_SESSION_LIFETIME`)؛ برای HTTPS پرچم `Secure` را با
  `SESSION_COOKIE_SECURE=1` فعال کنید.
- **debug**: به‌صورت پیش‌فرض خاموش است؛ `python run.py` هم فقط روی
  `127.0.0.1` گوش می‌دهد. `debug=True` روی `0.0.0.0` خطر اجرای کد دلخواه دارد.
- `SECRET_KEY` پیش‌فرض فقط برای توسعه است و در لاگ هشدار داده می‌شود؛ در
  production از `.env` مقدار تصادفی بدهید.
- فایل `.env` و پوشه‌های `instance/`، `uploads/` در `.gitignore` هستند.
- دسترسی‌ها با `security/decorators.py` و `helpers/workflow/permissions.py` کنترل می‌شوند.
- **پیشنهاد**: پیش از انتشار، رمز پیش‌فرض `admin123` را عوض کنید و برای
  کاربرانی که از ورودی اکسل ساخته می‌شوند رمز موقت اجباری بگذارید.

---

## تقویم کاری و مهلت پاسخ

مهلت پاسخ هر سند از «گروه/زیرگروه سند» گرفته می‌شود و بر اساس **روز کاری** محاسبه می‌شود:

1. `document_subgroups.days_review` (اگر بزرگ‌تر از صفر باشد)
2. `document_groups.days_review`
3. `SSPE_DEFAULT_SLA_DAYS`

پنجشنبه‌ها و جمعه‌ها (یا هر روزی که در `SSPE_WEEKEND_DAYS` تعریف شود) و تعطیلات ثبت‌شده کسر می‌شوند.
مثال: شروع چهارشنبه با مهلت ۱ روز کاری → شنبه؛ اگر شنبه تعطیل رسمی باشد → یکشنبه.

- مدیریت تعطیلات: صفحهٔ `/calendar` (فقط admin/manager) — با **کلیک روی هر روز** می‌توانید آن را
  تعطیل یا غیرتعطیل کنید؛ افزودن/حذف با فرم هم هست. ماشین‌حساب سررسید هم در همین صفحه است.
- تعطیلات ثابت شمسی (نوروز، ۱۲ و ۱۳ فروردین، ۱۴ و ۱۵ خرداد، ۲۲ بهمن، ۲۹ اسفند) به‌صورت
  seed برای ۱۴۰۴ تا ۱۴۰۶ اضافه می‌شوند.
- تعطیلات قمری هر سال جابه‌جا می‌شوند و باید از همان صفحه ثبت شوند.
- ستون‌های `sla_days`، `sla_source` و `response_due_date` روی `documents` ذخیره می‌شوند
  (`services/documents/sla.py`).

---

## نقشه راه پیشنهادی

- [x] تفکیک `init_db.py` به `tables/` ، `seeds/` ، `repositories/`
- [x] پوشه‌بندی `services/` ، `forms/` و `routes/` بر اساس موجودیت
- [x] افزودن تست معماری برای جلوگیری از import نشدن ماژول‌های route
- [ ] ادغام `static/css/app-ui.css` با ساختار ماژولار `core/base/components/pages`
- [ ] ادغام `database/documents.py` و `database/repositories/documents.py` (دو پیاده‌سازی `get_document`)
- [ ] افزودن تست برای سرویس‌های کلیدی (`document_service`، `note_service`، `search_service`)
- [ ] جایگزینی `init_db()` در زمان import با دستور `flask init-db`
- [ ] انتقال خروجی‌های تولیدشده از `uploads/` به مسیر `instance/exports/`
- [ ] جایگزینی `print("✅ ...")` با `logging` (روی کنسول با کدپیج غیر UTF-8 خطا می‌دهد)
