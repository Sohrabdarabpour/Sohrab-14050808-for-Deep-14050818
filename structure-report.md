# ساختار پروژه SSPE (نسخه Sohrab 14050808)

> تحلیل خودکار ساختار پوشه‌ها و معماری برنامه — تاریخ: 1405/08/09

---

## ۱. خلاصه

این یک برنامه **وب Flask** (Python) برای مدیریت مستندات و گزارش‌های سازمانی (پروژه‌ها، پیمانکاران، کارشناسان، دپارتمان‌ها، گردش‌کار تأیید یادداشت‌ها و دستیار هوش مصنوعی) است.

معماری آن **لایه‌ای بر پایه Blueprint** است:

```
app.py  →  routes/  →  services/  →  database/
                 ↘  forms/  (اعتبارسنجی)   ↘  helpers/ , security/  (کمکی)
                            ↕
                       templates/  +  static/
```

| مورد | مقدار |
|---|---|
| فایل‌های Python | ۱۶۰ (از این تعداد **۱۶ فایل «copy» تکراری**) |
| فایل‌های HTML (قالب) | ۷۳ |
| فایل‌های CSS | ۳۶ |
| فایل‌های JS | ۱ (`static/js/app.js`) |
| مجموع فایل‌ها (بدون `__pycache__`) | ۳۱۲ |
| خطوط Python | ~۳۳٫۹ هزار |
| خطوط کل کد (py+html+css+js) | ~۱۱۶ هزار |
| Blueprintهای ثبت‌شده | ۱۸ |

---

## ۲. پشته فناوری (`requirements.txt`)

`Flask` · `Flask-SQLAlchemy` · `Flask-Migrate` · `Jinja2` · `Werkzeug` · `openpyxl` · `pandas` · `numpy` · `xlrd` · `python-pptx` · `openai` (دستیار AI) · `opencv-python` · `python-dotenv` · `gunicorn`

---

## ۳. لایه‌ها و مسئولیت هر پوشه

| پوشه | لایه | مسئولیت |
|---|---|---|
| `app.py` | نقطه ورود | `create_app()`، ثبت ۱۸ Blueprint، فیلترهای تاریخ جلالی، ردیابی فعالیت کاربر، context processor، هندلرهای خطای ۴۰۰–۵۰۰ |
| `run.py` | اجرا | فقط فراخوانی اپ (۱۶۰ بایت) |
| `config.py` | تنظیمات | کلاس `Config` (SECRET_KEY، مسیر دیتابیس و …) |
| `routes/` | کنترلر | تعریف Blueprintها و endpointها؛ زیرپوشه برای هر ماژول |
| `services/` | منطق کسب‌وکار | سرویس‌ها + خروجی/ورودی Excel و PowerPoint |
| `database/` | دسترسی داده | `connection.py`، `init_db.py` و توابع CRUD جداگانه (`users.py`، `documents.py`، `reports.py`) + `migrations/` |
| `forms/` | اعتبارسنجی | فرم‌های WTForms برای هر موجودیت |
| `helpers/` | کمکی | `date_helper.py` (تاریخ جلالی)، `workflow/permissions.py` (قواعد دسترسی گردش‌کار) |
| `security/` | امنیت | `decorators.py` — دکوراتورهای احراز هویت/مجوز (`@login_required` و …) |
| `templates/` | نمایش | قالب‌های Jinja2، آینه‌ی ساختار `routes/` |
| `static/` | دارایی‌های سمت کلاینت | CSS چهارلایه، تصاویر، JS، آپلودهای کاربران |
| `instance/` | داده | فایل‌های SQLite |
| `uploads/` | خروجی موقت | خروجی‌های Excel |
| `scripts/` | ابزار | `seed_experts.py` (داده اولیه) |

---

## ۴. درخت کامل پوشه‌ها

```
SSPE/
├── database/
│   ├── migrations/
│   │   └── add_user_profile_columns.py
│   ├── __init__.py
│   ├── connection.py
│   ├── documents.py
│   ├── init_db.py
│   ├── reports.py
│   └── users.py
├── forms/
│   ├── contract_types/        { __init__.py, contract_type_form.py }
│   ├── contractors/           { __init__.py, contractor_form.py }
│   ├── document_group/        { __init__.py, forms.py }
│   ├── project_roles/         { __init__.py, project_role_form.py }
│   ├── projects/              { __init__.py, project_form.py }
│   ├── workflow/              { __init__.py, note_form.py }
│   ├── __init__.py
│   ├── auth_forms.py
│   ├── department_forms.py
│   ├── document_forms.py
│   └── user_forms.py
├── helpers/
│   ├── workflow/              { __init__.py, permissions.py (+۳ فایل copy) }
│   ├── __init__.py
│   └── date_helper.py
├── instance/
│   ├── database.db            (~۷٫۵ MB)
│   ├── database all.db        (~۷٫۵ MB)
│   └── database2.db           (~۷٫۵ MB)
├── routes/
│   ├── ai/                    { __init__.py, assistant.py }        /assistant
│   ├── contract_types/        { __init__.py, contract_type_routes.py }  /contract-types
│   ├── contractors/           { __init__.py, contractor_routes.py }     /contractors
│   ├── departments/           { __init__.py, department_routes.py }     /departments
│   ├── document_group/        { __init__.py, group_routes.py, subgroup_routes.py, helpers.py }  /document-groups
│   ├── profile/               { __init__.py, profile.py }          /profile
│   ├── project_roles/         { __init__.py, project_role_routes.py }   /project-roles
│   ├── projects/              { __init__.py, project_routes.py }        /projects
│   ├── reports/                                                         /reports
│   │   ├── __init__.py
│   │   ├── area.py
│   │   ├── area_departments.py
│   │   ├── contractors.py
│   │   ├── delays.py
│   │   ├── department.py
│   │   ├── department_documents.py
│   │   ├── department_expert_documents.py   (+ copy)
│   │   ├── department_performance.py        (+ copy)
│   │   ├── experts.py
│   │   ├── projects.py
│   │   ├── responsible.py
│   │   ├── status.py
│   │   ├── status_documents.py
│   │   └── units.py
│   ├── search/                { __init__.py, search_routes.py }    /search
│   ├── workflow/              { __init__.py, note_routes.py, notification_routes.py }  /workflow , /notifications
│   ├── __init__.py            ← ثبت و صادرات همه Blueprintها
│   ├── auth.py                /auth
│   ├── dashboard.py           /dashboard
│   ├── documents.py           /documents
│   ├── excel.py               /excel
│   ├── main.py                (بدون prefix)
│   ├── panel.py               /panel
│   ├── routes.py              ← استفاده نشده (کد مرده)
│   ├── import_routes.py       ← استفاده نشده (کد مرده)
│   ├── documents copy.py      ← تکراری
│   └── panel copy.py          ← تکراری
├── scripts/
│   └── seed_experts.py
├── security/
│   ├── __init__.py
│   └── decorators.py
├── services/
│   ├── ai/
│   │   ├── handlers/          { base, status, list, search, analytics, group,
│   │   │                        expert_documents, classification }_handlers.py
│   │   ├── __init__.py
│   │   ├── assistant_service.py
│   │   ├── cache.py           ← کش پاسخ‌ها
│   │   ├── context.py
│   │   ├── formatters.py
│   │   ├── llm_config.py
│   │   ├── llm_service.py
│   │   ├── llm_tools.py
│   │   ├── nlu.py             ← تشخیص قصد کاربر
│   │   └── registry.py        ← نگاشت intent → handler
│   ├── contract_types/        { __init__.py, contract_type_service.py }
│   ├── contractors/           { __init__.py, contractor_service.py, contractor_excel_service.py }
│   ├── document_group/
│   │   ├── report/            { __init__.py, excel_flat_service.py, ppt_service.py }
│   │   ├── __init__.py
│   │   ├── group_service.py
│   │   ├── group_excel_service.py
│   │   ├── subgroup_service.py
│   │   ├── subgroup_excel_service.py
│   │   └── subgroup_excel_flat_service.py
│   ├── project_roles/         { __init__.py, project_role_service.py }
│   ├── projects/              { __init__.py, project_service.py, project_excel_service.py, project_member_service.py }
│   ├── search/                { __init__.py, search_service.py }
│   ├── workflow/              { __init__.py, note_service.py (+copy), notification_service.py }
│   ├── __init__.py
│   ├── area_departments_service.py
│   ├── area_report_service.py
│   ├── avatar_service.py
│   ├── dashboard_service.py
│   ├── department_service.py
│   ├── department_documents_service.py
│   ├── department_expert_documents_service.py  (+ copy)
│   ├── department_performance_service.py       (+ copy)
│   ├── department_report_service.py
│   ├── document_service.py
│   ├── excel_service.py
│   ├── profile_service.py
│   ├── status_documents_service.py
│   ├── status_report_service.py
│   ├── user_service.py                         (+ copy)
│   └── user_excel_service.py                   (+ copy)
├── static/
│   ├── css/
│   │   ├── base/              { base.css, base copy.css }
│   │   ├── core/              { variables.css, reset.css, utilities.css }
│   │   ├── components/        { alerts, app-header, badges, buttons, card-layout,
│   │   │                        components, data-card, data-grid, document-card,
│   │   │                        empty-state, filter-panel, forms, mobile-menu,
│   │   │                        modal, navigation, page-footer, page-header2,
│   │   │                        page-layout, report-card, rtl, sidebar2,
│   │   │                        skeleton, stats-panel, status-card }.css
│   │   ├── pages/             { dashboard3, documents, panel, responsible,
│   │   │                        status, users }.css
│   │   └── app-ui.css         ← فایل قدیمی/جامع
│   ├── images/                { logo.png, sspe.png, sspe.jpg,
│   │                            default-profile-female.png, default-profile-male.png }
│   ├── js/
│   │   └── app.js
│   └── uploads/               (آواتار کاربران + خروجی‌های Excel پروژه/پیمانکار)
├── templates/
│   ├── ai/
│   │   ├── assistant/         { index.html, index copy.html, index copy 2.html }
│   │   └── documents/         { view.html }
│   ├── auth/                  { logout.html }
│   ├── components/            { base-layout: header.html, sidebar.html, footer.html }
│   ├── contract_types/        { form.html, list.html }
│   ├── contractors/           { form.html, list.html, view.html }
│   ├── dashboard/             { index.html }
│   ├── departments/           { form.html, list.html (+copy), view.html, expert_breakdown.html }
│   ├── document_group/
│   │   ├── groups/            { list, form, detail, import }.html
│   │   └── subgroups/         { list, form, detail, import }.html
│   ├── documents/             { index.html, view.html }
│   ├── errors/                { 400, 401, 403, 404, 500 }.html  + فایل بی‌نام «erore»
│   ├── excel/                 { import.html }
│   ├── notifications/         { list, by_expert, expert_detail, notif_dropdown }.html + فایل «یی»
│   ├── panel/                 { users.html, add_user.html, edit_user.html, user_detail.html }
│   ├── profile/               { profile.html, profile copy.html }
│   ├── project_roles/         { form.html, list.html }
│   ├── projects/              { form.html, list.html, view.html }
│   ├── reports/               { area, area_departments, department, department_documents,
│   │                            department_expert_documents, department_performance (+copy),
│   │                            responsible, status, status_documents }.html
│   ├── search/                { search.html, search2.html }
│   ├── workflow/              { inbox, my_notes, note_view, _note_card, _note_modal, _timeline }.html
│   ├── access_denied.html
│   ├── base.html              ← قالب پایه (extends در همه صفحات)
│   └── login.html
├── uploads/                   ← زائد: ۴ فایل copy (html/py) + excel_exports/
├── app.py
├── check_doc_control_dept.py  ← اسکریپت موقت
├── config.py
├── project_structure.json     ← خروجی show_structure.py
├── requirements.txt
├── run.py
├── show_structure.py          ← ابزار تولید همین ساختار
├── stracher.txt               ← طرح اولیه ساختار (Rev 1)
└── threshold                  ← فایل خالی
```

---

## ۵. نقشه ماژول‌ها (Blueprint ↔ سرویس ↔ قالب)

| # | Blueprint | مسیر URL | کنترلر | سرویس | قالب |
|---|---|---|---|---|---|
| ۱ | `main_bp` | `/` | `routes/main.py` | `dashboard_service` | `base.html`, `access_denied.html` |
| ۲ | `auth_bp` | `/auth` | `routes/auth.py` | `user_service` | `login.html`, `auth/logout.html` |
| ۳ | `dashboard_bp` | `/dashboard` | `routes/dashboard.py` | `dashboard_service.py` | `dashboard/index.html` |
| ۴ | `departments_bp` | `/departments` | `routes/departments/` | `department_service.py` | `departments/*` |
| ۵ | `panel_bp` | `/panel` | `routes/panel.py` | `user_service`, `user_excel_service` | `panel/*` |
| ۶ | `excel_bp` | `/excel` | `routes/excel.py` | `excel_service.py` | `excel/import.html` |
| ۷ | `documents_bp` | `/documents` | `routes/documents.py` | `document_service.py` | `documents/*` |
| ۸ | `reports_bp` | `/reports` | `routes/reports/*` (۱۵ فایل) | `*_report_service.py` | `reports/*` (۱۰ قالب) |
| ۹ | `profile_bp` | `/profile` | `routes/profile/` | `profile_service`, `avatar_service` | `profile/profile.html` |
| ۱۰ | `document_group_bp` | `/document-groups` | `routes/document_group/` | `services/document_group/` | `document_group/**` |
| ۱۱ | `assistant_bp` | `/assistant` | `routes/ai/assistant.py` | `services/ai/` (۱۰ ماژول + ۹ handler) | `ai/assistant/index.html` |
| ۱۲ | `contractor_bp` | `/contractors` | `routes/contractors/` | `contractor_service`, `contractor_excel_service` | `contractors/*` |
| ۱۳ | `contract_types_bp` | `/contract-types` | `routes/contract_types/` | `contract_type_service.py` | `contract_types/*` |
| ۱۴ | `project_roles_bp` | `/project-roles` | `routes/project_roles/` | `project_role_service.py` | `project_roles/*` |
| ۱۵ | `projects_bp` | `/projects` | `routes/projects/` | `project_service`, `project_member_service`, `project_excel_service` | `projects/*` |
| ۱۶ | `workflow_bp` | `/workflow` | `routes/workflow/note_routes.py` | `note_service`, `helpers/workflow/permissions` | `workflow/*` |
| ۱۷ | `notification_bp` | `/notifications` | `routes/workflow/notification_routes.py` | `notification_service.py` | `notifications/*` |
| ۱۸ | `search_bp` | `/search` | `routes/search/search_routes.py` | `search_service.py` | `search/search.html` |

نکته: `routes/reports/` با ۱۵ فایل بزرگ‌ترین ماژول است و `services/ai/` پیچیده‌ترین (لایه NLU → registry → handlers).

---

## ۶. الگوی تکرارشونده در ماژول‌های جدید

ماژول‌هایی مثل `projects`، `contractors`، `contract_types`، `project_roles`، `workflow` و `document_group` دقیقاً یک الگوی ۵ پوشه‌ای دارند — این الگوی مرجع برای ساخت ماژول جدید است:

```
routes/<name>/  __init__.py (Blueprint + url_prefix)  +  <name>_routes.py
forms/<name>/   __init__.py  +  <name>_form.py
services/<name>/ __init__.py +  <name>_service.py  (+ <name>_excel_service.py)
templates/<name>/ list.html , form.html , view.html
app.py + routes/__init__.py   ← ثبت Blueprint در دو جا
```

---

## ۷. مشکلات ساختاری و پیشنهاد مرتب‌سازی

### ۷-۱. فایل‌های تکراری «copy» (۲۴ فایل)
پراکنده در `routes/`، `services/`، `forms/`، `helpers/`، `static/css/base/`، `templates/ai/assistant/`، `templates/profile/`، `templates/reports/`، `templates/departments/` و `uploads/`.
خطر: ویرایش فایل اشتباه، سردرگمی در جستجو. پیشنهاد: انتقال به یک پوشه `_archive/` یا حذف.

### ۷-۲. کد مرده (import نمی‌شوند)
`routes/routes.py` · `routes/import_routes.py` · `routes/documents copy.py` · `routes/panel copy.py` · `routes/search/search_routes - Copy.py`
هیچ‌کدام در `routes/__init__.py` یا `app.py` ثبت نشده‌اند.

### ۷-۳. فایل‌های نامرتبط در `uploads/`
چهار فایل `.html` و `.py` (`department_documents_service copy.py` و …) داخل پوشه آپلود قرار گرفته‌اند؛ جای آن‌ها `services/` یا `templates/` است. همچنین `uploads/excel_exports/` انباشت خروجی‌های قدیمی (تا ۲ MB هر فایل) دارد.

### ۷-۴. سه دیتابیس هم‌اندازه در `instance/`
`database.db` · `database all.db` · `database2.db` — همه ~۷٫۵ MB. باید مشخص شود `config.py` کدام را استفاده می‌کند و بقیه آرشیو شوند.

### ۷-۵. فایل‌های زائد ریشه
`threshold` (۰ بایت) · `templates/errors/erore` · `templates/notifications/یی` · `project_structure.json` (خروجی ابزار) · `check_doc_control_dept.py` (اسکریپت موقت)

### ۷-۶. ناهمگونی CSS
هم‌زمان `static/css/app-ui.css` (فایل جامع قدیمی) و ساختار ماژولار `base/ core/ components/ pages/` وجود دارد. همچنین `page-header2.css` و `sidebar2.css` نشانه نسخه‌بندی دستی است. پیشنهاد: حذف تدریجی `app-ui.css` و ادغام نسخه‌های «2».

### ۷-۷. نبود تست و مستندات ساختاری
پوشه `tests/` که در `stracher.txt` پیش‌بینی شده ساخته نشده است. `README.md` هم وجود ندارد.

### ۷-۸. کش `__pycache__` با دو نسخه پایتون
هم `cpython-311` و هم `cpython-313` وجود دارد (نشانه اجرا با دو نسخه پایتون). افزودن `.gitignore` توصیه می‌شود.

---

## ۸. مقایسه با طرح اولیه (`stracher.txt`)

طرح اولیه «SSPE Rev 1» ساختاری تمیز با `tests/` و بدون نسخه‌های تکراری داشت. پیاده‌سازی فعلی بسیار گسترده‌تر شده (۱۸ Blueprint در برابر ۸) و ماژول‌های `ai`، `workflow`، `search`، `document_group`، `projects`، `contractors` اضافه شده‌اند؛ اما انضباط ساختاری طرح اولیه حفظ نشده است (فایل‌های copy، کد مرده، دیتابیس‌های تکراری).

---

# ۹. وضعیت پس از اصلاح

> این بخش پس از اجرای مرحله ۱ (پاکسازی و استانداردسازی ساختار) افزوده شده است.

## ۹-۱. کارهای انجام‌شده

| ردیف | مشکل | اقدام | وضعیت |
|---|---|---|---|
| ۱ | ۲۴ فایل تکراری «copy» | انتقال به `_archive/duplicates/` با حفظ مسیر اصلی | ✅ |
| ۲ | ۵ فایل کد مرده | انتقال `routes.py` و `import_routes.py` به `_archive/dead_code/` | ✅ |
| ۳ | فایل‌های `.py/.html` داخل `uploads/` | همراه گروه copy آرشیو شدند | ✅ |
| ۴ | سه دیتابیس هم‌اندازه | `database all.db` و `database2.db` به `_archive/legacy_databases/`؛ فقط `database.db` فعال است | ✅ |
| ۵ | فایل‌های زائد ریشه | `threshold`، `erore`، `یی`، `project_structure.json` به `_archive/junk/` | ✅ |
| ۶ | ابزارهای توسعه در ریشه | `show_structure.py`، `stracher.txt`، `check_doc_control_dept.py` به `_archive/tools/` | ✅ |
| ۷ | نبود تست | `tests/` با ۸ تست pytest (Blueprintها، مسیرها، رندر، ریدایرکت، ۴۰۴، کامپایل قالب‌ها، نبود فایل copy) | ✅ |
| ۸ | نبود مستندات | `README.md` (معماری، راه‌اندازی، الگوی ماژول جدید) + `_archive/README.md` | ✅ |
| ۹ | نبود ابزار کیفیت کد | `pyproject.toml` با تنظیمات black / ruff / isort / pytest | ✅ |
| ۱۰ | نبود `.gitignore` | `.gitignore` برای کش‌ها، دیتابیس، `uploads/`، `.env`، `_archive/`، `_backup/` | ✅ |
| ۱۱ | کش `__pycache__` (۳۳ پوشه) | حذف شد (بازتولیدشدنی) | ✅ |
| ۱۲ | مسیر دیتابیس غیرقابل‌تنظیم | `config.py`: افزودن متغیر محیطی `SSPE_DATABASE_PATH` با حفظ مقدار پیش‌فرض | ✅ |
| ۱۳ | `static/css/app-ui.css` موازی با ساختار ماژولار | نیازمند بازبینی بصری صفحه‌به‌صفحه | ⏳ بعدی |
| ۱۴ | `routes/reports/` با ۱۵ فایل تخت | نیازمند بازآرایی پکیجی و به‌روزرسانی importها | ⏳ بعدی |
| ۱۵ | `init_db()` در زمان import | پیشنهاد: دستور `flask init-db` | ⏳ بعدی |

## ۹-۲. آمار قبل و بعد

| شاخص | قبل | بعد |
|---|---|---|
| فایل‌های فعال | ۳۱۲ | **۲۸۷** |
| فایل Python | ۱۶۰ | **۱۴۲** |
| فایل HTML | ۷۳ | **۶۶** |
| فایل CSS | ۳۶ | **۳۵** |
| فایل‌های تکراری «copy» | ۲۴ | **۰** |
| دیتابیس در `instance/` | ۳ | **۱** |
| پوشه کش `__pycache__` | ۳۳ | **۰** |
| مسیرهای ثبت‌شده (routes) | ۱۵۶ | **۱۵۶** (بدون تغییر) |
| Blueprintها | ۱۸ | **۱۸** (بدون تغییر) |
| تست | ۰ | **۸ (همه پاس)** |

## ۹-۳. ریشه پروژه پس از اصلاح

```
SSPE/
├── app.py                  ← create_app، ثبت ۱۸ Blueprint
├── run.py
├── config.py               ← + پشتیبانی از SSPE_DATABASE_PATH
├── requirements.txt
├── pyproject.toml          ← black / ruff / isort / pytest
├── .gitignore
├── README.md
├── structure-report.md     ← همین گزارش
│
├── database/  forms/  helpers/  security/  services/  routes/
├── templates/  static/  scripts/
├── tests/                  ← جدید: conftest.py + test_smoke.py
├── instance/               ← فقط database.db
├── uploads/                ← خروجی‌های Excel
├── _archive/               ← ۳۶ فایل خارج‌شده از کد فعال + MOVED-FILES.tsv
└── _backup/                ← SSPE-20261031-1528.zip (۲۲٫۲ MB)
```

## ۹-۴. اعتبارسنجی

- `python -m pytest` → **۸ تست پاس**
- اجرای برنامه با دیتابیس واقعی → **۱۵۶ مسیر، ۱۸ Blueprint، بدون خطا**
- کامپایل همه ۶۶ قالب Jinja2 → **بدون خطا**
- هیچ فایل فعالی در `routes/`، `services/`، `forms/`، `helpers/`، `templates/`، `static/` به فایل‌های آرشیوشده ارجاع نمی‌دهد

**نقطه بازگشت:** استخراج `_backup/SSPE-20261031-1528.zip` روی ریشه پروژه، وضعیت قبل از تغییرات را کامل بازمی‌گرداند.

> ⚠️ **تصحیح:** این zip با `Compress-Archive` ساخته شده بود و **ساختار پوشه‌ها را حفظ نمی‌کند** (همه فایل‌ها در یک سطح قرار گرفتند). به‌همین دلیل حذف و با `_backup/SSPE-after-refactor-<timestamp>.zip` جایگزین شد که با `zipfile` ساخته شده و مسیرهای نسبی را کامل نگه می‌دارد (۳۸۶ فایل، ۳۷۳ مسیر تودرتو).

---

# ۱۰. مرحله ۲ — تفکیک `init_db.py` و پوشه‌بندی سرویس/فرم/روت

## ۱۰-۱. مسئله

`database/init_db.py` یک ماژول غول‌آسا بود: **۲۴۵۹ خط، ۸۷ KB** شامل هم‌زمان:

- ساخت **۱۸ جدول**
- **۴۲ ایندکس**
- **۹ تابع داده پیش‌فرض** (`create_default_*`)
- **۷۶ تابع CRUD** (`get_user`، `create_project`، `get_note`، `create_notification`، …)

یعنی برای اصلاح یک ستون در جدول `notifications` باید در فایلی با ۲۴۵۹ خط جست‌وجو می‌کردید — دقیقاً همان چیزی که قرار بود از آن پرهیز شود.

در کنار آن، `services/` و `forms/` و `routes/` هم فایل‌های تخت داشتند: `user_service.py`، `auth_forms.py`، `panel.py` و… که با پوشه‌های ماژول‌های دیگر (`projects/`، `contractors/`) ناهمگون بودند.

## ۱۰-۲. ساختار جدید دیتابیس

```
database/
├── connection.py           ← اتصال SQLite (بدون تغییر)
├── init_db.py              ← ۳۸ خط: فقط هماهنگ‌کننده
├── tables/                 ← ۱۸ فایل، یک فایل برای هر جدول
│   ├── __init__.py         ← TABLES + create_all() + create_indexes()
│   ├── users.py            ← CREATE_SQL + INDEX_SQL + create()
│   ├── document_statuses.py
│   ├── areas.py
│   ├── departments.py
│   ├── document_groups.py
│   ├── document_subgroups.py
│   ├── group_subgroups.py
│   ├── subgroup_departments.py
│   ├── documents.py        ← + migrate() برای ALTER TABLEهای قدیمی
│   ├── contractors.py
│   ├── contract_types.py
│   ├── project_roles.py
│   ├── projects.py
│   ├── project_members.py
│   ├── workflow_steps.py
│   ├── document_notes.py
│   ├── note_events.py
│   └── notifications.py
├── seeds/                  ← ۹ فایل، داده‌های پیش‌فرض
│   ├── __init__.py         ← SEED_STEPS + run_all()
│   ├── statuses.py · areas.py · departments.py · document_groups.py
│   └── contract_types.py · project_roles.py · workflow_steps.py
│       · admin.py · contractors.py
└── repositories/           ← ۱۰ فایل، توابع CRUD
    ├── __init__.py         ← __all__ شامل همه ۷۶ تابع
    ├── users.py · areas.py · contract_types.py · project_roles.py
    ├── projects.py · project_members.py · contractors.py
    └── workflow.py · notifications.py · documents.py
```

`init_db.py` الان فقط این است:

```python
def init_db():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    connection = get_connection()
    cursor = connection.cursor()
    try:
        _create_tables(cursor)        # database/tables/
        _migrate_documents(cursor)    # ستون‌های جدید documents
        _create_indexes(cursor)       # ایندکس‌های هر جدول
        connection.commit()
    finally:
        connection.close()
    _run_seeds()                      # database/seeds/
```

## ۱۰-۳. سازگاری با کد موجود

۲۶ نقطه از کد، توابع را از `database.init_db` import می‌کردند (`from database.init_db import get_note`). همه آن‌ها **بدون تغییر کار می‌کنند**، چون `init_db.py` این توابع را از `database/repositories/` دوباره صادر می‌کند:

```python
from .repositories import *          # سازگاری
__all__ = ["init_db"] + list(_REPOSITORY_EXPORTS)
```

## ۱۰-۴. ساختار جدید سرویس / فرم / روت

| لایه | قبل | بعد |
|---|---|---|
| `services/` | ۱۶ سرویس تخت + ۸ پوشه | **۱۶ پوشه**، صفر فایل تخت |
| `forms/` | ۴ فرم تخت + ۶ پوشه | **۱۱ پوشه**، صفر فایل تخت |
| `routes/` | ۶ روت تخت + ۱۱ پوشه | **۱۸ پوشه**، صفر فایل تخت |

نمونه‌ها:

```
services/user_service.py     → services/users/user_service.py
services/avatar_service.py   → services/users/avatar_service.py
services/document_service.py → services/documents/document_service.py
services/department_*.py (۵) → services/departments/
services/*_report_service.py → services/reports/
forms/auth_forms.py          → forms/auth/forms.py
forms/user_forms.py          → forms/users/forms.py
routes/panel.py              → routes/panel/panel_routes.py + __init__.py
routes/auth.py               → routes/auth/auth_routes.py + __init__.py
```

همه importها در **۲۲ فایل** بازنویسی شدند (`services.user_service` → `services.users.user_service` و …). برای روت‌ها هیچ بازنویسی import لازم نبود، چون `routes/<name>/__init__.py` همان `auth_bp`/`panel_bp` را صادر می‌کند و `from .auth import auth_bp` در `routes/__init__.py` دست‌نخورده کار می‌کند.

## ۱۰-۵. باگ واقعی که در همین مسیر پیدا شد

هنگام مقایسه فهرست مسیرها، تعداد از ۱۵۶ به ۱۵۷ رسید. علت:

> **`routes/reports/responsible.py` در `routes/reports/__init__.py` import نشده بود.**

نتیجه: مسیر `/reports/responsible` هرگز ثبت نمی‌شد و صفحه «مسئول رسیدگی» (همراه با `templates/reports/responsible.html` و `static/css/pages/responsible.css`) در برنامه واقعی **۴۰۴ می‌داد** — با اینکه فایل‌هایش کامل بودند.

این باگ با یک خط import اصلاح شد و برای اینکه تکرار نشود، تست `test_every_route_module_is_imported` اضافه شد.

## ۱۰-۶. اعتبارسنجی مرحله ۲

| بررسی | نتیجه |
|---|---|
| برابری ساختار دیتابیس (۱۸ جدول + ۴۲ ایندکس) | **۶۰ آبجکت، کاملاً یکسان** |
| برابری رکوردهای seed | **یکسان** (users=1، statuses=5، departments=10، document_groups=17، contract_types=11، project_roles=8، workflow_steps=3) |
| توابع CRUD منتقل‌شده | **۷۶ از ۷۶** (بدون گم‌شدن) |
| import سالم همه ماژول‌ها | **۱۸۶ ماژول، بدون خطا** |
| مسیرهای ثبت‌شده | **۱۵۷** (۱۵۶ قبلی + مسیر responsible که تازه فعال شد) |
| Blueprintها | **۱۸** (بدون تغییر) |
| تست‌ها | **۱۳ پاس** (۸ دود + ۵ معماری) |

## ۱۰-۷. آمار نهایی

| شاخص | ابتدا | مرحله ۱ | مرحله ۲ |
|---|---|---|---|
| خطوط `init_db.py` | ۲۴۵۹ | ۲۴۵۹ | **۳۸** |
| فایل‌های تخت در `services/` | ۱۶ | ۱۶ | **۰** |
| فایل‌های تخت در `forms/` | ۴ | ۴ | **۰** |
| فایل‌های تخت در `routes/` | ۶ | ۶ | **۰** |
| ماژول‌های دیتابیس | ۴ | ۴ | **۴۱** (۱۸ جدول + ۹ seed + ۱۰ CRUD + ۴ پایه) |
| تست | ۰ | ۸ | **۱۳** |
| مسیرهای ثبت‌شده | ۱۵۶ | ۱۵۶ | **۱۵۷** |

**نقطه بازگشت مرحله ۲:** `_backup/SSPE-after-refactor-20261031-1543.zip` (۳۸۶ فایل، با حفظ ساختار پوشه‌ها) و نسخه اصلی `init_db.py` در `_archive/refactor/init_db.py.original`.

---

# ۱۱. مرحله ۳ — بازطراحی لایه‌ی نمایش (CSS و JS)

## ۱۱-۱. تشخیص

اندازه‌گیری اولیه نشان داد مشکل اصلی «کمبود استایل» نیست، بلکه **جای اشتباه استایل** است:

| شاخص | مقدار قبل |
|---|---|
| خطوط CSS داخل قالب‌ها | **۴۵٬۵۶۲** خط در ۶۱ قالب |
| خطوط CSS در فایل‌های واقعی | ۷٬۳۱۹ خط در ۳۵ فایل |
| فایل‌های CSS که **هیچ‌جا استفاده نمی‌شدند** | **۲۸ از ۳۵** |
| خطوط JS داخل قالب‌ها | **۱۲٬۲۴۰** خط در ۳۹ قالب |
| خطوط JS در فایل‌های واقعی | ۹۹ خط (`app.js`) |
| بلوک‌های استایل تکراری (کپی‌برداری) | ۰ |
| بلوک‌های استایل حاوی Jinja (مانع استخراج) | ۰ |

یعنی هر صفحه استایل خودش را در دل خودش حمل می‌کرد و ۸۰٪ فایل‌های CSS پروژه مرده بودند.

## ۱۱-۲. کاری که انجام شد

**CSS — ۵۵ قالب، ۴۵٬۴۴۲ خط:**
```
templates/reports/area.html  →  static/css/pages/reports/area.css
templates/components/sidebar.html → static/css/components/sidebar.css
```
- هر قالب دقیقاً یک فایل CSS با **مسیر آینه‌ای** دارد
- لینک در `{% block styles %}` قالب قرار گرفت (در انتهای head، مثل قبل)
- قالب‌های partial (بدون `{% extends %}`) در `base.html` لینک شدند — **بعد از** بلوک styles، چون قبلاً استایلشان در body و بعد از استایل صفحه بود؛ ترتیب آبشاری حفظ شد

**JS — ۲۲ قالب، ۶٬۲۹۸ خط:**
```
templates/search/search.html  →  static/js/pages/search/search.js
```
- جای تگ `<script>` **تغییر نکرد** (بدون `defer`)، فقط محتوا به فایل رفت → ترتیب اجرا و زمان‌بندی یکسان

**CSS مرده — ۲۸ فایل، آرشیو شد:**
`static/css/components/*` و `pages/{dashboard3,responsible,status,users}.css` که هیچ قالبی به آن‌ها ارجاع نمی‌داد.

## ۱۱-۳. وضعیت بعد

| شاخص | قبل | بعد |
|---|---|---|
| CSS داخل قالب‌ها | ۴۵٬۵۶۲ | **۰** |
| فایل‌های CSS زنده | ۷ | **۶۷** |
| فایل‌های CSS مرده | ۲۸ | **۰** |
| JS داخل قالب‌ها | ۱۲٬۲۴۰ | **۵٬۸۹۹** (۱۷ فایل) |
| فایل‌های JS | ۱ | **۲۳** |
| ارجاع استاتیک شکسته | — | **۰ از ۱۳۹** |

## ۱۱-۴. باقی‌مانده: ۱۷ قالب با Jinja داخل JS

| خط | قالب |
|---:|---|
| ۹۵۰ | `ai/assistant/index.html` |
| ۸۰۲ | `dashboard/index.html` |
| ۷۷۹ | `reports/department_expert_documents.html` |
| ۴۱۸ | `reports/area.html` |
| ۳۹۷ | `workflow/note_view.html` |
| ۳۶۹ | `notifications/notif_dropdown.html` |
| ۳۵۹ | `components/header.html` |
| ۳۴۳ | `reports/department_documents.html` |
| ۳۹۶ | `reports/{status,department,area_departments}.html` |
| ۲۲۹+۲۲۱ | `notifications/{list,expert_detail}.html` |
| ۱۶۵ | `{workflow/_note_modal, auth/logout, contractors/view, reports/department_performance}.html` |

این‌ها با `{{ }}` کد JS می‌سازند. الگوی مهاجرت در `docs/DESIGN.md` بخش ۵ آمده است.

## ۱۱-۵. تست‌های جدید معماری

| تست | چه چیزی را تضمین می‌کند |
|---|---|
| `test_static_references_resolve` | هیچ ارجاع CSS/JS به فایل ناموجود |
| `test_no_inline_page_styles` | استایل صفحه دوباره داخل قالب برنگردد |
| `test_css_is_linked_from_base` | ترتیب آبشاری core → base → app-ui |

**جمع تست‌ها: ۱۶ پاس.**

## ۱۱-۶. نکته‌ی بازبینی

محتوای CSS و JS **کلمه‌به‌کلمه** منتقل شد و جای منطقی بارگذاری حفظ شد؛ اما تغییر ترتیب واقعی در مرورگر را فقط چشم انسان می‌تواند تأیید کند. قبل از انتشار، این صفحه‌ها یک‌بار بازبینی شوند:

`/dashboard` · `/documents` · `/reports/area` · `/reports/status` · `/search` · `/projects` · `/panel/users` · `/profile` · `/assistant`

---

# ۱۲. مرحله ۴ — بخش هوش مصنوعی: تست، امنیت، دو باگ

## ۱۲-۱. وضعیت اولیه

بخش AI از نظر حجم کامل بود (۹ ماژول سرویس، ۸ فایل handler، ۳۲ intent، ۱۱ مسیر)،
اما **صفر تست** داشت. یعنی هیچ سپری برای تغییرات آینده نداشت.

## ۱۲-۲. تست‌ها — `tests/test_ai.py` (۲۷ تست)

| گروه | تست‌ها |
|---|---|
| ثبت intentها | تعداد، ساختار `info()`، رد ثبت تکراری |
| تشخیص | سه intent پرکاربرد، سؤال نامفهوم، پنهان‌بودن intent ادمین |
| ساختار پاسخ | شکل `Formatters.response`، پاسخ استاندارد، پاسخ نامفهوم، سؤال خالی، برش سؤال بلند |
| محدودیت نرخ | قفل بعد از سقف، جدابودن شمارنده‌ی هر کاربر |
| HTTP | `ping` عمومی، ریدایرکت صفحه، ۴۰۱ برای API بدون لاگین، پاسخ JSON، رد سؤال خالی |
| امنیت | نبود کلید در سورس، خواندن از env، عدم افشای کلید در `describe()` |
| رگرسیون | خراب‌نشدن «تکمیل»، وجود intent راهنما |

LLM در fixture به‌صورت خودکار خاموش می‌شود تا هیچ تستی به شبکه درخواست نزند.

## ۱۲-۳. باگ ۱ — `NLU.clean` کلمه‌ها را می‌شکست

```python
# قبل
for w in sorted(cls.CONDITIONAL_FILLERS, key=len, reverse=True):
    text = text.replace(w, " ")       # بدون مرز کلمه
```

`CONDITIONAL_FILLERS` شامل «کمی» است و «تکمیل» هم شامل «کمی» است:

```
"چند سند تکمیل شده؟"  →  clean()  →  "چند سند ت ل شده"  →  intent: unknown
```

یعنی **intent شمارش اسناد تکمیل‌شده هرگز کار نمی‌کرد**. هر کلمه‌ای که «کمی»،
«یک» یا «یه» را در خود داشت (تکمیل، یکسان، یکی…) خراب می‌شد.

**اصلاح:** حذف با مرز کلمه (`NLU._strip_words`). چون `\b` برای فارسی کار
نمی‌کند، مرز با «فاصله یا ابتدا/انتهای رشته» تعریف شد.

## ۱۲-۴. باگ ۲ — «راهنما» حلقه بود

همه‌ی پاسخ‌های «نامفهوم» و «خالی» به کاربر پیشنهاد می‌دادند **«راهنما»**
بنویسد، ولی هیچ intentی این عبارت را نمی‌شناخت:

```
"راهنما"  →  unknown  →  پیشنهاد: راهنما  →  ...
```

**اصلاح:** `services/ai/handlers/help_handlers.py` با intent `help`
(اولویت ۹۹) که همان `_help_response` موجود را برمی‌گرداند. اکنون ۳۳ intent.

## ۱۲-۵. امنیت — کلیدهای API از سورس حذف شدند

| قبل | بعد |
|---|---|
| `AVALAI_API_KEY = "aa-Dl7Ex..."` در `llm_config.py` | فقط `os.environ.get("AVALAI_API_KEY", "")` |
| `DEEPSEEK_API_KEY = "sk-9824..."` در `llm_config.py` | فقط از `.env` |
| هیچ `.env` وجود نداشت | `.env` + `.env.example` |
| `python-dotenv` نصب بود ولی استفاده نمی‌شد | `config.py` بارگذاری می‌کند |

مقادیر واقعی به `.env` منتقل شدند، پس برنامه بدون تغییر کار می‌کند.

## ۱۲-۶. اعتبارسنجی

| بررسی | نتیجه |
|---|---|
| تست‌های AI | **۲۷ پاس** |
| کل تست‌ها | **۴۳ پاس** (۸ دود + ۸ معماری + ۲۷ AI) |
| تشخیص ۱۳ سؤال نمونه | **۱۲ درست** (قبل از اصلاح: ۱۱) |
| intentها | ۳۲ → **۳۳** |
| کلید در سورس | **۰** |

**نقطه بازگشت:** `_backup/SSPE-ai-<timestamp>.zip`

---

# ۱۳. مرحله ۵ — دستیار: پوشش پروژه/پیمانکار و احوال‌پرسی

## ۱۳-۱. تشخیص اولیه

پرسش: «آیا دستیار می‌تواند خودش به سؤالات پاسخ دهد یا باید کد نوشت؟»

بررسی نشان داد **باید کد نوشت**، به دو دلیل:

| لایه | وضعیت قبل |
|---|---|
| ابزارهای LLM | ۹ ابزار — همه درباره‌ی **اسناد**. هیچ ابزاری برای پروژه، پیمانکار یا ناحیه نبود |
| intentهای rule-based | ۳۳ intent — بدون احوال‌پرسی، بدون پروژه |

یعنی LLM بدون ابزار به داده‌ی پروژه‌ها دسترسی ندارد (و اگر بسازد، توهم است)،
و مسیر آفلاین هم «سلام» را نمی‌فهمید.

## ۱۳-۲. آنچه اضافه شد

### الف) `services/ai/handlers/social_handlers.py` — ۵ intent

| intent | نمونه |
|---|---|
| `greeting` | سلام، صبح بخیر، درود |
| `how_are_you` | چطوری، چه خبر |
| `thanks` | ممنون، مرسی، سپاس |
| `goodbye` | خداحافظ، فعلاً |
| `who_are_you` | تو کی هستی |

پاسخ‌ها با نام کوچک کاربر و سلام متناسب با ساعت روز شخصی‌سازی می‌شوند:
`صبح بخیر` تا ۱۲، `وقت بخیر` تا ۱۷، `عصر بخیر` تا ۲۱، سپس `شب بخیر`.

**نکته‌ی حیاتی:** الگوها با `^` و `$` لنگر انداخته‌اند. بدون این کار:

```
«سلام چند سند تکمیل شده؟»  →  greeting  ❌  (سؤال واقعی بلعیده می‌شود)
«سلام چند سند تکمیل شده؟»  →  count_completed  ✅
```

### ب) `services/ai/handlers/project_handlers.py` — ۶ intent

| intent | نمونه |
|---|---|
| `count_projects` | چند پروژه داریم؟ |
| `list_projects` | لیست پروژه‌ها |
| `project_details` | وضعیت پروژه خط ۲ |
| `count_contractors` | چند پیمانکار داریم |
| `list_contractors` | لیست پیمانکارها |
| `list_areas` | نواحی |

این handlerها همان repositoryهای موجود را صدا می‌زنند
(`database/repositories/projects.py` و …) — نه SQL تازه.

### ج) `services/ai/llm_tools.py` — ۶ ابزار جدید (۹ → ۱۵)

| ابزار | کار |
|---|---|
| `list_projects` | لیست پروژه با فیلتر وضعیت |
| `get_projects_summary` | آمار پروژه‌ها |
| `search_projects` | جستجو با نام/کد |
| `list_contractors` | لیست/جستجوی پیمانکار |
| `list_areas` | لیست نواحی |
| `get_contractor_documents` | اسناد یک پیمانکار |

## ۱۳-۳. تست‌های اضافه‌شده (۲۷ → ۴۸)

- تشخیص ۱۱ intent جدید (پارامتری)
- لنگرگذاری احوال‌پرسی (سؤال واقعی بلعیده نشود)
- «وضعیت پروژه X» → `project_details` نه `count_projects`
- پاسخ صمیمانه برای سلام/تشکر/خداحافظی
- پوشش ابزارهای LLM و اجرای واقعی آن‌ها

## ۱۳-۴. تعارض امتیاز که پیدا و رفع شد

`detect()` بر اساس «اولویت × اطمینان» انتخاب می‌کند، نه فقط اولویت:

```
count_projects   : 88 × 0.90 = 79.2   ← «وضعیت پروژه تست» را می‌برد
project_details  : 89 × 0.85 = 75.65
```

اصلاح: الگوی شمارش با `$` لنگر انداخت (تا وقتی نام پروژه دنبالش است فعال نشود)
و اولویت `project_details` به ۹۳ رسید.

## ۱۳-۵. اعتبارسنجی

| بررسی | نتیجه |
|---|---|
| intentها | ۳۳ → **۴۴** |
| ابزارهای LLM | ۹ → **۱۵** |
| تست‌های AI | ۲۷ → **۴۸** |
| کل تست‌ها | ۴۳ → **۶۴ پاس** |
| تشخیص ۱۲ پیام نمونه | **۱۲ درست** |
| داده‌ی واقعی برگشتی | ۱۰۴ پروژه · ۴۲ پیمانکار · ۱۲ ناحیه |
| مسیرها | ۱۵۷ (بدون تغییر) |

**نقطه بازگشت:** `_backup/SSPE-assistant-<timestamp>.zip`

---

# ۱۴. مرحله ۶ — سؤال با فیلترهای پیشرفته + خروجی اکسل

## ۱۴-۱. هدف

کاربر بتواند به زبان طبیعی سؤال فیلترشده بپرسد و خروجی اکسل بگیرد:

> «اسناد پیمانکار آبسان پالایش در ناحیه سیالات با وضعیت تکمیل از ماه گذشته»
> «خروجی اکسل اسناد پیمانکار MMTE»

## ۱۴-۲. اجزای ساخته‌شده

| فایل | نقش |
|---|---|
| `services/search/search_excel_service.py` | ساخت فایل اکسل از رکوردها (استایل، RTL، عرض ستون‌ها) |
| `services/search/search_filters.py` | نگاشت نام پارامترها + ساخت URL دانلود + توضیح انسانی فیلترها |
| `services/ai/search_filter_builder.py` | تبدیل جمله‌ی فارسی به فیلتر (وضعیت، موجودیت، بازه تاریخ، متن آزاد) |
| `services/ai/handlers/filter_handlers.py` | intentهای `filtered_search` و `filtered_export` |
| `routes/ai/export_routes.py` | مسیر `/assistant/export/search` برای دانلود xlsx |
| `services/ai/llm_tools_extra.py` | ۸ ابزار LLM (پروژه/پیمانکار/ناحیه/جستجو/اکسل) |

## ۱۴-۳. معماری

```
سؤال → SearchFilterBuilder → search_documents() → FilterHandlers → پاسخ + لینک
                                                        ↓
                              /assistant/export/search → build_search_excel() → xlsx
```

`search_documents()` **منبع واحد حقیقت** است؛ هیچ کوئری فیلتر دستی نوشته نشد.

## ۱۴-۴. نکته‌ی داده‌ای مهم

تاریخ‌ها در دیتابیس **میلادی** (`YYYY/MM/DD`) ذخیره شده‌اند ولی کاربر شمسی
می‌نویسد. `SearchFilterBuilder` تبدیل را انجام می‌دهد:

| عبارت کاربر | بازه‌ی تولیدشده |
|---|---|
| ماه گذشته | `2026/09/23` تا `2026/10/22` (مهر ۱۴۰۵) |
| امسال | `2026/03/21` تا امروز |
| ۱۴۰۵/۰۱/۰۱ | `2026/03/21` |

## ۱۴-۵. ⚠️ حادثه‌ی انکودینگ (مهم)

در جریان این مرحله، `services/ai/llm_tools.py` **بی‌صدا خراب شد**:

```python
# قبل
"description": "شمارش اسناد بر اساس وضعیت"
# بعد از نوشتن با PowerShell
"description": "ط´ظ…ط§ط±ط´ ط§ط³ظ†ط§ط¯ ط¨ط± ط§ط³ط§ط³ ظˆط¶ط¹غŒطھ"
```

**علت:** `Get-Content -Raw` در PowerShell 5.1 فایل را با کدپیج سیستم (cp1256)
می‌خواند و `Set-Content -Encoding UTF8` نتیجه را دوباره می‌نویسد → UTF-8 فارسی
به mojibake تبدیل می‌شود، **بدون هیچ خطا یا هشداری**.

**تأثیر:** توضیحات ابزارهای LLM خراب شد؛ در نتیجه مدل نمی‌توانست ابزار درست را
انتخاب کند (کار می‌کرد، ولی با توضیح بی‌معنی).

**بازیابی:** فایل از پشتیبان سالم `SSPE-display-refactor-20261031-1555.zip`
بازگردانده شد. (پشتیبان بعدی هم چون بعد از خرابی گرفته شده بود، خراب بود.)

**پیشگیری:** تست `test_source_files_are_not_mojibake` اضافه شد که الگوهای
mojibake را در همه‌ی فایل‌های سورس تشخیص می‌دهد.

## ۱۴-۶. تغییر معماری ابزارهای LLM

به‌جای ادامه‌دادن به فایل ۵۰۰ خطی `llm_tools.py`، ابزارهای جدید در
`llm_tools_extra.py` قرار گرفتند و با Mixin ترکیب شدند:

```python
class LLMTools(ExtraToolsMixin):
    ...
    tools.extend(EXTRA_TOOL_SCHEMAS)
```

ابزارهای LLM: **۹ → ۱۷**

## ۱۴-۷. اعتبارسنجی

| بررسی | نتیجه |
|---|---|
| تست‌ها | **۸۴ پاس** (۲۱ تست جدید برای فیلتر و اکسل) |
| مسیرها | ۱۵۷ → **۱۵۸** (`/assistant/export/search`) |
| ابزارهای LLM | ۹ → **۱۷** |
| اکسل خروجی | ۳۰۱ ردیف، ۱۷ ستون، RTL، هدر فارسی |
| بدون لاگین | ۳۰۲ (ریدایرکت) |
| بدون نتیجه | 404 با کد `no_results` |
| استخراج فیلتر | پیمانکار، پروژه، ناحیه، وضعیت، بازه نسبی و شمسی — همه درست |

**نقطه بازگشت:** `_backup/SSPE-search-export-<timestamp>.zip`

---

# ۱۵. مرحله ۷ — سخت‌سازی امنیت و درست‌کردن داده‌های دستیار

## ۱۵-۱. مسئله

سه ایراد در بازبینی امنیتی تأیید شد:

| # | مشکل | شواهد |
|---|---|---|
| ۱ | رمزها با **SHA-256 بدون نمک** ذخیره می‌شدند | `database/users.py` — دو کاربر با رمز یکسان، هش یکسان |
| ۲ | **CSRF** روی اکثر POSTها وجود نداشت | ساخت دپارتمان با یک POST بدون توکن، پاسخ ۳۰۲ |
| ۳ | جدول‌های `assistant_logs` و `assistant_feedback` ساخته نمی‌شدند | `log_query` بی‌صدا شکست می‌خورد؛ آمار همیشه صفر؛ بازخورد «ثبت شد» بدون ذخیره |

## ۱۵-۲. تغییرات

| فایل | تغییر |
|---|---|
| `security/passwords.py` | **جدید** — هش `scrypt` + بررسی هش قدیمی + `needs_rehash` |
| `database/users.py` | ورود با بررسی رمز (به‌جای مقایسه در SQL) + **ارتقای خودکار هش** + یکسان‌سازی زمان پاسخ |
| `services/profile/profile_service.py` | حذف منطق تکراری هش؛ استفاده از ماژول مشترک |
| `app.py` | بررسی `Origin`/`Referer` برای متدهای ناامن + هدرهای امنیتی + هشدار SECRET_KEY |
| `config.py` | کوکی `HttpOnly`/`SameSite=Lax`/`Secure` اختیاری، عمر ۱۲ ساعته، DEBUG پیش‌فرض خاموش |
| `run.py` | پیش‌فرض `127.0.0.1` بدون debug؛ قابل تنظیم با `SSPE_HOST`/`SSPE_PORT` |
| `routes/auth/auth_routes.py` | `session.permanent = True` |
| `database/tables/assistant_logs.py` · `assistant_feedback.py` | **جدید** — DDL + ایندکس (تعداد جداول ۱۸ → ۲۰) |
| `routes/ai/assistant.py` | بازخورد دیگر دروغ نمی‌گوید؛ خطای لاگ ثبت می‌شود |
| `services/users/avatar_service.py` | OpenCV اختیاری شد؛ برش مرکزی با Pillow به‌عنوان جایگزین |
| `requirements.txt` · `pyproject.toml` | افزودن `Flask-WTF`، `WTForms`، `jdatetime`، `Pillow`؛ حذف وابستگی‌های بلااستفاده |
| `.env.example` · `README.md` | مستندسازی متغیرهای جدید و رفتار امنیتی |
| `tests/test_security.py` | **جدید** — ۱۵ تست |

## ۱۵-۳. مهاجرت رمز بدون قطعی

```
رمز قدیمی (SHA-256) → ورود موفق → بازنویسی با scrypt → ورودهای بعدی
```

رمزهای قدیمی همچنان پذیرفته می‌شوند؛ هیچ کاربری قفل نمی‌شود و نیازی به
اسکریپت مهاجرت جداگانه نیست.

## ۱۵-۴. اعتبارسنجی

| بررسی | نتیجه |
|---|---|
| تست‌ها | **۹۹ پاس** (۸۴ قبلی + ۱۵ جدید) |
| ورود با `admin/admin123` | ۳۰۲ → هش در دیتابیس به `scrypt:` ارتقا یافت |
| POST هم‌مبدأ | ۳۰۲ (پذیرفته) |
| POST با `Origin: https://evil.example` | **۴۰۳** |
| کوکی نشست | `HttpOnly; SameSite=Lax` + انقضای ۱۲ ساعته |
| جدول‌های دستیار | ساخته شدند؛ `stats` و `feedback` واقعی شدند |
| صفحات کلیدی | `/dashboard` `/documents` `/search` `/projects` `/assistant` `/reports/area` `/profile` همه ۲۰۰ |

## ۱۵-۵. باقی‌مانده (مرحله بعد)

1. **توکن CSRF فرم‌های دستی**: بررسی Origin جلوی CSRF کلاسیک را می‌گیرد، ولی
   لایه‌ی دوم (توکن) برای ۳۳ فرم بدون `hidden_tag` هنوز اضافه نشده است.
2. **XSS در خروجی LLM**: `formatBotText` پاسخ را خام در `innerHTML` می‌گذارد؛
   پاسخ handlerها escape می‌شود ولی خروجی مدل نه.
3. **صفحه‌بندی `/documents/`**: دو بار خواندن کل ۸٬۷۸۲ رکورد و آمار در پایتون.
4. **کنترل نسخه**: روی این ماشین `git` نصب نیست؛ مخزن هنوز ساخته نشده است.
5. **رمز پیش‌فرض کاربران اکسل** (`123456`) باید به رمز موقت تصادفی تغییر کند.

---

# ۱۶. مرحله ۸ — لایه دوم CSRF، امن‌سازی خروجی AI و بازسازی صفحه اسناد

## ۱۶-۱. سه مسئله‌ای که در بازبینی تازه پیدا شد

| # | مسئله | شواهد |
|---|---|---|
| ۱ | قالب صفحه اسناد **صفر بایت** بود | `/documents/` با کد ۲۰۰ اما بدنه‌ی خالی؛ فایل در همه‌ی پشتیبان‌ها هم خالی بود |
| ۲ | فیلتر سال اسناد **هیچ نتیجه‌ای نداشت** | `get_jalali_year("2026/04/25")` عدد `2026` برمی‌گرداند؛ فیلتر سال ۱۴۰۵ بازه‌ی ۲۶۴۷ را می‌ساخت |
| ۳ | خروجی مدل خام در `innerHTML` | `formatBotText` هیچ پاک‌سازی‌ای نداشت |

## ۱۶-۲. تغییرات

| فایل | تغییر |
|---|---|
| `app.py` | فعال‌سازی `CSRFProtect` + هندلر `CSRFError` (JSON/HTML) + فیلتر `fa_digits` |
| `templates/*` | توکن CSRF به **۳۳ فرم** (۲۶ فرم دستی + ۷ فرم WTForms) و توکن به فرم داینامیک گردش‌کار |
| `templates/base.html` | متا تگ توکن + پچ خودکار `fetch`/`XHR` برای هدر `X-CSRFToken` |
| `config.py` | `WTF_CSRF_TIME_LIMIT=None` (اعتبار تا پایان نشست) |
| `services/ai/sanitizer.py` | **جدید** — پاک‌سازی HTML با allowlist (تگ/صفت/`style`/`href`) |
| `services/ai/assistant_service.py` | خروجی LLM پیش از نمایش sanitize می‌شود |
| `helpers/date_helper.py` | اصلاح `get_jalali_year` برای ورودی میلادی |
| `services/documents/document_service.py` | `get_page()` و `get_statistics()` با SQL؛ `get_available_years()` فقط ستون تاریخ را می‌خواند |
| `routes/documents/documents_routes.py` | صفحه‌بندی + آمار SQL |
| `templates/documents/index.html` | **بازسازی کامل** (نوار ابزار، سه پنل آمار، کارت اسناد، صفحه‌بندی) |
| `static/css/pages/documents.css` | استایل صفحه‌بندی، لینک کارت و لینک جستجو |
| `tests/test_documents_page.py` · `tests/test_sanitizer.py` | **جدید** — ۳۷ تست (CSRF + sanitizer + صفحه اسناد) |

## ۱۶-۳. کارایی صفحه اسناد

| شاخص | قبل | بعد |
|---|---|---|
| پاسخ `/documents/` | ۳۷۰ms (بدنه خالی) | **۱۳۸ms سرد / ۵۵ms گرم** |
| بارگذاری رکورد | دو بار کل ۸٬۷۸۲ سند با ۵ join | یک کوئری `COUNT` + یک صفحه ۲۴ ردیفی |
| آمار | حلقه پایتون روی ۸٬۷۸۲ رکورد | سه کوئری `GROUP BY` |
| حجم پاسخ | ۰ KB | ۱۲۹ KB (۲۴ کارت) |

## ۱۶-۴. اعتبارسنجی

| بررسی | نتیجه |
|---|---|
| تست‌ها | **۱۳۶ پاس** (۹۹ مرحله قبل + ۳۷ جدید) |
| POST فرم بدون توکن | ۴۰۰ |
| POST فرم با توکن | ۳۰۲ |
| `POST /assistant/ask` بدون هدر | ۴۰۰ (`csrf_error`) |
| `POST /assistant/ask` با هدر | ۲۰۰ |
| فیلتر سال | ۱۴۰۵ → ۱٬۶۶۷ · ۱۴۰۴ → ۷٬۱۱۲ · ۱۴۰۳ → ۳ (جمع = ۸٬۷۸۲) |
| جمع آمار با جمع صفحات | برابر در هر سه سال |
| صفحه ۱ و ۲ | رکوردهای متفاوت، ۲۴ کارت در هر صفحه |
| صفحه خارج از بازه | به آخرین صفحه محدود می‌شود |

## ۱۶-۵. باقی‌مانده

1. **کنترل نسخه**: `git` روی این ماشین نصب نیست.
2. **رمز موقت تصادفی** برای کاربران ورودی اکسل (به‌جای `123456`).
3. **CSP**: با وجود پاک‌سازی، هدر `Content-Security-Policy` به‌دلیل اسکریپت‌های inline فعلاً قابل فعال‌سازی نیست.
4. **دو منبع حقیقت داده** (ستون متنی و FK پیمانکار/پروژه) و `PRAGMA foreign_keys=0`.
5. **حالت سراسری در حافظه** (محدودیت نرخ/تاریخچه) مانع اجرای چند worker است.

---

# ۱۷. مرحله ۹ — تقویم کاری و مهلت پاسخ بر اساس گروه سند

## ۱۷-۱. مسئله

`document_subgroups.days_review` («بازه بررسی») از قبل وجود داشت ولی هیچ‌جا در محاسبهٔ
مهلت استفاده نمی‌شد؛ مهلت‌ها دستی و تقویمی بودند و تعطیلات در آن‌ها لحاظ نمی‌شد.

## ۱۷-۲. آنچه اضافه شد

| فایل | تغییر |
|---|---|
| `database/tables/calendar_holidays.py` | **جدید** — تعطیلات با تاریخ میلادی، معادل شمسی و سال |
| `database/repositories/holidays.py` | **جدید** — CRUD تعطیلات (لایهٔ داده) |
| `database/repositories/document_groups.py` | **جدید** — خوانش مهلت گروه/زیرگروه برای SLA |
| `database/tables/document_groups.py` | ستون `days_review` + `migrate()` |
| `database/tables/documents.py` | ستون‌های `sla_days`, `sla_source`, `response_due_date` |
| `database/seeds/holidays.py` | **جدید** — ۱۰ تعطیل رسمی ثابت × ۳ سال (۳۰ رکورد) |
| `services/calendar/working_days.py` | **جدید** — روز کاری، جمع/تفریق، شمارش، وضعیت ماه |
| `services/calendar/holiday_service.py` | **جدید** — منطق تعطیلات روی repository |
| `services/documents/sla.py` | **جدید** — اولویت زیرگروه → گروه → پیش‌فرض + ذخیره روی سند |
| `forms/calendar/forms.py` | **جدید** — فرم WTForms با اعتبارسنجی تاریخ شمسی |
| `routes/calendar/` | **جدید** — صفحهٔ تقویم، افزودن/حذف تعطیلی |
| `templates/calendar/index.html` + `static/css/pages/calendar.css` | **جدید** — ماه شمسی، آمار، ماشین‌حساب، کلیک روی روز |
| `templates/components/sidebar.html` | آیتم «تقویم کاری» در منوی اصلی (فقط admin/manager) با حالت active |
| `tests/test_calendar.py` | **جدید** — ۳۳ تست |

قاعدهٔ محاسبه: **سررسید = تاریخ شروع + N روز کاری**؛ پنجشنبه و جمعه (قابل تغییر با
`SSPE_WEEKEND_DAYS`)، تعطیلات رسمی و تعطیلات سازمانی کسر می‌شوند. مهلت مؤثر:
`زیرگروه.days_review` → `گروه.days_review` → `SSPE_DEFAULT_SLA_DAYS` (۷).

نمایش تقویم بر اساس **روز شمسی** است (قبلاً اشتباهاً شمارهٔ روز میلادی نمایش داده می‌شد) و با
کلیک روی هر روز، وضعیت تعطیل/غیرتعطیل آن تغییر می‌کند (POST به `/calendar/toggle`).

## ۱۷-۳. اعتبارسنجی

| بررسی | نتیجه |
|---|---|
| تست‌ها | **۱۶۹ پاس** (۱۳۶ + ۳۳ جدید) |
| تعطیلات seedشده | ۳۰ رکورد (۱۴۰۴، ۱۴۰۵، ۱۴۰۶) |
| صفحهٔ `/calendar` | ۲۰۰؛ فروردین ۱۴۰۵: ۳۱ روز شمسی ۱ تا ۳۱، ۶ تعطیل، ۷ آخر هفته |
| کلیک روی روز | ۳۱ فرم toggle؛ تعطیل→غیرتعطیل و برعکس با ریدایرکت به همان ماه |
| ماشین‌حساب واقعی | زیرگروه «لایحه ضرر و زیان» با ۲۰ روز کاری از ۱۴۰۵/۰۱/۰۱ → سررسید **۱۴۰۵/۰۲/۰۲** |
| منبع مهلت | «زیرگروه سند» به‌درستی نمایش داده شد |
| افزودن تعطیلی با CSRF | ۳۰۲ و در فهرست سال ظاهر شد |
| جدول‌ها / مسیرها | ۲۱ جدول، ۱۹ Blueprint |

## ۱۷-۴. باقی‌مانده

- تعطیلات قمری هر سال دستی ثبت شود (یا ورودی گروهی در فاز بعد).
- نمایش «روزهای کاری باقی‌مانده» در کارتابل/کارت سند پس از ساخت ارجاع‌ها.
- ستون `days_review` گروه هنوز فرم ویرایش ندارد؛ مقدارش فعلاً از seed/دیتابیس تنظیم می‌شود.

### قدم ۱۱ — سرویس ارجاع (✅ انجام شد)

فایل: `services/documents/assignment_service.py` (جدید)

توابع:
- `route_document()` — ارجاع به یک یا چند نفر (due_date محاسبه‌شده)
- `mark_read()` — رسید خواندن
- `accept()` / `start()` / `complete()` / `return_to_sender()` / `cancel()`
- `get_inbox()` — کوئری کارتابل با تب‌ها (active / unread / overdue / waiting / done)
- `get_document_assignments()` — درخت ارجاع‌ها
- `AssignmentStatus` / `AssignmentAction` — ثابت‌ها

تست موفق: ثبت سند → ارجاع → کارتابل → خواندن → پذیرش → انجام → تایم‌لاین.