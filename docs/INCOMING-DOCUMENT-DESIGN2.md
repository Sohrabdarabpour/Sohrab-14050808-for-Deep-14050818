
### انواع event_type:
`registered`, `sent_to_management`, `returned_from_management`, `routed_to_supervisor`, `routed_to_expert`, `expert_accepted`, `deficiency_requested`, `deficiency_fulfilled`, `response_prepared`, `response_approved_by_supervisor`, `response_approved_by_management`, `response_sent`, `finalized`, `archived`, `cancelled`, `attachment_added`, `sla_recalculated`, `overdue_detected`, `stage_changed`

---

## ۵. فرم مرحله‌به‌مرحله (Multi-step Form)

### مرحله ۱ — ثبت اولیه
- موضوع سند (اجباری)
- تاریخ نامه / تاریخ دریافت
- شماره نامه فرستنده / شماره قرارداد
- نام فرستنده / نوع فرستنده (پیمانکار/کارفرما/داخلی/سایر)
- پیمانکار / پروژه (فیلتر بر اساس پیمانکار)
- شماره اتوماسیون
- توضیحات

### مرحله ۲ — آپلود اسکن‌ها
- آپلود چند فایل (استریمی، بدون محدودیت حجم)
- پیش‌نمایش هر فایل
- نوع فایل: اسکن / نامه / مدرک / سایر
- توضیح برای هر فایل
- **ذخیره در `instance/uploads/packages/<dfc_code>/`**

### مرحله ۳ — اطلاعات مدیریت
- تاریخ ارسال به مدیریت (default: امروز)
- تاریخ بازگشت از دفتر مدیریت
- **تاریخ درج‌شده روی سند توسط مدیریت** (جدا از تاریخ بازگشت)
- متن دستور مدیریت (textarea)

### مرحله ۴ — طبقه‌بندی و ارجاع
- گروه سند / زیرگروه سند
- اولویت / محرمانگی
- **سرپرستان** (multi-select)
- **کارشناسان مستقیم** (multi-select، اختیاری)
- **نمایش زنده SLA:** مهلت + سررسید (با احتساب تعطیلات)

### مرحله ۵ — مرور و ثبت نهایی
- خلاصه‌ی همه اطلاعات
- دکمه‌ی «ثبت نهایی» → تخصیص DFC و WP + ساخت ارجاع‌های اولیه

**بعد از ثبت نهایی:** ریدایرکت به صفحه‌ی `/documents/work-package/<id>`

---

## ۶. نقش‌ها و دسترسی‌ها

| نقش | دسترسی |
|---|---|
| **کارشناس ثبت‌کننده** | ثبت اولیه، آپلود، ثبت اطلاعات مدیریت، تعیین گروه/سرپرستان |
| **سرپرست** | مشاهده در کارتابل، ارجاع به کارشناسان (متولی + همکار)، تأیید پاسخ |
| **کارشناس متولی** | تهیه پاسخ، درخواست رفع نقص، ارسال برای سرپرست |
| **کارشناس همکار** | مشاهده، ویرایش مشترک، اظهار نظر |
| **مدیر** | تأیید نهایی، مشاهده همه |
| **ادمین** | دسترسی کامل |

**قاعده مهم:** فقط **یک کارشناس می‌تواند متولی اصلی (`is_primary=1`)** باشد. سایر کارشناسان به‌عنوان «همکار» اضافه می‌شوند.

---

## ۷. مقادیر کشویی (فارسی)

### نوع فرستنده:
- `contractor` → «پیمانکار»
- `client` → «کارفرما»
- `internal` → «داخلی»
- `other` → «سایر»

### اولویت:
- `low` → «کم»
- `normal` → «معمولی»
- `high` → «بالا»
- `urgent` → «فوری»

### محرمانگی:
- `internal` → «داخلی»
- `confidential` → «محرمانه»

### مرحله (stage):
- `registered` → «ثبت اولیه»
- `sent_to_management` → «ارسال به مدیریت»
- `returned_from_management` → «بازگشت از مدیریت»
- `routed` → «ارجاع‌شده»
- `in_progress` → «در حال بررسی»
- `awaiting_contractor` → «در انتظار پیمانکار»
- `under_review` → «در انتظار تأیید سرپرست»
- `approved` → «تأییدشده توسط سرپرست»
- `closed` → «بسته‌شده»
- `archived` → «آرشیو»
- `cancelled` → «لغو»

### نتیجه نهایی:
- `approved` → «تأیید»
- `rejected` → «رد»
- `conditional` → «تأیید مشروط»
- `other` → «سایر»

### نوع نواقص:
- `verbal` → «شفاهی»
- `written` → «کتبی (نامه)»
- `email` → «ایمیل»
- `phone` → «تلفنی»

### نوع پیوست:
- `scan` → «اسکن»
- `letter` → «نامه»
- `evidence` → «مدرک»
- `response` → «پاسخ»
- `other` → «سایر»

---

## ۸. منطق SLA و دیرکرد

### اولویت تعیین مهلت:
1. `subgroup.days_review` اگر موجود و > 0
2. `group.days_review` اگر موجود و > 0
3. `SSPE_DEFAULT_SLA_DAYS` (پیش‌فرض ۷ روز)

### محاسبه:
- `sla_start_date` = `date_received`
- `response_due_date` = `sla_start_date` + N **روز کاری** (با احتساب پنجشنبه/جمعه و تعطیلات رسمی)
- `is_overdue` = 1 اگر `today > response_due_date` و stage فعال باشد
- `overdue_days` = تعداد روز کاری دیرکرد

### محاسبه مجدد:
- هنگام تغییر گروه/زیرگروه → `recalculate_sla()`
- هنگام تغییر تاریخ دریافت → `recalculate_sla()`
- به‌صورت دوره‌ای با `flask wp-alarms-scan`

---

## ۹. هشدارها

| رخداد | زمان | گیرنده |
|---|---|---|
| مهلت پاسخ نزدیک | ۱ روز قبل | سرپرست + کارشناس متولی |
| دیرکرد سند | بعد از سررسید | سرپرست + مدیر |
| دیرکرد ۳ روز | ۳ روز بعد | مدیر + علامت «بحرانی» |
| ارجاع بدون اقدام | ۴۸ ساعت | مسئول ارجاع |
| بازگشت از مدیریت | بلافاصله | ثبت‌کننده |

**جلوگیری از اسپم:** `dedupe_key` یکتا (`pkg:<id>:overdue:3d`)

---

## ۱۰. ساختار فایل‌ها
database/tables/
├── document_packages.py
├── document_package_counters.py
├── document_package_assignments.py
├── document_package_events.py
├── document_package_deficiencies.py
├── document_package_deficiency_items.py
└── document_package_attachments.py

services/documents/
├── work_package_service.py ← ثبت + تخصیص + گردش
├── work_package_sla_service.py ← SLA
├── work_package_assignment_service.py ← ارجاع
├── work_package_event_service.py ← رویدادها
├── work_package_attachment_service.py ← آپلود
├── work_package_deficiency_service.py ← نواقص
└── work_package_alarm_service.py ← هشدارها

routes/documents/
├── work_package_routes.py ← روت‌های صفحه و API
├── work_package_step_routes.py ← فرم چندمرحله‌ای
└── work_package_api.py ← APIهای JSON

templates/documents/work_package/
├── new_step1.html
├── new_step2.html
├── new_step3.html
├── new_step4.html
├── new_step5.html
├── view.html ← صفحه اصلی با تب‌ها
└── _partials/
├── _summary.html
├── _assignments.html
├── _timeline.html
├── _attachments.html
├── _deficiencies.html
└── _approvals.html
---

## ۱۱. نکات مهم پیاده‌سازی

1. **جدول `documents` قدیمی دست‌نخورده می‌ماند.** سیستم جدید کاملاً مستقل است.

2. **📌 قاعده‌ی طلایی تاریخ‌ها:**
   - **در دیتابیس:** همه‌ی تاریخ‌ها **میلادی** به فرمت `YYYY/MM/DD` ذخیره می‌شوند.
   - **در فرم‌های ورودی (UI):** کاربر تاریخ را **شمسی** وارد می‌کند (`1405/01/01`).
   - **تبدیل قبل از ذخیره:** با `DateHelper.convert_to_gregorian()`.
   - **در نمایش:** تاریخ میلادی از دیتابیس خوانده می‌شود و با `DateHelper.format_jalali()` به شمسی تبدیل و نمایش داده می‌شود.
   - **در JSON/API:** تاریخ‌ها به شمسی برگردانده می‌شوند.
   - **در قالب‌ها:** از فیلترهای `jalali_date` و `jalali_datetime` (که در `app.py` ثبت شده‌اند) استفاده کنید.
   - **ستون‌های تاریخ که این قاعده برایشان اعمال می‌شود:**
     - `date_letter`, `date_received`, `sender_ref_date`
     - `date_sent_to_management`, `date_returned_from_management`, `management_date_on_letter`
     - `sla_start_date`, `response_due_date`
     - `response_letter_date`, `date_sent_response`
     - `supervisor_approved_at`, `management_approved_at`
     - `closed_at`, `archived_at`
     - `created_at`, `updated_at`, `registered_at`
     - `due_date` (ارجاع‌ها)
     - `request_date`, `due_date`, `fulfilled_at` (نواقص)
     - `read_at`, `accepted_at`, `completed_at` (ارجاع‌ها)

3. **تاریخ‌های مرحله ۳ جداگانه ثبت می‌شوند:**
   - `date_sent_to_management`
   - `date_returned_from_management`
   - `management_date_on_letter`
   - **دلیل:** تفاوت این تاریخ‌ها (تأخیر دفتر مدیریت) قابل پیگیری باشد.

4. **کارشناس متولی** با `is_primary=1` در `document_package_assignments` مشخص می‌شود.

5. **همه‌ی عملیات باید در `document_package_events` ثبت شوند.**

6. **پوشه‌ی هر سند:** `instance/uploads/packages/<dfc_code>/` — فایل‌ها با UUID ذخیره می‌شوند.

7. **بدون محدودیت حجم آپلود:** `MAX_CONTENT_LENGTH = None` و آپلود استریمی.

8. **آپلود و پیش‌نمایش:** مطابق `document_attachments` (با `Content-Disposition: inline`).

9. **در سرویس‌ها، تاریخ فقط میلادی:** سرویس‌ها هیچ‌وقت با تاریخ شمسی کار نمی‌کنند. تبدیل در لایه‌ی روت انجام می‌شود.
---

## ۱۲. وضعیت پیاده‌سازی

| بخش | وضعیت |
|---|---|
| طراحی جداول | ✅ تأیید شد |
| Migration جداول جدید | ⏳ در انتظار |
| سرویس تخصیص کد (DFC + WP) | ⏳ |
| سرویس ثبت پکیج | ⏳ |
| سرویس SLA | ⏳ |
| سرویس ارجاع (assignment) | ⏳ |
| سرویس نواقص (deficiency) | ⏳ |
| سرویس هشدار (alarm) | ⏳ |
| فرم ۵ مرحله‌ای | ⏳ |
| صفحه‌ی پکیج (تب‌ها) | ⏳ |
| کارتابل | ⏳ |
| گزارش‌ها | ⏳ |
| تست نهایی | ⏳ |

---

## ۱۳. تصمیمات باقی‌مانده

| مورد | تصمیم |
|---|---|
| پیش‌نمایش PDF درون مودال | نیاز به `PDF.js`؛ فعلاً «باز کردن در تب جدید» |
| OCR اسناد فیزیکی | فاز بعدی |
| ایمیل/SMS | فعلاً فقط نوتیفیکیشن داخلی |
| امضای دیجیتال | فاز بعدی |
| رمزنگاری فایل‌ها | فاز بعدی (اگر محرمانگی بالا لازم است) |

---

## ۱۴. چک‌لیست قبل از شروع کدنویسی

- [x] تأیید طراحی جداول
- [x] تأیید گردش کار (Stage Machine)
- [x] تأیید منطق تخصیص WP
- [x] تأیید ساختار فرم ۵ مرحله‌ای
- [x] تأیید مقادیر کشویی فارسی
- [x] تأیید ساختار فایل‌ها

📌 قاعده‌ی طلایی تاریخ‌ها در پروژه
در دیتابیس: همه‌ی تاریخ‌ها به میلادی و به فرمت YYYY/MM/DD ذخیره می‌شوند.
در فرم‌های ورودی (UI): کاربر تاریخ را شمسی وارد می‌کند (۱۴۰۵/۰۱/۰۱ یا 1405/01/01).
تبدیل: قبل از ذخیره در دیتابیس، تاریخ شمسی → میلادی تبدیل می‌شود.
در نمایش (UI): تاریخ میلادی از دیتابیس خوانده می‌شود و به شمسی تبدیل و نمایش داده می‌شود.
در JSON/API: تاریخ‌ها به شمسی برگردانده می‌شوند (برای نمایش در UI).



---

## ✅ وضعیت پیاده‌سازی

| بخش | وضعیت |
|---|---|
| **فاز ۱: جداول دیتابیس** | ✅ **تکمیل شد** |
| ├─ `document_package_counters` | ✅ ساخته شد |
| ├─ `document_packages` (۶۵ ستون) | ✅ ساخته شد |
| ├─ `document_package_assignments` | ✅ ساخته شد |
| ├─ `document_package_events` | ✅ ساخته شد |
| ├─ `document_package_deficiencies` | ✅ ساخته شد |
| ├─ `document_package_deficiency_items` | ✅ ساخته شد |
| └─ `document_package_attachments` | ✅ ساخته شد |

| **فاز ۲: سرویس‌ها** | ⏳ در انتظار |
| ├─ `work_package_service.py` (تخصیص + ثبت) | ⏳ |
| ├─ `work_package_sla_service.py` | ⏳ |
| ├─ `work_package_assignment_service.py` | ⏳ |
| ├─ `work_package_event_service.py` | ⏳ |
| ├─ `work_package_attachment_service.py` | ⏳ |
| ├─ `work_package_deficiency_service.py` | ⏳ |
| └─ `work_package_alarm_service.py` | ⏳ |

| **فاز ۳: روت‌ها و فرم‌ها** | ⏳ |
| **فاز ۴: صفحه‌ی پکیج (تب‌ها)** | ⏳ |
| **فاز ۵: کارتابل** | ⏳ |
| **فاز ۶: گزارش‌ها** | ⏳ |
| **فاز ۷: تست نهایی** | ⏳ |

---

## 🎯 فاز بعدی: سرویس‌ها

**قدم بعدی:** ساخت `work_package_service.py` با توابع:
- `allocate_dfc_code(connection)` — تخصیص اتمیک DFC
- `allocate_wp_code(connection)` — تخصیص اتمیک WP
- `find_work_package(...)` — تشخیص WP موجود
- `register_package(...)` — ثبت کامل سند
- `change_stage(...)` — تغییر مرحله
- `get_package(package_id)` — خواندن
- `list_work_package_siblings(wp_code)` — همه اسناد یک WP

| **فاز ۲: سرویس‌ها** | ✅ **تکمیل شد** |
| ├─ `wp_event_service.py` | ✅ |
| ├─ `wp_service.py` | ✅ |
| ├─ `wp_sla_service.py` | ✅ |
| ├─ `wp_assignment_service.py` | ✅ |
| ├─ `wp_attachment_service.py` | ✅ |
| ├─ `wp_deficiency_service.py` | ✅ |
| ├─ `wp_alarm_service.py` | ✅ |
| └─ `__init__.py` | ✅ |

| **فاز ۳: روت‌ها و فرم ۵ مرحله‌ای** | ⏳ در انتظار |
| **فاز ۴: صفحه‌ی پکیج (تب‌ها)** | ⏳ |
| **فاز ۵: کارتابل** | ⏳ |
| **فاز ۶: گزارش‌ها** | ⏳ |
| **فاز ۷: تست نهایی** | ⏳ |


# سند طراحی «پکیج سند» (Work Package) — نسخه ۲

> **سند فنی زنده — نسخه ۲**
> این سند بازطراحی کامل سیستم پکیج سند است. مستقل از جدول `documents` قدیمی و با کدهای اختصاصی DFC و WP.
> **آخرین به‌روزرسانی:** پس از پیاده‌سازی فاز ۵ (کارتابل) و آماده‌سازی فاز ۶ (گزارش‌ها)

---

## 📌 قاعده‌ی طلایی تاریخ‌ها (غیرقابل‌تغییر)

> **در دیتابیس:** همه‌ی تاریخ‌ها **میلادی** به فرمت `YYYY/MM/DD` ذخیره می‌شوند.
> **در فرم‌های ورودی (UI):** کاربر تاریخ را **شمسی** وارد می‌کند (`1405/01/01`).
> **تبدیل قبل از ذخیره:** با `DateHelper.convert_to_gregorian()`.
> **در نمایش:** با `DateHelper.format_jalali()` به شمسی تبدیل می‌شود.
> **در JSON/API:** تاریخ‌ها به شمسی برگردانده می‌شوند.
> **در قالب‌ها:** از فیلترهای `jalali_date` و `jalali_datetime` استفاده می‌شود.
>
> **ستون‌های تاریخ که این قاعده برایشان اعمال می‌شود:**
> `date_letter`, `date_received`, `sender_ref_date`,
> `date_sent_to_management`, `date_returned_from_management`, `management_date_on_letter`,
> `sla_start_date`, `response_due_date`, `response_letter_date`, `date_sent_response`,
> `supervisor_approved_at`, `management_approved_at`, `closed_at`, `archived_at`,
> `created_at`, `updated_at`, `registered_at`, `due_date`, `request_date`,
> `fulfilled_at`, `read_at`, `accepted_at`, `completed_at`

---

## 🎯 تصمیم اصلی: جدول مستقل `document_packages`

**جدول جدید `document_packages` جدا از `documents` ساخته می‌شود.**

دلایل:
- جدول `documents` (با ۸٬۷۸۲ رکورد) دست‌نخورده باقی می‌ماند.
- پکیج سند دو کد اختصاصی دارد: `DFC-YYYY-NNNN` (برای سند) و `WP-YYYY-NNNN` (برای موضوع).
- منطق گردش، SLA و آرشیو کاملاً مستقل است.

---

## 📊 فاز ۱: جداول دیتابیس (✅ انجام شد)

### ۱-۱. `document_packages` (جدول اصلی، ۶۶ ستون)

#### شناسه‌ها و کدها
| ستون | نوع | توضیح |
|---|---|---|
| `id` | INTEGER PK | |
| `dfc_code` | TEXT UNIQUE | `DFC-1405-0001` |
| `work_package_code` | TEXT | `WP-1405-0001` |
| `package_year` | INTEGER | سال شمسی |
| `dfc_sequence` | INTEGER | شماره ترتیبی |

#### اطلاعات سند
| ستون | توضیح |
|---|---|
| `subject` | موضوع نامه (اجباری) |
| `description` | توضیحات |
| `date_letter` | تاریخ نامه (میلادی) |
| `date_received` | تاریخ دریافت (میلادی) |
| `sender_ref_no` | شماره نامه فرستنده |
| `sender_ref_date` | تاریخ نامه فرستنده (میلادی) |
| `contract_number` | شماره قرارداد (کلید تشخیص WP) |
| `sender_name` | نام فرستنده |
| `sender_type` | `contractor` / `client` / `internal` / `other` |
| `source_type` | منبع |
| `direction` | `incoming` / `outgoing` / `internal` |
| `contractor_id` | FK |
| `project_id` | FK |
| `automation_number` | شماره اتوماسیون |

#### ارسال به مدیریت (۳ تاریخ جدا)
| ستون | توضیح |
|---|---|
| `date_sent_to_management` | تاریخ ارسال به مدیریت |
| `date_returned_from_management` | تاریخ بازگشت از دفتر مدیریت |
| `management_date_on_letter` | **تاریخ درج‌شده روی سند توسط مدیریت** |
| `management_instruction` | متن دستور مدیریت |
| `management_action` | نوع دستور: `route_to_supervisor` / `archive` / `informational` / `urgent_action` |

#### دستور مدیریت و ارجاع
| ستون | توضیح |
|---|---|
| `group_id` | FK |
| `subgroup_id` | FK |
| `priority` | `low` / `normal` / `high` / `urgent` |
| `confidentiality` | `internal` / `confidential` |
| `supervisor_ids` | JSON (لیست سرپرستان) |
| `direct_expert_ids` | JSON (لیست کارشناسان مستقیم) |

#### گردش کار
| ستون | توضیح |
|---|---|
| `stage` | مرحله چرخه عمر (بخش ۴) |
| `current_supervisor_id` | سرپرست مسئول فعلی |
| `current_expert_id` | کارشناس متولی فعلی |

#### SLA
| ستون | توضیح |
|---|---|
| `sla_days` | مهلت (روز کاری) |
| `sla_source` | `subgroup` / `group` / `default` |
| `sla_start_date` | شروع |
| `sla_effective_days` | مهلت نهایی |
| `response_due_date` | سررسید |
| `is_overdue` | 0/1 |
| `overdue_days` | تعداد روز دیرکرد |

#### رفرنس
| ستون | توضیح |
|---|---|
| `reference_no` | رفرنس دستی |
| `response_to_id` | FK → پاسخ به کدام سند |
| `parent_package_id` | FK → والد ریشه |
| `work_package_subject` | موضوع اصلی پکیج |

#### نتیجه نهایی
| ستون | توضیح |
|---|---|
| `final_response` | متن پاسخ |
| `final_result` | `approved` / `rejected` / `conditional` / `other` |
| `final_result_notes` | توضیح نتیجه |
| `response_letter_number` | شماره نامه پاسخ |
| `response_letter_date` | تاریخ نامه پاسخ (میلادی) |
| `date_sent_response` | تاریخ ارسال پاسخ (میلادی) |

#### تأییدات
| ستون | توضیح |
|---|---|
| `supervisor_approved_by` | FK |
| `supervisor_approved_at` | (میلادی) |
| `management_approved_by` | FK |
| `management_approved_at` | (میلادی) |

#### متادیتا و آرشیو
| ستون | توضیح |
|---|---|
| `registered_by` | FK |
| `registered_at` | |
| `closed_by` / `closed_at` | |
| `archived_by` / `archived_at` | |
| `archive_reason` | |
| `reopen_count` | |
| `created_at` / `updated_at` | |
| `tags` | JSON |
| `notes` | |

---

### ۱-۲. `document_package_counters`

| ستون | توضیح |
|---|---|
| `kind` | `dfc` یا `wp` |
| `year` | سال شمسی |
| `last_value` | آخرین شماره |

PK مرکب: (`kind`, `year`)

---

### ۱-۳. `document_package_assignments` (ارجاع‌ها)

| ستون | توضیح |
|---|---|
| `id` | PK |
| `package_id` | FK |
| `parent_id` | FK (درخت ارجاع) |
| `from_user_id` / `to_user_id` | |
| `to_department_id` | |
| `assignee_role` | `supervisor` / `expert` / `collaborator` / `manager` |
| `action` | `route` / `refer` / `return` / `forward` / `cc` |
| `instruction` | دستور |
| `is_primary` | **0/1 — متولی اصلی** |
| `priority` | |
| `due_date` | مهلت (میلادی) |
| `due_days` | مهلت (روز کاری) |
| `status` | `pending` / `accepted` / `in_progress` / `done` / `returned` / `cancelled` |
| `read_at` / `accepted_at` / `completed_at` | (میلادی) |
| `returned_at` / `cancelled_at` / `cancel_reason` | |
| `is_overdue` / `overdue_days` | |
| `created_at` / `updated_at` | |

---

### ۱-۴. `document_package_events` (تایم‌لاین)

| ستون | توضیح |
|---|---|
| `id` | PK |
| `package_id` | FK |
| `actor_id` | FK |
| `event_type` | نوع رویداد (بخش ۴) |
| `summary` | خلاصه |
| `payload` | JSON |
| `assignment_id` | FK اختیاری |
| `created_at` | |

**فقط append-only — UPDATE/DELETE ممنوع.**

---

### ۱-۵. `document_package_deficiencies` (نواقص)

| ستون | توضیح |
|---|---|
| `id` | PK |
| `package_id` | FK |
| `assignment_id` | FK اختیاری |
| `mode` | `verbal` / `written` / `email` / `phone` |
| `reference_no` | شماره نامه/ایمیل |
| `request_date` | تاریخ درخواست (میلادی) |
| `due_date` | مهلت (میلادی) |
| `items` | JSON |
| `status` | `open` / `partial` / `fulfilled` / `cancelled` |
| `requested_by` | FK |
| `fulfilled_at` | (میلادی) |
| `notes` | |
| `created_at` / `updated_at` | |

### ۱-۶. `document_package_deficiency_items` (چک‌لیست)

| ستون | توضیح |
|---|---|
| `id` | PK |
| `request_id` | FK |
| `title` | عنوان مدرک |
| `is_received` | 0/1 |
| `received_at` | (میلادی) |
| `note` | |
| `sort_order` | |

---

### ۱-۷. `document_package_attachments` (پیوست‌ها)

| ستون | توضیح |
|---|---|
| `id` | PK |
| `package_id` | FK |
| `parent_attachment_id` | FK |
| `original_name` | نام اصلی |
| `stored_name` | نام UUID روی دیسک |
| `mime` / `size` / `sha256` | |
| `kind` | `scan` / `letter` / `evidence` / `response` / `other` |
| `description` | |
| `previewable` | 0/1 |
| `uploaded_by` | FK |
| `created_at` | |

**مسیر ذخیره:** `instance/uploads/packages/<dfc_code>/<uuid>.<ext>`

---

## 🔄 بخش ۴: گردش کار (Stage Machine)
## 🔄 بخش ۴: گردش کار (Stage Machine)
registered → ثبت اولیه (کارشناس)

sent_to_management → ارسال فیزیکی به مدیریت

returned_from_management → بازگشت از مدیریت + ثبت دستور

routed → تعیین گروه/زیرگروه/سرپرستان

in_progress → ارجاع به سرپرست → کارشناس

awaiting_contractor → درخواست رفع نقص

under_review → پاسخ تهیه شد، منتظر تأیید سرپرست

approved → تأیید سرپرست، منتظر تأیید مدیریت

closed → تأیید مدیریت + ارسال پاسخ

archived → آرشیو

cancelled → لغو

### انتقال‌های مجاز:

registered → sent_to_management, cancelled
sent_to_management → returned_from_management, cancelled, archived (اگر management_action=archive)
returned_from_management → routed, cancelled
routed → in_progress, cancelled
in_progress → awaiting_contractor, under_review, cancelled
awaiting_contractor → in_progress, cancelled
under_review → approved, in_progress
approved → closed, in_progress
closed → archived
archived → (پایانی)
cancelled → (پایانی)


### انواع event_type:
`registered`, `sent_to_management`, `returned_from_management`, `routed_to_supervisor`, `routed_to_expert`, `expert_accepted`, `deficiency_requested`, `deficiency_fulfilled`, `response_prepared`, `response_approved_by_supervisor`, `response_approved_by_management`, `response_sent`, `finalized`, `archived`, `cancelled`, `attachment_added`, `sla_recalculated`, `overdue_detected`, `stage_changed`

---

## 🎨 بخش ۵: مقادیر کشویی (فارسی)

### نوع فرستنده:
| مقدار DB | نمایش فارسی |
|---|---|
| `contractor` | پیمانکار |
| `client` | کارفرما |
| `internal` | داخلی |
| `other` | سایر |

### اولویت:
| مقدار DB | نمایش فارسی |
|---|---|
| `low` | کم |
| `normal` | معمولی |
| `high` | بالا |
| `urgent` | فوری |

### محرمانگی:
| مقدار DB | نمایش فارسی |
|---|---|
| `internal` | داخلی |
| `confidential` | محرمانه |

### مرحله (stage):
| مقدار DB | نمایش فارسی |
|---|---|
| `registered` | ثبت اولیه |
| `sent_to_management` | ارسال به مدیریت |
| `returned_from_management` | بازگشت از مدیریت |
| `routed` | ارجاع‌شده |
| `in_progress` | در حال بررسی |
| `awaiting_contractor` | در انتظار پیمانکار |
| `under_review` | در انتظار تأیید سرپرست |
| `approved` | تأییدشده توسط سرپرست |
| `closed` | بسته‌شده |
| `archived` | آرشیو |
| `cancelled` | لغو |

### نوع اقدام مدیریت:
| مقدار DB | نمایش فارسی |
|---|---|
| `route_to_supervisor` | ارجاع به سرپرست |
| `archive` | بایگانی |
| `informational` | جهت اطلاع |
| `urgent_action` | اقدام فوری |

### نتیجه نهایی:
| مقدار DB | نمایش فارسی |
|---|---|
| `approved` | تأیید |
| `rejected` | رد |
| `conditional` | تأیید مشروط |
| `other` | سایر |

### نوع نواقص:
| مقدار DB | نمایش فارسی |
|---|---|
| `verbal` | شفاهی |
| `written` | کتبی (نامه) |
| `email` | ایمیل |
| `phone` | تلفنی |

### نوع پیوست:
| مقدار DB | نمایش فارسی |
|---|---|
| `scan` | اسکن |
| `letter` | نامه |
| `evidence` | مدرک |
| `response` | پاسخ |
| `other` | سایر |

---

## 🧮 بخش ۶: منطق تخصیص کدها

### تخصیص DFC:
1. سال شمسی جاری از `jdatetime.date.today().year`
2. مقدار بعدی از `document_package_counters` (`kind='dfc'`, `year=سال`)
3. فرمت: `DFC-YYYY-NNNN`
4. **اتمیک** با `BEGIN IMMEDIATE` + `ON CONFLICT`
5. شماره هرگز بازاستفاده نمی‌شود

### تخصیص WP (اولویت تشخیص):
1. اگر `reference_no` در `document_packages` باشد → همان WP
2. اگر `sender_ref_no` باشد → همان WP
3. اگر `contract_number` + `contractor_id` باشد → همان WP
4. اگر `contract_number` + `project_id` باشد → همان WP
5. اگر `automation_number` باشد → همان WP
6. اگر `force_new_wp=True` → WP جدید
7. در غیر این صورت → WP جدید

---

## ⏱ بخش ۷: منطق SLA

### اولویت:
1. `subgroup.days_review` (اگر > 0)
2. `group.days_review` (اگر > 0)
3. `SSPE_DEFAULT_SLA_DAYS` (پیش‌فرض ۷)

### محاسبه:
- `sla_start_date` = `date_received`
- `response_due_date` = `sla_start_date` + N **روز کاری** (با احتساب تعطیلات)
- `is_overdue` = 1 اگر `today > response_due_date` و stage فعال
- `overdue_days` = روزهای کاری دیرکرد

### محاسبه مجدد:
- هنگام تغییر گروه/زیرگروه → `recalculate_sla()`
- هنگام تغییر تاریخ دریافت → `recalculate_sla()`
- دوره‌ای با `flask wp-alarms-scan`

### پیش‌نمایش زنده:
- در مودال بازگشت از مدیریت، تابع `preview_sla()` مهلت و سررسید را بدون ذخیره محاسبه و نمایش می‌دهد.

---

## 🔔 بخش ۸: هشدارها

| رخداد | زمان | گیرنده |
|---|---|---|
| مهلت پاسخ نزدیک | ۱ روز قبل | سرپرست + کارشناس متولی |
| دیرکرد سند | بعد از سررسید | سرپرست + مدیر |
| دیرکرد ۳ روز | ۳ روز بعد | مدیر + علامت «بحرانی» |
| ارجاع بدون اقدام | ۴۸ ساعت | مسئول ارجاع |
| بازگشت از مدیریت | بلافاصله | ثبت‌کننده |

**جلوگیری از اسپم:** `dedupe_key` یکتا (`pkg:<id>:overdue:3d`)

---

## 📁 بخش ۹: ساختار فایل‌ها

database/tables/
├── document_package_counters.py ✅
├── document_packages.py ✅
├── document_package_assignments.py ✅
├── document_package_events.py ✅
├── document_package_deficiencies.py ✅
├── document_package_attachments.py ✅
└── init.py ✅

database/migrations/
└── add_management_action.py ✅

services/work_package/
├── init.py ✅
├── wp_event_service.py ✅
├── wp_service.py ✅
├── wp_sla_service.py ✅
├── wp_assignment_service.py ✅
├── wp_attachment_service.py ✅
├── wp_deficiency_service.py ✅
├── wp_alarm_service.py ✅
└── wp_report_service.py ✅

routes/work_package/
├── init.py ✅
├── wp_routes.py ✅
├── wp_step_routes.py ✅
├── wp_api_routes.py ✅
└── wp_attachment_routes.py ✅

routes/reports/
└── package_reports.py ✅

routes/inbox/
├── init.py ✅
└── inbox_routes.py ✅

templates/work_package/
├── new.html ✅
├── list.html ✅
├── view.html ✅
└── print_label.html ✅

templates/reports/
├── package_overdue.html ✅
├── package_workload.html ✅
├── package_cycle_time.html ✅
└── package_pending_management.html ✅

templates/inbox/
└── inbox.html ✅

templates/components/
└── sidebar.html ✅ (به‌روزرسانی با جستجو).


---

## ✅ وضعیت پیاده‌سازی

| بخش | وضعیت |
|---|---|
| **فاز ۱: جداول دیتابیس** | ✅ **تکمیل شد** |
| ├─ `document_package_counters` | ✅ |
| ├─ `document_packages` (۶۶ ستون) | ✅ |
| ├─ `document_package_assignments` | ✅ |
| ├─ `document_package_events` | ✅ |
| ├─ `document_package_deficiencies` | ✅ |
| ├─ `document_package_deficiency_items` | ✅ |
| └─ `document_package_attachments` | ✅ |

| **فاز ۲: سرویس‌ها** | ✅ **تکمیل شد** |
| ├─ `wp_event_service.py` | ✅ |
| ├─ `wp_service.py` | ✅ |
| ├─ `wp_sla_service.py` | ✅ |
| ├─ `wp_assignment_service.py` | ✅ |
| ├─ `wp_attachment_service.py` | ✅ |
| ├─ `wp_deficiency_service.py` | ✅ |
| ├─ `wp_alarm_service.py` | ✅ |
| └─ `wp_report_service.py` | ✅ |

| **فاز ۳: روت‌ها و فرم** | ✅ **تکمیل شد** |
| ├─ `wp_routes.py` (نمایش + چاپ) | ✅ |
| ├─ `wp_step_routes.py` (ثبت سریع) | ✅ |
| ├─ `wp_api_routes.py` (APIها) | ✅ |
| ├─ `wp_attachment_routes.py` | ✅ |
| ├─ `new.html` (فرم تک‌مرحله‌ای) | ✅ |
| ├─ `list.html` | ✅ |
| ├─ `view.html` (۷ تب + نوار پیشرفت) | ✅ |
| └─ `print_label.html` | ✅ |

| **فاز ۴: صفحه‌ی پکیج (تب‌ها)** | ✅ **تکمیل شد** |
| ├─ نوار پیشرفت مرحله‌ای | ✅ |
| ├─ تب خلاصه | ✅ |
| ├─ تب ارجاع‌ها | ✅ |
| ├─ تب نواقص | ✅ |
| ├─ تب پیوست‌ها | ✅ |
| ├─ تب اسناد مرتبط | ✅ |
| ├─ تب تایم‌لاین | ✅ |
| └─ مودال بازگشت از مدیریت (کامل) | ✅ |

| **فاز ۵: کارتابل** | ✅ **تکمیل شد** |
| ├─ `get_inbox_merged` (ترکیبی) | ✅ |
| ├─ روت‌های کارتابل | ✅ |
| └─ قالب `inbox.html` (تفکیک بصری) | ✅ |

| **فاز ۶: گزارش‌ها** | ✅ **تکمیل شد** |
| ├─ `wp_report_service.py` | ✅ |
| ├─ `package_reports.py` | ✅ |
| ├─ `package_overdue.html` | ✅ |
| ├─ `package_workload.html` | ✅ |
| ├─ `package_cycle_time.html` | ✅ |
| └─ `package_pending_management.html` | ✅ |

| **فاز ۷: تست نهایی** | ⏳ در انتظار |

---

## 📝 یادداشت‌های پیاده‌سازی

### ۱. جستجوی سریع در سایدبار
- باکس جستجو در سایدبار قرار دارد (نه در هدر).
- جستجو بر اساس: DFC، شماره نامه، موضوع، شماره قرارداد.
- API: `POST /work-package/search` با `{q: "..."}`

### ۲. انتخاب‌گر چند کاربر (برای ارجاع)
- در مودال بازگشت از مدیریت، کاربر با تایپ نام جستجو می‌شود.
- API: `POST /work-package/search-users` با `{q: "..."}`
- انتخاب‌شده‌ها به‌صورت chip با × حذف نمایش داده می‌شوند.

### ۳. مدیریت دستورالعمل بازگشت
- `management_action` یکی از: `route_to_supervisor` / `archive` / `informational` / `urgent_action`
- اگر `archive` → سند مستقیم به `archived` می‌رود
- اگر `route_to_supervisor` → سند به `routed` می‌رود و ارجاع به سرپرست ساخته می‌شود
- اگر `informational` → سند به `returned_from_management` می‌رود (بدون ارجاع)

### ۴. پوشه‌ی فایل‌ها
- هر سند پوشه‌ی اختصاصی دارد: `instance/uploads/packages/<dfc_code>/`
- نام فایل روی دیسک: UUID + پسوند اصلی
- نام اصلی در دیتابیس ذخیره می‌شود

### ۵. فیلتر پروژه‌ها
- در فرم ثبت، وقتی پیمانکار انتخاب می‌شود، پروژه‌ها فیلتر می‌شوند.
- API: `GET /documents/api/contractors/<id>/projects`

### ۶. پیش‌نمایش فایل
- تصویر/ویدیو/صدا در مودال نمایش داده می‌شود.
- PDF در تب جدید باز می‌شود (به دلیل محدودیت مرورگر).
- سایر فایل‌ها → لینک دانلود

---

## ⚠️ نکات مهم

### ۱. جدول `documents` قدیمی دست‌نخورده
- همه‌ی سرویس‌های جدید روی `document_packages` کار می‌کنند.
- سیستم قدیمی (`documents`) همچنان کار می‌کند.
- کارتابل ترکیبی از هر دو نمایش می‌دهد.

### ۲. قاعده‌ی طلایی تاریخ‌ها
- همه‌ی تاریخ‌ها در دیتابیس میلادی، در UI شمسی.
- `DateHelper.convert_to_gregorian()` قبل از ذخیره
- `DateHelper.format_jalali()` بعد از خواندن

### ۳. اتمیک بودن شماره‌گذاری
- `BEGIN IMMEDIATE` در `_allocate_counter`
- `ON CONFLICT` برای جلوگیری از تکرار
- شماره هرگز بازاستفاده نمی‌شود

### ۴. دسترسی سه‌لایه
- ادمین/مدیر/سرپرست/کنترل‌مستندات: دسترسی کامل
- ثبت‌کننده: دسترسی به سند خودش
- مسئول ارجاع فعال: دسترسی به سند ارجاع‌شده

---

## 🎯 قدم‌های باقی‌مانده

| قدم | کار |
|---|---|
| **فاز ۷** | تست نهایی کل چرخه |
| ├─ ثبت → آپلود → ارسال → بازگشت → ارجاع → پاسخ → تأیید → بستن | ⏳ |
| ├─ اجرای `flask wp-alarms-scan` | ⏳ |
| └─ تست هشدارها | ⏳ |

| **بهبودهای آینده** | |
|---|---|
| ├─ پیش‌نمایش PDF در مودال (PDF.js) | ⏳ |
| ├─ ایمیل/SMS | ⏳ |
| ├─ امضای دیجیتال | ⏳ |
| ├─ OCR اسناد فیزیکی | ⏳ |
---

## ✅ وضعیت پیاده‌سازی

| بخش | وضعیت |
|---|---|
| **فاز ۱: جداول دیتابیس** | ✅ **تکمیل شد** |
| ├─ `document_package_counters` | ✅ |
| ├─ `document_packages` (۶۶ ستون) | ✅ |
| ├─ `document_package_assignments` | ✅ |
| ├─ `document_package_events` | ✅ |
| ├─ `document_package_deficiencies` | ✅ |
| ├─ `document_package_deficiency_items` | ✅ |
| └─ `document_package_attachments` | ✅ |

| **فاز ۲: سرویس‌ها** | ✅ **تکمیل شد** |
| ├─ `wp_event_service.py` | ✅ |
| ├─ `wp_service.py` | ✅ |
| ├─ `wp_sla_service.py` | ✅ |
| ├─ `wp_assignment_service.py` | ✅ |
| ├─ `wp_attachment_service.py` | ✅ |
| ├─ `wp_deficiency_service.py` | ✅ |
| ├─ `wp_alarm_service.py` | ✅ |
| └─ `wp_report_service.py` | ✅ |

| **فاز ۳: روت‌ها و فرم** | ✅ **تکمیل شد** |
| ├─ `wp_routes.py` (نمایش + چاپ) | ✅ |
| ├─ `wp_step_routes.py` (ثبت سریع) | ✅ |
| ├─ `wp_api_routes.py` (APIها) | ✅ |
| ├─ `wp_attachment_routes.py` | ✅ |
| ├─ `new.html` (فرم تک‌مرحله‌ای) | ✅ |
| ├─ `list.html` | ✅ |
| ├─ `view.html` (۷ تب + نوار پیشرفت) | ✅ |
| └─ `print_label.html` | ✅ |

| **فاز ۴: صفحه‌ی پکیج (تب‌ها)** | ✅ **تکمیل شد** |
| ├─ نوار پیشرفت مرحله‌ای | ✅ |
| ├─ تب خلاصه | ✅ |
| ├─ تب ارجاع‌ها | ✅ |
| ├─ تب نواقص | ✅ |
| ├─ تب پیوست‌ها | ✅ |
| ├─ تب اسناد مرتبط | ✅ |
| ├─ تب تایم‌لاین | ✅ |
| └─ مودال بازگشت از مدیریت (کامل) | ✅ |

| **فاز ۵: کارتابل** | ✅ **تکمیل شد** |
| ├─ `get_inbox_merged` (ترکیبی) | ✅ |
| ├─ روت‌های کارتابل | ✅ |
| └─ قالب `inbox.html` (تفکیک بصری) | ✅ |

| **فاز ۶: گزارش‌ها** | ✅ **تکمیل شد** |
| ├─ `wp_report_service.py` | ✅ |
| ├─ `package_reports.py` | ✅ |
| ├─ `package_overdue.html` | ✅ |
| ├─ `package_workload.html` | ✅ |
| ├─ `package_cycle_time.html` | ✅ |
| └─ `package_pending_management.html` | ✅ |

| **فاز ۷: تست نهایی** | ⏳ در انتظار |

---

## 📝 یادداشت‌های پیاده‌سازی

### ۱. جستجوی سریع در سایدبار
- باکس جستجو در سایدبار قرار دارد (نه در هدر).
- جستجو بر اساس: DFC، شماره نامه، موضوع، شماره قرارداد.
- API: `POST /work-package/search` با `{q: "..."}`

### ۲. انتخاب‌گر چند کاربر (برای ارجاع)
- در مودال بازگشت از مدیریت، کاربر با تایپ نام جستجو می‌شود.
- API: `POST /work-package/search-users` با `{q: "..."}`
- انتخاب‌شده‌ها به‌صورت chip با × حذف نمایش داده می‌شوند.

### ۳. مدیریت دستورالعمل بازگشت
- `management_action` یکی از: `route_to_supervisor` / `archive` / `informational` / `urgent_action`
- اگر `archive` → سند مستقیم به `archived` می‌رود
- اگر `route_to_supervisor` → سند به `routed` می‌رود و ارجاع به سرپرست ساخته می‌شود
- اگر `informational` → سند به `returned_from_management` می‌رود (بدون ارجاع)

### ۴. پوشه‌ی فایل‌ها
- هر سند پوشه‌ی اختصاصی دارد: `instance/uploads/packages/<dfc_code>/`
- نام فایل روی دیسک: UUID + پسوند اصلی
- نام اصلی در دیتابیس ذخیره می‌شود

### ۵. فیلتر پروژه‌ها
- در فرم ثبت، وقتی پیمانکار انتخاب می‌شود، پروژه‌ها فیلتر می‌شوند.
- API: `GET /documents/api/contractors/<id>/projects`

### ۶. پیش‌نمایش فایل
- تصویر/ویدیو/صدا در مودال نمایش داده می‌شود.
- PDF در تب جدید باز می‌شود (به دلیل محدودیت مرورگر).
- سایر فایل‌ها → لینک دانلود

---

## ⚠️ نکات مهم

### ۱. جدول `documents` قدیمی دست‌نخورده
- همه‌ی سرویس‌های جدید روی `document_packages` کار می‌کنند.
- سیستم قدیمی (`documents`) همچنان کار می‌کند.
- کارتابل ترکیبی از هر دو نمایش می‌دهد.

### ۲. قاعده‌ی طلایی تاریخ‌ها
- همه‌ی تاریخ‌ها در دیتابیس میلادی، در UI شمسی.
- `DateHelper.convert_to_gregorian()` قبل از ذخیره
- `DateHelper.format_jalali()` بعد از خواندن

### ۳. اتمیک بودن شماره‌گذاری
- `BEGIN IMMEDIATE` در `_allocate_counter`
- `ON CONFLICT` برای جلوگیری از تکرار
- شماره هرگز بازاستفاده نمی‌شود

### ۴. دسترسی سه‌لایه
- ادمین/مدیر/سرپرست/کنترل‌مستندات: دسترسی کامل
- ثبت‌کننده: دسترسی به سند خودش
- مسئول ارجاع فعال: دسترسی به سند ارجاع‌شده

---

## 🎯 قدم‌های باقی‌مانده

| قدم | کار |
|---|---|
| **فاز ۷** | تست نهایی کل چرخه |
| ├─ ثبت → آپلود → ارسال → بازگشت → ارجاع → پاسخ → تأیید → بستن | ⏳ |
| ├─ اجرای `flask wp-alarms-scan` | ⏳ |
| └─ تست هشدارها | ⏳ |

| **بهبودهای آینده** | |
|---|---|
| ├─ پیش‌نمایش PDF در مودال (PDF.js) | ⏳ |
| ├─ ایمیل/SMS | ⏳ |
| ├─ امضای دیجیتال | ⏳ |
| ├─ OCR اسناد فیزیکی | ⏳ |