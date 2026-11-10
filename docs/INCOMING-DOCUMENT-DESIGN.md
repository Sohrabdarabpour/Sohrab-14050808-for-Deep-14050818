# طراحی «پکیج سند ورودی» — ثبت، مسیر، کارتابل و هشدار

> پیشنهاد معماری برای فرم ثبت سند ورودی، شماره‌گذاری `DFC-YYYY-NNNN`، ارجاع به سرپرست/کارشناس،
> تکمیل مدارک، بستهٔ نامه‌ها و رفرنس‌ها، کارتابل و هشدارها.
> این سند طرح است؛ هیچ تغییری در دیتابیس اعمال نشده است.

---

## ۱. تصمیم اصلی: «سند» همان «پکیج» است

پیشنهاد: **جدول `documents` به‌عنوان هدر پکیج باقی بماند** و چند ستون + چند جدول کنار آن اضافه شود.

دلیل:

| گزینه | نتیجه |
|---|---|
| جدول جدید `document_packages` | جستجوی پیشرفته، ابزارهای AI، گزارش‌ها و اکسل همه به `documents` وابسته‌اند → دو منبع حقیقت و دوباره‌کاری |
| **افزودن ستون به `documents` + جدول‌های satellite** | ۸٬۷۸۲ رکورد فعلی بدون مهاجرت سنگین می‌مانند؛ جستجو/AI/گزارش‌ها بدون تغییر کار می‌کنند |

یعنی هر «موضوع» یک ردیف در `documents` است، و نامه‌ها، ارجاع‌ها، درخواست تکمیل مدارک، پیوست‌ها و
رویدادها به آن آویزان می‌شوند. این دقیقاً همان «پکیج پیرامون موضوع» است.

---

## ۲. ستون‌های جدید `documents`

```sql
ALTER TABLE documents ADD COLUMN package_code TEXT;            -- DFC-1405-0001 (یکتا)
ALTER TABLE documents ADD COLUMN direction TEXT DEFAULT 'incoming';  -- incoming | outgoing | internal
ALTER TABLE documents ADD COLUMN source_type TEXT;             -- client | contractor | internal | other
ALTER TABLE documents ADD COLUMN source_department_id INTEGER; -- وقتی منبع داخلی است
ALTER TABLE documents ADD COLUMN sender_name TEXT;             -- نام فرستنده/امضاکننده
ALTER TABLE documents ADD COLUMN sender_ref_no TEXT;           -- شماره نامه فرستنده
ALTER TABLE documents ADD COLUMN sender_ref_date TEXT;         -- میلادی YYYY/MM/DD (نمایش شمسی)
ALTER TABLE documents ADD COLUMN priority TEXT DEFAULT 'normal';       -- low | normal | high | urgent
ALTER TABLE documents ADD COLUMN confidentiality TEXT DEFAULT 'internal'; -- internal | confidential
ALTER TABLE documents ADD COLUMN stage TEXT DEFAULT 'registered';      -- وضعیت پکیج (بخش ۴)
ALTER TABLE documents ADD COLUMN registered_by INTEGER;
ALTER TABLE documents ADD COLUMN closed_at TEXT;
ALTER TABLE documents ADD COLUMN closed_by INTEGER;

-- ★ مهلت پاسخ محاسبه‌شده (پیاده‌سازی‌شده)
ALTER TABLE documents ADD COLUMN sla_days INTEGER;            -- مهلت مؤثر (روز کاری)
ALTER TABLE documents ADD COLUMN sla_source TEXT;             -- subgroup | group | default
ALTER TABLE documents ADD COLUMN response_due_date TEXT;      -- سررسید محاسبه‌شده (میلادی)

CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_package_code
    ON documents(package_code) WHERE package_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_stage ON documents(stage);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_type);
```

نکته‌ها:

- ستون‌های قدیمی (`code_dfc`، `contractor`، `project_name`، …) **دست نمی‌خورند** تا اکسل و گزارش‌ها نشکنند.
- `package_code` کد رسمی است؛ `code_dfc` مقدار قدیمی/واردشده می‌ماند.
- `direction` جدا از `source_type` است: یک سند «وارده» می‌تواند از کارفرما، پیمانکار یا داخل باشد.
- تاریخ‌ها مثل بقیهٔ پروژه **میلادی ذخیره** و **شمسی نمایش** می‌شوند.

---

## ۳. جدول‌های جدید

### ۳-۱. `document_references` — همهٔ نامه‌ها، رفرنس‌ها و ارتباطات

| ستون | توضیح |
|---|---|
| `id` | — |
| `document_id` | FK → documents |
| `ref_type` | `incoming_letter` · `outgoing_letter` · `verbal_request` · `phone_call` · `meeting` · `email` · `transmittal` · `completion_request` · `completion_response` · `reminder` · `other` |
| `direction` | `in` / `out` / `internal` |
| `is_official` | ۱ رسمی (نامه) / ۰ غیررسمی (شفاهی، تلفن) |
| `channel` | `letter` · `email` · `phone` · `meeting` · `verbal` · `portal` |
| `ref_no` / `ref_date` | شماره و تاریخ نامه |
| `party_type` | `client` · `contractor` · `internal` · `other` |
| `contractor_id` / `department_id` / `person_name` | طرف مقابل |
| `subject` / `summary` / `outcome` | موضوع، خلاصه، نتیجه |
| `response_to_id` | پاسخ به کدام رفرنس (زنجیرهٔ نامه و پاسخ) |
| `attachment_id` | اسکن/فایل نامه |
| `created_by` / `created_at` | — |

این جدول همان چیزی است که «با نامه یا شفاهی» را پوشش می‌دهد: `is_official=0, channel=verbal`.

### ۳-۲. `document_assignments` — ارجاع به سرپرست و کارشناس (درخت)

| ستون | توضیح |
|---|---|
| `id` | — |
| `document_id` | FK |
| `parent_id` | ارجاع والد (NULL = ارجاع اولیه از ثبت‌کننده) |
| `from_user_id` / `to_user_id` / `to_department_id` | مسیر |
| `assignee_role` | `supervisor` · `expert` · `manager` |
| `action` | `route` · `refer` · `return` · `forward` |
| `instruction` | دستور/توضیح ارجاع |
| `priority` | ارثی از سند، قابل تغییر |
| `due_date` | مهلت اقدام (میلادی) |
| `status` | `pending` · `accepted` · `in_progress` · `done` · `returned` · `cancelled` |
| `read_at` / `accepted_at` / `completed_at` | رسید خواندن و انجام |
| `created_at` / `updated_at` | — |

- «ارسال به یک یا چند سرپرست» = چند ردیف با `parent_id IS NULL`.
- «هر سرپرست به چند کارشناس» = فرزندهای همان ردیف.
- کارتابل = ارجاع‌هایی که `to_user_id = من` و `status IN (pending, accepted, in_progress)`.

### ۳-۳. `document_completion_requests` — تکمیل مدارک

| ستون | توضیح |
|---|---|
| `id`, `document_id` | — |
| `requested_by` | چه کسی درخواست داد |
| `contractor_id` | از چه پیمانکاری |
| `mode` | `written` (نامه) / `verbal` (شفاهی) |
| `reference_id` | نامهٔ درخواست (اگر کتبی) |
| `request_date` / `due_date` | تاریخ درخواست و مهلت |
| `status` | `open` · `partial` · `fulfilled` · `cancelled` |
| `note` | توضیح، شاهدان، شرایط شفاهی |
| `fulfilled_at` / `closed_by` | — |

### ۳-۴. `document_completion_items` — چک‌لیست مدارک

| ستون | توضیح |
|---|---|
| `id`, `request_id` | — |
| `title` | نام مدرک (مثلاً «نقشه تأییدشده») |
| `is_received` / `received_at` | دریافت شد؟ |
| `reference_id` / `attachment_id` | نامهٔ ارسال مدرک |
| `note` | — |

درصد تکمیل = تعداد دریافت‌شده / کل آیتم‌ها. این تنها راه واقعی برای گفتن «چقدر مانده».

### ۳-۵. `document_events` — تایم‌لاین و ممیزی (فقط افزودنی)

| ستون | توضیح |
|---|---|
| `id`, `document_id`, `actor_id` | — |
| `event_type` | `registered` · `routed` · `referred` · `accepted` · `returned` · `letter_added` · `completion_requested` · `completion_fulfilled` · `status_changed` · `closed` · `reopened` · `alarm` |
| `summary` | متن کوتاه برای نمایش |
| `payload` | JSON جزئیات (شناسه‌ها، از/به، تغییر وضعیت) |
| `created_at` | — |

هر عملیات باید یک ردیف اینجا بنویسد. حذف/ویرایش ممنوع → تاریخچهٔ قابل استناد.

### ۳-۶. `document_attachments`

| ستون | توضیح |
|---|---|
| `id`, `document_id`, `reference_id`, `event_id` | اتصال |
| `original_name`, `stored_name`, `mime`, `size` | فایل |
| `kind` | `letter` · `scan` · `evidence` · `other` |
| `uploaded_by`, `created_at` | — |

جایگزین رفتار فعلیِ پراکنده در `uploads/`؛ فایل‌ها در `instance/uploads/<document_id>/`.

### ۳-۷. `document_counters` — شماره‌گذاری

```sql
CREATE TABLE IF NOT EXISTS document_counters (
    year INTEGER PRIMARY KEY,       -- سال شمسی
    last_value INTEGER NOT NULL DEFAULT 0
);
```

### ۳-۸. `document_alarms` — هشدارها (برای جلوگیری از تکرار)

| ستون | توضیح |
|---|---|
| `id`, `document_id` | — |
| `alarm_type` | `assignment_due` · `assignment_overdue` · `completion_due` · `document_deadline` · `no_action` |
| `target_user_id` | گیرنده |
| `level` | `info` · `warning` · `critical` |
| `due_at` | زمان مؤثر |
| `status` | `pending` · `sent` · `acked` · `dismissed` |
| `dedupe_key` UNIQUE | مثل `assignment:42:overdue:3d` |
| `created_at` / `sent_at` / `acked_at` | — |

خروجی هر هشدار یک ردیف در `notifications` موجود هم می‌سازد تا زنگ و badge فعلی کار کند.

### ۳-۹. (اختیاری) `document_watchers`

چه کسانی «در جریان» باشند بدون اینکه اقدامی کنند (مدیر دپارتمان، کنترل‌مستندات، جانشین در مرخصی).
اگر لازم نیست، حذف شود.

---

## ۴. گردش وضعیت (stage) و مجوزها

```
draft ──ثبت──> registered ──ارسال به سرپرست──> routed
                                                 │
                            ┌────────────────────┼────────────────────┐
                            ▼                    ▼                    ▼
                     in_progress ──درخواست تکمیل──> awaiting_contractor
                            │                    │
                            └──اقدام کارشناس─────┘
                                     │
                                under_review ──تأیید نهایی──> closed
                                     │
                                 cancelled / archived
```

| اقدام | ثبت‌کننده (doc_controller) | سرپرست | کارشناس | مدیر/ادمین |
|---|---|---|---|---|
| ثبت سند و شماره | ✅ | — | — | ✅ |
| ارسال به یک/چند سرپرست | ✅ | — | — | ✅ |
| پذیرش/ارجاع به کارشناس | — | ✅ (دپارتمان خودش) | — | ✅ |
| افزودن نامه/رفرنس | ✅ | ✅ | ✅ (سند خودش) | ✅ |
| درخواست تکمیل مدارک | ✅ | ✅ | ⚠️ قابل تنظیم | ✅ |
| تأیید دریافت مدارک | ✅ | ✅ | — | ✅ |
| بستن پکیج | ✅ | ✅ | — | ✅ |
| بازگشایی/لغو | — | — | — | ✅ |
| مشاهده | همه | دپارتمان + ارجاع‌ها | فقط ارجاع‌های خودش | همه |

قاعده: **همهٔ بررسی‌ها سمت سرور** (نه فقط مخفی‌کردن دکمه). افزودن `helpers/permissions.py` با
توابع `can_view_package`، `can_route`، `can_complete`، `can_close`.

---

## ۴-۵. مهلت پاسخ و تقویم کاری (✅ پیاده‌سازی شد)

مهلت پاسخ از قبل در `document_subgroups.days_review` تعریف شده بود ولی هیچ‌جا استفاده نمی‌شد.
حالا:

| اولویت | منبع | ستون |
|---|---|---|
| ۱ | زیرگروه سند | `document_subgroups.days_review` |
| ۲ | گروه سند (مقدار پیش‌فرض گروه) | `document_groups.days_review` (ستون جدید) |
| ۳ | سامانه | `SSPE_DEFAULT_SLA_DAYS` (پیش‌فرض ۷) |

**فرمول:** سررسید = تاریخ دریافت + N **روز کاری**. روز شروع روز صفر است؛ پنجشنبه و جمعه
(یا هر روزِ `SSPE_WEEKEND_DAYS`) و تعطیلات جدول `calendar_holidays` کسر می‌شوند.

```
دریافت شنبه ۱۴۰۵/۰۱/۰۱، مهلت ۳ روز کاری، ۲ تا ۴ فروردین تعطیل، پنجشنبه/جمعه تعطیل:
یکشنبه ۲(تعطیل) → دوشنبه ۳(تعطیل) → سه‌شنبه ۴(تعطیل) → چهارشنبه ۵ (۱)
→ پنجشنبه ۶(آخر هفته) → جمعه ۷(آخر هفته) → شنبه ۸ (۲) → یکشنبه ۹ (۳)
⇒ سررسید = ۱۴۰۵/۰۱/۰۹
```

### جدول تعطیلات

```sql
CREATE TABLE calendar_holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holiday_date TEXT NOT NULL UNIQUE,   -- میلادی YYYY/MM/DD
    jalali_date TEXT NOT NULL,           -- شمسی (نمایش)
    jalali_year INTEGER NOT NULL,        -- فیلتر سال
    title TEXT NOT NULL,
    kind TEXT DEFAULT 'official',        -- official | company | other
    is_active INTEGER DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- تعطیلات ثابت شمسی (نوروز، ۱۲/۱۳ فروردین، ۱۴/۱۵ خرداد، ۲۲ بهمن، ۲۹ اسفند) برای ۱۴۰۴–۱۴۰۶
  به‌صورت seed اضافه می‌شوند.
- تعطیلات قمری هر سال جابه‌جا می‌شوند → از صفحهٔ `/calendar` ثبت می‌شوند (یا ورودی گروهی بعداً).
- کش ۶۰ ثانیه‌ای + `invalidate` بعد از هر تغییر، تا هر درخواست به دیتابیس نزند.

### صفحهٔ `/calendar`

- تقویم ماه شمسی با رنگ‌بندی روز کاری / تعطیل / جمعه و برجسته‌کردن امروز.
- آمار ماه: تعداد روز کاری، تعطیل رسمی، آخر هفته.
- مدیریت تعطیلات سال (افزودن/حذف) — فقط admin/manager.
- **ماشین‌حساب مهلت:** انتخاب گروه/زیرگروه + تاریخ شروع → مهلت مؤثر، منبع آن و سررسید شمسی.
- در فرم ثبت سند (فاز ۱) همین محاسبه هنگام انتخاب زیرگروه به‌صورت زنده نمایش داده می‌شود و
  `sla_days` / `sla_source` / `response_due_date` روی سند ذخیره می‌شوند.

### اثر بر هشدارها

همهٔ هشدارهای بخش ۷ به‌جای «روز تقویمی» با «روز کاری باقی‌مانده» سنجیده می‌شوند
(`working_days.working_days_left`) تا تعطیلات، مهلت را واقعی‌تر کند.

---

## ۵. شماره‌گذاری `DFC-YYYY-NNNN`

- سال از `DateHelper.now_tehran()` (شمسی).
- تخصیص اتمیک:

```python
with transaction():                    # BEGIN IMMEDIATE
    row = db.execute("SELECT last_value FROM document_counters WHERE year = ?", (year,)).fetchone()
    next_value = (row["last_value"] if row else 0) + 1
    db.execute("INSERT INTO document_counters(year, last_value) VALUES(?, ?) "
               "ON CONFLICT(year) DO UPDATE SET last_value = ?", (year, next_value, next_value))
    code = f"DFC-{year}-{next_value:04d}"
```

- `UNIQUE` روی `package_code`؛ در صورت برخورد، یک بار retry.
- شماره **هرگز بازاستفاده یا حذف نمی‌شود**؛ سند لغوشده هم شماره‌اش را نگه می‌دارد (برای حسابرسی).
- مهاجرت: برای ۸٬۷۸۲ سند فعلی به ترتیب `id` و بر اساس سال شمسیِ `date_received` شماره تولید و
  در ستون `package_code` ذخیره می‌شود؛ `code_dfc` قدیمی دست‌نخورده می‌ماند.
- پیشنهاد تکمیلی: QR/بارکد روی برگهٔ چاپی که به `/documents/<id>` اشاره کند.

---

## ۶. کارتابل

مسیر `/inbox` با تب‌ها و badge:

| تب | کوئری |
|---|---|
| اقدام من | `assignments.to_user_id = me AND status IN ('pending','in_progress')` |
| خوانده‌نشده | همان + `read_at IS NULL` |
| دیرکرد | همان + `due_date < today` |
| در انتظار دیگران | `assignments.from_user_id = me AND status IN (...)` |
| تکمیل مدارک | `completion_requests.status IN ('open','partial')` و من مسئولم |
| بسته‌شده‌های من | `done` در ۳۰ روز گذشته |

هر ردیف: کد پکیج، موضوع، منبع (کارفرما/پیمانکار/داخلی)، اولویت، از چه کسی، مهلت، وضعیت،
نقطهٔ خوانده‌نشده و دکمه‌های سریع (خواندم / ارجاع / انجام شد).

- شمارندهٔ کارتابل در هدر (کنار زنگ اعلان‌ها) با polling هر ۶۰ ثانیه — همان الگوی فعلی نوتیفیکیشن‌ها.
- «کارتابل من» و «ارجاع‌های من» در سایدبار زیر منوی اسناد.

---

## ۷. هشدارها و تشدید (Escalation)

| رخداد | زمان | گیرنده |
|---|---|---|
| مهلت ارجاع نزدیک | ۱ روز قبل | مسئول ارجاع |
| دیرکرد ارجاع | ۱ روز بعد | مسئول + سرپرست دپارتمان |
| دیرکرد ۳ روز | ۳ روز | سرپرست دپارتمان |
| دیرکرد ۷ روز | ۷ روز | مدیر/ادمین + علامت «بحرانی» روی پکیج |
| بدون اقدام (حتی خوانده‌نشده) | ۴۸ ساعت | مسئول + سرپرست |
| مهلت تکمیل مدارک | ۲ روز قبل / روز موعد | مسئول تکمیل + سرپرست |
| دیرکرد تکمیل مدارک | ۳ روز | سرپرست + هشدار «پیگیری پیمانکار» |
| مهلت کل سند (`deadline`) | ۳ روز قبل، روز موعد، هر ۷ روز بعد | مسئول پکیج + مدیر |

اجرا:

- دستور `flask alarms-scan` (ساخت در `routes/cli.py` یا `app.py`)، هر ۱۵ دقیقه با Task Scheduler ویندوز.
- بررسی «تنبل» هنگام باز کردن کارتابل: اگر هشدارِ ارسال‌نشده باشد همان لحظه ساخته می‌شود (تا بدون
  scheduler هم چیزی از دست نرود).
- `dedupe_key` یونیک از اسپم جلوگیری می‌کند.
- ارسال ایمیل/SMS اختیاری و در فاز بعد؛ فعلاً اعلان داخلی.

---

## ۸. صفحه‌ها

1. **`/documents/new`** — فرم سه‌مرحله‌ای:
   - مرحله ۱: منبع و نامه (نوع منبع، پیمانکار/پروژه/دپارتمان، فرستنده، شماره و تاریخ نامه، موضوع،
     اولویت، محرمانگی، تاریخ دریافت، پیوست، توضیح).
   - مرحله ۲: مسیر (چند سرپرست، دستور و مهلت هر کدام، امکان افزودن «در جریان»).
   - مرحله ۳: تکمیل مدارک (اختیاری: کتبی/شفاهی، چک‌لیست مدارک، مهلت) + مرور و ثبت.
   - پس از ثبت: تخصیص کد، ساخت ارجاع‌ها، هشدارها، اعلان‌ها → redirect به صفحهٔ پکیج.
2. **`/documents/<id>`** — پکیج با تب‌ها:
   خلاصه · ارجاع‌ها (درخت) · نامه‌ها و رفرنس‌ها · تکمیل مدارک · پیوست‌ها · تایم‌لاین · یادداشت‌ها.
3. **`/inbox`** — کارتابل (بخش ۶).
4. **گزارش‌ها** — ورودی بر اساس منبع، زمان چرخه (ثبت→بستن)، رعایت SLA، بار کاری کارشناسان،
   نرخ تکمیل مدارک، اسناد بحرانی.

---

## ۹. یکپارچگی با بخش‌های موجود

- **جستجو:** افزودن `package_code`، `sender_ref_no`، `source_type`، `stage` به ستون‌های جستجو و فیلترها.
- **AI:** سه ابزار جدید: «کارتابل من»، «اسناد دیرکرد»، «در انتظار تکمیل مدارک».
- **گزارش‌ها/اکسل:** خروجی پکیج شامل نامه‌ها و ارجاع‌ها.
- **یادداشت‌های گردش‌کار (`document_notes`):** دست‌نخورده می‌مانند؛ آن‌ها «گردش تأیید محتوا» هستند و
  ارجاع‌های جدید «گردش سند». در صفحهٔ پکیج هر دو نمایش داده می‌شوند ولی در هم ادغام نمی‌شوند.
- **داده‌های قدیمی:** `source_type='legacy'`، `stage` بر اساس وضعیت فعلی (تکمیل→closed، در حال بررسی→in_progress، …).

---

## ۱۰. چیزهایی که ممکن است ندیده باشید (پیشنهاد افزودن)

| مورد | چرا لازم است |
|---|---|
| **رسید خواندن** (`read_at`) | «فرستادم ولی ندید» رایج‌ترین شکایت کارتابل است |
| **مهلت در سطح هر ارجاع** | یک مهلت کلی برای چند کارشناس هم‌زمان کار نمی‌کند |
| **جانشین/واگذاری موقت** | مرخصی سرپرست نباید گردش را بخواباند |
| **جلوگیری از ثبت تکراری** | هشدار بر اساس `sender_ref_no + source_type` («این نامه قبلاً ثبت شده») |
| **شمارهٔ باطل‌شده** | شمارهٔ مصرف‌شده حذف نمی‌شود؛ فقط سند لغو می‌شود |
| **درصد تکمیل چک‌لیست** | پاسخ به «چقدر مانده» بدون تماس تلفنی |
| **اسناد «در جریان» (CC)** | مدیر بدون اینکه مسئول شود، مطلع باشد |
| **محرمانگی** | محدودکردن مشاهدهٔ اسناد خاص به نقش‌های مشخص |
| **نگهداشت/آرشیو** | بستن پکیج بعد از N سال و خارج‌کردن از کارتابل |
| **چاپ برگهٔ سند + QR** | گردش فیزیکی و برچسب‌گذاری پرونده |
| **گزارش زمان چرخه** | تنها معیار واقعی بهبود فرآیند |
| **لاگ تغییرات (event)** | پاسخ به «چه کسی چه زمانی چه کرد» |
| **بکاپ قبل از مهاجرت** | تغییر ستون‌ها بدون نقطهٔ بازگشت ریسک است |

---

## ۱۱. فازبندی پیشنهادی

| فاز | تحویل | تخمین |
|---|---|---|
| **۱ — پایه** | ستون‌ها + ۴ جدول اصلی (refs, assignments, events, counters) + شماره‌گذاری + فرم ثبت + صفحهٔ پکیج (خلاصه/تایم‌لاین) + مجوزها + تست | ۲ تا ۳ روز کاری |
| **۲ — مسیر و کارتابل** | ارجاع چندسرپرستی/چندکارشناس + پذیرش + کارتابل + badge + اعلان + رسید خواندن | ۲ روز |
| **۳ — تکمیل مدارک و نامه‌ها** | رفرنس‌ها + پیوست‌ها + درخواست کتبی/شفاهی + چک‌لیست + هشدارها + `alarms-scan` | ۲ تا ۳ روز |
| **۴ — یکپارچگی** | فیلترهای جستجو + ابزارهای AI + گزارش‌ها/اکسل + چاپ/QR + مهاجرت داده قدیمی | ۲ روز |

هر فاز با تست و بدون شکستن ۱۵۸ مسیر فعلی تحویل می‌شود.

---

## ۱۲. تصمیم‌هایی که باید تأیید کنید

1. **همان `documents` پکیج باشد؟** (پیشنهاد: بله)
2. ارجاع به چند **دپارتمان** هم‌زمان لازم است یا چند سرپرست از یک دپارتمان کافی است؟
3. نامه‌های فیزیکی اسکن می‌شوند؟ حجم تقریبی و نیاز به OCR؟
4. تکمیل مدارک **شفاهی** را چه کسی ثبت می‌کند و چه مدرکی نگه می‌داریم (یادداشت + شاهد)؟
5. اعلان فقط داخلی باشد یا ایمیل/SMS هم لازم است؟
6. امضای نهایی مدیر/مدیرعامل قبل از بستن پکیج لازم است؟
7. شمارهٔ دستی هم مجاز باشد یا شمارهٔ سیستم اجباری است؟

---

## ۱۳. وضعیت پیاده‌سازی

| بخش | وضعیت |
|---|---|
| جدول `calendar_holidays` + seed تعطیلات ثابت ۱۴۰۴–۱۴۰۶ | ✅ انجام شد |
| ستون `days_review` روی `document_groups` (مهلت پیش‌فرض گروه) | ✅ انجام شد |
| ستون‌های `sla_days` / `sla_source` / `response_due_date` روی `documents` | ✅ انجام شد |
| سرویس روز کاری (`services/calendar/working_days.py`) با احتساب جمعه و تعطیلات | ✅ انجام شد |
| تعیین مهلت با اولویت زیرگروه → گروه → پیش‌فرض | ✅ انجام شد |
| صفحهٔ `/calendar` (تقویم، تعطیلات، ماشین‌حساب) | ✅ انجام شد |
| ۳۳ تست تقویم/SLA | ✅ همه سبز (مجموع ۱۶۹ تست) |
| جدول‌ها و فرم ثبت سند (ارجاع، نامه‌ها، تکمیل مدارک) | ⏳ فاز ۱ به بعد |


# لاگ پیاده‌سازی «پکیج سند»

این فایل هر قدم پیاده‌سازی را ثبت می‌کند تا در آینده بدانید چه کارهایی انجام شده و چرا.

---

## فاز ۱ — زیرساخت دیتابیس و آپلود

### قدم ۱ — فایل‌های جدول (✅ انجام شد)

| فایل | جدول |
|---|---|
| `database/tables/document_counters.py` | `document_counters` |
| `database/tables/document_assignments.py` | `document_assignments` |
| `database/tables/document_events.py` | `document_events` |
| `database/tables/document_references.py` | `document_references` |
| `database/tables/document_completion_requests.py` | `document_completion_requests` + `items` |
| `database/tables/document_attachments.py` | `document_attachments` |
| `database/tables/document_alarms.py` | `document_alarms` |
| `database/tables/document_watchers.py` | `document_watchers` |

### قدم ۲ — Migration ستون‌ها (✅ انجام شد)

فایل: `database/migrations/add_document_package_columns.py`
۲۳ ستون جدید به `documents` اضافه شد.

### قدم ۳ — ثبت جداول (✅ انجام شد)

فایل: `database/tables/__init__.py` ویرایش شد.

### قدم ۴ — هماهنگی init_db (✅ انجام شد)

فایل: `database/init_db.py` ویرایش شد — migration جدید اضافه شد.

**تست:** `python check_package_setup.py` → همه چیز OK (۲۳ ستون، ۹ جدول، ۲۳ ایندکس).

### قدم ۵ — تنظیمات آپلود (✅ انجام شد)

فایل: `config.py`:
- `MAX_CONTENT_LENGTH = None` (حذف محدودیت Flask)
- `DOCUMENT_UPLOAD_ROOT = instance/uploads`
- `ALLOWED_UPLOAD_EXTENSIONS` — لیست پسوندهای مجاز
- `PREVIEWABLE_EXTENSIONS` — پسوندهای قابل پیش‌نمایش
- `MAX_UPLOAD_SIZE_BYTES = None`

### قدم ۶ — سرویس رویدادها (✅ انجام شد)

فایل: `services/documents/event_service.py`
- `log_event()` — ثبت رویداد در تایم‌لاین
- `list_events()` — خواندن تایم‌لاین سند
- `EventType` — لیست ثابت انواع رویداد

### قدم ۷ — سرویس ذخیره‌سازی (✅ انجام شد)

فایل: `services/documents/storage_service.py`
- آپلود استریمی تکه‌تکه (chunk 1MB)
- محاسبه‌ی SHA-256
- نام‌گذاری UUID
- ذخیره در `instance/uploads/<document_id>/`
- تشخیص previewable
- حذف امن

### قدم ۸ — تست سرویس‌ها (✅ انجام شد)

فایل موقت: `test_services.py` — همه تست‌ها سبز.

---

## تصمیمات معماری

1. **جدول `document_assignments` مستقل از `document_notes` است.** گردش تأیید محتوا (notes) دست‌نخورده می‌ماند؛ گردش سند (assignments) موازی کار می‌کند.
2. **`document_events` فقط append-only است.** هر عملیات باید یک ردیف اینجا بنویسد.
3. **آپلود استریمی.** فایل تکه‌تکه خوانده می‌شود، در RAM بارگذاری نمی‌شود.
4. **شماره‌گذاری اتمیک** با `BEGIN IMMEDIATE` روی `document_counters` (در قدم‌های بعد).
5. **فایل‌ها با UUID ذخیره می‌شوند** — نام اصلی در DB می‌ماند، نام فیزیکی UUID است.
6. **دسترسی سه‌لایه:** ثبت‌کننده، ادمین/مدیر، مسئول ارجاع فعال.

---

## قدم‌های بعدی

- [ ] روت‌های آپلود/preview/download
- [ ] سرویس ثبت سند + شماره‌گذاری اتمیک
- [ ] سرویس ارجاع
- [ ] سرویس SLA
- [ ] کارتابل (`/inbox`)
- [ ] هشدارها (alarm scanner)
- [ ] آرشیو و بازگشایی

### قدم ۹ — روت‌های آپلود/preview/download (✅ انجام شد)

فایل: `routes/documents/attachment_routes.py` (جدید)
فایل: `routes/documents/__init__.py` (ویرایش شد — import attachment_routes)

روت‌ها:
- `POST /documents/<id>/attachments/upload` — آپلود استریمی
- `GET /documents/<id>/attachments.json` — لیست JSON
- `GET /documents/attachments/<id>/preview` — inline + Range (206)
- `GET /documents/attachments/<id>/download` — attachment + Range
- `POST /documents/attachments/<id>/delete` — حذف + رویداد
- `GET /documents/attachments/test-page/<id>` — صفحه‌ی تست (فقط DEBUG)

نکات فنی:
- صفحه‌ی تست از CSRF token استفاده می‌کند (`X-CSRFToken` header) — بدون آن 400 می‌دهد.
- `conditional=True` در `send_file` → پشتیبانی از Range/ETag/Last-Modified.
- دسترسی: `admin/manager/supervisor/doc_controller` + ثبت‌کننده + مسئول ارجاع فعال.

تست موفق:
- آپلود PDF/TXT از مرورگر → 200
- پیش‌نمایش inline → 200 + 206 (Range)
- دانلود با نام اصلی
- حذف فایل از دیسک

### قدم ۱۰ — سرویس پکیج سند (✅ انجام شد)

فایل: `services/documents/package_service.py` (جدید)
فایل: `services/documents/__init__.py` (ادغام DocumentService + جدید)

توابع:
- `allocate_package_code()` — شماره‌گذاری اتمیک DFC-YYYY-NNNN (BEGIN + commit)
- `register_document()` — ثبت سند + شماره + SLA + رویداد
- `change_stage()` — انتقال مرحله با قواعد مجاز (STAGE_TRANSITIONS)
- `get_package()` — خواندن کامل پکیج با JOINها
- `Stage` — کلاس ثابت‌ها
- `STAGE_TRANSITIONS` — گراف مجاز انتقال

تست موفق:
- ثبت سند اول → DFC-1405-0001 (id=8783)
- ثبت سند دوم → DFC-1405-0002 (اتمیک)
- routed → archived رد شد
- تایم‌لاین ۲ رویداد ثبت کرد

### قدم ۱۱ — سرویس ارجاع (✅ انجام شد)

فایل: `services/documents/assignment_service.py` (جدید)

توابع:
- `route_document()` — ارجاع به یک یا چند نفر
- `mark_read()` / `accept()` / `start()` / `complete()` / `return_to_sender()` / `cancel()`
- `get_inbox()` — کوئری کارتابل با تب‌ها
- `get_document_assignments()` — درخت ارجاع‌ها
- `AssignmentStatus` / `AssignmentAction` — ثابت‌ها

تست موفق:
- ثبت سند DFC-1405-0003
- ارجاع به کارشناس با مهلت ۳ روز کاری
- کارتابل: ۱ مورد active
- چرخه‌ی کامل: read → accept → start → complete
- تایم‌لاین ۷ رویداد
- کارتابل بعد از انجام: active=0، done=1

### قدم ۱۲ — روت‌های ارجاع و کارتابل (✅ انجام شد)

فایل: `routes/documents/assignment_routes.py` (جدید)
فایل: `routes/inbox/__init__.py` (جدید)
فایل: `routes/inbox/inbox_routes.py` (جدید)
فایل: `templates/inbox/inbox.html` (جدید)
فایل: `routes/documents/__init__.py` (ویرایش — import assignment_routes)
فایل: `routes/__init__.py` (ویرایش — inbox_bp)
فایل: `app.py` (ویرایش — register_blueprint inbox_bp)

روت‌ها:
- `POST /documents/<id>/route` — ارجاع
- `POST /documents/assignments/<id>/{read,accept,start,complete,return,cancel}`
- `GET /documents/<id>/assignments.json`
- `GET /inbox/` — کارتابل
- `GET /inbox/api/counts` — شمارنده‌ها
- `GET /inbox/api/<tab>` — لیست JSON

تست: کارتابل ۵ تب، شمارنده‌ها، اقدامات inline.

### قدم ۱۳ — صفحه‌ی تست ارجاع (✅ انجام شد)

فایل: `routes/documents/assignment_test_routes.py` (جدید)
فایل: `routes/documents/__init__.py` (ویرایش)

آدرس: `GET /documents/assignment-test-page/<id>` (فقط DEBUG)
امکانات: انتخاب چند گیرنده، دستور، مهلت، اولویت، نمایش درخت ارجاع‌ها.

تست: ارجاع از صفحه‌ی تست + مشاهده در کارتابل + چرخه‌ی accept/start/complete.

### قدم ۱۴ — سرویس SLA (✅ انجام شد)

فایل: `services/documents/sla_service.py` (جدید)
- `recalculate_sla()` — اولویت زیرگروه → گروه → پیش‌فرض
- `refresh_overdue_flags()` — پرچم دیرکرد همه‌ی اسناد
- `is_document_overdue()`
- `_add_working_days()` / `_working_days_between()` — با fallback

تست: سند 8785 → ۷ روز، سررسید 2026/11/21، دیرکرد ۰.

### قدم ۱۵ — سرویس هشدار (✅ انجام شد)

فایل: `services/documents/alarm_service.py` (جدید)
- `scan_assignments()` — نزدیک مهلت / دیرکرد ۱-۳-۷ / بدون اقدام ۴۸h
- `scan_documents()` — دیرکرد مهلت کل ۱-۳-۷-۱۴
- `scan_all()` — اجرای همه
- `list_user_alarms()` / `ack_alarm()`
- dedupe_key یکتا → جلوگیری از اسپم
- اتصال به `notifications` موجود

تست: `flask alarms-scan` → ۲ هشدار ارجاع، notification ساخته شد.

### قدم ۱۶ — CLI (✅ انجام شد)

فایل: `routes/cli.py` (جدید) + ثبت در `app.py`
- `flask alarms-scan`
- `flask refresh-overdue`
- `flask recalc-sla <id>`

### قدم ۱۷ — صفحه‌ی کامل پکیج (✅ انجام شد)

فایل: `routes/documents/package_routes.py` (جدید)
فایل: `templates/documents/package.html` (جدید)
فایل: `routes/documents/__init__.py` (ویرایش)

آدرس: `GET /documents/package/<id>`
تب‌ها: خلاصه | ارجاع‌ها | تایم‌لاین | پیوست‌ها
API: `POST /documents/package/<id>/change-stage`

تست: صفحه لود شد، ارجاع از این صفحه، تایم‌لاین، آپلود و حذف پیوست.


### اصلاح — پیش‌نمایش پیوست (✅ تکمیل شد — با یک یادداشت)

- **آپلود:** کاملاً عملیاتی و بدون محدودیت حجم.
- **پیش‌نمایش عکس/ویدیو/صدا:** داخل مودال به‌درستی کار می‌کند.
- **پیش‌نمایش PDF:** به دلیل محدودیت‌های امنیتی مرورگرها (Chrome/Edge)، فایل PDF داخل `iframe` یا `object` سفید نمایش داده می‌شود. راه‌حل فعلی: نمایش یک کارت زیبا با دکمه‌ی «باز کردن در تب جدید».
- **یادداشت برای آینده (TODO):** برای رندر PDF درون مودال، باید کتابخانه‌ی `PDF.js` (مولّد موزیلا) را به پروژه اضافه کنیم و فایل را با آن رندر کنیم.


# طراحی «پکیج سند ورودی» — ثبت، مسیر، کارتابل و هشدار

> **سند فنی زنده (Living Document)**
> این سند معماری و وضعیت پیاده‌سازی «پکیج سند» را در پروژه SSPE ثبت می‌کند.
> بخش‌های علامت‌گذاری‌شده با ✅ در کدبیس پیاده‌سازی شده‌اند.

---

## ۱. تصمیم اصلی: «سند» همان «پکیج» است

**جدول `documents` به‌عنوان هدر پکیج باقی می‌ماند** و چند ستون + چند جدول ماهواره‌ای (satellite) به آن اضافه شده است.

دلیل انتخاب این معماری:
- جستجوی پیشرفته، ابزارهای AI، گزارش‌ها و اکسل همه به `documents` وابسته‌اند.
- با ایجاد جدول جدید، دو منبع حقیقت ایجاد می‌شد و دوباره‌کاری رخ می‌داد.
- ۸٬۷۸۲ رکورد فعلی بدون مهاجرت سنگین حفظ می‌شوند.

یعنی هر «موضوع» یک ردیف در `documents` است، و نامه‌ها، ارجاع‌ها، درخواست تکمیل مدارک، پیوست‌ها و رویدادها به آن آویزان می‌شوند. این دقیقاً همان «پکیج پیرامون موضوع» است.

---

## ۲. ستون‌های جدید `documents` (✅ انجام شد)

```sql
-- شماره‌گذاری و طبقه‌بندی
ALTER TABLE documents ADD COLUMN package_code TEXT;          -- DFC-1405-0001 (یکتا)
ALTER TABLE documents ADD COLUMN package_year INTEGER;
ALTER TABLE documents ADD COLUMN direction TEXT DEFAULT 'incoming';
ALTER TABLE documents ADD COLUMN source_type TEXT;
ALTER TABLE documents ADD COLUMN source_department_id INTEGER;
ALTER TABLE documents ADD COLUMN priority TEXT DEFAULT 'normal';
ALTER TABLE documents ADD COLUMN confidentiality TEXT DEFAULT 'internal';

-- فرستنده
ALTER TABLE documents ADD COLUMN sender_name TEXT;
ALTER TABLE documents ADD COLUMN sender_ref_no TEXT;
ALTER TABLE documents ADD COLUMN sender_ref_date TEXT;

-- مرحله چرخه عمر
ALTER TABLE documents ADD COLUMN stage TEXT DEFAULT 'draft';

-- SLA کامل
ALTER TABLE documents ADD COLUMN sla_start_date TEXT;
ALTER TABLE documents ADD COLUMN sla_effective_days INTEGER;
ALTER TABLE documents ADD COLUMN is_overdue INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN overdue_days INTEGER DEFAULT 0;

-- آرشیو
ALTER TABLE documents ADD COLUMN registered_by INTEGER;
ALTER TABLE documents ADD COLUMN registered_at TEXT;
ALTER TABLE documents ADD COLUMN closed_by INTEGER;
ALTER TABLE documents ADD COLUMN closed_at TEXT;
ALTER TABLE documents ADD COLUMN archived_by INTEGER;
ALTER TABLE documents ADD COLUMN archived_at TEXT;
ALTER TABLE documents ADD COLUMN archive_reason TEXT;
ALTER TABLE documents ADD COLUMN reopen_count INTEGER DEFAULT 0;

# طراحی «پکیج سند ورودی» — ثبت، مسیر، کارتابل و هشدار

> **سند فنی زنده (Living Document)**
> این سند معماری و وضعیت پیاده‌سازی «پکیج سند» را در پروژه SSPE ثبت می‌کند.
> بخش‌های علامت‌گذاری‌شده با ✅ در کدبیس پیاده‌سازی شده‌اند.

---

## ۱. تصمیم اصلی: «سند» همان «پکیج» است

**جدول `documents` به‌عنوان هدر پکیج باقی می‌ماند** و چند ستون + چند جدول ماهواره‌ای (satellite) به آن اضافه شده است.

دلیل انتخاب این معماری:
- جستجوی پیشرفته، ابزارهای AI، گزارش‌ها و اکسل همه به `documents` وابسته‌اند.
- با ایجاد جدول جدید، دو منبع حقیقت ایجاد می‌شد و دوباره‌کاری رخ می‌داد.
- ۸٬۷۸۲ رکورد فعلی بدون مهاجرت سنگین حفظ می‌شوند.

یعنی هر «موضوع» یک ردیف در `documents` است، و نامه‌ها، ارجاع‌ها، درخواست تکمیل مدارک، پیوست‌ها و رویدادها به آن آویزان می‌شوند. این دقیقاً همان «پکیج پیرامون موضوع» است.

---

## ۲. ستون‌های جدید `documents` (✅ انجام شد)

```sql
-- شماره‌گذاری و طبقه‌بندی
ALTER TABLE documents ADD COLUMN package_code TEXT;          -- DFC-1405-0001 (یکتا)
ALTER TABLE documents ADD COLUMN package_year INTEGER;
ALTER TABLE documents ADD COLUMN direction TEXT DEFAULT 'incoming';
ALTER TABLE documents ADD COLUMN source_type TEXT;
ALTER TABLE documents ADD COLUMN source_department_id INTEGER;
ALTER TABLE documents ADD COLUMN priority TEXT DEFAULT 'normal';
ALTER TABLE documents ADD COLUMN confidentiality TEXT DEFAULT 'internal';

-- فرستنده و قرارداد
ALTER TABLE documents ADD COLUMN sender_name TEXT;
ALTER TABLE documents ADD COLUMN sender_ref_no TEXT;
ALTER TABLE documents ADD COLUMN sender_ref_date TEXT;
ALTER TABLE documents ADD COLUMN contract_number TEXT;       -- ★ جدید

-- مرحله چرخه عمر
ALTER TABLE documents ADD COLUMN stage TEXT DEFAULT 'draft';

-- SLA کامل
ALTER TABLE documents ADD COLUMN sla_start_date TEXT;
ALTER TABLE documents ADD COLUMN sla_effective_days INTEGER;
ALTER TABLE documents ADD COLUMN is_overdue INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN overdue_days INTEGER DEFAULT 0;

-- آرشیو
ALTER TABLE documents ADD COLUMN registered_by INTEGER;
ALTER TABLE documents ADD COLUMN registered_at TEXT;
ALTER TABLE documents ADD COLUMN closed_by INTEGER;
ALTER TABLE documents ADD COLUMN closed_at TEXT;
ALTER TABLE documents ADD COLUMN archived_by INTEGER;
ALTER TABLE documents ADD COLUMN archived_at TEXT;
ALTER TABLE documents ADD COLUMN archive_reason TEXT;
ALTER TABLE documents ADD COLUMN reopen_count INTEGER DEFAULT 0;