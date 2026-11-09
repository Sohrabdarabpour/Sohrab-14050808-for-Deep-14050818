"""
Cache system with TTL
"""
import time
import hashlib
from functools import wraps


class Cache:
    """سیستم کش ساده با TTL"""

    _store = {}

    @classmethod
    def _key(cls, *args, **kwargs):
        raw = f"{args}|{sorted(kwargs.items())}"
        return hashlib.md5(raw.encode()).hexdigest()

    @classmethod
    def get(cls, key):
        item = cls._store.get(key)
        if not item:
            return None
        value, expires = item
        if time.time() > expires:
            del cls._store[key]
            return None
        return value

    @classmethod
    def set(cls, key, value, ttl=60):
        cls._store[key] = (value, time.time() + ttl)

    @classmethod
    def clear(cls):
        cls._store.clear()


def cached(ttl=60):
    """دکوراتور کش برای توابع"""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = Cache._key(fn.__name__, *args, **kwargs)
            hit = Cache.get(key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            Cache.set(key, result, ttl=ttl)
            return result
        return wrapper
    return deco