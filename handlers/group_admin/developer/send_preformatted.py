send_ui = """
<pre>
📘 دليل استخدام نظام UI (Level 3)

━━━━━━━━━━━━━━━━━━━
📤 إرسال رسالة (Text فقط)
━━━━━━━━━━━━━━━━━━━

send_ui(
    chat_id=message.chat.id,
    text="مرحبا 👋",
    owner_id=message.from_user.id
)

✔ بدون أزرار
✔ بدون تعقيد


━━━━━━━━━━━━━━━━━━━
📤 إرسال رسالة + أزرار
━━━━━━━━━━━━━━━━━━━

send_ui(
    chat_id=message.chat.id,
    text="اختر عملية:",
    buttons=[
        btn("🔴 حذف", "delete", "danger"),
        btn("🟢 موافق", "accept", "success")
    ],
    layout=[2],
    owner_id=message.from_user.id
)

✔ layout=[2] = زرّين في صف واحد


━━━━━━━━━━━━━━━━━━━
📤 إرسال صورة + أزرار
━━━━━━━━━━━━━━━━━━━

send_ui(
    chat_id=message.chat.id,
    text="📸 صورة",
    photo="https://...",
    buttons=[
        btn("➡️ التالي", "next"),
        btn("❌ حذف", "delete", "danger")
    ],
    layout=[1,1],
    owner_id=message.from_user.id
)


━━━━━━━━━━━━━━━━━━━
✏️ تعديل رسالة (بدون أزرار)
━━━━━━━━━━━━━━━━━━━

edit_ui(
    call,
    "✅ تم التنفيذ"
)

✔ يحذف الأزرار تلقائيًا


━━━━━━━━━━━━━━━━━━━
✏️ تعديل رسالة + أزرار
━━━━━━━━━━━━━━━━━━━

edit_ui(
    call,
    "اختر:",
    buttons=[
        btn("رجوع", "back"),
        btn("التالي", "next")
    ],
    layout=[2]
)


━━━━━━━━━━━━━━━━━━━
🔁 التنقل بين الصفحات
━━━━━━━━━━━━━━━━━━━

btn("التالي", "next_page", data={"page": 1})

داخل الأكشن:

@register_action("next_page")
def next_page(call, data):
    page = data.get("page", 0) + 1

    edit_ui(
        call,
        f"📄 الصفحة {page}",
        buttons=[
            btn("⬅️ السابق", "prev_page", {"page": page}),
            btn("➡️ التالي", "next_page", {"page": page})
        ],
        layout=[2]
    )


━━━━━━━━━━━━━━━━━━━
📦 تمرير البيانات (Data)
━━━━━━━━━━━━━━━━━━━

btn("شراء", "buy", data={"id": 5})

داخل الأكشن:

@register_action("buy")
def buy(call, data):
    item_id = data.get("id")


━━━━━━━━━━━━━━━━━━━
🔙 زر رجوع
━━━━━━━━━━━━━━━━━━━

btn("⬅️ رجوع", "back")

✔ يرجع للواجهة السابقة تلقائيًا


━━━━━━━━━━━━━━━━━━━
🧠 نظام الحالة (State)
━━━━━━━━━━━━━━━━━━━

set_state(user_id, "inside_shop", {"page": 1})

الحصول على الحالة:

state = get_state(user_id)

state["state"]       # اسم الحالة
state["data"]        # البيانات

حذف الحالة:

clear_state(user_id)


━━━━━━━━━━━━━━━━━━━
📜 حفظ الصفحات (History)
━━━━━━━━━━━━━━━━━━━

يتم تلقائيًا عند استخدام send_ui

✔ يستخدم للرجوع


━━━━━━━━━━━━━━━━━━━
🎨 layout (توزيع الأزرار)
━━━━━━━━━━━━━━━━━━━

layout=[1]        ➜ زر واحد
layout=[2]        ➜ زرين
layout=[2,1]      ➜ 2 فوق / 1 تحت
layout=[3,2,1]    ➜ متدرج

مثال:

buttons = [1,2,3,4,5,6]
layout = [3,2,1]

النتيجة:
[1][2][3]
[4][5]
[6]


━━━━━━━━━━━━━━━━━━━
🔒 حماية الأزرار
━━━━━━━━━━━━━━━━━━━

owner_id=message.from_user.id

✔ يمنع أي شخص غير المرسل من الضغط


━━━━━━━━━━━━━━━━━━━
🧩 إنشاء زر
━━━━━━━━━━━━━━━━━━━

btn("النص", "action", "style", data={})

style:
- primary
- secondary
- success
- danger


━━━━━━━━━━━━━━━━━━━
⚡ مثال كامل
━━━━━━━━━━━━━━━━━━━

send_ui(
    chat_id=message.chat.id,
    text="🏙️ مدينتك",
    buttons=[
        btn("🏗️ بناء", "build"),
        btn("🏪 متجر", "open_shop"),
        btn("❌ إغلاق", "delete", "danger")
    ],
    layout=[2,1],
    owner_id=message.from_user.id
)


━━━━━━━━━━━━━━━━━━━
🔥 ملاحظات مهمة
━━━━━━━━━━━━━━━━━━━

✔ buttons=None ➜ بدون أزرار  
✔ buttons=[] ➜ بدون أزرار  
✔ edit_ui بدون buttons ➜ يحذف الأزرار  
✔ لازم owner_id للرجوع  
✔ لازم import للأكشنات  

━━━━━━━━━━━━━━━━━━━

👑 انتهى - أنت الآن تستخدم نظام UI احترافي
</pre>
"""

from core.bot import bot
from handlers.group_admin.permissions import is_developer

def send_preformatted(message):

    # ✅ تحقق من المطور (مهم: ترسل id وليس message)
    if not is_developer(message.from_user.id):
        return

    bot.reply_to(
        message,
        send_ui,
        parse_mode="HTML"
    )