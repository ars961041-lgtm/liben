# handlers/tops/top_service.py

from database.db_queries import (
    get_global_top_activity,
    get_top_richest,
    get_top_countries,
    get_top_cities,
    get_top_cities_by,
    get_top_countries_by
)

from handlers.tops.tops_builder import build_top


# ═══════════════════════════════
# 🧠 أنواع التوبات
# ═══════════════════════════════

TOPS = {

    "richest": {
        "title": "💰 أغنى اللاعبين",
        "func": get_top_richest
    },

    "activity": {
        "title": "📊 النشاط العالمي",
        "func": get_global_top_activity
    },

    "countries": {
        "title": "🌍 توب الدول",
        "func": get_top_countries
    },

    "cities": {
        "title": "🏙 توب المدن",
        "func": get_top_cities
    }
}


# ═══════════════════════════════
# 🏙 فلاتر المدن
# ═══════════════════════════════

CITY_FILTERS = {
    "economy": "💰 الاقتصاد",
    "population": "👥 السكان",
    "health": "🏥 الصحة",
    "education": "📚 التعليم",
    "infra": "🛣 البنية التحتية"
}


# ═══════════════════════════════
# 🌍 فلاتر الدول
# ═══════════════════════════════

COUNTRY_FILTERS = {
    "economy": "💰 الاقتصاد",
    "health": "🏥 الصحة",
    "education": "📚 التعليم",
    "military": "🪖 القوة العسكرية",
    "infra": "🛣 البنية التحتية"
}


# ═══════════════════════════════
# 🧠 جلب بيانات التوب
# ═══════════════════════════════

def get_top_data(top_type, metric=None):

    # ---- المدن ----
    if top_type == "cities":

        if metric:
            return get_top_cities_by(metric)

        return get_top_cities()

    # ---- الدول ----
    if top_type == "countries":

        if metric:
            return get_top_countries_by(metric)

        return get_top_countries()

    # ---- باقي التوبات ----
    top = TOPS.get(top_type)

    if not top:
        return []

    func = top["func"]

    return func()


# ═══════════════════════════════
# 🎯 تجهيز النص النهائي
# ═══════════════════════════════

def get_top_text(top_type, metric=None):

    # ---- تحديد العنوان ----

    if top_type == "cities" and metric:

        title = f"🏙 توب المدن — {CITY_FILTERS.get(metric, metric)}"

    elif top_type == "countries" and metric:

        title = f"🌍 توب الدول — {COUNTRY_FILTERS.get(metric, metric)}"

    else:

        title = TOPS.get(top_type, {}).get("title", "🏆 توب")


    # ---- جلب البيانات ----

    rows = get_top_data(top_type, metric)


    if not rows:
        return "❌ لا توجد بيانات."


    # ---- بناء النص ----

    return build_top(title, rows)