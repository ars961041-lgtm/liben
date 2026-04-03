# handlers/tops/tops_menu.py

from database.db_queries.tops_queries import (
    get_group_members_stats,
    get_top_richest
)

from utils.helpers import send_reply
from handlers.tops.tops_builder import build_top


# ═══════════════════════════════
# 📊 CITY METRICS
# ═══════════════════════════════

CITY_METRICS = [
    "population",
    "economy",
    "health",
    "education",
    "infra"
]

CITY_LABELS = {
    "population": "السكان",
    "economy": "الاقتصاد",
    "health": "الصحة",
    "education": "التعليم",
    "infra": "البنية التحتية"
}


# ═══════════════════════════════
# 🌍 COUNTRY METRICS
# ═══════════════════════════════

COUNTRY_METRICS = [
    "economy",
    "health",
    "education",
    "military",
    "infra"
]

COUNTRY_LABELS = {
    "economy": "الاقتصاد",
    "health": "الصحة",
    "education": "التعليم",
    "military": "القوة العسكرية",
    "infra": "البنية التحتية"
}


# ═══════════════════════════════
# 💰 توب الأغنى (نصي)
# ═══════════════════════════════

def show_top_richest(message, limit=10, note=""):

    rows = get_top_richest(limit)

    text = (
        build_top("💰 توب الأغنى", rows, note=note)
        if rows else
        "❌ لا توجد بيانات."
    )

    send_reply(message, text)


# ═══════════════════════════════
# 🔥 توب المتفاعلين (نصي)
# ═══════════════════════════════

def show_top_activity(message, limit=10, note=""):

    members = get_group_members_stats(message.chat.id, limit)

    if not members:
        send_reply(message, "❌ لا يوجد بيانات متاحة.")
        return

    rows = [
        {
            "name": m.get("name", "Unknown"),
            "value": f"{m.get('messages_count', 0)} رسالة"
        }
        for m in members
    ]

    text = build_top("🔥 أعلى المتفاعلين", rows, note=note)

    send_reply(message, text)