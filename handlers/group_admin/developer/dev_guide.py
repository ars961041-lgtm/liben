"""
دليل المطور التفاعلي — شرح كل ميزة يمكن للمطور إدارتها
"""
from core.bot import bot
from core.admin import is_any_dev
from utils.pagination import btn, send_ui, edit_ui, register_action
from utils.helpers import get_lines
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

_B  = "p"
_GR = "su"
_RD = "d"

# ══════════════════════════════════════════
# محتوى الأقسام
# ══════════════════════════════════════════

_SECTIONS = {
    "overview": {
        "emoji": "📋",
        "title": "نظرة عامة",
        "pages": [
            {
                "title": "🛠 ما يمكن للمطور إدارته",
                "content": (
                    "👑 <b>المطور الأساسي (Primary):</b>\n"
                    "• تعديل ثوابت البوت (أسعار، كولداون، رسائل)\n"
                    "• إضافة/إزالة/ترقية المطورين\n"
                    "• الكتم العالمي وكتم المجموعات\n"
                    "• إدارة الأصول والمباني والجنود\n\n"
                    "🔧 <b>المطور الثانوي (Secondary):</b>\n"
                    "• الكتم العالمي وكتم المجموعات\n"
                    "• عرض الثوابت (بدون تعديل)\n"
                    "• الوصول للوحة التذاكر\n\n"
                    "📌 <b>الأوامر الرئيسية:</b>\n"
                    "<code>لوحة الإدارة</code> — فتح لوحة التحكم\n"
                    "<code>شرح المطور</code> — هذا الدليل"
                ),
            },
        ],
    },

    "constants": {
        "emoji": "⚙️",
        "title": "ثوابت البوت",
        "pages": [
            {
                "title": "⚙️ ما هي الثوابت؟",
                "content": (
                    "الثوابت هي قيم يمكن تعديلها دون إعادة تشغيل البوت.\n"
                    "تُطبَّق فوراً على جميع العمليات.\n\n"
                    "💰 <b>ثوابت الحرب:</b>\n"
                    "• <code>attack_cost</code> — تكلفة الهجوم (افتراضي: 500)\n"
                    "• <code>support_send_cost</code> — تكلفة طلب الدعم (100)\n"
                    "• <code>recovery_minutes</code> — دقائق التعافي (30)\n"
                    "• <code>max_loss_pct</code> — أقصى خسارة (0.60)\n"
                    "• <code>travel_time_normal</code> — وقت السفر ثانية (1200)\n\n"
                    "🏦 <b>ثوابت الاقتصاد:</b>\n"
                    "• <code>country_creation_cost</code> — تكلفة إنشاء دولة (100)\n"
                    "• <code>alliance_creation_cost</code> — تكلفة إنشاء تحالف (500)\n"
                    "• <code>hidden_country_cost</code> — تكلفة الإخفاء اليومي (200)"
                ),
            },
            {
                "title": "⚙️ كيفية التعديل",
                "content": (
                    "1️⃣ افتح: <code>لوحة الإدارة</code>\n"
                    "2️⃣ اضغط: ⚙️ ثوابت البوت\n"
                    "3️⃣ اضغط ✏️ بجانب الثابت المراد تعديله\n"
                    "4️⃣ أرسل القيمة الجديدة\n\n"
                    "✅ يُطبَّق التغيير فوراً\n"
                    "⚠️ لا يمكن حذف الثوابت، فقط تعديلها\n\n"
                    "📌 <b>ثوابت أخرى مهمة:</b>\n"
                    "• <code>daily_ticket_limit</code> — حد التذاكر اليومي (2)\n"
                    "• <code>ticket_cooldown_sec</code> — كولداون التذاكر (10)\n"
                    "• <code>max_level_diff</code> — فارق المستوى للهجوم (3)\n"
                    "• <code>bot_name</code> — اسم البوت\n"
                    "• <code>welcome_msg</code> — رسالة الترحيب"
                ),
            },
        ],
    },

    "dev_roles": {
        "emoji": "👨‍💻",
        "title": "أدوار المطورين",
        "pages": [
            {
                "title": "👨‍💻 إدارة المطورين",
                "content": (
                    "📌 <b>الوصول:</b>\n"
                    "<code>لوحة الإدارة</code> → 👨‍💻 المطورون\n\n"
                    "➕ <b>إضافة مطور:</b>\n"
                    "اضغط ➕ إضافة مطور → أرسل ID المستخدم\n"
                    "يمكن تحديد الدور: <code>ID secondary</code> أو <code>ID primary</code>\n\n"
                    "⬆️ <b>ترقية مطور ثانوي → أساسي:</b>\n"
                    "اضغط ⬆️ ترقية بجانب اسمه\n\n"
                    "⬇️ <b>تخفيض مطور أساسي → ثانوي:</b>\n"
                    "اضغط ⬇️ تخفيض (لا يعمل على المطور الافتراضي)\n\n"
                    "🗑 <b>إزالة مطور:</b>\n"
                    "اضغط 🗑 إزالة (لا يعمل على المطور الافتراضي)"
                ),
            },
            {
                "title": "👨‍💻 التحقق من الصلاحيات",
                "content": (
                    "في الكود يمكن استخدام:\n\n"
                    "<code>from core.admin import is_primary_dev, is_secondary_dev, is_any_dev</code>\n\n"
                    "• <code>is_primary_dev(user_id)</code> — مطور أساسي فقط\n"
                    "• <code>is_secondary_dev(user_id)</code> — مطور ثانوي فقط\n"
                    "• <code>is_any_dev(user_id)</code> — أي نوع من المطورين\n\n"
                    "📌 <b>مثال:</b>\n"
                    "<code>if not is_primary_dev(user_id):\n"
                    "    return '❌ للمطور الأساسي فقط'</code>"
                ),
            },
        ],
    },

    "mute_system": {
        "emoji": "🔇",
        "title": "نظام الكتم",
        "pages": [
            {
                "title": "🔇 الكتم العالمي",
                "content": (
                    "الكتم العالمي يمنع المستخدم من التفاعل في جميع المجموعات.\n"
                    "رسائله تُحذف تلقائياً.\n\n"
                    "📌 <b>عبر اللوحة:</b>\n"
                    "<code>لوحة الإدارة</code> → 🔇 الكتم العالمي\n"
                    "اضغط ➕ كتم مستخدم → أرسل: <code>ID السبب</code>\n\n"
                    "📌 <b>عبر الأمر النصي السريع:</b>\n"
                    "<code>كتم عالمي [ID] [السبب]</code>\n"
                    "<code>رفع كتم عالمي [ID]</code>\n\n"
                    "✅ <b>رفع الكتم:</b>\n"
                    "اضغط 🔊 رفع كتم بجانب المستخدم"
                ),
            },
            {
                "title": "🔕 كتم المجموعة",
                "content": (
                    "كتم المجموعة يمنع المستخدم من التفاعل في مجموعة محددة فقط.\n\n"
                    "📌 <b>عبر اللوحة:</b>\n"
                    "<code>لوحة الإدارة</code> → 🔕 كتم المجموعة\n"
                    "(يعمل في المجموعة التي أرسلت منها الأمر)\n\n"
                    "📌 <b>الفرق بين الأنواع:</b>\n"
                    "🔇 عالمي — يؤثر على كل المجموعات\n"
                    "🔕 مجموعة — يؤثر على مجموعة واحدة فقط\n"
                    "🔇 قديم (كتم) — النظام القديم لا يزال يعمل"
                ),
            },
        ],
    },

    "war_admin": {
        "emoji": "⚔️",
        "title": "إدارة الحرب",
        "pages": [
            {
                "title": "⚔️ ثوابت الحرب القابلة للتعديل",
                "content": (
                    "جميع هذه القيم تُعدَّل من <code>لوحة الإدارة → ثوابت البوت</code>\n\n"
                    "⏱️ <b>الأوقات:</b>\n"
                    "• <code>travel_time_normal</code> — وقت السفر العادي (ثانية)\n"
                    "• <code>travel_time_sudden</code> — وقت الهجوم المباغت\n"
                    "• <code>recovery_minutes</code> — دقائق التعافي بعد المعركة\n\n"
                    "💰 <b>التكاليف:</b>\n"
                    "• <code>attack_cost</code> — تكلفة الهجوم\n"
                    "• <code>support_send_cost</code> — تكلفة طلب الدعم\n"
                    "• <code>card_use_cost</code> — تكلفة استخدام بطاقة\n\n"
                    "📊 <b>الخسائر والغنائم:</b>\n"
                    "• <code>max_loss_pct</code> — أقصى نسبة خسارة (0.0–1.0)\n"
                    "• <code>loot_min_pct</code> — أدنى نسبة غنائم\n"
                    "• <code>loot_max_pct</code> — أقصى نسبة غنائم"
                ),
            },
            {
                "title": "⚔️ إدارة الأصول والجنود",
                "content": (
                    "📌 <b>لوحة المطور الأصلية:</b>\n"
                    "من <code>لوحة المطور</code> (الأمر القديم)\n\n"
                    "🏗 <b>إدارة المباني:</b>\n"
                    "• إضافة/تعديل/حذف أنواع المباني\n"
                    "• تعديل الأسعار والتأثيرات\n"
                    "• إدارة الفروع والمستويات\n\n"
                    "🪖 <b>إدارة الجنود والمعدات:</b>\n"
                    "• إضافة/تعديل أنواع الجنود\n"
                    "• تعديل قيم الهجوم والدفاع والـ HP\n"
                    "• تعديل أسعار الشراء\n\n"
                    "📌 <b>ملاحظة:</b>\n"
                    "التغييرات تؤثر على اللاعبين الجدد فقط\n"
                    "اللاعبون الحاليون يحتفظون بما اشتروه"
                ),
            },
        ],
    },

    "tickets_admin": {
        "emoji": "🎫",
        "title": "إدارة التذاكر",
        "pages": [
            {
                "title": "🎫 نظام التذاكر",
                "content": (
                    "📌 <b>الوصول للوحة التذاكر:</b>\n"
                    "<code>لوحة التذاكر</code> أو <code>/tickets</code>\n\n"
                    "📬 <b>التذاكر المفتوحة:</b>\n"
                    "عرض كل التذاكر التي تحتاج رداً\n\n"
                    "📁 <b>جميع التذاكر:</b>\n"
                    "عرض كل التذاكر مع pagination\n\n"
                    "💬 <b>الرد على تذكرة:</b>\n"
                    "• اضغط 💬 رد في مجموعة المطورين\n"
                    "• أو رد مباشرة على رسالة التذكرة\n\n"
                    "🔒 <b>إغلاق تذكرة:</b>\n"
                    "اضغط 🔒 إغلاق التذكرة\n"
                    "يُشعَر المستخدم تلقائياً\n\n"
                    "📊 <b>الإحصائيات:</b>\n"
                    "• تذاكر اليوم / المفتوحة / المغلقة / الإجمالي"
                ),
            },
            {
                "title": "🎫 ثوابت التذاكر",
                "content": (
                    "يمكن تعديل هذه القيم من <code>لوحة الإدارة → ثوابت البوت</code>\n\n"
                    "• <code>daily_ticket_limit</code> — حد التذاكر اليومي للمستخدم (2)\n"
                    "• <code>ticket_cooldown_sec</code> — كولداون بين التذاكر (10 ثانية)\n\n"
                    "📌 <b>مجموعة المطورين:</b>\n"
                    "معرف المجموعة محفوظ في: <code>dev_group_id</code>\n"
                    "يمكن تعديله من ثوابت البوت إذا تغيرت المجموعة"
                ),
            },
        ],
    },

    "azkar": {
        "emoji": "📿",
        "title": "إدارة الأذكار",
        "pages": [
            {
                "title": "📿 إدارة الأذكار",
                "content": (
                    "📌 <b>الوصول (طريقتان):</b>\n"
                    "• <code>لوحة الإدارة</code> → 📿 إدارة الأذكار\n"
                    "• أو اكتب مباشرة: <code>إدارة الأذكار</code>\n\n"
                    "📋 <b>أنواع الأذكار (type):</b>\n"
                    "• <code>0</code> = 🌅 أذكار الصباح\n"
                    "• <code>1</code> = 🌙 أذكار المساء\n"
                    "• <code>2</code> = 😴 أذكار النوم\n"
                    "• <code>3</code> = ☀️ أذكار الاستيقاظ\n\n"
                    "🔧 <b>العمليات المتاحة:</b>\n"
                    "• عرض قائمة الأذكار لكل نوع\n"
                    "• ✏️ تعديل نص أي ذكر\n"
                    "• 🔢 تعديل عدد التكرار\n"
                    "• 🗑 حذف ذكر (المطور الأساسي فقط)\n"
                    "• ➕ إضافة ذكر جديد بالصيغة:\n"
                    "  <code>النص | عدد التكرار</code>\n\n"
                    "🗄 <b>قاعدة البيانات:</b>\n"
                    "الأذكار محفوظة في <code>azkar.db</code> منفصلة عن باقي البيانات.\n"
                    "تقدم المستخدمين محفوظ في جدول <code>azkar_progress</code>."
                ),
            },
            {
                "title": "📿 الأذكار — ميزات المستخدم",
                "content": (
                    "هذه الميزات للمستخدمين العاديين — ليست للإدارة.\n\n"
                    "▶️ <b>أوامر المستخدم:</b>\n"
                    "• <code>أذكار الصباح</code> 🌅\n"
                    "• <code>أذكار المساء</code> 🌙\n"
                    "• <code>أذكار النوم</code> 😴\n"
                    "• <code>أذكار الاستيقاظ</code> ☀️\n"
                    "• <code>ذكرني ذكري</code> — تذكير يومي تلقائي\n"
                    "• <code>ذكر</code> — ذكر مخصص مؤقت\n\n"
                    "🔄 <b>إعادة التعيين اليومية:</b>\n"
                    "تقدم كل مستخدم يُعاد تلقائياً في اليوم التالي.\n\n"
                    "⚠️ <b>ملاحظة للمطور:</b>\n"
                    "الأذكار والمجلة ميزتان مستقلتان تماماً.\n"
                    "الأذكار = محتوى ديني وتعبدي.\n"
                    "المجلة = أخبار وأحداث اللعبة."
                ),
            },
        ],
    },

    "magazine": {
        "emoji": "📰",
        "title": "المجلة والهدايا",
        "pages": [
            {
                "title": "📰 المجلة اليومية",
                "content": (
                    "📌 <b>الوصول:</b>\n"
                    "<code>لوحة الإدارة</code> → 📰 المجلة والهدايا\n\n"
                    "📰 <b>ما هي المجلة؟</b>\n"
                    "منشورات يومية يراها اللاعبون بكتابة <code>المجلة</code>.\n"
                    "تُستخدم لإعلانات اللعبة، تحديثات الميزات، أحداث خاصة.\n\n"
                    "🔧 <b>العمليات:</b>\n"
                    "• ➕ إضافة منشور (عنوان + نص)\n"
                    "• 📋 عرض المنشورات الحالية\n"
                    "• 🗑 حذف منشور\n\n"
                    "⚠️ <b>المجلة ≠ الأذكار:</b>\n"
                    "المجلة خاصة بأخبار اللعبة فقط.\n"
                    "لا تضع محتوى دينياً في المجلة."
                ),
            },
            {
                "title": "🎁 نظام الهدايا",
                "content": (
                    "📌 <b>الأمر:</b>\n"
                    "<code>هدية</code> أو <code>/developer_gift</code>\n\n"
                    "🎁 <b>أنواع الهدايا:</b>\n"
                    f"• 💰 <b>{CURRENCY_ARABIC_NAME}</b> — رصيد مباشر لجميع اللاعبين\n"
                    "• 🏙 <b>مستوى مدن</b> — ترقية مستوى مدن اللاعبين\n"
                    "• 🪖 <b>جنود</b> — إضافة جنود لجيوش اللاعبين\n\n"
                    "📋 <b>الخطوات:</b>\n"
                    "1️⃣ اختر نوع الهدية\n"
                    "2️⃣ أدخل القيمة\n"
                    "3️⃣ أدخل ملاحظة (تظهر في المجلة)\n"
                    "4️⃣ معاينة → تأكيد\n\n"
                    "📊 <b>التسجيل:</b>\n"
                    "كل هدية تُسجَّل في <code>gift_log</code>\n"
                    "وتُضاف تلقائياً كمنشور في المجلة."
                ),
            },
        ],
    },

    "group_rules": {
        "emoji": "📜",
        "title": "قوانين المجموعات",
        "pages": [
            {
                "title": "📜 نظام القوانين — نظرة عامة",
                "content": (
                    "📌 <b>الأوامر:</b>\n"
                    "• <code>القوانين</code>\n"
                    "• <code>قوانين الجروب</code>\n\n"
                    "✍️ <b>حفظ القوانين (مشرف):</b>\n"
                    "ارد على رسالة تحتوي القوانين بـ <code>القوانين</code>\n\n"
                    "📋 <b>أزرار المشرف:</b>\n"
                    "• 🗑️ مسح — يحذف من DB\n"
                    "• 📌 تثبيت — يفك التثبيت القديم أولاً\n"
                    "• 🔔 تفعيل/إيقاف الإرسال للجدد\n"
                    "• ℹ️ تفاصيل — من أضافها ومتى\n"
                    "• ❌ إخفاء — يحذف الرسالة\n\n"
                    "👤 <b>أزرار الأعضاء:</b>\n"
                    "• ❌ إخفاء فقط\n\n"
                    "⚠️ <b>الحد الأقصى:</b> 4096 حرف."
                ),
            },
            {
                "title": "📜 Auto-Send والـ Throttle",
                "content": (
                    "🔔 <b>الإرسال التلقائي للأعضاء الجدد:</b>\n"
                    "عند تفعيله، يُرسَل القوانين لكل عضو جديد.\n\n"
                    "⚡ <b>Throttle (منع الإرسال المتكرر):</b>\n"
                    "إذا انضم عدة أعضاء في وقت واحد،\n"
                    "يُرسَل القوانين مرة واحدة فقط كل 10 ثوانٍ لكل مجموعة.\n"
                    "هذا يمنع الـ spam عند الانضمام الجماعي.\n\n"
                    "🗄 <b>قاعدة البيانات:</b>\n"
                    "جدول <code>group_rules</code> في DB الرئيسية.\n"
                    "الحقول: chat_id, rules, updated_by, updated_at, auto_send"
                ),
            },
        ],
    },
}


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def open_dev_guide(message):
    """يفتح دليل المطور — للمطورين فقط"""
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_any_dev(user_id):
        bot.reply_to(message, "❌ هذا الدليل للمطورين فقط.")
        return

    _send_guide_menu(chat_id, user_id)


def _send_guide_menu(chat_id, user_id):
    owner = (user_id, chat_id)
    text  = (
        "📚 <b>دليل المطور التفاعلي</b>\n"
        f"{get_lines()}\n\n"
        "اختر القسم الذي تريد شرحه:"
    )
    buttons = [
        btn(f"{s['emoji']} {s['title']}", "devguide_section",
            data={"sid": sid, "p": 0}, owner=owner, color=_B)
        for sid, s in _SECTIONS.items()
    ]
    buttons.append(btn("❌ إخفاء", "devguide_hide", owner=owner, color=_RD))

    layout = _grid(len(buttons) - 1, 2) + [1]
    send_ui(chat_id, text=text, buttons=buttons, layout=layout, owner_id=user_id)


@register_action("devguide_section")
def show_section(call, data):
    sid   = data.get("sid")
    page  = int(data.get("p", 0))
    owner = (call.from_user.id, call.message.chat.id)

    if not is_any_dev(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ للمطورين فقط", show_alert=True)
        return

    section = _SECTIONS.get(sid)
    if not section:
        bot.answer_callback_query(call.id, "❌ القسم غير موجود", show_alert=True)
        return

    pages = section["pages"]
    total = len(pages)
    page  = max(0, min(page, total - 1))
    pg    = pages[page]

    text = (
        f"{section['emoji']} <b>{section['title']}</b>\n"
        f"{get_lines()}\n\n"
        f"📋 <b>{pg['title']}</b>\n"
        f"{get_lines()}\n\n"
        f"{pg['content']}"
    )
    if total > 1:
        text += f"\n\n📄 صفحة {page + 1} / {total}"

    nav = []
    if page < total - 1:
        nav.append(btn("التالي ◀️", "devguide_section",
                       data={"sid": sid, "p": page + 1}, owner=owner, color=_B))
    if page > 0:
        nav.append(btn("▶️ السابق", "devguide_section",
                       data={"sid": sid, "p": page - 1}, owner=owner, color=_B))

    buttons = list(nav)
    buttons.append(btn("🔙 القائمة الرئيسية", "devguide_back", owner=owner, color=_RD))

    layout = ([len(nav)] if nav else []) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("devguide_back")
def back_to_guide_menu(call, data):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_any_dev(user_id):
        return

    owner = (user_id, chat_id)
    text  = (
        "📚 <b>دليل المطور التفاعلي</b>\n"
        f"{get_lines()}\n\n"
        "اختر القسم الذي تريد شرحه:"
    )
    buttons = [
        btn(f"{s['emoji']} {s['title']}", "devguide_section",
            data={"sid": sid, "p": 0}, owner=owner, color=_B)
        for sid, s in _SECTIONS.items()
    ]
    buttons.append(btn("❌ إخفاء", "devguide_hide", owner=owner, color=_RD))
    layout = _grid(len(buttons) - 1, 2) + [1]
    edit_ui(call, text=text, buttons=buttons, layout=layout)


@register_action("devguide_hide")
def hide_guide(call, data):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


def _grid(n: int, cols: int = 2) -> list:
    layout, rem = [], n
    while rem > 0:
        layout.append(min(cols, rem))
        rem -= cols
    return layout or [1]
