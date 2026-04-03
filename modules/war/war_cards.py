"""
⚠️ DEPRECATED — هذا الملف مهجور ولا يُستخدم في النظام الحالي.
البطاقات الآن محفوظة في جدول `cards` بقاعدة البيانات.
استخدم: database/db_queries/advanced_war_queries.py → get_all_cards()
يمكن حذف هذا الملف بأمان.
"""
# war_cards.py

# ─────────────────────────────
# 🃏 أنواع البطاقات
# ─────────────────────────────
CARDS = {
    "attack_boost": {
        "name": "هجوم مضاعف",
        "type": "attack",
        "value": 0.25  # +25%
    },
    "defense_boost": {
        "name": "درع قوي",
        "type": "defense",
        "value": 0.30  # +30%
    },
    "hp_boost": {
        "name": "تعزيز الصحة",
        "type": "hp",
        "value": 0.20
    },
    "rage": {
        "name": "غضب",
        "type": "attack",
        "value": 0.40
    },
    "fortress": {
        "name": "حصن",
        "type": "defense",
        "value": 0.50
    }
}


# ─────────────────────────────
# 🎴 جلب بطاقة
# ─────────────────────────────
def get_card(card_name):
    return CARDS.get(card_name)


# ─────────────────────────────
# 🎲 بطاقات عشوائية
# ─────────────────────────────
import random

def get_random_cards(count=1):
    keys = list(CARDS.keys())
    selected = random.sample(keys, min(count, len(keys)))
    return [CARDS[k] for k in selected]