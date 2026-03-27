import time

USER_CACHE = {}

CACHE_TTL = 600  # 10 دقائق


def get_cache(user_id):

    if user_id in USER_CACHE:

        data, timestamp = USER_CACHE[user_id]

        if time.time() - timestamp < CACHE_TTL:
            return data

        USER_CACHE.pop(user_id, None)

    return None


def set_cache(user_id, data):

    USER_CACHE[user_id] = (data, time.time())