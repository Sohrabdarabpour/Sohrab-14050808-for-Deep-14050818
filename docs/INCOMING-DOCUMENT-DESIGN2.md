
markdown
# سند طراحی «پکیج سند» (Work Package) — نسخه ۴ (نهایی)

> **سند فنی زنده و جامع**
> این سند، مرجع کامل معماری، پیاده‌سازی و وضعیت پروژه‌ی «پکیج سند» است.
> **آخرین به‌روزرسانی:** پس از اصلاحات فرم ثبت، منطق رفرنس‌ها، و تکمیل تب رفرنس‌ها

---

## 📌 فهرست مطالب

1. [قاعده‌ی طلایی تاریخ‌ها](#قاعده-طلایی-تاریخها)
2. [تصمیم اصلی: جدول مستقل](#تصمیم-اصلی)
3. [فاز ۱: جداول دیتابیس](#فاز-۱-جداول-دیتابیس)
4. [فاز ۲: سرویس‌ها](#فاز-۲-سرویسها)
5. [فاز ۳: روت‌ها و فرم](#فاز-۳-روتها-و-فرم)
6. [فاز ۴: صفحه‌ی پکیج](#فاز-۴-صفحهی-پکیج)
7. [فاز ۵: کارتابل](#فاز-۵-کارتابل)
8. [فاز ۶: گزارش‌ها](#فاز-۶-گزارشها)
9. [گردش کار (Stage Machine)](#گردش-کار)
10. [منطق تخصیص کدها (DFC + WP)](#منطق-تخصیص-کدها)
11. [منطق SLA و دیرکرد](#منطق-sla)
12. [منطق رفرنس‌های چندگانه (اصلاح‌شده)](#منطق-رفرنسهای-چندگانه)
13. [هشدارها](#هشدارها)
14. [وضعیت پیاده‌سازی](#وضعیت-پیادهسازی)
15. [نکات مهم و تصمیمات](#نکات-مهم)
16. [قدم‌های باقی‌مانده](#قدمهای-باقیمانده)

---

## 📌 قاعده‌ی طلایی تاریخ‌ها

> **در دیتابیس:** همه‌ی تاریخ‌ها **میلادی** به فرمت `YYYY/MM/DD` ذخیره می‌شوند.
> **در فرم‌های ورودی (UI):** کاربر تاریخ را **شمسی** وارد می‌کند (`1405/01/01`).
> **تبدیل قبل از ذخیره:** با `DateHelper.convert_to_gregorian()`.
> **در نمایش:** با `DateHelper.format_jalali()` به شمسی تبدیل می‌شود.
> **در JSON/API:** تاریخ‌ها به شمسی برگردانده می‌شوند.
> **در قالب‌ها:** از فیلترهای `jalali_date` و `jalali_datetime` استفاده می‌شود.
>
> **ستون‌های تاریخ:**
> `date_letter`, `date_received`, `sender_ref_date`,
> `date_sent_to_management`, `date_returned_from_management`, `management_date_on_letter`,
> `sla_start_date`, `response_due_date`, `response_letter_date`, `date_sent_response`,
> `supervisor_approved_at`, `management_approved_at`, `closed_at`, `archived_at`,
> `created_at`, `updated_at`, `registered_at`, `due_date`, `request_date`,
> `fulfilled_at`, `read_at`, `accepted_at`, `completed_at`

---

## 🎯 تصمیم اصلی

**جدول جدید `document_packages` جدا از `documents` ساخته می‌شود.**

دلایل:
- جدول `documents` (با ۸٬۷۸۲ رکورد) دست‌نخورده باقی می‌ماند.
- پکیج سند دو کد اختصاصی دارد: `DFC-YYYY-NNNN` و `WP-YYYY-NNNN`.
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

#### ارسال به مدیریت
| ستون | توضیح |
|---|---|
| `date_sent_to_management` | تاریخ ارسال به مدیریت |
| `date_returned_from_management` | تاریخ بازگشت از دفتر مدیریت |
| `management_date_on_letter` | تاریخ درج‌شده روی سند |
| `management_instruction` | متن دستور مدیریت |
| `management_action` | نوع دستور: `route_to_supervisor` / `archive` / `informational` / `urgent_action` |

#### دستور مدیریت و ارجاع
| ستون | توضیح |
|---|---|
| `group_id` | FK |
| `subgroup_id` | FK |
| `priority` | `low` / `normal` / `high` / `urgent` |
| `confidentiality` | `internal` / `confidential` |
| `supervisor_ids` | JSON |
| `direct_expert_ids` | JSON |

#### گردش کار
| ستون | توضیح |
|---|---|
| `stage` | مرحله چرخه عمر |
| `current_supervisor_id` | سرپرست مسئول |
| `current_expert_id` | کارشناس متولی |

#### SLA
| ستون | توضیح |
|---|---|
| `sla_days`, `sla_source`, `sla_start_date`, `sla_effective_days` | |
| `response_due_date`, `is_overdue`, `overdue_days` | |

#### رفرنس
| ستون | توضیح |
|---|---|
| `reference_no` | رفرنس اصلی (اولین رفرنس) |
| `response_to_id` | FK → پاسخ به کدام سند |
| `parent_package_id` | FK → والد ریشه |
| `work_package_subject` | موضوع اصلی پکیج |

#### نتیجه نهایی
| ستون | توضیح |
|---|---|
| `final_response`, `final_result`, `final_result_notes` | |
| `response_letter_number`, `response_letter_date`, `date_sent_response` | |

#### تأییدات
| ستون | توضیح |
|---|---|
| `supervisor_approved_by`, `supervisor_approved_at` | |
| `management_approved_by`, `management_approved_at` | |

#### متادیتا و آرشیو
| ستون | توضیح |
|---|---|
| `registered_by`, `registered_at` | |
| `closed_by`, `closed_at` | |
| `archived_by`, `archived_at`, `archive_reason` | |
| `reopen_count`, `created_at`, `updated_at`, `tags`, `notes` | |

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
| `id`, `package_id`, `parent_id` | |
| `from_user_id`, `to_user_id`, `to_department_id` | |
| `assignee_role` | `supervisor` / `expert` / `collaborator` / `manager` |
| `action` | `route` / `refer` / `return` / `forward` / `cc` |
| `instruction` | دستور |
| `is_primary` | 0/1 — متولی اصلی |
| `priority`, `due_date`, `due_days` | |
| `status` | `pending` / `accepted` / `in_progress` / `done` / `returned` / `cancelled` |
| `read_at`, `accepted_at`, `completed_at` | |
| `returned_at`, `cancelled_at`, `cancel_reason` | |
| `is_overdue`, `overdue_days`, `created_at`, `updated_at` | |

---

### ۱-۴. `document_package_events` (تایم‌لاین)

| ستون | توضیح |
|---|---|
| `id`, `package_id`, `actor_id` | |
| `event_type`, `summary`, `payload` | |
| `assignment_id`, `created_at` | |

**فقط append-only — UPDATE/DELETE ممنوع.**

---

### ۱-۵. `document_package_deficiencies` (نواقص)

| ستون | توضیح |
|---|---|
| `id`, `package_id`, `assignment_id` | |
| `mode` | `verbal` / `written` / `email` / `phone` |
| `reference_no`, `request_date`, `due_date` | |
| `items` (JSON), `status`, `requested_by` | |
| `fulfilled_at`, `notes`, `created_at`, `updated_at` | |

### ۱-۶. `document_package_deficiency_items`

| ستون | توضیح |
|---|---|
| `id`, `request_id`, `title` | |
| `is_received`, `received_at`, `note`, `sort_order` | |

---

### ۱-۷. `document_package_attachments` (پیوست‌ها)

| ستون | توضیح |
|---|---|
| `id`, `package_id`, `parent_attachment_id` | |
| `original_name`, `stored_name`, `mime`, `size`, `sha256` | |
| `kind` | `scan` / `letter` / `evidence` / `response` / `other` |
| `description`, `previewable`, `uploaded_by`, `created_at` | |

**مسیر ذخیره:** `instance/uploads/packages/<dfc_code>/<uuid>.<ext>`

---

### ۱-۸. `document_package_wp_links` (اتصال چندگانه به WP)

| ستون | توضیح |
|---|---|
| `id`, `package_id`, `work_package_code` | |
| `is_primary` | 0/1 |
| `linked_by`, `linked_at` | |

---

### ۱-۹. `document_package_references` (رفرنس‌های چندگانه)

| ستون | توضیح |
|---|---|
| `id`, `package_id`, `reference_no` | |
| `description`, `created_by`, `created_at` | |

**کاربرد:** یک سند می‌تواند چند رفرنس داشته باشد (عطف به، پیرو، در پاسخ به...).

---

## 🔄 فاز ۲: سرویس‌ها (✅ انجام شد)

### ساختار
services/work_package/
├── init.py
├── wp_event_service.py ← رویدادها
├── wp_service.py ← ثبت + تخصیص + تغییر مرحله + رفرنس‌ها
├── wp_sla_service.py ← SLA
├── wp_assignment_service.py ← ارجاع
├── wp_attachment_service.py ← آپلود
├── wp_deficiency_service.py ← نواقص
├── wp_alarm_service.py ← هشدارها
└── wp_report_service.py ← گزارش‌ها

text

### توابع کلیدی `wp_service.py`
- `_allocate_counter(connection, kind, year)` — تخصیص اتمیک
- `find_work_package(...)` — تشخیص WP موجود
- `register_package(...)` — ثبت سند (با `references` و `all_refs`)
- `change_stage(...)` — تغییر مرحله
- `get_package(package_id)` — خواندن
- `list_work_package_siblings(wp_code)` — همه اسناد یک WP
- `link_package_to_wps(...)` — اتصال چندگانه
- `get_package_wps(package_id)` — WPهای یک سند
- `suggest_wps_for_reference(...)` — پیشنهاد WP (با منطق چندگانه)
- `find_wps_by_references(refs)` — جستجو با رفرنس
- `find_contractor_and_project_by_contract_number(...)` — تشخیص پیمانکار/پروژه
- `add_package_references(...)` — ثبت رفرنس‌های چندگانه
- `get_package_references(package_id)` — خواندن رفرنس‌ها (برای تب رفرنس‌ها)

---

## 🎨 فاز ۳: روت‌ها و فرم (✅ انجام شد)

### ساختار
routes/work_package/
├── init.py
├── wp_routes.py ← نمایش + چاپ + پاس دادن package_references
├── wp_step_routes.py ← ثبت سریع
├── wp_api_routes.py ← APIها
└── wp_attachment_routes.py ← آپلود/preview/download

text

### مسیرهای اصلی
| مسیر | متد | توضیح |
|---|---|---|
| `/work-package/` | GET | لیست پکیج‌ها |
| `/work-package/new` | GET/POST | ثبت سریع |
| `/work-package/<id>` | GET | صفحه‌ی پکیج (با تب رفرنس‌ها) |
| `/work-package/<id>/print-label` | GET | چاپ کد DFC |
| `/work-package/<id>/attachments/upload` | POST | آپلود |
| `/work-package/<id>/route` | POST | ارجاع |
| `/work-package/<id>/change-stage` | POST | تغییر مرحله |
| `/work-package/<id>/return-from-management` | POST | بازگشت از مدیریت |
| `/work-package/<id>/deficiencies` | POST | ثبت نواقص |
| `/work-package/<id>/link-wps` | POST | اتصال چندگانه |
| `/work-package/<id>/wps.json` | GET | WPهای یک سند |
| `/work-package/search` | POST | جستجو |
| `/work-package/suggest-wps` | POST | پیشنهاد WP (با همه‌ی رفرنس‌ها) |
| `/work-package/lookup-contract` | POST | تشخیص پیمانکار/پروژه |
| `/work-package/preview-sla` | POST | پیش‌نمایش SLA |
| `/work-package/search-users` | POST | جستجوی کاربران |
| `/work-package/attachments/<id>/preview` | GET | پیش‌نمایش |
| `/work-package/attachments/<id>/download` | GET | دانلود |
| `/work-package/attachments/<id>/delete` | POST | حذف |

### فرم ثبت (تک‌مرحله‌ای)
- **`templates/work_package/new.html`** — فرم کامل با:
  - **چند رفرنس** (با `name="references[]"`)
  - **دکمه‌ی «جستجوی رفرنس»** (به‌جای جستجوی خودکار)
  - **دکمه‌ی «انتخاب همه» / «لغو انتخاب همه»**
  - **شمارنده‌ی «X مورد انتخاب شده»**
  - **نمایش رفرنس‌های منطبق** زیر کد DFC در هر کارت WP
  - **پر شدن خودکار پیمانکار/پروژه** از شماره قرارداد (با `TRIM` و `setTimeout` 800ms)
  - **استایل مدرن** با گرادیانت و ریسپانسیو (حداکثر عرض ۱۴۰۰px)

---

## 📄 فاز ۴: صفحه‌ی پکیج (✅ انجام شد)

### `templates/work_package/view.html`
- **نوار پیشرفت مرحله‌ای** (ثبت اولیه → آپلود → ارسال به مدیریت → بازگشت → ارجاع)
- **۷ تب:**
  1. خلاصه (اطلاعات + SLA + مدیریت + نتیجه نهایی)
  2. ارجاع‌ها (فرم ارجاع + درخت)
  3. **رفرنس‌ها** (نمایش همه‌ی رفرنس‌های سند از `document_package_references`)
  4. نواقص (درخواست + چک‌لیست)
  5. پیوست‌ها (آپلود + لیست)
  6. اسناد مرتبط (siblings)
  7. تایم‌لاین

- **مودال بازگشت از مدیریت** (کامل):
  - تاریخ بازگشت
  - تاریخ درج‌شده روی سند
  - دستور مدیریت
  - نوع اقدام (ارجاع / بایگانی / جهت اطلاع / اقدام فوری)
  - گروه + زیرگروه (با پیش‌نمایش زنده SLA)
  - **انتخاب‌گر پیشرفته سرپرستان** (با جستجو و chips)
  - اگر `archive` → مستقیم آرشیو
  - اگر `route_to_supervisor` → ارجاع + تغییر مرحله

- **مودال ویرایش WPها** (اتصال چندگانه)

---

## 📥 فاز ۵: کارتابل (✅ انجام شد)

### `routes/inbox/inbox_routes.py`
- `get_inbox_merged` — ترکیب ارجاع‌های پکیج جدید + قدیمی
- ۵ تب: اقدام من، خوانده‌نشده، دیرکرد، در انتظار دیگران، انجام‌شده
- تفکیک بصری با برچسب «پکیج» (سبز) و «قدیمی» (خاکستری)

### `templates/inbox/inbox.html`
- نمایش با badge نوع
- اولویت‌بندی خودکار
- دکمه‌های اقدام (پذیرش/شروع/اتمام)

---

## 📊 فاز ۶: گزارش‌ها (✅ انجام شد)

### `services/work_package/wp_report_service.py`
- `get_overdue_packages(limit)` — اسناد دیرکرد
- `get_expert_workload()` — بار کاری کارشناسان
- `get_cycle_time_report(days)` — زمان چرخه
- `get_pending_management(limit)` — در انتظار مدیریت
- `get_pending_deficiencies(limit)` — در انتظار تکمیل مدارک

### `routes/reports/package_reports.py`
- `/reports/package/overdue`
- `/reports/package/workload`
- `/reports/package/cycle-time`
- `/reports/package/pending-management`
- `/reports/package/api/*`

### قالب‌ها
- `package_overdue.html`
- `package_workload.html`
- `package_cycle_time.html`
- `package_pending_management.html`

---

## 🔄 گردش کار (Stage Machine)
registered → ثبت اولیه

sent_to_management → ارسال فیزیکی به مدیریت

returned_from_management → بازگشت از مدیریت

routed → تعیین سرپرستان

in_progress → در حال بررسی

awaiting_contractor → در انتظار رفع نقص

under_review → منتظر تأیید سرپرست

approved → تأیید سرپرست

closed → بسته‌شده

archived → آرشیو

cancelled → لغو

text

### انتقال‌های مجاز
```python
STAGE_TRANSITIONS = {
    "registered":               ["sent_to_management", "cancelled"],
    "sent_to_management":       ["returned_from_management", "cancelled", "archived"],
    "returned_from_management": ["routed", "cancelled"],
    "routed":                   ["in_progress", "cancelled"],
    "in_progress":              ["awaiting_contractor", "under_review", "cancelled"],
    "awaiting_contractor":      ["in_progress", "cancelled"],
    "under_review":             ["approved", "in_progress"],
    "approved":                 ["closed", "in_progress"],
    "closed":                   ["archived"],
    "archived":                 [],
    "cancelled":                [],
}
انواع event_type
registered, sent_to_management, returned_from_management, routed_to_supervisor, routed_to_expert, expert_accepted, deficiency_requested, deficiency_fulfilled, response_prepared, response_approved_by_supervisor, response_approved_by_management, response_sent, finalized, archived, cancelled, attachment_added, sla_recalculated, overdue_detected, stage_changed, wp_links_updated

🧮 منطق تخصیص کدها
تخصیص DFC (اتمیک)
سال شمسی جاری

_allocate_counter("dfc", year) با BEGIN IMMEDIATE

فرمت: DFC-YYYY-NNNN

شماره هرگز بازاستفاده نمی‌شود

تخصیص WP (تشخیص هوشمند)
اولویت تشخیص (در find_work_package):

جستجو در document_package_references با رفرنس

sender_ref_no + contract_number

sender_ref_no + contractor_id

contract_number + contractor_id

contract_number + project_id

automation_number

نکته: اگر force_new_wp=True باشد → همیشه WP جدید

🔗 منطق رفرنس‌های چندگانه (اصلاح‌شده)
ثبت (در register_package)
رفرنس‌ها از request.form.getlist("references[]") خوانده می‌شوند.

all_refs = ترکیب reference_no + references (بدون تکراری).

اولین رفرنس در document_packages.reference_no و همه در document_package_references ذخیره می‌شوند (داخل try، قبل از commit).

پیشنهاد WP (در suggest_wps_for_reference)
منطق دقیق:

اگر all_references داده شده → همه‌ی رفرنس‌ها جستجو می‌شوند.

اگر فقط reference_no → همان یک رفرنس.

جستجو در دو مرحله:

sender_ref_no سندها (اولویت اول — چون شماره‌ی نامه‌ی خود سند است).
document_package_references (اگر رفرنس دستی ثبت شده).
اگر هم رفرنس و هم قرارداد:

اول تطابق دقیق (هم رفرنس و هم قرارداد).

بعد فقط رفرنس.

برچسب‌های منبع تطابق:

sender_ref+contract → «سند مرجع + تطابق قرارداد»

reference+contract → «تطابق دقیق»

sender_ref → «سند مرجع»

reference → «همان رفرنس»

روت suggest_wps_api
همه‌ی رفرنس‌ها را به‌عنوان all_references پاس می‌دهد (نه فقط اولی).

اگر رفرنس خالی باشد → هیچ پیشنهادی برنمی‌گرداند.

فرم ثبت
دکمه‌ی «جستجوی رفرنس» به‌جای جستجوی خودکار هنگام تایپ.

دکمه‌های «انتخاب همه» / «لغو انتخاب همه».

شمارنده‌ی «X مورد انتخاب شده».

نمایش رفرنس‌های منطبق (matching_references) زیر هر کارت WP.

نمایش در صفحه‌ی پکیج
تب «رفرنس‌ها» در view.html که همه‌ی رفرنس‌های سند را از document_package_references نشان می‌دهد.

نیاز به پاس دادن package_references از wp_routes.py:

python
package_references = wp_service.get_package_references(package_id)
# در render_template:
package_references=package_references
⏱ منطق SLA
اولویت
subgroup.days_review (اگر > 0)

group.days_review (اگر > 0)

SSPE_DEFAULT_SLA_DAYS (پیش‌فرض ۷)

محاسبه
sla_start_date = date_received

response_due_date = sla_start_date + N روز کاری

is_overdue = 1 اگر today > response_due_date و stage فعال

overdue_days = روزهای کاری دیرکرد

محاسبه مجدد
هنگام تغییر گروه/زیرگروه

هنگام تغییر تاریخ دریافت

دوره‌ای با flask wp-alarms-scan

🔔 هشدارها
رخداد	زمان	گیرنده
مهلت پاسخ نزدیک	۱ روز قبل	سرپرست + کارشناس متولی
دیرکرد سند	بعد از سررسید	سرپرست + مدیر
دیرکرد ۳ روز	۳ روز بعد	مدیر + علامت بحرانی
ارجاع بدون اقدام	۴۸ ساعت	مسئول ارجاع
بازگشت از مدیریت	بلافاصله	ثبت‌کننده
جلوگیری از اسپم: dedupe_key یکتا (pkg:<id>:overdue:3d)

✅ وضعیت پیاده‌سازی
فاز	بخش	وضعیت
۱	جداول دیتابیس (۹ جدول)	✅
۲	سرویس‌ها (۸ سرویس)	✅
۳	روت‌ها و فرم (با جستجوی رفرنس + انتخاب همه)	✅
۴	صفحه‌ی پکیج (۷ تب + تب رفرنس‌ها)	✅
۵	کارتابل ترکیبی	✅
۶	گزارش‌ها (۵ گزارش)	✅
۷	تست نهایی	⏳
۷	مستندسازی	✅
📝 نکات مهم
۱. جدول documents قدیمی دست‌نخورده
همه‌ی سرویس‌های جدید روی document_packages کار می‌کنند.

کارتابل ترکیبی از هر دو نمایش می‌دهد.

۲. قاعده‌ی طلایی تاریخ‌ها
همه‌ی تاریخ‌ها در دیتابیس میلادی، در UI شمسی.

۳. اتمیک بودن شماره‌گذاری
BEGIN IMMEDIATE + ON CONFLICT

شماره هرگز بازاستفاده نمی‌شود.

۴. دسترسی سه‌لایه
ادمین/مدیر/سرپرست/کنترل‌مستندات: کامل

ثبت‌کننده: سند خودش

مسئول ارجاع فعال: سند ارجاع‌شده

۵. آپلود بدون محدودیت
استریمی + SHA-256

مسیر: instance/uploads/packages/<dfc_code>/

۶. پیش‌نمایش فایل
تصویر/ویدیو/صدا → مودال

PDF → تب جدید (محدودیت مرورگر)

سایر → دانلود

۷. اتصال چندگانه به WP
یک سند می‌تواند به چند WP متصل باشد (document_package_wp_links)

یکی از آن‌ها is_primary=1 است (نمایش پیش‌فرض)

ستون work_package_code در document_packages = WP اصلی

۸. رفرنس‌های چندگانه (اصلاح‌شده)
یک سند می‌تواند چند رفرنس داشته باشد (document_package_references)

اولین رفرنس در reference_no ستون هم ذخیره می‌شود

در فرم با name="references[]" ارسال می‌شوند

جستجو در sender_ref_no سندها + جدول document_package_references

همه‌ی رفرنس‌ها جستجو می‌شوند (نه فقط اولی)

در تب رفرنس‌ها در صفحه‌ی پکیج نمایش داده می‌شوند

۹. تشخیص پیمانکار/پروژه از شماره قرارداد
API: POST /work-package/lookup-contract

جستجو در projects.contract_number با TRIM

اگر پیدا شد → پیمانکار و پروژه خودکار پر می‌شوند

۱۰. پیشنهاد WP
تا زمانی که رفرنس وارد نشود → هیچ WPی پیشنهاد نمی‌شود

همه‌ی رفرنس‌ها جستجو می‌شوند

اول sender_ref_no، بعد document_package_references

اگر تطابق دقیق نبود → فقط با رفرنس (بدون سقوط به قرارداد)

دکمه‌ی «جستجوی رفرنس» (نه جستجوی خودکار)

دکمه‌های «انتخاب همه» / «لغو انتخاب همه»

۱۱. اصلاحات اخیر
حذف ستون تکراری management_instruction از CREATE_SQL

افزودن migrate به document_packages.py

رفع خطای lookup_contract_api تکراری

افزودن package_references به view.html برای تب رفرنس‌ها

استایل مدرن‌تر برای فرم ثبت (max-width: 1400px)

انتخاب‌گر پیشرفته‌ی کارشناس/سرپرست (با جستجو و chips)

🎯 قدم‌های باقی‌مانده
فاز ۷: تست نهایی
□ ثبت سند جدید با چند رفرنس
□ آپلود اسکن
□ ارسال به مدیریت
□ بازگشت از مدیریت (با ارجاع)
□ پذیرش در کارتابل
□ تهیه پاسخ
□ تأیید سرپرست
□ تأیید مدیریت
□ بستن سند
□ آرشیو
□ اجرای flask wp-alarms-scan
□ تست هشدارها
□ تست تب رفرنس‌ها (نمایش همه)
بهبودهای آینده
□ پیش‌نمایش PDF درون مودال (PDF.js)
□ ایمیل/SMS
□ امضای دیجیتال
□ OCR اسناد فیزیکی
□ گزارش‌های پیشرفته‌تر (PPT)
□ گراف ارتباط اسناد (visualization)
🔧 دستورات مفید
مقداردهی اولیه دیتابیس
powershell
python -m database.init_db
اجرای migration خاص
powershell
python -m database.migrations.add_management_action
بررسی جداول
powershell
python -c "from database.connection import get_connection; c = get_connection(); rows = c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'document_package%' ORDER BY name\").fetchall(); [print(r['name']) for r in rows]; c.close()"
بررسی رفرنس‌های ثبت‌شده
powershell
python -c "from database.connection import get_connection; c = get_connection(); rows = c.execute('SELECT package_id, reference_no FROM document_package_references ORDER BY id DESC LIMIT 10').fetchall(); [print(dict(r)) for r in rows]; c.close()"
بررسی ستون‌های document_packages
powershell
python -c "from database.connection import get_connection; c = get_connection(); cols = [r['name'] for r in c.execute('PRAGMA table_info(document_packages)').fetchall()]; print('تعداد:', len(cols)); from collections import Counter; dup = [k for k, v in Counter(cols).items() if v > 1]; print('تکراری:', dup if dup else 'هیچ'); c.close()"
اجرای اسکنر هشدارها
powershell
flask wp-alarms-scan
📌 نتیجه‌گیری
این سند، مرجع کامل پروژه‌ی «پکیج سند» است. هر توسعه‌دهنده یا AI که به این پروژه نگاه کند، با مطالعه‌ی این فایل:

معماری کامل را می‌فهمد

می‌داند چه چیزی پیاده شده

می‌داند چه چیزی باقی مانده

قواعد تاریخ و منطق‌ها را می‌داند