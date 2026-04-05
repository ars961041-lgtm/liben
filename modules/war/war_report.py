"""
⚠️ DEPRECATED — هذا الملف مهجور ولا يُستخدم في النظام الحالي.
التقارير الآن تُولَّد في: modules/war/live_battle_engine._send_final_report()
يمكن حذف هذا الملف بأمان.
"""
# war_report.py
from utils.helpers import get_lines

def format_battle_report(attacker_name, defender_name, result):
    winner = result["winner"]
    attacker_hp = int(result["attacker_remaining_hp"])
    defender_hp = int(result["defender_remaining_hp"])

    # تحديد اسم الفائز
    winner_name = attacker_name if winner == "attacker" else defender_name

    # بناء نص الخسائر
    def format_losses(losses):
        if not losses:
            return "لا توجد خسائر 🎉"
        text = ""
        for l in losses:
            text += f"• نوع {l['troop_type_id']} ➖ {l['lost']}\n"
        return text

    attacker_losses = format_losses(result["attacker_losses"])
    defender_losses = format_losses(result["defender_losses"])

    # الرسالة النهائية
    report = f"""
⚔️ <b>معركة ملحمية!</b>

🏙 <b>{attacker_name}</b> 🆚 <b>{defender_name}</b>

{get_lines()}

🔥 <b>القوة المتبقية:</b>
🟥 المهاجم: {attacker_hp}
🟦 المدافع: {defender_hp}

{get_lines()}

🏆 <b>الفائز:</b>
👑 {winner_name}

{get_lines()}

📉 <b>خسائر المهاجم:</b>
{attacker_losses}

📉 <b>خسائر المدافع:</b>
{defender_losses}

{get_lines()}

💬 <i>إما أن تحكم… أو تُمحى</i>
"""

    return report