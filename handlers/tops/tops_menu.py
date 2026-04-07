"""
ثوابت قوائم التوب — محتفظ به للتوافق مع الكود القديم.
الفئات الجديدة تُعرَّف في tops_handler.TOP_CATEGORIES.
"""
# backward-compat — بعض الأماكن قد تستورد هذه الثوابت
CITY_METRICS   = ["population", "economy", "health", "education", "infra"]
CITY_LABELS    = {"population": "السكان", "economy": "الاقتصاد",
                  "health": "الصحة", "education": "التعليم", "infra": "البنية التحتية"}
COUNTRY_METRICS = ["economy", "health", "education", "military", "infra"]
COUNTRY_LABELS  = {"economy": "الاقتصاد", "health": "الصحة",
                   "education": "التعليم", "military": "القوة العسكرية", "infra": "البنية التحتية"}
