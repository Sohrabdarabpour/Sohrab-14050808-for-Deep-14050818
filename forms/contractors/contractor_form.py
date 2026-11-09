class ContractorForm:
    FIELDS = [
        {"name": "name", "label": "نام پیمانکار", "type": "text",
         "required": True, "col": 12, "icon": "fa-building"},

        {"name": "code", "label": "کد پیمانکار", "type": "text",
         "col": 6, "icon": "fa-barcode"},
        {"name": "national_id", "label": "کد ملی / شناسه ملی", "type": "text",
         "col": 6, "icon": "fa-id-card"},

        {"name": "economic_code", "label": "کد اقتصادی", "type": "text",
         "col": 6, "icon": "fa-hashtag"},
        {"name": "registration_number", "label": "شماره ثبت", "type": "text",
         "col": 6, "icon": "fa-file-signature"},

        {"name": "manager_name", "label": "نام مدیرعامل", "type": "text",
         "col": 6, "icon": "fa-user-tie"},
        {"name": "grade", "label": "رتبه / گرید", "type": "text",
         "col": 6, "icon": "fa-ranking-star"},

        {"name": "phone", "label": "تلفن", "type": "text",
         "col": 4, "icon": "fa-phone"},
        {"name": "mobile", "label": "موبایل", "type": "text",
         "col": 4, "icon": "fa-mobile-screen"},
        {"name": "email", "label": "ایمیل", "type": "email",
         "col": 4, "icon": "fa-envelope"},

        {"name": "province", "label": "استان", "type": "text",
         "col": 6, "icon": "fa-map"},
        {"name": "city", "label": "شهر", "type": "text",
         "col": 6, "icon": "fa-location-dot"},

        {"name": "postal_code", "label": "کد پستی", "type": "text",
         "col": 6, "icon": "fa-mail-bulk"},

        {"name": "address", "label": "آدرس", "type": "textarea",
         "col": 12, "icon": "fa-map-location-dot"},
        {"name": "description", "label": "توضیحات", "type": "textarea",
         "col": 12, "icon": "fa-comment-dots"},

        {"name": "is_active", "label": "فعال", "type": "checkbox",
         "default": 1, "col": 12, "icon": "fa-toggle-on"},
    ]

    @classmethod
    def get_fields(cls):
        return cls.FIELDS

    @classmethod
    def empty_data(cls):
        return {f["name"]: f.get("default", "") for f in cls.FIELDS}

    @classmethod
    def from_model(cls, contractor):
        return {
            f["name"]: contractor.get(f["name"], "")
            for f in cls.FIELDS
        }