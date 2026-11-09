class ProjectForm:
    """فرم پروژه — ساختار بخش‌بندی‌شده"""

    SECTIONS = [
        # ==========================================================
        # بخش ۱: اطلاعات اصلی
        # ==========================================================
        {
            "title": "اطلاعات اصلی",
            "icon": "fa-diagram-project",
            "fields": [
                {"name": "name", "label": "نام پروژه", "type": "text",
                 "required": True, "col": 12, "icon": "fa-diagram-project",
                 "placeholder": "مثال: پروژه سد کرخه"},
                {"name": "code", "label": "کد پروژه", "type": "text",
                 "col": 6, "icon": "fa-barcode",
                 "placeholder": "PRJ-001", "ltr": True},
                {"name": "project_number", "label": "شماره پروژه", "type": "text",
                 "col": 6, "icon": "fa-hashtag", "placeholder": "1403/125"},
                {"name": "description", "label": "توضیحات", "type": "textarea",
                 "col": 12, "icon": "fa-align-right", "rows": 2},
            ],
        },

        # ==========================================================
        # بخش ۲: ارتباطات
        # ==========================================================
        {
            "title": "ارتباطات پروژه",
            "icon": "fa-link",
            "fields": [
                {"name": "contractor_id", "label": "پیمانکار", "type": "select",
                 "col": 6, "icon": "fa-helmet-safety",
                 "source": "contractors", "empty_label": "— انتخاب کنید —"},
                {"name": "contract_type_id", "label": "نوع قرارداد", "type": "select",
                 "col": 6, "icon": "fa-file-contract",
                 "source": "contract_types", "empty_label": "— انتخاب کنید —"},
                {"name": "area_id", "label": "ناحیه", "type": "select",
                 "col": 6, "icon": "fa-map-location-dot",
                 "source": "areas", "empty_label": "— انتخاب کنید —"},
            ],
        },

        # ==========================================================
        # بخش ۳: اطلاعات قرارداد (ریالی + ارزی)
        # ==========================================================
        {
            "title": "اطلاعات قرارداد",
            "icon": "fa-file-signature",
            "fields": [
                # ----- ریالی -----
                {"name": "contract_number", "label": "شماره قرارداد (ریالی)",
                 "type": "text", "col": 6, "icon": "fa-hashtag",
                 "ltr": True, "placeholder": "1403/125"},
                {"name": "contract_amount", "label": "مبلغ قرارداد (ریال)",
                 "type": "number", "col": 6, "icon": "fa-money-bill-wave",
                 "ltr": True, "placeholder": "50000000000"},

                # ----- ارزی -----
                {"name": "contract_number_foreign", "label": "شماره قرارداد (ارزی)",
                 "type": "text", "col": 4, "icon": "fa-passport",
                 "ltr": True, "placeholder": "F-2024/001"},
                {"name": "contract_amount_foreign", "label": "مبلغ قرارداد (ارزی)",
                 "type": "number", "col": 4, "icon": "fa-dollar-sign",
                 "ltr": True, "placeholder": "1000000"},
                {"name": "currency", "label": "واحد پول", "type": "select",
                 "col": 4, "icon": "fa-coins",
                 "options": [
                     {"value": "USD", "label": "دلار آمریکا (USD)"},
                     {"value": "EUR", "label": "یورو (EUR)"},
                     {"value": "GBP", "label": "پوند (GBP)"},
                     {"value": "AED", "label": "درهم امارات (AED)"},
                     {"value": "CNY", "label": "یوان چین (CNY)"},
                     {"value": "JPY", "label": "ین ژاپن (JPY)"},
                     {"value": "RUB", "label": "روبل روسیه (RUB)"},
                     {"value": "TRY", "label": "لیر ترکیه (TRY)"},
                     {"value": "OTHER", "label": "سایر"},
                 ]},

                # ----- تاریخ‌ها -----
                {"name": "contract_start_date", "label": "تاریخ شروع قرارداد",
                 "type": "text", "col": 6, "icon": "fa-calendar-plus",
                 "placeholder": "1403/01/01"},
                {"name": "contract_end_date", "label": "تاریخ پایان قرارداد",
                 "type": "text", "col": 6, "icon": "fa-calendar-check",
                 "placeholder": "1404/01/01"},

                # ----- بودجه -----
                {"name": "budget", "label": "بودجه (ریال)",
                 "type": "number", "col": 12, "icon": "fa-sack-dollar",
                 "ltr": True, "placeholder": "60000000000"},
            ],
        },

        # ==========================================================
        # بخش ۴: زمان‌بندی
        # ==========================================================
        {
            "title": "زمان‌بندی پروژه",
            "icon": "fa-clock",
            "fields": [
                {"name": "start_date", "label": "تاریخ شروع پروژه",
                 "type": "text", "col": 6, "icon": "fa-calendar-plus",
                 "placeholder": "1403/01/01"},
                {"name": "planned_end_date", "label": "پایان برنامه‌ای",
                 "type": "text", "col": 6, "icon": "fa-calendar-check",
                 "placeholder": "1405/01/01"},
                {"name": "actual_end_date", "label": "پایان واقعی",
                 "type": "text", "col": 6, "icon": "fa-flag-checkered",
                 "placeholder": "1405/01/15"},
                {"name": "duration_days", "label": "مدت (روز)",
                 "type": "number", "col": 6, "icon": "fa-stopwatch",
                 "ltr": True},
            ],
        },

        # ==========================================================
        # بخش ۵: وضعیت و پیشرفت‌ها
        # ==========================================================
        {
            "title": "وضعیت و پیشرفت",
            "icon": "fa-signal",
            "fields": [
                {"name": "status", "label": "وضعیت", "type": "select",
                 "col": 4, "icon": "fa-circle-half-stroke",
                 "options": [
                     {"value": "active",    "label": "فعال"},
                     {"value": "completed", "label": "تکمیل شده"},
                     {"value": "paused",    "label": "متوقف شده"},
                     {"value": "cancelled", "label": "لغو شده"},
                     {"value": "pending",   "label": "در انتظار شروع"},
                 ]},
                {"name": "priority", "label": "اولویت", "type": "select",
                 "col": 4, "icon": "fa-flag",
                 "options": [
                     {"value": "low",      "label": "کم"},
                     {"value": "medium",   "label": "متوسط"},
                     {"value": "high",     "label": "بالا"},
                     {"value": "critical", "label": "بحرانی"},
                 ]},
                {"name": "progress_percent", "label": "پیشرفت کلی (٪)",
                 "type": "number", "col": 4, "icon": "fa-percent",
                 "min": 0, "max": 100, "ltr": True},

                # ★ پیشرفت‌های تفکیکی
                {"name": "physical_progress", "label": "پیشرفت فیزیکی (٪)",
                 "type": "number", "col": 3, "icon": "fa-trowel-bricks",
                 "min": 0, "max": 100, "ltr": True},
                {"name": "time_progress", "label": "پیشرفت برنامه‌ای (٪)",
                 "type": "number", "col": 3, "icon": "fa-clock",
                 "min": 0, "max": 100, "ltr": True},
                {"name": "financial_progress_rial", "label": "پیشرفت مالی ریالی (٪)",
                 "type": "number", "col": 3, "icon": "fa-money-bill-1-wave",
                 "min": 0, "max": 100, "ltr": True},
                {"name": "financial_progress_foreign", "label": "پیشرفت مالی ارزی (٪)",
                 "type": "number", "col": 3, "icon": "fa-dollar-sign",
                 "min": 0, "max": 100, "ltr": True},
            ],
        },

        # ==========================================================
        # بخش ۶: مکان
        # ==========================================================
        {
            "title": "موقعیت مکانی",
            "icon": "fa-map-location-dot",
            "fields": [
                {"name": "province", "label": "استان", "type": "text",
                 "col": 6, "icon": "fa-map"},
                {"name": "city", "label": "شهر", "type": "text",
                 "col": 6, "icon": "fa-city"},
                {"name": "location", "label": "موقعیت / آدرس", "type": "text",
                 "col": 12, "icon": "fa-location-dot"},
            ],
        },

        # ==========================================================
        # بخش ۷: یادداشت و وضعیت نهایی
        # ==========================================================
        {
            "title": "یادداشت و وضعیت",
            "icon": "fa-comment-dots",
            "fields": [
                {"name": "notes", "label": "یادداشت‌ها", "type": "textarea",
                 "col": 12, "icon": "fa-note-sticky", "rows": 3},
                {"name": "is_active", "label": "پروژه فعال", "type": "checkbox",
                 "default": 1, "col": 12, "icon": "fa-toggle-on",
                 "description": "در صورت فعال بودن، پروژه در لیست‌ها نمایش داده می‌شود"},
            ],
        },
    ]

    @classmethod
    def get_sections(cls):
        return cls.SECTIONS

    @classmethod
    def get_all_fields(cls):
        fields = []
        for section in cls.SECTIONS:
            for field in section["fields"]:
                fields.append(field)
        return fields

    @classmethod
    def empty_data(cls):
        return {f["name"]: f.get("default", "") for f in cls.get_all_fields()}

    @classmethod
    def from_model(cls, model):
        return {f["name"]: model.get(f["name"], "") for f in cls.get_all_fields()}