class ContractTypeForm:
    """
    فرم نوع قرارداد
    ساختار داده‌ای فیلدها برای رندر خودکار در قالب
    """

    FIELDS = [
        {
            "name": "title",
            "label": "عنوان نوع قرارداد",
            "type": "text",
            "required": True,
            "col": 8,
            "icon": "fa-file-contract",
            "placeholder": "مثال: EPC (طراحی + تأمین + اجرا)",
        },
        {
            "name": "code",
            "label": "کد",
            "type": "text",
            "col": 4,
            "icon": "fa-barcode",
            "placeholder": "EPC",
            "ltr": True,
        },
        {
            "name": "color",
            "label": "رنگ",
            "type": "color",
            "col": 6,
            "icon": "fa-palette",
            "default": "#1b698b",
        },
        {
            "name": "sort_order",
            "label": "ترتیب نمایش",
            "type": "number",
            "col": 6,
            "icon": "fa-sort-numeric-down",
            "default": 0,
        },
        {
            "name": "description",
            "label": "توضیحات",
            "type": "textarea",
            "col": 12,
            "icon": "fa-align-right",
            "rows": 3,
        },
        {
            "name": "is_active",
            "label": "فعال",
            "type": "checkbox",
            "default": 1,
            "col": 12,
            "icon": "fa-toggle-on",
            "description": "در صورت فعال بودن، در فرم‌های پروژه نمایش داده می‌شود",
        },
    ]

    @classmethod
    def get_fields(cls):
        return cls.FIELDS

    @classmethod
    def empty_data(cls):
        return {f["name"]: f.get("default", "") for f in cls.FIELDS}

    @classmethod
    def from_model(cls, model):
        return {f["name"]: model.get(f["name"], "") for f in cls.FIELDS}