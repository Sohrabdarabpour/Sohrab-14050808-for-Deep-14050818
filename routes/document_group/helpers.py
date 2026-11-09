# routes/document_group/helpers.py
import json

def parse_sort_orders(raw):
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return {int(k): int(v) for k, v in data.items()}
    except (ValueError, TypeError, AttributeError):
        return {}