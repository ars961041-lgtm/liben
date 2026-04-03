from telebot import types
from core.bot import bot
from core.memory import remember, recall

# ───────────── الصفحات والميزات ─────────────
PAGES = [
    ["bold","italic","underline","strike"],
    ["spoiler","quote","exquote","code"],
    ["pre","python","link","mention"],
    ["time"]
]

# ───────────── فتح الدليل مع زر المعاينة الثابت وزر الرجوع ─────────────
def open_format_guide(message):
    user_id = message.from_user.id

    # زر المعاينة الثابت
    preview_btn = types.InlineKeyboardButton(
        text="معاينة النص المكتوب أسفل الرسالة مباشرة", 
        callback_data="preview_text"
    )
    
    # زر الرجوع للرئيسية
    home_btn = types.InlineKeyboardButton(
        text="رجوع للرئيسية", 
        callback_data="guide_home"
    )
    
    # إنشاء لوحة الصفحات
    markup = types.InlineKeyboardMarkup(row_width=2)
    for page in PAGES:
        for feature in page:
            markup.add(types.InlineKeyboardButton(
                text=feature, callback_data=f"feature_{feature}"
            ))
    
    # إضافة زر المعاينة وزر الرجوع أسفل كل الصفحات
    markup.add(preview_btn)
    markup.add(home_btn)
    
    # إرسال رسالة الدليل
    bot.send_message(
        chat_id=message.chat.id,
        text=(
            "مرحبًا في دليل التنسيقات.\n"
            "اختر أي ميزة لتعرف فائدتها وطريقة استخدامها.\n"
            "يمكنك كتابة أي نص أسفل الرسالة وسيتم معاينته مباشرة عند الضغط على زر المعاينة."
        ),
        reply_markup=markup
    )

# ───────────── التعامل مع معاينة النص ─────────────
def handle_preview_callback(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    user_id = call.from_user.id
    
    # جلب نص المستخدم من الذاكرة
    text_to_preview = recall(user_id, "format_text")
    
    # تعديل نفس الرسالة لعرض المعاينة
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text=f"معاينة النص:\n\n{text_to_preview}",
        reply_markup=call.message.reply_markup
    )

# ───────────── استقبال نصوص المستخدم وحفظها ─────────────
def receive_user_text(message):
    if not message.text:  # تجاهل الوسائط غير النصية
        return
    # حفظ نص المستخدم للمعاينة
    remember(message.from_user.id, "format_text", message.text)