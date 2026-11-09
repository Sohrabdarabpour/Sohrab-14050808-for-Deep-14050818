# سند طراحی — SSPE

این سند «قواعد معماری» پروژه است: هر کسی (یا هر عاملی) که کدی اضافه می‌کند، باید از این قراردادها پیروی کند.

---

## ۱. اصول

1. **هر فایل یک مسئولیت.** یک فایل route نباید SQL بنویسد، یک فایل CSS نباید منطق داشته باشد، یک قالب نباید ۲ هزار خط استایل در خودش داشته باشد.
2. **قرارداد بر حدس مقدم است.** نام فایل و مسیر آن باید بدون باز کردنش بگوید چه کاری می‌کند.
3. **تغییر باید قابل اثبات باشد.** هر بازآرایی با تست یا مقایسه‌ی ماشینی تأیید می‌شود، نه با «به نظر درست می‌آید».
4. **هیچ‌چیز حذف نمی‌شود، آرشیو می‌شود.** `_archive/` تاریخچه‌ی تغییرات ساختاری است.

---

## ۲. لایه‌ها

```
app.py            نقطه ورود، ثبت Blueprintها، error handlerها
   │
routes/           کنترلر: دریافت درخواست، اعتبارسنجی ورودی، انتخاب سرویس، رندر قالب
   │
services/         منطق کسب‌وکار: قاعده‌ها، محاسبات، هماهنگی بین موجودیت‌ها
   │
database/         داده: schema (tables) + seedها + کوئری‌ها (repositories)
   │
forms/            اعتبارسنجی WTForms        helpers/ , security/   کمکی و امنیت
   │
templates/        نمایش (Jinja)              static/             دارایی‌های سمت کلاینت
```

**قاعده‌ی جریان:** `routes → services → repositories`. پرش از یک لایه ممنوع است:
route نباید مستقیم `get_connection()` صدا بزند، و repository نباید `render_template` کند.

---

## ۳. ساختار دارایی‌های سمت کلاینت

### CSS — ترتیب آبشاری (به همین ترتیب بارگذاری می‌شود)

| # | مسیر | نقش |
|---|---|---|
| ۱ | `css/core/variables.css` | **توکن‌های طراحی**: رنگ، فاصله، فونت، شعاع، سایه |
| ۲ | `css/core/reset.css` | نرمال‌سازی مرورگر |
| ۳ | `css/core/utilities.css` | کلاس‌های کمکی (`.mt-2`, `.d-none`, …) |
| ۴ | `css/base/base.css` | تایپوگرافی و پایه‌ی صفحه |
| ۵ | `css/app-ui.css` | چیدمان اصلی برنامه (هدر، سایدبار، محتوا) |
| ۶ | `css/components/*.css` | کامپوننت‌های مشترک (header، sidebar، notif_dropdown، …) |
| ۷ | `{% block styles %}` | **CSS اختصاصی هر صفحه** |
| ۸ | `{% block css %}` | استثناهای صفحه |

> هر صفحه دقیقاً یک فایل CSS دارد: `static/css/pages/<مسیر قالب>.css`
> مثال: `templates/reports/area.html` ← `static/css/pages/reports/area.css`

### JS

| مسیر | نقش |
|---|---|
| `static/js/app.js` | رفتار سراسری (سایدبار، منو، ابزارهای عمومی) |
| `static/js/pages/<مسیر قالب>.js` | رفتار اختصاصی هر صفحه |

**قواعد:**
- JS هر صفحه در فایل خودش، بارگذاری با `<script src>` در همان نقطه‌ای که قبلاً بود (ترتیب تغییر نمی‌کند).
- برای انتقال داده از Jinja به JS، از `data-*` روی المنت یا
  `<script type="application/json" id="page-data">` استفاده کنید — **نه** ساختن کد JS با Jinja.
- متغیر سراسری جدید اضافه نکنید؛ از `data-*` بخوانید.

---

## ۴. قواعد نام‌گذاری

| موجودیت | مسیر |
|---|---|
| جدول | `database/tables/<table>.py` → `CREATE_SQL`، `INDEX_SQL`، `create()`، `migrate()` |
| داده پیش‌فرض | `database/seeds/<entity>.py` → `run()` |
| کوئری | `database/repositories/<entity>.py` → توابع `get_*`، `create_*`، `update_*`، `delete_*` |
| سرویس | `services/<entity>/<entity>_service.py` → کلاس `<Entity>Service` |
| فرم | `forms/<entity>/forms.py` |
| روت | `routes/<entity>/` → `__init__.py` (Blueprint) + `<entity>_routes.py` |
| قالب | `templates/<entity>/list.html` ، `form.html` ، `view.html` |
| CSS صفحه | `static/css/pages/<entity>/<page>.css` |
| JS صفحه | `static/js/pages/<entity>/<page>.js` |

همه‌ی نام‌ها `snake_case` و انگلیسی‌اند. متن فارسی فقط داخل رشته‌ها و قالب‌ها.

---

## ۵. وضعیت مهاجرت دارایی‌ها

| مورد | قبل | بعد |
|---|---|---|
| خطوط CSS داخل قالب‌ها | ۴۵٬۵۶۲ | **۰** |
| فایل CSS واقعی | ۳۵ (۲۸ تای آن مرده) | **۶۷** (همه زنده) |
| خطوط JS داخل قالب‌ها | ۱۲٬۲۴۰ | **۵٬۸۹۹** (۱۷ فایل) |
| فایل JS واقعی | ۱ (`app.js`، ۹۹ خط) | **۲۳** |

### باقی‌مانده: ۱۷ قالب با Jinja داخل JS

این قالب‌ها اسکریپتی دارند که با `{{ }}` یا `{% %}` ساخته می‌شود، بنابراین نمی‌توان کورکورانه بیرون کشید. الگوی مهاجرت:

**قبل:**
```html
<script>
  const areaId = {{ area.id }};
  const colors = { completed: "{{ status.color }}" };
</script>
```

**بعد:**
```html
<div id="page-config" data-area-id="{{ area.id }}" data-colors='{{ colors_json }}'></div>
<script src="{{ url_for('static', filename='js/pages/reports/area.js') }}"></script>
```

```js
// area.js
const el = document.getElementById("page-config");
const areaId = Number(el.dataset.areaId);
```

فهرست این ۱۷ فایل در `structure-report.md` بخش ۱۱ آمده است.

---

## ۶. چک‌لیست هر تغییر

- [ ] لایه‌ی درست را تغییر دادم؟ (route / service / repository / template)
- [ ] فایل جدید در مسیر و با نام قراردادش هست؟
- [ ] CSS یا JS جدید در `static/` است، نه داخل قالب؟
- [ ] `pytest` پاس می‌شود؟
- [ ] اگر ارجاع استاتیک اضافه/حذف شد، `test_static_references_resolve` را اجرا کردم؟

---

## ۷. تست‌های معماری

`tests/test_architecture.py` این قراردادها را ماشینی بررسی می‌کند:

| تست | چه چیزی را می‌گیرد |
|---|---|
| `test_every_route_module_is_imported` | ماژول route که import نشده و مسیرش ۴۰۴ می‌دهد |
| `test_services_are_packaged_per_entity` | فایل تخت جدید در `services/` |
| `test_forms_are_packaged_per_entity` | فایل تخت جدید در `forms/` |
| `test_one_file_per_table` | کم‌شدن/جابه‌جایی جدول‌ها |
| `test_init_db_is_thin` | بزرگ‌شدن دوباره‌ی `init_db.py` |

---

## ۸. بخش هوش مصنوعی

### معماری

```
routes/ai/assistant.py       端点های HTTP (ask, history, suggestions, export, …)
        │
services/ai/assistant_service.py   AssistantService.ask()  ← نقطه‌ی ورود
        │
        ├── nlu.py        نرمال‌سازی و پاک‌سازی متن فارسی
        ├── registry.py   ثبت intentها + تشخیص + اجرا
        ├── handlers/     یک فایل برای هر دسته‌ی intent
        ├── formatters.py ساخت پاسخ استاندارد
        ├── context.py    حافظه‌ی گفتگو
        └── llm_service.py + llm_tools.py   مسیر LLM (اختیاری)
```

**جریان پاسخ:** `ask()` → `NLU.clean` → `IntentRegistry.detect` →
اگر intent شناخته شد: `handler` → `Formatters.response`
اگر نشد: `LLM` (در صورت فعال بودن) → در غیر این صورت پاسخ «نامفهوم».

### دو لایه‌ی پاسخ‌دهی

| لایه | چه چیزی را می‌داند | وابستگی |
|---|---|---|
| **rule-based** (۴۴ intent) | سؤالات مشخص و تکرارشونده: آمار، لیست، پروژه، پیمانکار، احوال‌پرسی | هیچ — آفلاین کار می‌کند |
| **LLM + tools** (۱۵ ابزار) | سؤالات باز و ترکیبی («پروژه‌های دارای تأخیر با پیمانکار X») | کلید API و شبکه |

مهم: LLM **بدون ابزار** نمی‌تواند به داده‌های سیستم دسترسی داشته باشد.
هر قابلیت جدید باید هم intent (برای اطمینان) و هم tool (برای پاسخ ترکیبی) بگیرد.

### فایل‌های handler

| فایل | intentها |
|---|---|
| `status_handlers.py` | شمارش بر اساس وضعیت |
| `list_handlers.py` | لیست کارها، دیرکرد، امروز |
| `analytics_handlers.py` | روند، رتبه‌بندی، کارشناسان |
| `search_handlers.py` | جستجو در اسناد |
| `group_handlers.py` | گروه و زیرگروه اسناد |
| `expert_documents_handlers.py` | اسناد کارشناسان |
| `classification_handlers.py` | طبقه‌بندی و خروجی |
| `help_handlers.py` | راهنما |
| `social_handlers.py` | سلام، احوال‌پرسی، تشکر، خداحافظی، معرفی |
| `project_handlers.py` | پروژه، پیمانکار، ناحیه |

### ⚠️ لنگرگذاری الگوهای احوال‌پرسی

الگوهای اجتماعی **باید** با `^` و `$` لنگر بیندازند، وگرنه جمله‌ی واقعی را
می‌بلعند:

```python
# درست
r"^\s*(سلام|درود|صبح بخیر)[\s!؟?.]*$"

# غلط — «سلام چند سند تکمیل شده؟» را هم می‌گیرد
r"(سلام|درود)"
```

### افزودن یک intent جدید

فقط دو کار: یک دکوراتور + یک تابع، در فایل handler مربوطه.

```python
# services/ai/handlers/list_handlers.py
class ListHandlers(BaseHandler):

    @IntentRegistry.register(
        name="list_critical",          # یکتا
        patterns=[r"(فوری|بحرانی).{0,20}(لیست|نشون|بده)"],
        priority=85,                   # بالاتر = برنده در تعلق چندگانه
        confidence=0.9,
        description="لیست اسناد بحرانی",
        admin_only=False,
    )
    @staticmethod
    def handle_list_critical(question, entities, user_id, is_admin):
        return Formatters.response("...", "list", data=[...])
```

سپس کلاس را در `services/ai/handlers/__init__.py` و در بلوک import
`assistant_service.py` اضافه کنید تا ثبت شود.

### قواعد intent

1. **نام یکتا** باشد — ثبت تکراری خطا می‌دهد (`ValueError`).
2. **`priority`** را با intentهای موجود هماهنگ کنید (۸۰–۹۹ رزرو است).
3. **regex روی متن پاک‌شده** اجرا می‌شود، پس `NLU.clean` را در نظر بگیرید.
4. برای دسترسی محدود از **`admin_only=True`** استفاده کنید، نه بررسی دستی.
5. اگر پاسخ از دیتابیس می‌آید، خطا را به `Formatters` ندهید؛ `assistant_service`
   خودش خطای handler را می‌گیرد و پاسخ خطا برمی‌گرداند.

### ⚠️ دام شناخته‌شده: مرز کلمه در فارسی

`\b` در پایتون برای حروف فارسی کار **نمی‌کند**. برای حذف یک کلمه از متن،
همیشه از مرز فاصله استفاده کنید (`NLU._strip_words` الگوی مرجع است).
باگ واقعی که رخ داده بود: `replace("کمی", " ")` کلمه‌ی «تکمیل» را به «ت ل»
تبدیل می‌کرد و intent شمارش اسناد تکمیل‌شده هرگز شناسایی نمی‌شد.

### کلیدهای API

- فقط در `.env` — هرگز در سورس کد.
- `tests/test_ai.py::test_no_hardcoded_api_keys_in_source` جلوی برگشت را می‌گیرد.
- `LLMConfig.describe()` وضعیت را **بدون افشای کلید** برمی‌گرداند (برای `/assistant/llm-health`).

---

## ۹. جستجوی پیشرفته و خروجی اکسل

### جریان

```
سؤال کاربر
   ↓
SearchFilterBuilder   (services/ai/search_filter_builder.py)
   ↓  {"contractor_id": 2, "status_code": "completed", "date_from": …}
search_documents()    (services/search/search_service.py — منبع واحد حقیقت)
   ↓
FilterHandlers        (services/ai/handlers/filter_handlers.py)
   ↓  پاسخ HTML + لینک دانلود
/assistant/export/search   (routes/ai/export_routes.py)
   ↓
build_search_excel()  (services/search/search_excel_service.py)
```

### قواعد

1. **`search_documents()` تنها منبع فیلتر است.** هیچ‌جا کوئری دستی برای فیلتر نوشته نمی‌شود.
2. **نام پارامترها مشترک است** (`services/search/search_filters.py`): لینکی که دستیار
   می‌سازد با صفحه‌ی جستجو یکی است — `q`, `status`, `contractor`, `project`,
   `area`, `group`, `subgroup`, `user`, `date_from`, `date_to`, `date_column`.
3. **تاریخ‌ها در دیتابیس میلادی `YYYY/MM/DD`** هستند. اگر کاربر تاریخ شمسی بدهد
   (`1405/01/01`) یا عبارت نسبی («ماه گذشته»، «امسال»)، `SearchFilterBuilder`
   آن را به میلادی تبدیل می‌کند. اگر سال ≥ ۱۵۰۰ باشد میلادی فرض می‌شود.
4. **خروجی اکسل یک پیاده‌سازی دارد:** `build_search_excel()`. صفحه‌ی جستجو و
   دستیار هر دو باید از آن استفاده کنند.

### استخراج فیلتر از متن

| ورودی کاربر | خروجی |
|---|---|
| «اسناد پیمانکار آبسان پالایش» | `contractor_id` (تطبیق طولانی‌ترین نام) |
| «ناحیه سیالات» | `area_id` |
| «پروژه حفاظ گذاری» | `project_id` (از `search_projects`، فقط وقتی تک‌نتیجه باشد) |
| «با وضعیت تکمیل» | `status_code="completed"` |
| «ماه گذشته» | `date_from`…`date_to` (ماه شمسی قبل) |
| «از ۱۴۰۵/۰۱/۰۱ تا ۱۴۰۵/۰۳/۳۱» | تبدیل به میلادی |
| بقیه‌ی متن معنادار | `query` |

---

## ۱۰. ⚠️ قاعده‌ی انکودینگ (تجربه‌ی گران‌قیمت)

**هرگز متن فارسی را با here-string یا `Set-Content` پاورشل در فایل‌های پروژه ننویسید.**

در ویندوز، `Get-Content` و `Set-Content` در PowerShell 5.1 فایل را با **کدپیج سیستم
(cp1256)** می‌خوانند و می‌نویسند؛ نتیجه این است که UTF-8 فارسی به mojibake تبدیل
می‌شود و فایل **بی‌صدا** خراب می‌شود — بدون خطا، بدون هشدار.

اتفاقی که واقعاً افتاد: `services/ai/llm_tools.py` این‌طور خراب شد و توضیحات ابزارها
به `ظ„غŒط³طھ ظ¾ط±ظˆعکظ‡` تبدیل شد؛ LLM هم دیگر نمی‌توانست ابزار درست را انتخاب کند.

**راه درست:**
- نوشتن متن فارسی فقط با ابزار فایل (write/edit) که UTF-8 را درست مدیریت می‌کند.
- اگر مجبور به استفاده از پاورشل هستید: فقط ASCII بنویسید.
- بررسی سلامت: `_check_encoding.py`-style test — وجود یک عبارت فارسی مشخص را چک کنید،
  نه این‌که به خروجی کنسول اعتماد کنید (کنسول خودش mojibake نشان می‌دهد حتی وقتی فایل سالم است).
- بازیابی: از آخرین `_backup/*.zip` سالم، فایل را بازگردانید.
