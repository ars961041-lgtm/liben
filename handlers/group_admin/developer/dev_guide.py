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
    "other_tools": {
        "emoji": "🔧",
        "title": "أدوات أخرى",
        "pages": [
            {
                "title": "🔧 أدوات أخرى — نظرة عامة",
                "content": (
                    "هذا القسم يشرح الأدوات المساعدة التي لا تندرج تحت الألعاب أو الإدارة.\n\n"
                    "💌 <b>نظام الهمسات:</b>\n"
                    "يتيح للأعضاء إرسال رسائل خاصة (همسات) داخل المجموعة.\n"
                    "• <code>همسة @username</code> — همسة لمستخدم محدد\n"
                    "• <code>همسة @all</code> — همسة لجميع الأعضاء النشطين\n"
                    "• <code>همسة</code> + رد على رسالة — همسة للمُرسِل\n\n"
                    "⚙️ <b>تحكم المشرف في الهمسات:</b>\n"
                    "• <code>تفعيل الهمسات</code> — يُفعّل النظام في المجموعة\n"
                    "• <code>تعطيل الهمسات</code> — يُعطّل النظام في المجموعة\n"
                    "• أو من لوحة <code>الأوامر</code> → 💌 الهمسات\n\n"
                    "🗄 <b>قاعدة البيانات:</b>\n"
                    "الهمسات محفوظة في جدول <code>whispers</code> في DB الرئيسية.\n"
                    "الإعداد محفوظ في عمود <code>enable_whispers</code> في جدول <code>groups</code>."
                ),
            },
            {
                "title": "💌 الهمسات — التفاصيل التقنية",
                "content": (
                    "📌 <b>الملفات المعنية:</b>\n"
                    "• <code>modules/whispers/whisper_handler.py</code> — المنطق الرئيسي\n"
                    "• <code>modules/whispers/whispers_keyboards.py</code> — بناء الأزرار\n"
                    "• <code>database/db_queries/whispers_queries.py</code> — الاستعلامات\n"
                    "• <code>database/db_schema/whispers.py</code> — تعريف الجداول\n\n"
                    "🔄 <b>تدفق الهمسة:</b>\n"
                    "1️⃣ المستخدم يكتب <code>همسة @username</code> في المجموعة\n"
                    "2️⃣ البوت يُنشئ token ويرسل زر 'كتابة الهمسة'\n"
                    "3️⃣ المستخدم يضغط الزر → يفتح الخاص مع البوت\n"
                    "4️⃣ يكتب النص → يُحفظ في DB → إشعار في المجموعة\n"
                    "5️⃣ المستقبِل يضغط 'عرض الهمسة' → يرى النص في popup\n\n"
                    "⏱️ <b>التنظيف التلقائي:</b>\n"
                    "• همسات غير مقروءة تُحذف بعد 3 أيام\n"
                    "• همسات مقروءة تُحذف بعد يوم واحد\n\n"
                    "🚦 <b>Rate Limit:</b>\n"
                    "5 همسات كحد أقصى كل 60 ثانية لكل مستخدم."
                ),
            },
        ],
    },

    "overview": {
        "emoji": "📋",
        "title": "نظرة عامة",
        "pages": [
            {
                "title": "🛠 ما يمكن للمطور إدارته",
                "content": (
                    "👑 <b>المطور الأساسي (Primary):</b>\n"
                    "• تعديل ثوابت البوت عبر لوحة المطور (أسعار، كولداون، رسائل)\n"
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

    "analytics": {
        "emoji": "📊",
        "title": "نظام الإحصائيات",
        "pages": [
            {
                "title": "📊 جداول السجل المستخدمة",
                "content": (
                    "نظام الإحصائيات يستخرج بياناته من جداول السجل التالية:\n\n"
                    "📦 <b>asset_log</b>\n"
                    "كل عملية شراء أو ترقية لأصل في مدينة.\n"
                    "الحقول: city_id, user_id, asset_id, action, quantity, cost, ts\n\n"
                    "💸 <b>bank_transfers</b>\n"
                    "كل تحويل بنكي بين لاعبين.\n"
                    "الحقول: from_user_id, to_user_id, amount, fee, created_at\n\n"
                    "⚔️ <b>battle_history</b>\n"
                    "أرشيف المعارك المكتملة.\n"
                    "الحقول: attacker/defender_country_id, winner, loot, duration_seconds\n\n"
                    "🕵️ <b>spy_operations</b>\n"
                    "كل عملية تجسس مع نتيجتها.\n"
                    "الحقول: attacker_country_id, target_country_id, result\n\n"
                    "🗺️ <b>exploration_log</b>\n"
                    "مهام الاستكشاف ونتائجها.\n\n"
                    "💰 <b>war_costs_log</b>\n"
                    "كل خصم مالي مرتبط بعمليات الحرب."
                ),
            },
            {
                "title": "📊 كيفية إضافة إحصائية جديدة",
                "content": (
                    "📌 <b>الخطوات:</b>\n\n"
                    "1️⃣ أضف دالة استعلام في:\n"
                    "<code>database/db_queries/analytics_queries.py</code>\n\n"
                    "مثال:\n"
                    "<code>def get_top_X(limit=10, since=None):\n"
                    "    conn = get_db_conn()\n"
                    "    cursor = conn.cursor()\n"
                    "    since = since or 0\n"
                    "    cursor.execute('SELECT ... WHERE ts >= ?', (since,))\n"
                    "    return [dict(r) for r in cursor.fetchall()]</code>\n\n"
                    "2️⃣ أضف أمر نصي في <code>_COMMANDS</code> داخل:\n"
                    "<code>handlers/analytics_handler.py</code>\n\n"
                    "3️⃣ أضف formatter في نفس الملف:\n"
                    "<code>def _fmt_X(since, period): ...</code>\n\n"
                    "4️⃣ أضف case في <code>_dispatch()</code>\n\n"
                    "📅 <b>دعم الفترات الزمنية تلقائي:</b>\n"
                    "كل دالة تقبل <code>since</code> (Unix timestamp).\n"
                    "<code>_resolve_period(text)</code> يحوّل الكلمة المفتاحية\n"
                    "إلى timestamp تلقائياً."
                ),
            },
            {
                "title": "📊 الأوامر المتاحة",
                "content": (
                    "📦 <b>أصول المدن:</b>\n"
                    "• <code>إحصائيات الأصول</code> — أكثر الأصول شراءً\n"
                    "• <code>أكثر ترقية</code> — أكثر الأصول ترقيةً\n"
                    "• <code>أكبر منفقين</code> — أكثر اللاعبين إنفاقاً\n\n"
                    "💸 <b>التحويلات البنكية:</b>\n"
                    "• <code>إحصائيات التحويلات</code> — حجم + أكثر المرسلين\n\n"
                    "⚔️ <b>الحرب:</b>\n"
                    "• <code>إحصائيات المعارك</code> — ملخص + أكثر الفائزين\n"
                    "• <code>أكثر هجوما</code> — أكثر الدول هجوماً\n"
                    "• <code>إحصائيات التجسس</code> — نجاح التجسس\n"
                    "• <code>إحصائيات الاستكشاف</code> — مهام الاستكشاف\n"
                    "• <code>أكبر منفقين حرب</code> — إنفاق الحرب\n\n"
                    "📅 <b>الفترات:</b>\n"
                    "افتراضي = هذا الشهر\n"
                    "أضف <code>الأسبوع</code> أو <code>كل الوقت</code> للتغيير"
                ),
            },
        ],
    },

    "bank_account_cmd": {
        "emoji": "🏦",
        "title": "أمر حسابي / حسابه",
        "pages": [
            {
                "title": "🏦 كيف يعمل الأمر",
                "content": (
                    "📌 <b>الأوامر:</b>\n"
                    "• <code>حسابي</code> — يعرض حساب المرسل\n"
                    "• <code>حسابه</code> + رد على رسالة — يعرض حساب المستهدف\n\n"
                    "🔄 <b>منطق التحديد:</b>\n"
                    "<code>if text == 'حسابه' and message.reply_to_message:\n"
                    "    target_id = message.reply_to_message.from_user.id\n"
                    "else:\n"
                    "    target_id = message.from_user.id</code>\n\n"
                    "📋 <b>البيانات المعروضة:</b>\n"
                    "• رقم الحساب (Telegram user_id)\n"
                    "• الرصيد من <code>user_accounts.balance</code>\n"
                    "• القروض من <code>loans</code> حيث status IN ('active','overdue')\n"
                    "• مجموع الدين المتبقي = amount - repaid لكل قرض\n\n"
                    "✅ <b>إذا لا يوجد حساب:</b>\n"
                    "يُعرض رسالة واضحة — لا يُرمى خطأ."
                ),
            },
            {
                "title": "🏦 الكود المرجعي",
                "content": (
                    "📌 <b>الدالة الرئيسية:</b>\n"
                    "<code>_build_account_info(target_user_id, display_name)</code>\n"
                    "في: <code>modules/bank/commands/bank_commands.py</code>\n\n"
                    "📌 <b>الاستعلامات المستخدمة:</b>\n"
                    "• <code>check_bank_account(user_id)</code>\n"
                    "  → SELECT balance FROM user_accounts WHERE user_id=?\n\n"
                    "• <code>get_user_balance(user_id)</code>\n"
                    "  → SELECT balance FROM user_accounts WHERE user_id=?\n\n"
                    "• <code>get_active_loans(user_id)</code>\n"
                    "  → SELECT ... FROM loans WHERE user_id=?\n"
                    "    AND status IN ('active','overdue')\n\n"
                    "📌 <b>لإضافة حقل جديد:</b>\n"
                    "عدّل <code>_build_account_info()</code> فقط —\n"
                    "لا تحتاج لتغيير أي handler آخر."
                ),
            },
        ],
    },

    "constants": {
        "emoji": "⚙️",
        "title": "لوحة المطور",
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
                    "2️⃣ اضغط: 🛠 لوحة المطور\n"
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
            {
                "title": "👤 دعم @username في أوامر الإدارة",
                "content": (
                    "📌 <b>الميزة:</b>\n"
                    "أوامر الكتم والحظر والتقييد وترقية المشرف\n"
                    "تقبل الآن <code>@username</code> مباشرةً في نص الأمر.\n\n"
                    "📋 <b>أمثلة:</b>\n"
                    "<code>كتم @username</code>\n"
                    "<code>حظر @username</code>\n"
                    "<code>تقييد @username</code>\n"
                    "<code>رفع مشرف @username</code>\n\n"
                    "🔄 <b>آلية العمل:</b>\n"
                    "1️⃣ البوت يستخرج @username من نص الأمر\n"
                    "2️⃣ يبحث عنه في جدول <code>users</code> (عمود <code>username</code>)\n"
                    "3️⃣ يحوّله إلى <code>user_id</code> ويكمل الأمر عادياً\n\n"
                    "⚠️ <b>شرط:</b>\n"
                    "المستخدم يجب أن يكون قد تفاعل مع البوت مسبقاً\n"
                    "حتى يكون username محفوظاً في قاعدة البيانات.\n\n"
                    "📌 <b>الكود المرجعي:</b>\n"
                    "• <code>get_user_id_by_username()</code> في:\n"
                    "  <code>database/db_queries/users_queries.py</code>\n"
                    "• <code>get_target_user()</code> في:\n"
                    "  <code>handlers/group_admin/restrictions.py</code>"
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
                    "جميع هذه القيم تُعدَّل من <code>لوحة الإدارة → 🛠 لوحة المطور</code>\n\n"
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
                    "📌 <b>لوحة الإدارة:</b>\n"
                    "من <code>لوحة الإدارة</code> → 🛠 لوحة المطور\n\n"
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
                    "يمكن تعديل هذه القيم من <code>لوحة الإدارة → 🛠 لوحة المطور</code>\n\n"
                    "• <code>daily_ticket_limit</code> — حد التذاكر اليومي للمستخدم (2)\n"
                    "• <code>ticket_cooldown_sec</code> — كولداون بين التذاكر (10 ثانية)\n\n"
                    "📌 <b>مجموعة المطورين:</b>\n"
                    "معرف المجموعة محفوظ في: <code>dev_group_id</code>\n"
                    "يمكن تعديله من لوحة المطور إذا تغيرت المجموعة"
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

    "quotes_feature": {
        "emoji": "💬",
        "title": "الاقتباسات التلقائية",
        "pages": [
            {
                "title": "💬 كيف تعمل الاقتباسات التلقائية",
                "content": (
                    "📌 <b>الملفات المعنية:</b>\n"
                    "• <code>modules/content_hub/quotes_sender.py</code> — المنطق الرئيسي\n"
                    "• <code>modules/content_hub/seed_content.py</code> — البيانات الافتراضية\n"
                    "• <code>database/daily_tasks.py</code> — التسجيل في المُجدوِل\n\n"
                    "🔄 <b>دورة الحياة:</b>\n"
                    "1️⃣ المُجدوِل يستدعي <code>send_periodic_quotes()</code> كل 5 دقائق\n"
                    "2️⃣ تقرأ الدالة <code>quotes_interval_minutes</code> من bot_constants\n"
                    "3️⃣ تجلب المجموعات التي <code>quotes_enabled = 1</code>\n"
                    "4️⃣ لكل مجموعة: تتحقق من آخر إرسال (throttle في الذاكرة)\n"
                    "5️⃣ إذا حان الوقت → تختار جدولاً عشوائياً من الخمسة\n"
                    "6️⃣ تجلب صفاً عشوائياً بكفاءة عبر <code>random_key</code>\n"
                    "7️⃣ ترسل المحتوى للمجموعة\n\n"
                    "⚙️ <b>الثابت القابل للتعديل:</b>\n"
                    "• <code>quotes_interval_minutes</code> — الفترة بالدقائق (افتراضي: 10)"
                ),
            },
            {
                "title": "💬 التفعيل والإيقاف",
                "content": (
                    "📌 <b>أوامر المشرف:</b>\n"
                    "• <code>تفعيل الاقتباسات</code> — يضع <code>quotes_enabled=1</code>\n"
                    "• <code>إيقاف الاقتباسات</code> — يضع <code>quotes_enabled=0</code>\n\n"
                    "📌 <b>في الكود:</b>\n"
                    "<code>from modules.content_hub.quotes_sender import toggle_quotes\n"
                    "toggle_quotes(tg_group_id, enable=True)</code>\n\n"
                    "📌 <b>جداول المحتوى (في content_hub.db):</b>\n"
                    "• <code>quotes</code> — اقتباسات\n"
                    "• <code>anecdotes</code> — نوادر\n"
                    "• <code>stories</code> — قصص\n"
                    "• <code>wisdom</code> — حكم\n"
                    "• <code>poetry</code> — شعر\n\n"
                    "📌 <b>إضافة محتوى جديد:</b>\n"
                    "من لوحة المطور → 📜 اقتباسات\n"
                    "أو عبر <code>insert_content(table, text)</code> في hub_db.py"
                ),
            },
        ],
    },

    "rankings": {
        "emoji": "🏆",
        "title": "ترتيبات المجلة",
        "pages": [
            {
                "title": "🏆 ما هي ترتيبات المجلة؟",
                "content": (
                    "نظام تلقائي يحسب ترتيبات اللاعبين أسبوعياً وشهرياً\n"
                    "ويُنشرها في المجلة مع مكافآت للفائزين.\n\n"
                    "📅 <b>التوقيت:</b>\n"
                    "• <b>أسبوعي</b> — كل يوم اثنين منتصف الليل (توقيت اليمن)\n"
                    "• <b>شهري</b> — أول يوم من كل شهر منتصف الليل\n\n"
                    "🏆 <b>ترتيبات الأسبوع:</b>\n"
                    "• 💰 أغنى لاعب\n"
                    "• ⚔️ محارب الأسبوع (أكثر انتصارات)\n"
                    "• 🕵️ جاسوس الأسبوع (أنجح عمليات)\n"
                    "• 📦 الأصل الأكثر شراءً\n"
                    "• 📤 أكثر المحوّلين\n"
                    "• 😇 أفضل سمعة / 😈 أسوأ سمعة\n\n"
                    "🌟 <b>ترتيبات الشهر:</b>\n"
                    "• 🏆 أكثر الدول انتصاراً (مع ميداليات 🥇🥈🥉)\n"
                    "• 💎 أثرى لاعب\n"
                    "• 🗡 أكثر الدول هجوماً\n"
                    "• 🏙 أكثر المنفقين على المدن\n"
                    "• 🌍 أقوى تحالف\n"
                    "• 🌟 متصدر الموسم الحالي"
                ),
            },
            {
                "title": "🏆 المكافآت والثوابت",
                "content": (
                    "🎁 <b>المكافآت تُدفع تلقائياً:</b>\n"
                    "عند نشر الترتيب، يحصل كل فائز على مكافأة\n"
                    "مباشرة في حسابه البنكي.\n\n"
                    "⚙️ <b>ثوابت المكافآت (قابلة للتعديل):</b>\n"
                    "• <code>weekly_ranking_reward</code> — مكافأة بطل الأسبوع (500)\n"
                    "• <code>monthly_ranking_reward</code> — مكافأة بطل الشهر (2000)\n\n"
                    "📌 <b>لتعديل المكافآت:</b>\n"
                    "<code>لوحة الإدارة</code> → 🛠 لوحة المطور\n"
                    "ابحث عن <code>weekly_ranking_reward</code>\n\n"
                    "📰 <b>النشر في المجلة:</b>\n"
                    "كل ترتيب يُنشر كمنشور في المجلة تلقائياً.\n"
                    "اللاعبون يرونه بكتابة <code>المجلة</code>."
                ),
            },
            {
                "title": "🏆 الكود المرجعي",
                "content": (
                    "📌 <b>الملف الرئيسي:</b>\n"
                    "<code>modules/magazine/rankings.py</code>\n\n"
                    "📌 <b>الدوال الرئيسية:</b>\n"
                    "• <code>publish_weekly_rankings()</code>\n"
                    "  ينشر ترتيب الأسبوع ويدفع المكافآت\n\n"
                    "• <code>publish_monthly_rankings()</code>\n"
                    "  ينشر ترتيب الشهر ويدفع المكافآت\n\n"
                    "• <code>maybe_publish_weekly()</code>\n"
                    "  تُستدعى من المُجدوِل — تتحقق إذا كان اليوم اثنين\n\n"
                    "• <code>maybe_publish_monthly()</code>\n"
                    "  تُستدعى من المُجدوِل — تتحقق إذا كان اليوم الأول\n\n"
                    "📌 <b>التسجيل في المُجدوِل:</b>\n"
                    "في <code>database/daily_tasks.py</code>:\n"
                    "<code>@register_daily\n"
                    "def publish_magazine_rankings():\n"
                    "    _safe(_do_weekly_rankings)\n"
                    "    _safe(_do_monthly_rankings)</code>\n\n"
                    "📌 <b>لإضافة ترتيب جديد:</b>\n"
                    "أضف حساب البيانات في <code>rankings.py</code>\n"
                    "واستدعِ <code>db.add_post(title, body, 0)</code>"
                ),
            },
        ],
    },

    "quran_systems": {
        "emoji": "📖",
        "title": "نظام القرآن",
        "pages": [
            {
                "title": "📖 الأنظمة + Streak + Dedup",
                "content": (
                    "📖 <b>التلاوة:</b> <code>user_quran_progress</code>\n"
                    "📚 <b>قراءة سورة:</b> <code>surah_read_progress</code>\n"
                    "🕌 <b>الختمة:</b> <code>khatma_progress</code>\n\n"
                    "🛡 <b>منع التكرار:</b>\n"
                    "<code>khatma_counted_ayat(user_id, ayah_id, log_date)</code>\n"
                    "كل آية تُحسب مرة واحدة يومياً فقط.\n\n"
                    "🔥 <b>Streak — سماحية 7 أيام:</b>\n"
                    "• gap == 0 → نفس اليوم، لا تغيير\n"
                    "• gap == 1 → streak + 1\n"
                    "• gap ≤ 7 → streak + 1 (grace period)\n"
                    "• gap > 7 → reset to 1\n\n"
                    "🏆 <b>الإنجازات:</b>\n"
                    "<code>khatma_achievements_seen(user_id, key)</code>\n"
                    "• total_read ≥ 1000 → قارئ نشيط\n"
                    "• streak ≥ 7 → أسبوع متواصل\n"
                    "تُعلَن مرة واحدة فقط."
                ),
            },
            {
                "title": "🔔 تذكيرات + التذاكر",
                "content": (
                    "🔔 <b>تذكيرات الختمة:</b>\n"
                    "<code>khatma_reminders</code> — max 2\n"
                    "المُجدوِل: <code>khatmah_reminder.py</code>\n"
                    "Silent fail إذا حجب المستخدم البوت.\n\n"
                    "📱 <b>شرط الخاص:</b>\n"
                    "<code>bot.send_chat_action(uid, 'typing')</code>\n"
                    "إذا فشل → <code>send_private_access_panel()</code>\n\n"
                    "🎫 <b>التذاكر — نص فقط:</b>\n"
                    "في <code>handle_ticket_message_input()</code>:\n"
                    "<code>if not message.text: → رفض + رسالة واضحة</code>\n"
                    "الصور والملصقات والملفات مرفوضة.\n"
                    "لا crash — يُرجع True ويُعلم المستخدم."
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

    "post_creator": {
        "emoji": "📝",
        "title": "إنشاء المنشورات",
        "pages": [
            {
                "title": "📝 Post Creator — نظرة عامة",
                "content": (
                    "📌 <b>الأمر:</b>\n"
                    "<code>إنشاء منشور</code> أو <code>new post</code>\n\n"
                    "📋 <b>خطوات الإنشاء:</b>\n"
                    "1️⃣ اختر وجهة النشر (هذه المحادثة أو معرّف قناة/مجموعة)\n"
                    "2️⃣ هل يحتوي المنشور على صورة؟\n"
                    "3️⃣ أرسل نص المنشور\n"
                    "4️⃣ هل تريد إضافة أزرار؟\n"
                    "5️⃣ اختر عدد الأزرار في كل صف\n"
                    "6️⃣ معاينة → نشر\n\n"
                    "🎨 <b>صيغة الأزرار:</b>\n"
                    "<code>نص | رابط | رقم_اللون</code>\n"
                    "• 1 = أزرق  • 2 = أخضر  • 3 = أحمر\n\n"
                    "📌 <b>ملاحظة:</b> للمطورين فقط."
                ),
            },
            {
                "title": "📝 التحقق من الوجهة",
                "content": (
                    "عند إدخال معرّف قناة/مجموعة، يتحقق البوت تلقائياً من:\n\n"
                    "✅ <b>الفحوصات:</b>\n"
                    "• هل البوت عضو في الوجهة؟\n"
                    "• هل البوت مشرف في القناة؟\n"
                    "• هل يملك صلاحية نشر الرسائل؟\n\n"
                    "❌ <b>إذا فشل الفحص:</b>\n"
                    "يُعرض خطأ واضح ويُطلب معرّف آخر.\n"
                    "لا يتقدم التدفق حتى تُحلّ المشكلة.\n\n"
                    "📌 <b>أسباب شائعة للفشل:</b>\n"
                    "• البوت لم يُضَف للقناة بعد\n"
                    "• البوت ليس مشرفاً في القناة\n"
                    "• صلاحية 'نشر الرسائل' غير مفعّلة للبوت\n"
                    "• المعرّف خاطئ أو القناة غير موجودة"
                ),
            },
        ],
    },

    "economy_stats": {
        "emoji": "📊",
        "title": "إحصائيات الاقتصاد",
        "pages": [
            {
                "title": "📊 ما هي economy_stats؟",
                "content": (
                    "جدول <code>economy_stats</code> هو الطبقة الاقتصادية الكلية للعبة.\n"
                    "يخزن مؤشرات الاقتصاد العالمي كأزواج مفتاح/قيمة.\n\n"
                    "📋 <b>المفاتيح المتاحة:</b>\n"
                    "• <code>inflation</code> — مؤشر التضخم (0.75–2.5)\n"
                    "  يُحسب من: إجمالي الأموال ÷ 1,000,000 (الخط الأساسي)\n"
                    "  يؤثر على: الرواتب والاستثمار\n\n"
                    "• <code>event_multiplier</code> — مضاعف الحدث العالمي النشط\n"
                    "  يؤثر على: الرواتب، الاستثمار، الغنائم\n\n"
                    "• <code>sink</code> — إجمالي الأموال المسحوبة من التداول\n"
                    "  المصادر: رسوم التحويل + مشتريات الأصول\n\n"
                    "• <code>total_salary_paid</code> — إجمالي الرواتب المدفوعة\n"
                    "• <code>total_investments</code> — عدد عمليات الاستثمار\n"
                    "• <code>total_investment_profit/loss</code> — أرباح/خسائر الاستثمار\n"
                    "• <code>total_transfers</code> — عدد التحويلات البنكية\n"
                    "• <code>total_transfer_volume</code> — حجم التحويلات\n"
                    "• <code>total_transfer_fees</code> — رسوم التحويل المحصّلة\n"
                    "• <code>total_city_spending</code> — إجمالي الإنفاق على المدن"
                ),
            },
            {
                "title": "📊 كيف يؤثر التضخم على اللعبة",
                "content": (
                    "🔄 <b>دورة التضخم:</b>\n\n"
                    "1️⃣ <b>حساب التضخم:</b>\n"
                    "<code>inflation = total_money / 1,000,000</code>\n"
                    "مقيّد بين 0.75 و 2.5\n\n"
                    "2️⃣ <b>تأثيره على الراتب:</b>\n"
                    "<code>adapt_salary_amount(base, user_id)</code>\n"
                    "• تضخم عالٍ → راتب أقل (القوة الشرائية تنخفض)\n"
                    "• تضخم منخفض → راتب أعلى\n"
                    "• الأرصدة الكبيرة تحصل على راتب أقل (soft cap)\n\n"
                    "3️⃣ <b>تأثيره على الاستثمار:</b>\n"
                    "<code>adapt_investment_outcome(amount)</code>\n"
                    "• تضخم عالٍ → أرباح أقل، خسائر أكبر\n"
                    "• تضخم منخفض → فرص ربح أفضل\n\n"
                    "4️⃣ <b>المصارف (Money Sink):</b>\n"
                    "رسوم التحويل + مشتريات الأصول تُسحب من التداول\n"
                    "هذا يخفض التضخم تدريجياً"
                ),
            },
            {
                "title": "📊 قراءة وكتابة economy_stats في الكود",
                "content": (
                    "📌 <b>القراءة:</b>\n"
                    "<code>from database.db_queries.economy_queries import get_economy_stat\n\n"
                    "inflation = get_economy_stat('inflation', 1.0)\n"
                    "# الوسيط الثاني = القيمة الافتراضية إذا لم يوجد المفتاح</code>\n\n"
                    "📌 <b>الكتابة:</b>\n"
                    "<code>from database.db_queries.economy_queries import set_economy_stat\n\n"
                    "set_economy_stat('inflation', 1.25)\n"
                    "# يُحدَّث تلقائياً مع last_updated</code>\n\n"
                    "📌 <b>تحديث التضخم (يدوياً أو من daily_tasks):</b>\n"
                    "<code>from modules.economy.services.economy_service import compute_inflation_index\n\n"
                    "compute_inflation_index()  # يحسب ويحفظ تلقائياً</code>\n\n"
                    "⚠️ <b>ملاحظة:</b>\n"
                    "جميع القيم مخزنة كـ TEXT في DB.\n"
                    "<code>get_economy_stat</code> تُعيدها كـ float تلقائياً."
                ),
            },
            {
                "title": "📊 أين تُستخدم economy_stats في اللعبة",
                "content": (
                    "🏦 <b>البنك:</b>\n"
                    "• <code>salary()</code> — يطبق التضخم + soft cap على الراتب\n"
                    "• <code>invest()</code> — يستخدم <code>adapt_investment_outcome()</code>\n"
                    "• <code>transfer_funds()</code> — يسجل الرسوم في <code>sink</code>\n\n"
                    "🏙 <b>المدن والأصول:</b>\n"
                    "• <code>buy_asset()</code> / <code>upgrade_asset()</code>\n"
                    "  يسجل الإنفاق في <code>total_city_spending</code> و <code>sink</code>\n\n"
                    "🌍 <b>الأحداث العالمية:</b>\n"
                    "• <code>event_generator()</code> يكتب <code>event_multiplier</code>\n"
                    "• <code>get_event_multiplier()</code> يقرأه في الحسابات\n\n"
                    "📅 <b>المهام اليومية:</b>\n"
                    "• <code>compute_inflation_index()</code> يُشغَّل يومياً\n"
                    "  لتحديث <code>inflation</code> بناءً على إجمالي الأموال"
                ),
            },
        ],
    },

    "system_events": {
        "emoji": "🌍",
        "title": "الأحداث العالمية",
        "pages": [
            {
                "title": "🌍 ما هي الأحداث العالمية؟",
                "content": (
                    "الأحداث العالمية هي تأثيرات مؤقتة تُطبَّق على جميع اللاعبين في نفس الوقت.\n\n"
                    "📋 <b>أنواع الأحداث:</b>\n"
                    "• ⚔️ حرب — تعزيز الهجوم أو الدفاع\n"
                    "• 💰 اقتصاد — زيادة الدخل أو الرواتب\n"
                    "• 🕵️ تجسس — تعزيز نجاح العمليات\n"
                    "• 🏰 تحالفات — تعزيز الدعم والخبرة\n"
                    "• 🌪️ كوارث — تأثيرات سلبية مؤقتة\n"
                    "• 🌟 تقدم — زيادة الخبرة والنفوذ\n\n"
                    "⏱️ <b>المدة:</b> من 4 إلى 12 ساعة حسب نوع الحدث.\n\n"
                    "📌 <b>أمر المستخدم:</b>\n"
                    "<code>الأحداث</code> ← يعرض الحدث النشط وتأثيره"
                ),
            },
            {
                "title": "⚙️ كيف تعمل الأحداث — للمطور",
                "content": (
                    "🔄 <b>دورة حياة الحدث:</b>\n\n"
                    "1️⃣ <b>الإطلاق (Trigger):</b>\n"
                    "<code>trigger_random_event()</code>\n"
                    "• يتحقق أولاً: هل يوجد حدث نشط؟\n"
                    "• إذا نعم → لا يُطلق حدثاً جديداً\n"
                    "• إذا لا → يختار حدثاً عشوائياً من <code>EVENT_POOL</code>\n\n"
                    "2️⃣ <b>الحفظ في DB:</b>\n"
                    "يُحفظ في جدول <code>global_events</code> بحالة <code>active</code>\n\n"
                    "3️⃣ <b>الإشعار:</b>\n"
                    "<code>_notify_event_start()</code> → يُرسَل لمجموعة المطورين\n\n"
                    "4️⃣ <b>الإنهاء التلقائي:</b>\n"
                    "<code>_schedule_event_end()</code> → thread منفصل ينتظر المدة\n"
                    "ثم يُحدّث الحالة إلى <code>ended</code> ويُرسَل إشعار الانتهاء"
                ),
            },
            {
                "title": "🔧 استخدام تأثير الحدث في الكود",
                "content": (
                    "📌 <b>كيف تقرأ تأثير الحدث النشط:</b>\n\n"
                    "<code>from modules.progression.global_events import get_event_effect\n\n"
                    "bonus = get_event_effect('atk_bonus')\n"
                    "# يرجع 0.15 إذا كان حدث الحرب نشطاً\n"
                    "# يرجع 0.0 إذا لم يكن هناك حدث أو المفتاح مختلف\n\n"
                    "final_attack = base_attack * (1 + bonus)</code>\n\n"
                    "📋 <b>مفاتيح التأثير المتاحة:</b>\n"
                    "• <code>atk_bonus</code> — تعزيز الهجوم\n"
                    "• <code>def_bonus</code> — تعزيز الدفاع\n"
                    "• <code>income_bonus</code> — تعزيز الدخل\n"
                    "• <code>salary_bonus</code> — تعزيز الرواتب\n"
                    "• <code>loot_bonus</code> — تعزيز الغنائم\n"
                    "• <code>spy_success_bonus</code> — تعزيز التجسس\n"
                    "• <code>xp_bonus</code> — تعزيز الخبرة\n"
                    "• <code>troop_cost_discount</code> — خصم الجنود"
                ),
            },
            {
                "title": "⏱️ الجدولة التلقائية",
                "content": (
                    "🔄 <b>كيف تُطلَق الأحداث تلقائياً:</b>\n\n"
                    "<code>schedule_event_checker()</code>\n"
                    "• يعمل في thread منفصل عند بدء البوت\n"
                    "• يفحص كل ساعة (قابل للتعديل: <code>event_check_interval</code>)\n"
                    "• احتمال 30% لإطلاق حدث جديد في كل فحص\n"
                    "• لا يُطلق حدثاً إذا كان هناك حدث نشط\n\n"
                    "📌 <b>مثال عملي:</b>\n"
                    "• الساعة 12:00 → فحص → لا حدث نشط → 30% احتمال\n"
                    "• إذا نجح → يُطلق 'ازدهار اقتصادي' لمدة 12 ساعة\n"
                    "• الساعة 13:00 → فحص → حدث نشط → لا شيء\n"
                    "• الساعة 00:00 → الحدث ينتهي → إشعار للمطورين\n\n"
                    "⚙️ <b>لإطلاق حدث يدوياً:</b>\n"
                    "<code>from modules.progression.global_events import trigger_random_event\n"
                    "trigger_random_event()</code>"
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
