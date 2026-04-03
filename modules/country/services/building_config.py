# modules/country/services/building_config.py

# -----------------------------
# ⚙️ إعدادات المباني
# -----------------------------
BUILDING_CONFIG = {
    "hospital": {
        "name_ar": "مستشفى",
        "emoji": "🏥",
        "base_cost": 1000,
        "cost_scale": 1.5,
        "maintenance_cost": 50,
        "income": 0,
        "stat_impact": {"health_level": 5}
    },
    "school": {
        "name_ar": "مدرسة",
        "emoji": "🏫",
        "base_cost": 1500,
        "cost_scale": 1.5,
        "maintenance_cost": 70,
        "income": 0,
        "stat_impact": {"education_level": 5}
    },
    "factory": {
        "name_ar": "مصنع",
        "emoji": "🏭",
        "base_cost": 2000,
        "cost_scale": 1.6,
        "maintenance_cost": 100,
        "income": 300,
        "stat_impact": {"economy_score": 5}
    },
    "military_base": {
        "name_ar": "قاعدة عسكرية",
        "emoji": "🪖",
        "base_cost": 5000,
        "cost_scale": 1.7,
        "maintenance_cost": 500,
        "income": 0,
        "stat_impact": {"military_power": 10}
    },
    "infrastructure": {
        "name_ar": "بنية تحتية",
        "emoji": "🛣",
        "base_cost": 800,
        "cost_scale": 1.4,
        "maintenance_cost": 30,
        "income": 0,
        "stat_impact": {"infrastructure_level": 5}
    },
    "bank": {
        "name_ar": "بنك محلي",
        "emoji": "🏦",
        "base_cost": 3000,
        "cost_scale": 1.6,
        "maintenance_cost": 150,
        "income": 100,
        "stat_impact": {"economy_score": 3}
    }
}

# -----------------------------
# 🔍 جلب معلومات المبنى
# -----------------------------
def get_building_info(building_type: str):
    """إرجاع إعدادات المبنى حسب نوعه"""
    return BUILDING_CONFIG.get(building_type)

# -----------------------------
# 💰 حساب تكلفة الترقية من المستوى الحالي إلى المستوى المستهدف
# -----------------------------
def calculate_upgrade_cost(base_cost: float, current_level: int, cost_scale: float, target_level: int):
    """تكلفة الترقية من current_level إلى target_level"""
    total_cost = 0
    for level in range(current_level, target_level):
        total_cost += base_cost * (cost_scale ** (level - 1))
    return round(total_cost)

# -----------------------------
# 💵 حساب تكلفة شراء عدد معين من المباني
# -----------------------------
def calculate_buy_cost(base_cost: float, quantity: int):
    """تكلفة شراء عدد quantity من المباني"""
    return base_cost * quantity