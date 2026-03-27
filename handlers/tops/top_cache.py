import time

TOP_CACHE = {}

CACHE_TTL = 600  # 10 دقائق


def get_top_cache(key):

    if key in TOP_CACHE:

        data, timestamp = TOP_CACHE[key]

        if time.time() - timestamp < CACHE_TTL:
            return data

        TOP_CACHE.pop(key, None)

    return None


def set_top_cache(key, data):

    TOP_CACHE[key] = (data, time.time())