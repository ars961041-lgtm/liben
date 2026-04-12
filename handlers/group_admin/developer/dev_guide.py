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
            {
                "title": "🔗 رابط المجموعة",
                "content": (
                    "📌 <b>الملف المعني:</b>\n"
                    "• <code>handlers/command_handlers/group_commands.py</code> — دالة <code>_send_group_link</code>\n\n"
                    "▶️ <b>المشغّلات:</b>\n"
                    "• <code>الرابط</code>\n"
                    "• <code>رابط القروب</code>\n\n"
                    "🔄 <b>التدفق:</b>\n"
                    "1️⃣ يستدعي <code>bot.export_chat_invite_link(cid)</code>\n"
                    "2️⃣ يبني رسالة HTML مع اسم الطالب + ID + اسم المجموعة\n"
                    "3️⃣ يُرفق زر URL مباشر 🔗 رابط المجموعة\n"
                    "4️⃣ عند فشل جلب الرابط → رسالة خطأ واضحة بدون crash\n\n"
                    "⚙️ <b>الصلاحية المطلوبة:</b>\n"
                    "البوت يجب أن يكون مشرفاً بصلاحية <b>دعوة المستخدمين</b>.\n\n"
                    "📌 <b>ملاحظة:</b>\n"
                    "يعمل في المجموعات فقط — لا يستجيب في الخاص أو القنوات."
                ),
            },
        ],
    },

    "azkar_content": {
        "emoji": "📿",
        "title": "نظام الأذكار (المحتوى)",
        "pages": [
            {
                "title": "📿 نظام الأذكار — نظرة عامة",
                "content": (
                    "نظام الأذكار نوع محتوى مستقل مع دعم النشر التلقائي.\n\n"
                    "▶️ <b>أمر المستخدم:</b>\n"
                    "• <code>أذكار</code> — يعرض ذكراً عشوائياً\n"
                    "• <code>أذكار [رقم]</code> — يعرض ذكراً بمعرف محدد\n\n"
                    "⚙️ <b>التفعيل التلقائي (للمشرفين):</b>\n"
                    "• <code>تفعيل الأذكار</code> — يبدأ الإرسال التلقائي\n"
                    "• <code>إيقاف الأذكار</code> — يوقف الإرسال\n\n"
                    "🗄 <b>قاعدة البيانات:</b>\n"
                    "• جدول <code>azkar</code> في <code>content_hub.db</code>\n"
                    "• عمود <code>azkar_enabled</code> في جدول <code>groups</code>\n\n"
                    "📌 <b>الملفات المعنية:</b>\n"
                    "• <code>modules/content_hub/azkar_sender.py</code> — المُرسِل التلقائي\n"
                    "• <code>modules/content_hub/hub_db.py</code> — تعريف الجدول\n"
                    "• <code>database/db_schema/groups.py</code> — عمود <code>azkar_enabled</code>\n"
                    "• <code>database/daily_tasks.py</code> — تسجيل <code>send_azkar</code>"
                ),
            },
            {
                "title": "📿 الفرق بين الأذكار والاقتباسات",
                "content": (
                    "📊 <b>مقارنة النظامين:</b>\n\n"
                    "💬 <b>الاقتباسات (quotes_sender):</b>\n"
                    "• جدول: <code>quotes</code> فقط\n"
                    "• عمود التفعيل: <code>quotes_enabled</code>\n"
                    "• الأمر: <code>تفعيل الاقتباسات</code> / <code>إيقاف الاقتباسات</code>\n"
                    "• الثابت: <code>quotes_interval_minutes</code>\n\n"
                    "📿 <b>الأذكار (azkar_sender):</b>\n"
                    "• جدول: <code>azkar</code> فقط\n"
                    "• عمود التفعيل: <code>azkar_enabled</code>\n"
                    "• الأمر: <code>تفعيل الأذكار</code> / <code>إيقاف الأذكار</code>\n"
                    "• الثابت: <code>azkar_interval_minutes</code>\n\n"
                    "⛔ <b>لا تُرسَل تلقائياً:</b>\n"
                    "anecdotes / stories / wisdom / poetry\n"
                    "هذه تُعرض بالأمر المباشر فقط.\n\n"
                    "📌 <b>إدارة المحتوى:</b>\n"
                    "<code>لوحة الإدارة</code> → 📚 إدارة المحتوى → 📿 أذكار\n"
                    "الجدول فارغ عند الإنشاء — يُملأ من لوحة المطور أو seed."
                ),
            },
        ],
    },

    "quran_khatmah": {
        "emoji": "📖",
        "title": "نظام القرآن والختمة",
        "pages": [
            {
                "title": "📖 أوامر القرآن — نظرة عامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/quran/quran_handler.py</code> — dispatcher الأوامر\n"
                    "• <code>modules/quran/khatmah.py</code> — منطق الختمة والإعدادات\n"
                    "• <code>modules/quran/surah_reader.py</code> — عرض الآيات والتنقل\n"
                    "• <code>modules/quran/quran_db.py</code> — طبقة قاعدة البيانات\n"
                    "• <code>modules/quran/quran_service.py</code> — منطق الأعمال\n"
                    "• <code>modules/quran/quran_ui.py</code> — بناء النصوص والأزرار\n\n"
                    "▶️ <b>أوامر المستخدم:</b>\n"
                    "• <code>ختمتي</code> — يعرض الآية التالية مباشرة\n"
                    "• <code>إعدادات ختمة</code> — لوحة الإحصائيات والإعدادات\n"
                    "• <code>تذكير ختمتي</code> — إعداد تذكيرات يومية\n"
                    "• <code>تلاوة</code> — استئناف التلاوة الحرة\n"
                    "• <code>قراءة سورة</code> — قراءة سورة بعينها\n"
                    "• <code>مفضلتي</code> — الآيات المحفوظة\n"
                    "• <code>آية [كلمة]</code> — بحث في القرآن\n\n"
                    "▶️ <b>أوامر المطور:</b>\n"
                    "• <code>إضافة آيات</code> — واجهة إضافة آيات\n"
                    "• <code>إضافة تفسير</code> — واجهة إضافة تفاسير\n"
                    "• <code>اضف آيات [سورة] [رقم]</code> — إضافة نصية مباشرة\n"
                    "• <code>عدل آية [id]</code> — تعديل نص آية\n"
                    "• <code>عدل تفسير [id]</code> — تعديل تفسير"
                ),
            },
            {
                "title": "🕌 ختمتي — التدفق التقني",
                "content": (
                    "📌 <b>الأمر الجديد:</b> <code>ختمتي</code>\n"
                    "يعرض الآية التالية مباشرة — بدون لوحة أو قوائم.\n\n"
                    "🔄 <b>التدفق:</b>\n"
                    "1️⃣ <code>handle_khatmah_read_command(message)</code>\n"
                    "2️⃣ <code>db.get_khatma(uid)</code> → last_surah + last_ayah\n"
                    "3️⃣ <code>db.get_ayah_by_sura_number(surah, ayah)</code>\n"
                    "4️⃣ <code>_show_khatmah_ayah(uid, cid, ayah)</code>\n"
                    "5️⃣ <code>db.update_khatma(uid, sura_id, ayah_number)</code>\n\n"
                    "📌 <b>الأمر الجديد:</b> <code>إعدادات ختمة</code>\n"
                    "يفتح لوحة الإحصائيات والإعدادات.\n\n"
                    "🔄 <b>التدفق:</b>\n"
                    "1️⃣ <code>handle_khatmah_settings_command(message)</code>\n"
                    "2️⃣ <code>_show_khatmah_settings(cid, uid)</code>\n\n"
                    "📌 <b>أزرار الإعدادات:</b>\n"
                    "• <code>kh_continue</code> → <code>_show_khatmah_ayah</code>\n"
                    "• <code>kh_goal_panel</code> → هدف يومي\n"
                    "• <code>kh_rem_panel</code> → تذكيرات\n"
                    "• <code>kh_reset_prompt</code> → إعادة ضبط\n\n"
                    "⚠️ <b>لا توجد قائمة سور في تدفق الختمة</b>\n"
                    "التنقل يعبر السور تلقائياً عبر <code>get_next_ayah(aid)</code>"
                ),
            },
            {
                "title": "🔘 أزرار القراءة — kh_next / kh_prev",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/quran/surah_reader.py</code>\n\n"
                    "🔄 <b>التنقل المتواصل:</b>\n"
                    "• <code>kh_next</code> → <code>db.get_next_ayah(aid)</code>\n"
                    "  يعبر السور تلقائياً — بدون قيد <code>sura_id</code>\n"
                    "• <code>kh_prev</code> → <code>db.get_prev_ayah(aid)</code>\n"
                    "  نفس المنطق للخلف\n\n"
                    "📌 <b>الدالة الرئيسية:</b>\n"
                    "<code>_show_khatmah_ayah(uid, cid, ayah, call, reply_to, returned)</code>\n\n"
                    "تقوم بـ:\n"
                    "1️⃣ <code>db.save_surah_read_progress(uid, sura_id, ayah_number)</code>\n"
                    "2️⃣ <code>db.update_khatma(uid, sura_id, ayah_number)</code>\n"
                    "3️⃣ بناء نص الآية مع اسم السورة + رقم الآية\n"
                    "4️⃣ أزرار: التالية، السابقة، تفسير، مفضلة، 🔙 ختمتي\n\n"
                    "📌 <b>أزرار التفسير والمفضلة:</b>\n"
                    "• <code>kh_tafseer</code> / <code>kh_show_tafseer</code>\n"
                    "• <code>kh_fav</code> — toggle المفضلة\n"
                    "• <code>kh_back_main</code> → <code>_show_khatmah_settings</code>"
                ),
            },
            {
                "title": "🗄 قاعدة بيانات الختمة",
                "content": (
                    "📌 <b>الجداول:</b>\n\n"
                    "• <code>khatma_progress</code>\n"
                    "  user_id, last_surah, last_ayah, total_read, updated_at\n\n"
                    "• <code>khatma_goals</code>\n"
                    "  user_id, daily_target\n\n"
                    "• <code>khatma_daily_log</code>\n"
                    "  user_id, log_date, count\n\n"
                    "• <code>khatma_streak</code>\n"
                    "  user_id, current_streak, last_read_date\n\n"
                    "• <code>khatma_reminders</code>\n"
                    "  id, user_id, hour, minute, tz_offset, enabled\n\n"
                    "• <code>khatma_counted_ayat</code>\n"
                    "  user_id, ayah_id, log_date — منع تكرار العد\n\n"
                    "📌 <b>الدوال الرئيسية في quran_db.py:</b>\n"
                    "• <code>get_khatma(uid)</code> — آخر موضع\n"
                    "• <code>update_khatma(uid, surah_id, ayah_number)</code>\n"
                    "• <code>reset_khatma(uid)</code> — إعادة من الفاتحة\n"
                    "• <code>get_streak(uid)</code> / <code>get_today_count(uid)</code>\n"
                    "• <code>get_due_khatma_reminders(utc_h, utc_m)</code>"
                ),
            },
        ],
    },

    "invite_commands": {
        "emoji": "📩",
        "title": "أوامر الدعوات السريعة",
        "pages": [
            {
                "title": "📩 دعوة تحالف — التقنية",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/alliances/alliance_commands.py</code>\n"
                    "📌 <b>الدالة:</b> <code>_quick_invite(message)</code>\n\n"
                    "▶️ <b>الأمر:</b> <code>دعوة تحالف</code> (رد على رسالة)\n\n"
                    "🔄 <b>التدفق:</b>\n"
                    "1️⃣ التحقق من وجود رد على رسالة\n"
                    "2️⃣ المُرسِل يجب أن يكون في تحالف\n"
                    "3️⃣ الهدف يجب أن يملك دولة\n"
                    "4️⃣ الهدف يجب ألا يكون في تحالف\n"
                    "5️⃣ استدعاء <code>send_alliance_invite()</code> من <code>alliances_queries</code>\n"
                    "6️⃣ إشعار الهدف في الخاص (صامت عند الفشل)\n\n"
                    "📋 <b>دعوات التحالف:</b>\n"
                    "• <code>دعوات تحالف</code> / <code>دعوات التحالف</code> → نفس الدالة <code>_show_invites()</code>\n\n"
                    "📋 <b>دعوات الدول:</b>\n"
                    "• <code>دعوات الدول</code> → <code>_show_country_invites()</code>\n"
                    "• في: <code>modules/country/country_commands.py</code>\n"
                    "• يستدعي <code>get_pending_country_invites(user_id)</code>"
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
                "title": "👤 تحديد المستخدم المستهدف — resolve_user",
                "content": (
                    "📌 <b>طرق تحديد الهدف (3 طرق):</b>\n"
                    "1️⃣ الرد على رسالة المستخدم\n"
                    "2️⃣ <code>@username</code> في نص الأمر\n"
                    "3️⃣ رقم <code>user_id</code> مباشرة في نص الأمر\n\n"
                    "📋 <b>أمثلة:</b>\n"
                    "<code>كتم @username</code>\n"
                    "<code>حظر 123456789</code>\n"
                    "<code>تقييد @username</code>\n"
                    "<code>رفع مشرف 123456789</code>\n\n"
                    "🔄 <b>دالة الحل الموحدة:</b>\n"
                    "<code>resolve_user(message)</code>\n"
                    "في: <code>handlers/group_admin/restrictions.py</code>\n"
                    "تُرجع: <code>(user_id, name, error_msg)</code>\n\n"
                    "⚠️ <b>حالات الخطأ المعالجة:</b>\n"
                    "• @username غير موجود في DB → رسالة واضحة\n"
                    "• المستخدم مشرف → رفض مع رسالة\n"
                    "• المستخدم ليس في المجموعة → رسالة واضحة\n"
                    "• المستخدم بوت → رفض مع رسالة\n"
                    "• مطور البوت → محمي دائماً\n\n"
                    "📌 <b>الكتم للمطور:</b>\n"
                    "إذا استخدم المطور <code>كتم</code> → يُطبَّق عالمياً تلقائياً\n"
                    "إذا كان للبوت صلاحية الحذف → يحذف الرسائل صامتاً\n"
                    "إذا لم تكن له صلاحية → يتجاهل بصمت (لا خطأ)"
                ),
            },
            {
                "title": "📋 قوائم الإجراءات التأديبية",
                "content": (
                    "📌 <b>الأوامر (للمشرفين):</b>\n"
                    "• <code>المكتومين</code> — قائمة المكتومين في المجموعة\n"
                    "• <code>المحظورين</code> — قائمة المحظورين في المجموعة\n"
                    "• <code>المقيدين</code> — قائمة المقيدين في المجموعة\n\n"
                    "📌 <b>أمر المطور فقط:</b>\n"
                    "• <code>مكتومين سورس</code> — قائمة الكتم العالمي\n\n"
                    "🔄 <b>آلية العمل:</b>\n"
                    "جميع القوائم تمر عبر دالة موحدة:\n"
                    "<code>show_moderation_list(message, list_type)</code>\n"
                    "في: <code>handlers/group_admin/moderation_list.py</code>\n\n"
                    "📋 <b>مصادر البيانات:</b>\n"
                    "• مكتوم/محظور/مقيد → <code>group_members</code>\n"
                    "  (حقول: is_muted, is_banned, is_restricted)\n"
                    "• كتم عالمي → <code>global_mutes</code>\n"
                    "• الأسماء → LEFT JOIN مع <code>users.name</code>\n\n"
                    "📄 <b>التنسيق:</b>\n"
                    "LTR: <code>1. ID: 123456 | Name: Ahmed</code>\n"
                    "10 مستخدمين في الصفحة — أزرار: ➡️ ⬅️ ❌"
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

    "city_sectors": {
        "emoji": "🏙",
        "title": "قطاعات المدينة",
        "pages": [
            {
                "title": "🛒 أمر الشراء المباشر — التقنية",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/country/city_commands.py</code>\n\n"
                    "▶️ <b>الصيغ المدعومة:</b>\n"
                    "• <code>شراء [اسم]</code> — كمية = 1\n"
                    "• <code>شراء [اسم] [كمية]</code>\n"
                    "• <code>شراء [اسم متعدد الكلمات] [كمية]</code>\n\n"
                    "🔒 <b>الحارس المشترك:</b> <code>modules/war/store_guard.py</code>\n"
                    "• <code>require_country(message)</code> — يتحقق من امتلاك دولة\n"
                    "• <code>require_alliance(message)</code> — يتحقق من الانتماء لتحالف\n"
                    "• كلاهما يرسل رسالة خطأ موحدة ويرجع None عند الفشل\n\n"
                    "🗂 <b>تطبيق الحارس على المتاجر:</b>\n"
                    "• <code>متجر</code> / <code>شراء</code> → require_country (عبر city_id)\n"
                    "• <code>متجر القوات</code> / <code>متجر المعدات</code> / <code>متجر العتاد</code> → require_country\n"
                    "• <code>متجر البطاقات</code> → require_country\n"
                    "• <code>متجر التحالف</code> → require_alliance\n\n"
                    "🔄 <b>منطق التحليل (_parse_buy_args):</b>\n"
                    "• يأخذ كل الكلمات بعد 'شراء'\n"
                    "• إذا كانت الكلمة الأخيرة رقماً → كمية\n"
                    "• الباقي → اسم العنصر\n\n"
                    "🔍 <b>منطق البحث (_resolve_item):</b>\n"
                    "يبحث بالترتيب في:\n"
                    "1️⃣ <code>assets</code> (name أو name_ar)\n"
                    "2️⃣ <code>troop_types</code> (name أو name_ar)\n"
                    "3️⃣ <code>equipment_types</code> (name أو name_ar)"
                ),
            },
            {
                "title": "🏙 نظام القطاعات — كيف تعمل",
                "content": (
                    "المدينة تحتوي على 4 قطاعات متشابكة.\n"
                    "كل قطاع يولّد تأثيرات مباشرة وغير مباشرة.\n\n"
                    "🏥 <b>الصحة</b> → <code>stat_health</code>\n"
                    "• يُحسب <code>health_bonus = min(0.25, health × 0.001)</code>\n"
                    "• يُطبَّق في <code>maintenance_service._get_hospital_reduction()</code>\n"
                    "• يقلل تكلفة صيانة الجيش حتى 25%\n\n"
                    "📚 <b>التعليم</b> → <code>stat_education</code>\n"
                    "• يُحسب <code>education_bonus = min(0.20, education × 0.001)</code>\n"
                    "• يُطبَّق كمضاعف على <code>income</code> في <code>calculate_city_effects()</code>\n"
                    "• يزيد دخل المدينة حتى +20%\n\n"
                    "🛣 <b>البنية التحتية</b> → <code>stat_infrastructure</code>\n"
                    "• يُحسب <code>infra_bonus = min(0.20, infrastructure × 0.001)</code>\n"
                    "• يُطبَّق على الدخل (+20%) وعلى قوة الجيش (+15%)\n"
                    "• يُطبَّق في <code>power_calculator.get_country_power()</code>\n\n"
                    "✨ <b>مكافأة التنويع:</b>\n"
                    "إذا كانت المدينة تمتلك أصولاً من جميع القطاعات الأربعة\n"
                    "→ +10% إضافي على الدخل الكلي"
                ),
            },
            {
                "title": "🏙 الملفات المعنية والصيغ",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>database/db_queries/assets_queries.py</code>\n"
                    "  → <code>calculate_city_effects(city_id)</code>\n"
                    "  → يُرجع: economy, health, education, infrastructure,\n"
                    "    income, maintenance, health_bonus, education_bonus, infra_bonus\n\n"
                    "• <code>modules/war/maintenance_service.py</code>\n"
                    "  → <code>_get_hospital_reduction(country_id)</code>\n"
                    "  → يجمع health_bonus من كل مدن الدولة\n\n"
                    "• <code>modules/war/power_calculator.py</code>\n"
                    "  → <code>get_country_power(country_id)</code>\n"
                    "  → يجمع infra_bonus من كل مدن الدولة → يضرب في القوة\n\n"
                    "📐 <b>الصيغ:</b>\n"
                    "<code>health_bonus    = min(0.25, health × 0.001)</code>\n"
                    "<code>education_bonus = min(0.20, education × 0.001)</code>\n"
                    "<code>infra_bonus     = min(0.20, infrastructure × 0.001)</code>\n"
                    "<code>income × (1 + edu_bonus + infra_bonus [+ 0.10 synergy])</code>\n"
                    "<code>power  × (1 + min(0.15, Σinfra_bonus))</code>\n"
                    "<code>maintenance_rate × (1 - Σhealth_bonus)</code>"
                ),
            },
        ],
    },

    "city_progression": {
        "emoji": "⭐",
        "title": "أنظمة المحاكاة المتقدمة",
        "pages": [
            {
                "title": "🔴 نظام التمرد التصاعدي",
                "content": (
                    "📌 <b>الجدول:</b> city_rebellion_state\n"
                    "  (city_id, stage 0-3, days_at_stage, recovery_days)\n"
                    "📌 <b>الملف:</b> <code>modules/city/rebellion_engine.py</code>\n\n"
                    "📐 <b>عتبات التصاعد:</b>\n"
                    "مرحلة 1: sat < 30 لـ 1+ يوم → دخل ×0.70\n"
                    "مرحلة 2: sat < 20 لـ 3+ أيام → دخل ×0.40 + أضرار عشوائية\n"
                    "مرحلة 3: sat < 10 لـ 5+ أيام → دخل ×0.0 + بناء محجوب + جيش -40%\n\n"
                    "📐 <b>عتبات التعافي:</b>\n"
                    "3→2: sat ≥ 20 لـ 2 أيام\n"
                    "2→1: sat ≥ 30 لـ 2 أيام\n"
                    "1→0: sat ≥ 40 لـ 1 يوم\n"
                    "كل تعافٍ → +5 رضا\n\n"
                    "📐 <b>الدوال:</b>\n"
                    "<code>get_rebellion_stage(city_id)</code> → 0-3\n"
                    "<code>tick_rebellion_stage(city_id)</code> → يومياً\n"
                    "<code>get_rebellion_income_modifier(city_id)</code>\n"
                    "<code>get_rebellion_army_penalty(city_id)</code>\n"
                    "<code>is_construction_blocked(city_id)</code>"
                ),
            },
            {
                "title": "👥 أنواع السكان",
                "content": (
                    "📌 <b>الجدول:</b> city_population_types\n"
                    "  (city_id, workers, soldiers, scholars)\n"
                    "📌 <b>الملف:</b> <code>modules/city/population_types.py</code>\n\n"
                    "📐 <b>التوزيع الأساسي:</b>\n"
                    "عمال = 60% | جنود = 20% | علماء = 20%\n\n"
                    "📐 <b>المعدّلات:</b>\n"
                    "تعليم عالٍ → يحول عمال → علماء (حتى 10%)\n"
                    "رضا < 40 → يحول علماء → عمال (حتى 10%)\n"
                    "تمرد → يحول عمال → جنود (5% × المرحلة)\n\n"
                    "📐 <b>التأثيرات:</b>\n"
                    "<code>get_worker_income_bonus()</code> → +0.5% دخل/1% فوق 60%\n"
                    "<code>get_scholar_xp_multiplier()</code> → +1% XP/1% فوق 20%\n"
                    "<code>get_soldier_army_bonus()</code> → soldiers // 10 خانة إضافية\n"
                    "<code>apply_war_soldier_loss()</code> → يُستدعى بعد المعارك"
                ),
            },
            {
                "title": "💰 الاقتصاد الداخلي",
                "content": (
                    "📌 <b>الجدول:</b> country_tax_policy (country_id, tax_rate)\n"
                    "📌 <b>الملف:</b> <code>modules/city/internal_economy.py</code>\n\n"
                    "📐 <b>الصيغ اليومية:</b>\n"
                    "<code>tax_income  = workers × 0.05 × tax_rate</code>\n"
                    "<code>consumption = population × 0.002</code>\n"
                    "<code>production  = workers × 0.10 × (1+edu+infra)</code>\n"
                    "<code>net = tax_income + production - consumption</code>\n\n"
                    "📐 <b>معدل الضريبة (5%–40%):</b>\n"
                    "افتراضي = 15%\n"
                    "> 20% → رضا -2 لكل 5% زيادة\n"
                    "< 15% → رضا +1 لكل 5% نقصان\n\n"
                    "📐 <b>الدوال:</b>\n"
                    "<code>get_tax_rate(country_id)</code>\n"
                    "<code>set_tax_rate(country_id, rate)</code>\n"
                    "<code>tick_internal_economy(city_id, country_id, owner_id)</code>"
                ),
            },
            {
                "title": "🌍 الهجرة بين الدول",
                "content": (
                    "📌 <b>الجدول:</b> inter_country_migration_log\n"
                    "📌 <b>الملف:</b> <code>modules/city/city_simulation.py</code>\n\n"
                    "📐 <b>شروط الهجرة بين الدول:</b>\n"
                    "• رضا المصدر < 30\n"
                    "• رضا الوجهة > رضا المصدر + 25\n"
                    "• الوجهة تحت 95% من طاقتها\n"
                    "• لم تهاجر هذه المدينة في آخر 7 أيام\n\n"
                    "📐 <b>الكمية:</b>\n"
                    "<code>amount = min(200, source_pop × 0.01)</code>\n\n"
                    "📐 <b>الهجرة الداخلية (نفس الدولة):</b>\n"
                    "فارق رضا ≥ 15 + رضا المصدر < 40\n"
                    "<code>amount = min(500, source_pop × 0.02)</code>"
                ),
            },
            {
                "title": "🏛 القرارات الحكومية",
                "content": (
                    "📌 <b>الجدول:</b> country_decisions\n"
                    "📌 <b>الملف:</b> <code>modules/city/government_decisions.py</code>\n"
                    "📌 <b>Handler:</b> <code>handlers/government_handler.py</code>\n"
                    "📌 <b>الأمر:</b> <code>قرار حكومي</code>\n\n"
                    "📐 <b>القرارات المتاحة:</b>\n"
                    "• tax_increase: دخل +15%, رضا -10\n"
                    "• tax_decrease: دخل -10%, رضا +10\n"
                    "• military_focus: جيش +20%, دخل -10%, XP +15%\n"
                    "• economic_boost: دخل +20%, جيش -10%, رضا +5\n"
                    "• infra_invest: طاقة سكان +20%, دخل -5%, رضا +8\n"
                    "• education_drive: XP +30%, علماء +5%, دخل -5%\n\n"
                    "📐 <b>القواعد:</b>\n"
                    "مدة القرار: 3 أيام\n"
                    "كولداون بعد الانتهاء: 3 أيام\n"
                    "قرار واحد نشط في كل وقت\n\n"
                    "📐 <b>الدوال:</b>\n"
                    "<code>get_active_decision(country_id)</code>\n"
                    "<code>get_decision_effect(country_id, effect_key)</code>\n"
                    "<code>make_decision(country_id, decision_key)</code>"
                ),
            },
            {
                "title": "🌍 الأحداث العالمية الجديدة",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/progression/global_events.py</code>\n\n"
                    "📐 <b>الأحداث الجديدة المضافة:</b>\n"
                    "• epidemic (😷) — رضا السكان ينخفض عالمياً\n"
                    "• global_recession (📉) — دخل -20% لـ 12 ساعة\n"
                    "• war_tensions (⚔️) — تكاليف حرب -15%, غنائم +10%\n"
                    "• tech_breakthrough (⚙️) — إنتاج +25% لـ 10 ساعات\n\n"
                    "📐 <b>مفاتيح التأثير الجديدة:</b>\n"
                    "<code>satisfaction_penalty</code> — يُطبَّق على رضا المدن\n"
                    "<code>production_bonus</code> — يُطبَّق على الإنتاج الداخلي\n"
                    "<code>war_tension_bonus</code> — يُطبَّق على تكاليف الحرب\n\n"
                    "📐 <b>التكامل:</b>\n"
                    "<code>get_event_effect('effect_key')</code> → float\n"
                    "يُستدعى من: war_economy, internal_economy, city_stats"
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
                    "• أو رد مباشرة على رسالة التذكرة\n"
                    "• يمكن الرد بنص أو صورة أو فيديو\n\n"
                    "🔒 <b>إغلاق تذكرة:</b>\n"
                    "اضغط 🔒 إغلاق التذكرة\n"
                    "يُشعَر المستخدم تلقائياً\n\n"
                    "📊 <b>الإحصائيات:</b>\n"
                    "• تذاكر اليوم / المفتوحة / المغلقة / الإجمالي"
                ),
            },
            {
                "title": "🖼 دعم الوسائط في التذاكر",
                "content": (
                    "📌 <b>الأنواع المدعومة:</b>\n"
                    "• ✅ نص\n"
                    "• ✅ صورة (مع تعليق اختياري)\n"
                    "• ✅ فيديو (مع تعليق اختياري)\n"
                    "• ❌ ملصقات، صوت، ملفات، GIF — مرفوضة\n\n"
                    "🔄 <b>آلية العمل:</b>\n"
                    "1️⃣ المستخدم يرسل صورة/فيديو في حالة <code>awaiting_ticket_msg</code>\n"
                    "2️⃣ البوت يستخرج <code>file_id</code> و<code>file_unique_id</code>\n"
                    "3️⃣ يُحفظان في جدول <code>ticket_messages</code>\n"
                    "4️⃣ يُرسَل الوسيط للمجموعة مباشرة بـ <code>file_id</code>\n"
                    "   (بدون تنزيل أو رفع — كفاءة عالية)\n\n"
                    "📌 <b>الملفات المعنية:</b>\n"
                    "• <code>modules/tickets/ticket_handler.py</code>\n"
                    "  → <code>_extract_message_info()</code> — يستخرج النوع والـ file_id\n"
                    "  → <code>_is_unsupported_media()</code> — يرفض الأنواع غير المدعومة\n"
                    "  → <code>send_to_devs()</code> — يرسل للمجموعة حسب النوع\n"
                    "• <code>modules/tickets/ticket_db.py</code>\n"
                    "  → عمودا <code>file_id</code> و<code>file_unique_id</code> في <code>ticket_messages</code>"
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
            {
                "title": "✅ خطوة التأكيد قبل الإرسال",
                "content": (
                    "بعد كتابة رسالة التذكرة، يُعرض على المستخدم شاشة مراجعة\n"
                    "قبل إرسالها للمطور.\n\n"
                    "📋 <b>ما يراه المستخدم:</b>\n"
                    "• نوع التذكرة\n"
                    "• معاينة المحتوى (نص أو وصف الوسيط)\n"
                    "• زر ✅ إرسال — يُرسل التذكرة ويحتسبها\n"
                    "• زر ❌ إلغاء — يُلغي دون احتساب من الحد اليومي\n\n"
                    "📌 <b>الآلية:</b>\n"
                    "الرسالة تُحفظ مؤقتاً في <code>_PENDING_CONFIRM</code>\n"
                    "عند التأكيد → <code>confirm_and_send_ticket()</code>\n"
                    "عند الإلغاء → <code>cancel_pending_ticket()</code>\n\n"
                    "⚠️ <b>الحد اليومي لا يُحتسب إلا عند التأكيد الفعلي.</b>"
                ),
            },
            {
                "title": "🚫 حظر المستخدمين من التذاكر",
                "content": (
                    "📌 <b>كيفية الحظر:</b>\n"
                    "يظهر زر 🚫 حظر المستخدم تحت كل تذكرة في مجموعة المطورين.\n"
                    "اضغطه لحظر المستخدم فوراً.\n\n"
                    "📋 <b>تأثير الحظر:</b>\n"
                    "• المستخدم لا يستطيع فتح تذاكر جديدة\n"
                    "• يُشعَر المستخدم برسالة واضحة عند المحاولة\n"
                    "• يُشعَر المستخدم فور تطبيق الحظر\n\n"
                    "🗄 <b>قاعدة البيانات:</b>\n"
                    "الحظر محفوظ في جدول <code>ticket_bans</code>\n"
                    "الحقول: user_id, banned_at, reason\n\n"
                    "📌 <b>دوال DB:</b>\n"
                    "• <code>ban_ticket_user(user_id)</code>\n"
                    "• <code>unban_ticket_user(user_id)</code>\n"
                    "• <code>is_ticket_banned(user_id)</code> → bool"
                ),
            },
            {
                "title": "🔓 رفع الحظر وقائمة المحظورين",
                "content": (
                    "📌 <b>رفع الحظر:</b>\n"
                    "<code>تذكرة رفع &lt;user_id&gt;</code>\n"
                    "مثال: <code>تذكرة رفع 123456789</code>\n\n"
                    "✅ <b>النتيجة:</b>\n"
                    "• تأكيد يعرض ID واسم المستخدم\n"
                    "• إشعار للمستخدم بأنه يمكنه الإرسال مجدداً\n\n"
                    "📋 <b>قائمة المحظورين:</b>\n"
                    "<code>تذكرة محظورين</code>\n\n"
                    "• تعرض 20 مستخدماً في كل صفحة\n"
                    "• تنسيق LTR: <code>ID: 123 | Name: Ahmed</code>\n"
                    "• أزرار التنقل: ➡️ السابق / ⬅️ التالي / ❌ إغلاق\n\n"
                    "📌 <b>مصدر الأسماء:</b>\n"
                    "جدول <code>users</code> عمود <code>name</code>\n"
                    "إذا لم يُوجد → يُعرض <code>Unknown</code>"
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
                    "تقدم المستخدمين محفوظ في جدول <code>azkar_progress</code>.\n\n"
                    "📌 <b>تفعيل الأذكار التلقائية للمجموعة:</b>\n"
                    "• من لوحة <code>الأوامر</code> → 📿 الأذكار التلقائية (زر toggle)\n"
                    "• أو بالأمر: <code>تفعيل الأذكار</code> / <code>إيقاف الأذكار</code>\n"
                    "• العمود: <code>groups.azkar_enabled</code>\n"
                    "• الدالة: <code>toggle_azkar()</code> في <code>azkar_sender.py</code>\n"
                    "• أو عبر النظام العام: <code>toggle_feature(cid, 'azkar_enabled')</code>"
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

    "channels_feature": {
        "emoji": "📡",
        "title": "ميزة القنوات",
        "pages": [
            {
                "title": "📡 البنية العامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/content_hub/channel_admin.py</code> — أوامر الربط/فك الربط\n"
                    "• <code>modules/content_hub/channel_sync.py</code> — استقبال المنشورات\n"
                    "• <code>modules/content_hub/hub_db.py</code> — قاعدة البيانات\n"
                    "• <code>main.py</code> — تسجيل handlers القنوات\n\n"
                    "📋 <b>جدول DB:</b>\n"
                    "<code>linked_channels</code> في <code>content_hub.db</code>\n"
                    "الحقول: channel_id, channel_name, content_type, linked_at\n\n"
                    "📂 <b>جداول المحتوى المستهدفة:</b>\n"
                    "quotes | anecdotes | stories | wisdom | poetry\n\n"
                    "🔑 <b>أوامر المطور:</b>\n"
                    "• <code>ربط قناة</code>\n"
                    "• <code>فك ربط قناة</code>\n"
                    "• <code>القنوات المرتبطة</code>"
                ),
            },
            {
                "title": "🔄 تدفق الربط — خطوة بخطوة",
                "content": (
                    "📌 <b>الملف:</b> <code>channel_admin.py</code>\n\n"
                    "1️⃣ <b>المطور يكتب</b> <code>ربط قناة</code>\n"
                    "   → <code>_start_link_flow()</code> تُعيّن state: <code>ch_link / await_channel</code>\n\n"
                    "2️⃣ <b>المطور يرسل معرف القناة</b> أو يعيد توجيه رسالة\n"
                    "   → <code>_process_channel_input()</code>\n"
                    "   → يتحقق أن البوت مشرف عبر <code>bot.get_chat_member()</code>\n"
                    "   → إذا فشل → رسالة خطأ واضحة + clear state\n\n"
                    "3️⃣ <b>يعرض أزرار نوع المحتوى</b>\n"
                    "   → quotes | stories | anecdotes | wisdom | poetry\n\n"
                    "4️⃣ <b>المطور يختار النوع</b>\n"
                    "   → callback <code>ch_select_type</code>\n"
                    "   → <code>link_channel(channel_id, content_type, name)</code>\n"
                    "   → INSERT OR UPDATE في <code>linked_channels</code>\n\n"
                    "✅ <b>النتيجة:</b> كل منشور جديد في القناة يُستورد تلقائياً."
                ),
            },
            {
                "title": "📥 استقبال المنشورات — channel_sync.py",
                "content": (
                    "📌 <b>التسجيل في main.py:</b>\n"
                    "<code>@bot.channel_post_handler(func=lambda m: True)\n"
                    "def on_channel_post(message):\n"
                    "    handle_channel_post(message)</code>\n\n"
                    "<code>@bot.edited_channel_post_handler(func=lambda m: True)\n"
                    "def on_channel_post_edit(message):\n"
                    "    handle_channel_post_edit(message)</code>\n\n"
                    "📌 <b>منطق handle_channel_post():</b>\n"
                    "1️⃣ <code>get_linked_channel(channel_id)</code> — هل القناة مرتبطة؟\n"
                    "2️⃣ استخراج النص: <code>message.text or message.caption</code>\n"
                    "3️⃣ <code>_clean(text)</code> — إزالة أسطر فارغة ومسافات زائدة\n"
                    "4️⃣ <code>insert_content(table, text)</code> — INSERT OR IGNORE\n\n"
                    "📌 <b>منطق handle_channel_post_edit():</b>\n"
                    "1️⃣ نفس الفحص\n"
                    "2️⃣ <code>upsert_content_by_text(old, new)</code>\n"
                    "3️⃣ إذا لم يجد النص القديم → يُدرج كمحتوى جديد\n\n"
                    "⚠️ <b>الوسائط بدون نص تُتجاهل تلقائياً.</b>"
                ),
            },
            {
                "title": "🗄️ دوال قاعدة البيانات",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/content_hub/hub_db.py</code>\n\n"
                    "🔗 <b>ربط قناة:</b>\n"
                    "<code>link_channel(channel_id, content_type, channel_name)\n"
                    "# INSERT OR UPDATE — آمن للاستدعاء مرتين</code>\n\n"
                    "❌ <b>فك الربط:</b>\n"
                    "<code>unlink_channel(channel_id) → bool</code>\n\n"
                    "🔍 <b>جلب قناة:</b>\n"
                    "<code>get_linked_channel(channel_id) → dict | None</code>\n\n"
                    "📋 <b>جلب الكل:</b>\n"
                    "<code>get_all_linked_channels() → list[dict]</code>\n\n"
                    "📝 <b>تحديث محتوى بالنص:</b>\n"
                    "<code>upsert_content_by_text(table, old_text, new_text) → bool</code>\n\n"
                    "📌 <b>INSERT OR IGNORE في insert_content():</b>\n"
                    "يمنع التكرار — نفس النص لا يُدرج مرتين."
                ),
            },
            {
                "title": "➕ إضافة نوع محتوى جديد",
                "content": (
                    "📌 <b>لإضافة نوع محتوى جديد (مثلاً: jokes):</b>\n\n"
                    "1️⃣ <b>في hub_db.py:</b>\n"
                    "<code>CONTENT_TYPES['نكتة'] = 'jokes'\n"
                    "TYPE_LABELS['jokes'] = '😂 نكتة'</code>\n"
                    "وأضف <code>'jokes'</code> في حلقة <code>create_tables()</code>\n\n"
                    "2️⃣ <b>في channel_admin.py:</b>\n"
                    "<code>_TYPE_BUTTONS.append(('😂 نكت', 'jokes'))</code>\n\n"
                    "3️⃣ <b>في hub_handler.py:</b>\n"
                    "أضف الأمر العربي في <code>CONTENT_TYPES</code> إذا أردت أمراً للمستخدم.\n\n"
                    "4️⃣ <b>في dev_control_panel.py:</b>\n"
                    "أضف زراً في <code>_show_content_hub_panel()</code>:\n"
                    "<code>btn('😂 نكت', 'hub_dev_type', {'type': 'jokes'}, ...)</code>\n\n"
                    "✅ <b>الجدول يُنشأ تلقائياً</b> عند أول استدعاء لـ <code>create_tables()</code>."
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
                    "⚠️ <b>سياسة النشر التلقائي:</b>\n"
                    "فقط <b>الاقتباسات</b> و<b>الأذكار</b> تُنشر تلقائياً.\n"
                    "anecdotes / stories / wisdom / poetry — بالأمر المباشر فقط.\n\n"
                    "🔄 <b>دورة الحياة:</b>\n"
                    "1️⃣ المُجدوِل يستدعي <code>send_periodic_quotes()</code> كل 5 دقائق\n"
                    "2️⃣ تقرأ الدالة <code>quotes_interval_minutes</code> من bot_constants\n"
                    "3️⃣ تجلب المجموعات التي <code>quotes_enabled = 1</code>\n"
                    "4️⃣ لكل مجموعة: تتحقق من آخر إرسال (throttle في الذاكرة)\n"
                    "5️⃣ إذا حان الوقت → تجلب صفاً عشوائياً من جدول quotes\n"
                    "6️⃣ ترسل المحتوى للمجموعة\n\n"
                    "⚙️ <b>الثابت القابل للتعديل:</b>\n"
                    "• <code>quotes_interval_minutes</code> — الفترة بالدقائق (افتراضي: 10)"
                ),
            },
            {
                "title": "💬 التفعيل والإيقاف",
                "content": (
                    "📌 <b>طريقتان للتفعيل (للمشرفين):</b>\n"
                    "• من لوحة <code>الأوامر</code> → 💬 الاقتباسات التلقائية (زر toggle)\n"
                    "• أو بالأمر: <code>تفعيل الاقتباسات</code> / <code>إيقاف الاقتباسات</code>\n\n"
                    "📌 <b>في الكود:</b>\n"
                    "<code>from modules.content_hub.quotes_sender import toggle_quotes\n"
                    "toggle_quotes(tg_group_id, enable=True)</code>\n\n"
                    "📌 <b>جداول المحتوى (في content_hub.db):</b>\n"
                    "• <code>quotes</code> — اقتباسات ✅ تُنشر تلقائياً\n"
                    "• <code>azkar</code> — أذكار ✅ تُنشر تلقائياً\n"
                    "• <code>anecdotes / stories / wisdom / poetry</code> — بالأمر فقط ❌\n\n"
                    "📌 <b>إضافة محتوى جديد:</b>\n"
                    "من لوحة المطور → 📜 اقتباسات\n"
                    "أو عبر <code>insert_content(table, text)</code> في hub_db.py"
                ),
            },
            {
                "title": "📿 الأذكار التلقائية — التقنية",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/content_hub/azkar_sender.py</code>\n\n"
                    "🔄 <b>دورة الحياة (مطابقة للاقتباسات):</b>\n"
                    "1️⃣ المُجدوِل يستدعي <code>send_periodic_azkar()</code> كل 5 دقائق\n"
                    "2️⃣ تقرأ الدالة <code>azkar_interval_minutes</code> من bot_constants\n"
                    "3️⃣ تجلب المجموعات التي <code>azkar_enabled = 1</code>\n"
                    "4️⃣ throttle في الذاكرة يمنع الإرسال المتكرر\n"
                    "5️⃣ تجلب صفاً عشوائياً من جدول <code>azkar</code> في content_hub.db\n\n"
                    "⚙️ <b>الثابت القابل للتعديل:</b>\n"
                    "• <code>azkar_interval_minutes</code> — الفترة بالدقائق (افتراضي: 10)\n\n"
                    "📌 <b>طريقتان للتفعيل (للمشرفين):</b>\n"
                    "• من لوحة <code>الأوامر</code> → 📿 الأذكار التلقائية (زر toggle)\n"
                    "• أو بالأمر: <code>تفعيل الأذكار</code> / <code>إيقاف الأذكار</code>\n\n"
                    "📌 <b>في الكود:</b>\n"
                    "<code>from modules.content_hub.azkar_sender import toggle_azkar\n"
                    "toggle_azkar(tg_group_id, enable=True)</code>\n\n"
                    "📌 <b>ملاحظة:</b>\n"
                    "الاقتباسات والأذكار مستقلان تماماً — كل منهما له:\n"
                    "• عمود DB خاص به (quotes_enabled / azkar_enabled)\n"
                    "• ثابت interval خاص به\n"
                    "• throttle cache مستقل في الذاكرة"
                ),
            },
        ],
    },

    "alliance_governance_dev": {
        "emoji": "🏛️",
        "title": "حوكمة التحالفات",
        "pages": [
            {
                "title": "🏛️ البنية العامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/alliances/governance_handler.py</code> — واجهة المستخدم\n"
                    "• <code>database/db_queries/alliance_governance_queries.py</code> — الاستعلامات\n"
                    "• <code>database/db_schema/alliance_governance.py</code> — مخطط DB\n\n"
                    "📋 <b>الجداول:</b>\n"
                    "• <code>alliance_treasury</code> — الخزينة المشتركة\n"
                    "• <code>alliance_treasury_log</code> — سجل المعاملات\n"
                    "• <code>alliance_reputation</code> — السمعة (0–1000)\n"
                    "• <code>alliance_reputation_log</code> — سجل أحداث السمعة\n"
                    "• <code>alliance_titles</code> — الألقاب الديناميكية\n"
                    "• <code>alliance_role_permissions</code> — صلاحيات الأدوار\n"
                    "• <code>alliance_tax_config</code> — إعدادات الضرائب\n\n"
                    "▶️ <b>الأمر:</b> <code>حوكمة التحالف</code>"
                ),
            },
            {
                "title": "🏦 الخزينة والأدوار",
                "content": (
                    "📌 <b>الخزينة:</b>\n"
                    "<code>get_treasury(alliance_id)</code> → balance, total_deposited, total_withdrawn\n"
                    "<code>deposit_treasury(aid, uid, amount, note)</code>\n"
                    "<code>withdraw_treasury(aid, uid, amount, note)</code>\n"
                    "<code>reward_member(aid, uid, amount, note)</code>\n"
                    "<code>get_treasury_log(aid, limit)</code>\n\n"
                    "📌 <b>أنواع المعاملات (tx_type):</b>\n"
                    "deposit | withdraw | loot_share | upgrade_cost | war_fund | reward | tax\n\n"
                    "📌 <b>الأدوار والصلاحيات:</b>\n"
                    "• leader — كل الصلاحيات\n"
                    "• officer — declare_war, manage_members, set_tax\n"
                    "• member — لا صلاحيات إدارية\n\n"
                    "<code>has_permission(alliance_id, user_id, 'declare_war')</code> → bool\n"
                    "<code>get_member_role(alliance_id, user_id)</code> → str\n"
                    "<code>promote_member(aid, uid)</code> / <code>demote_member(aid, uid)</code>"
                ),
            },
            {
                "title": "⭐ السمعة والألقاب",
                "content": (
                    "📌 <b>السمعة (0–1000، تبدأ من 100):</b>\n"
                    "<code>get_alliance_reputation(alliance_id)</code>\n"
                    "<code>update_alliance_reputation(aid, delta, reason)</code>\n\n"
                    "📐 <b>تأثير السمعة على القوة:</b>\n"
                    "score 0–200: 0.90x | 200–400: 1.00x\n"
                    "400–600: 1.05x | 600–800: 1.10x | 800+: 1.15x\n\n"
                    "📌 <b>الألقاب الديناميكية:</b>\n"
                    "<code>get_alliance_titles(alliance_id)</code>\n"
                    "<code>get_all_current_titles()</code>\n"
                    "<code>TITLE_DEFINITIONS</code> — قاموس تعريف الألقاب\n\n"
                    "📌 <b>الضرائب:</b>\n"
                    "<code>get_tax_config(alliance_id)</code>\n"
                    "<code>set_tax_rate(alliance_id, rate)</code>\n"
                    "تُجمع تلقائياً من أعضاء التحالف وتُودع في الخزينة."
                ),
            },
        ],
    },

    "diplomacy_dev": {
        "emoji": "🤝",
        "title": "الدبلوماسية الاستراتيجية",
        "pages": [
            {
                "title": "🤝 البنية العامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/alliances/diplomacy_handler.py</code> — واجهة المستخدم\n"
                    "• <code>modules/alliances/diplomacy_service.py</code> — منطق الأعمال\n"
                    "• <code>database/db_queries/alliance_diplomacy_queries.py</code> — الاستعلامات\n"
                    "• <code>database/db_schema/alliance_diplomacy.py</code> — مخطط DB\n\n"
                    "▶️ <b>الأمر:</b> <code>دبلوماسية التحالف</code>\n\n"
                    "📋 <b>أنواع المعاهدات:</b>\n"
                    "• <code>non_aggression</code> — عدم اعتداء\n"
                    "• <code>military_alliance</code> — تحالف عسكري\n"
                    "• <code>trade_agreement</code> — اتفاقية تجارية\n\n"
                    "📋 <b>أنواع التوسع:</b>\n"
                    "• <code>merger</code> — اندماج كامل\n"
                    "• <code>absorption</code> — استيعاب تحالف أصغر\n\n"
                    "📋 <b>الاتحادات:</b>\n"
                    "تحالفات متعددة تتحد تحت مظلة واحدة"
                ),
            },
            {
                "title": "🤝 المعاهدات والتوسع",
                "content": (
                    "📌 <b>إرسال معاهدة:</b>\n"
                    "<code>send_treaty_proposal(user_id, target_alliance_id,\n"
                    "                    treaty_type, duration_days=30)</code>\n"
                    "التكلفة: 200 — يُخصم من رصيد المُرسِل\n\n"
                    "📌 <b>الرد على معاهدة:</b>\n"
                    "<code>respond_to_treaty(user_id, treaty_id, accept=True)</code>\n\n"
                    "📌 <b>خيانة معاهدة:</b>\n"
                    "<code>betray_treaty(user_id, treaty_id)</code>\n"
                    "→ عقوبة سمعة كبيرة على التحالف الخائن\n\n"
                    "📌 <b>التوسع:</b>\n"
                    "<code>send_expansion_proposal(user_id, target_id, expansion_type)</code>\n"
                    "<code>execute_expansion(user_id, proposal_id)</code>\n\n"
                    "📌 <b>مكافأة الدبلوماسية على التصويت:</b>\n"
                    "<code>get_diplomacy_vote_bonus(alliance_id)</code> → float\n"
                    "المعاهدات النشطة تزيد وزن التصويت في الحروب"
                ),
            },
        ],
    },

    "progression_dev": {
        "emoji": "📊",
        "title": "نظام التقدم والإنجازات",
        "pages": [
            {
                "title": "🏅 الإنجازات",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/progression/achievements.py</code>\n\n"
                    "📋 <b>الجداول:</b>\n"
                    "• <code>achievements</code> — كتالوج الإنجازات\n"
                    "• <code>user_achievements</code> — الإنجازات المكتسبة\n\n"
                    "📌 <b>فحص وإعطاء إنجاز:</b>\n"
                    "<code>check_and_award(user_id, condition_type, current_value)</code>\n"
                    "يُستدعى بعد كل حدث مهم (معركة، تحويل، إلخ)\n\n"
                    "📌 <b>trigger_achievement_check:</b>\n"
                    "<code>trigger_achievement_check(user_id, 'influence_gained')</code>\n\n"
                    "📋 <b>فئات الإنجازات:</b>\n"
                    "battle | spy | economy | alliance | influence\n\n"
                    "📋 <b>أنواع الشروط (condition_type):</b>\n"
                    "battles_won | balance | transfers_sent | influence_points\n"
                    "spy_success | cities_owned | alliance_wars_won\n\n"
                    "📌 <b>المكافآت:</b>\n"
                    "reward_conis (مالية) + reward_card_name (بطاقة) + reward_reputation"
                ),
            },
            {
                "title": "🌍 النفوذ — صيغة لوغاريتمية",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/progression/influence.py</code>\n\n"
                    "📐 <b>الصيغة اللوغاريتمية:</b>\n"
                    "<code>bonus = rate × log2(points/100 + 1)</code>\n"
                    "تناقص العوائد: كل مضاعفة تُضيف نصف ما أضافته السابقة\n\n"
                    "📐 <b>الحدود القصوى:</b>\n"
                    "• income_bonus_pct: حد أقصى 40%\n"
                    "• war_advantage_pct: حد أقصى 20%\n\n"
                    "📌 <b>الدوال:</b>\n"
                    "<code>add_influence(country_id, points, reason)</code>\n"
                    "<code>get_influence(country_id)</code> → dict\n"
                    "<code>ensure_influence(country_id)</code>\n\n"
                    "📌 <b>تكامل مع الأحداث العالمية:</b>\n"
                    "إذا كان حدث xp_bonus نشطاً → النقاط تُضاعَف تلقائياً\n"
                    "إذا كان reason يحتوي 'alliance' → alliance_xp_bonus يُطبَّق"
                ),
            },
            {
                "title": "🏆 المواسم",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/progression/seasons.py</code>\n\n"
                    "📋 <b>الجداول:</b>\n"
                    "• <code>seasons</code> — المواسم النشطة والمنتهية\n"
                    "• <code>season_history</code> — الترتيبات النهائية لكل موسم\n\n"
                    "📌 <b>الدوال:</b>\n"
                    "<code>get_active_season()</code> → dict | None\n"
                    "<code>create_season(name)</code> → season_id\n"
                    "<code>check_season()</code> — يُشغَّل يومياً من daily_tasks\n\n"
                    "📐 <b>المدة:</b>\n"
                    "<code>season_duration_days</code> — قابل للتعديل من لوحة المطور (افتراضي: 30)\n\n"
                    "📌 <b>المكافآت:</b>\n"
                    "<code>WARRIOR_OF_SEASON_AWARD</code>\n"
                    "<code>KNIGHT_OF_SEASON_AWARD</code>\n"
                    "<code>SEASON_CHAMPION_AWARD</code>\n"
                    "تُدفع تلقائياً عند انتهاء الموسم"
                ),
            },
        ],
    },

    "political_war_dev": {
        "emoji": "⚔️",
        "title": "الحرب السياسية — صيغ المطور",
        "pages": [
            {
                "title": "⚔️ البنية العامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/war/handlers/political_war_handler.py</code> — واجهة المستخدم\n"
                    "• <code>modules/war/services/political_war_service.py</code> — منطق الأعمال\n"
                    "• <code>database/db_queries/political_war_queries.py</code> — الاستعلامات\n"
                    "• <code>database/db_schema/political_war.py</code> — مخطط DB\n\n"
                    "📋 <b>الجداول:</b>\n"
                    "• <code>political_wars</code> — إعلانات الحرب\n"
                    "• <code>political_war_votes</code> — تصويت الدول\n"
                    "• <code>political_war_members</code> — الدول المشاركة\n"
                    "• <code>political_war_log</code> — سجل الأحداث\n"
                    "• <code>war_cooldowns</code> — كولداون التحالف\n\n"
                    "📌 <b>الثوابت:</b>\n"
                    "<code>WAR_DECLARATION_COST = 500</code>\n"
                    "<code>LOOT_PERCENT = 0.10</code>\n"
                    "<code>VOTE_THRESHOLD = 0.60</code>\n"
                    "<code>WAR_COOLDOWN_SEC = 43200  # 12 ساعة</code>"
                ),
            },
            {
                "title": "⚔️ صيغة وزن التصويت",
                "content": (
                    "📐 <b>وزن التصويت لكل دولة:</b>\n\n"
                    "<code>raw_weight = (military_power / 1000)\n"
                    "           + (economy_score / 5000)\n"
                    "           + alliance_rank</code>\n\n"
                    "حيث:\n"
                    "• <code>alliance_rank</code>: قائد=3، ضابط=2، عضو=1\n"
                    "• <code>raw_weight = max(1.0, raw_weight)</code>\n\n"
                    "📐 <b>مضاعفات إضافية:</b>\n"
                    "<code>loyalty_mult = 0.7 + (loyalty_score/100) × 0.6</code>\n"
                    "→ نطاق: 0.70x–1.30x\n\n"
                    "<code>rep_bonus = get_reputation_vote_weight_bonus()</code>\n"
                    "→ نطاق: -0.10 إلى +0.30\n\n"
                    "<code>dip_bonus = get_diplomacy_vote_bonus()</code>\n"
                    "→ نطاق: 0.0 إلى +1.0\n\n"
                    "<code>final_weight = raw_weight × loyalty_mult\n"
                    "              × (1 + rep_bonus)\n"
                    "              × (1 + dip_bonus)</code>"
                ),
            },
            {
                "title": "⚔️ مراحل الحرب والولاء",
                "content": (
                    "📐 <b>مراحل الحرب:</b>\n"
                    "1️⃣ <code>voting</code> — 24 ساعة للتصويت\n"
                    "2️⃣ <code>preparation</code> — 20 دقيقة للتحضير\n"
                    "3️⃣ <code>active</code> — الحرب نشطة\n"
                    "4️⃣ <code>ended</code> / <code>cancelled</code>\n\n"
                    "📐 <b>الغنائم:</b>\n"
                    "<code>loot = budget × 0.10</code>\n"
                    "<code>treasury_cut = loot × 0.20</code>\n"
                    "<code>per_winner = (loot - treasury_cut) / len(winners)</code>\n\n"
                    "📐 <b>نظام الولاء (0–100):</b>\n"
                    "<code>LOYALTY_SUPPORT_BONUS   = +10.0</code>\n"
                    "<code>LOYALTY_IGNORE_PENALTY  = -15.0</code>\n"
                    "<code>LOYALTY_WITHDRAW_PENALTY= -20.0</code>\n"
                    "<code>LOYALTY_WIN_BONUS       = +5.0</code>\n"
                    "<code>DEFENSIVE_IGNORE_PENALTY= -22.5</code>\n\n"
                    "📐 <b>ألقاب الولاء:</b>\n"
                    "≥75: 🤝 وفي | 40–74: 😐 محايد | <40: ⚠️ غير موثوق"
                ),
            },
            {
                "title": "⚔️ قوة الدولة — الصيغة الكاملة",
                "content": (
                    "📐 <b>صيغة القوة الكاملة:</b>\n\n"
                    "<code>raw = Σ(qty × (atk×1.0 + def×0.5 + hp×0.1))\n"
                    "    + Σ(qty × (atk_bonus + def_bonus×0.5))</code>\n\n"
                    "<code>alliance_mult = min(1.50,\n"
                    "  (1 + atk_b + def_b×0.5 + hp_b×0.3)\n"
                    "  × rep_bonus)  # سقف ناعم 1.50x</code>\n\n"
                    "<code>infra_mult  = 1 + min(0.15, Σinfra_bonus)\n"
                    "level_mult  = 1 + min(0.57, avg_level_mil_bonus)\n"
                    "maint_pen   = get_maintenance_penalty()\n"
                    "size_pen    = min(0.20, max(0, cities-7) × 0.02)</code>\n\n"
                    "<code>power = raw × alliance_mult\n"
                    "      × infra_mult × level_mult\n"
                    "      × (1 - maint_pen)\n"
                    "      × (1 - size_pen)</code>\n\n"
                    "📌 <b>الملف:</b> <code>modules/war/power_calculator.py</code>"
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

    "poll_system": {
        "emoji": "📊",
        "title": "نظام الاستفتاء المتقدم",
        "pages": [
            {
                "title": "📊 البنية العامة والملفات",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/polls/poll_handler.py</code> — wizard + callbacks + UI\n"
                    "• <code>modules/polls/poll_closer.py</code> — إغلاق التصويتات المنتهية\n"
                    "• <code>database/db_schema/polls.py</code> — تعريف الجداول\n"
                    "• <code>database/db_queries/polls_queries.py</code> — الاستعلامات\n"
                    "• <code>database/daily_tasks.py</code> — تسجيل job الإغلاق التلقائي\n\n"
                    "▶️ <b>أوامر المستخدم:</b>\n"
                    "<code>إنشاء تصويت</code> / <code>بناء تصويت</code> — بدء الإنشاء\n"
                    "<code>لوحة التصويت</code> — فتح لوحة تحكم المنشئ\n"
                    "  • رد على رسالة التصويت → يفتح لوحة ذلك التصويت\n"
                    "  • بدون رد → يفتح آخر تصويت أنشأه المستخدم في المحادثة\n"
                    "مسجّلة في <code>shared_commands.py</code> — تعمل في الخاص والمجموعات\n\n"
                    "🔐 <b>الصلاحيات:</b>\n"
                    "• الإنشاء: مشرف/مالك في الوجهة المستهدفة\n"
                    "• التصويت: أي عضو في المجموعة/القناة\n"
                    "• التحكم: المنشئ فقط (created_by)\n"
                    "• التفاصيل: الجميع (show_voters يتحكم في قائمة المصوتين)\n\n"
                    "📌 <b>دوال الاستعلام الرئيسية:</b>\n"
                    "• <code>get_poll_by_message(chat_id, message_id)</code>\n"
                    "• <code>get_latest_poll_by_creator(chat_id, user_id)</code>\n"
                    "• <code>add_poll_option(poll_id, text)</code> — نص فقط"
                ),
            },
            {
                "title": "📊 هيكل قاعدة البيانات",
                "content": (
                    "📋 <b>جدول polls:</b>\n"
                    "id, chat_id, message_id, question\n"
                    "question_media_id, question_media_type\n"
                    "description, description_media_id, description_media_type\n"
                    "poll_type (normal|quiz)\n"
                    "allow_change — هل يُسمح بتغيير الصوت؟\n"
                    "max_vote_changes — حد عدد التغييرات (0=غير محدود)\n"
                    "lock_before_end — قفل التغيير قبل X ثانية من الإغلاق\n"
                    "is_hidden — إخفاء النتائج حتى الإغلاق\n"
                    "show_voters — عرض قائمة المصوتين\n"
                    "is_closed, end_time, created_by, created_at\n\n"
                    "📋 <b>جدول poll_options:</b>\n"
                    "id, poll_id, text\n"
                    "votes_count — عداد denormalized للأداء\n"
                    "(لا وسائط للخيارات — تم الحذف)\n\n"
                    "📋 <b>جدول poll_votes:</b>\n"
                    "id, poll_id, user_id, option_id, voted_at\n"
                    "change_count — عدد مرات تغيير الصوت\n"
                    "UNIQUE(poll_id, user_id) — صوت واحد لكل مستخدم\n\n"
                    "📌 <b>الفهارس:</b>\n"
                    "idx_polls_chat, idx_polls_end_time (partial)\n"
                    "idx_poll_votes_poll_user, idx_poll_options_poll"
                ),
            },
            {
                "title": "📊 تدفق الإنشاء — State Machine",
                "content": (
                    "📌 <b>الحالة:</b> <code>poll_creator</code>  TTL: 15 دقيقة\n\n"
                    "📐 <b>الخطوات:</b>\n"
                    "1️⃣ <code>await_target_id</code> — هذه المحادثة أو أرسل معرّف الشات\n"
                    "   → زر 📍 هذه المحادثة يتخطى الإدخال مباشرة\n"
                    "   → <code>_validate_target()</code>: وجود الشات + صلاحيات البوت + صلاحيات المستخدم\n"
                    "2️⃣ <code>await_poll_type</code> — normal | quiz\n"
                    "3️⃣ <code>await_question</code> — نص السؤال\n"
                    "4️⃣ <code>await_question_media</code> — صورة/فيديو (اختياري)\n"
                    "5️⃣ <code>await_description</code> — نص أو وسائط (اختياري)\n"
                    "6️⃣ <code>await_options</code> — إضافة الخيارات (نص فقط)\n"
                    "   → كل خيار يُضاف مباشرة، لا سؤال عن وسائط\n"
                    "7️⃣ <code>await_settings</code> — كل الإعدادات\n"
                    "8️⃣ <code>poll_publish</code> → DB → إرسال → لوحة تحكم المنشئ\n\n"
                    "📌 <b>الإدخال:</b>\n"
                    "• <code>handle_poll_input()</code> — نصوص\n"
                    "• <code>handle_poll_media()</code> — وسائط السؤال/الوصف فقط\n"
                    "كلاهما مسجّل في <code>_handle_input_states</code> في <code>replies.py</code>"
                ),
            },
            {
                "title": "📊 منطق التصويت — Race-Safe",
                "content": (
                    "📌 <b>callback:</b> <code>poll_vote</code>\n\n"
                    "🔐 <b>الحماية من Race Conditions:</b>\n"
                    "• per-poll <code>threading.Lock</code> يمنع التنفيذ المتزامن\n"
                    "• <code>BEGIN IMMEDIATE</code> يقفل DB للكتابة حتى COMMIT\n"
                    "• كل العمليات (قراءة + كتابة) داخل transaction واحدة\n\n"
                    "📐 <b>منطق cast_vote():</b>\n"
                    "1️⃣ قراءة التصويت داخل BEGIN IMMEDIATE\n"
                    "2️⃣ فحص is_closed + end_time\n"
                    "3️⃣ فحص lock_before_end (قفل آخر X ثانية)\n"
                    "4️⃣ التحقق من وجود الخيار في هذا التصويت\n"
                    "5️⃣ إذا صوّت مسبقاً:\n"
                    "   • نفس الخيار → 'same'\n"
                    "   • allow_change=False → 'no_change'\n"
                    "   • change_count >= max_vote_changes → 'change_limit'\n"
                    "   • غير ذلك → UPDATE + تعديل votes_count\n"
                    "6️⃣ صوت جديد → INSERT + votes_count++\n\n"
                    "📌 <b>أسباب الرفض:</b>\n"
                    "closed | no_change | change_limit | locked | invalid_option | error"
                ),
            },
            {
                "title": "📊 التحديث الحي — Batched Updates",
                "content": (
                    "📌 <b>المشكلة:</b>\n"
                    "في المجموعات الكبيرة قد تصل عشرات الأصوات في ثانية واحدة.\n"
                    "تحديث الرسالة لكل صوت يسبب flood وأخطاء Telegram.\n\n"
                    "📌 <b>الحل — Batched Updates:</b>\n"
                    "<code>_schedule_message_update(msg, poll_id)</code>\n"
                    "• يُجدوِل تحديثاً بعد <code>_UPDATE_DELAY = 2.0</code> ثانية\n"
                    "• إذا وصلت أصوات متعددة في نفس الفترة → تحديث واحد فقط\n"
                    "• <code>_pending_updates</code> dict + <code>_update_lock</code> يمنعان التكرار\n\n"
                    "📌 <b>التحديث الفعلي:</b>\n"
                    "<code>_refresh_poll_message(msg, poll_id)</code>\n"
                    "• وسائط → <code>edit_message_caption</code>\n"
                    "• نص → <code>edit_message_text</code>\n\n"
                    "📌 <b>شريط التقدم الملوّن:</b>\n"
                    "<code>_colored_bar(pct)</code>\n"
                    "🟩 pct ≥ 50%  |  🟥 pct < 50%  |  ⬜ pct = 0%"
                ),
            },
            {
                "title": "📊 الإغلاق التلقائي — Scheduler",
                "content": (
                    "📌 <b>لماذا لا threading.Timer؟</b>\n"
                    "threading.Timer يُفقد عند إعادة تشغيل البوت.\n"
                    "التصويتات المنتهية تبقى مفتوحة حتى يصوّت أحد.\n\n"
                    "📌 <b>الحل — Scheduler Job:</b>\n"
                    "في <code>database/daily_tasks.py</code>:\n"
                    "<code>@register_interval\n"
                    "def close_expired_polls():\n"
                    "    for poll in get_expired_polls():\n"
                    "        close_expired_poll(poll)</code>\n\n"
                    "يعمل كل 5 دقائق — موثوق حتى بعد إعادة التشغيل.\n\n"
                    "📌 <b>poll_closer.py:</b>\n"
                    "<code>close_expired_poll(poll)</code>\n"
                    "1️⃣ <code>close_poll(poll_id)</code> — تحديث DB\n"
                    "2️⃣ <code>_refresh_closed_message(poll)</code> — تحديث الرسالة\n"
                    "3️⃣ <code>_notify_closed(poll)</code> — إشعار بالنتيجة\n\n"
                    "📌 <b>get_expired_polls():</b>\n"
                    "يستخدم الفهرس <code>idx_polls_end_time</code> (partial index)\n"
                    "للبحث السريع عن التصويتات المنتهية فقط."
                ),
            },
            {
                "title": "📊 الأداء وحالات الحافة",
                "content": (
                    "⚡ <b>تحسينات الأداء:</b>\n"
                    "• <code>votes_count</code> denormalized في poll_options\n"
                    "  → <code>get_total_votes()</code> يجمع الأعداد بدلاً من COUNT(*)\n"
                    "• <code>get_option_voters()</code> لها LIMIT=20 دائماً\n"
                    "• Partial index على end_time لتسريع استعلام الإغلاق\n"
                    "• Batched updates تقلل استدعاءات Telegram API\n\n"
                    "🛡 <b>حالات الحافة:</b>\n"
                    "• حذف خيار: ON DELETE CASCADE يحذف الأصوات المرتبطة\n"
                    "• خيار غير موجود في التصويت: فحص صريح داخل transaction\n"
                    "  → رفض بـ 'invalid_option'\n"
                    "• تصويت بعد انتهاء الوقت: يُغلق التصويت ويرفض الصوت\n"
                    "• إعادة تشغيل البوت: الـ scheduler يُغلق التصويتات المنتهية\n"
                    "  في أول دورة بعد الإعادة (خلال 5 دقائق)\n\n"
                    "📌 <b>show_voters:</b>\n"
                    "• المنشئ يرى المصوتين دائماً في الإحصائيات\n"
                    "• الآخرون يرون فقط إذا show_voters=1\n"
                    "• <code>handle_poll_details()</code> يتحقق من كلا الشرطين\n\n"
                    "🎛 <b>لوحة التحكم بعد النشر:</b>\n"
                    "• <code>handle_poll_control_panel()</code> في <code>poll_handler.py</code>\n"
                    "• يستدعي <code>get_poll_by_message()</code> إذا كان رداً\n"
                    "• يستدعي <code>get_latest_poll_by_creator()</code> بدون رد\n"
                    "• يُرسل <code>_send_creator_panel()</code> للمنشئ فقط"
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

    "news_system": {
        "emoji": "📰",
        "title": "نظام الأخبار العالمي",
        "pages": [
            {
                "title": "📰 البنية العامة",
                "content": (
                    "📌 <b>الملفات الرئيسية:</b>\n"
                    "• <code>modules/magazine/news_db.py</code> — جداول DB والـ cooldown\n"
                    "• <code>modules/magazine/news_templates.py</code> — قوالب درامية عشوائية\n"
                    "• <code>modules/magazine/news_generator.py</code> — API العام\n"
                    "• <code>modules/magazine/news_broadcaster.py</code> — البث للمجموعات\n"
                    "• <code>modules/magazine/news_handler.py</code> — واجهة المستخدم\n\n"
                    "📋 <b>جداول DB:</b>\n"
                    "• <code>news_posts</code> — كل المنشورات مع importance/category\n"
                    "• <code>news_cooldowns</code> — منع التكرار لكل event_key\n\n"
                    "🔑 <b>مستويات الأهمية:</b>\n"
                    "LOW | MEDIUM | HIGH | CRITICAL\n\n"
                    "📂 <b>الفئات:</b>\n"
                    "war | economy | rankings | alliance | rebellion | event | general"
                ),
            },
            {
                "title": "🎭 نظام القوالب الدرامية",
                "content": (
                    "📌 <b>الملف:</b> <code>modules/magazine/news_templates.py</code>\n\n"
                    "كل نوع حدث يملك 2–4 قوالب عشوائية بأسلوب درامي.\n"
                    "البوت يختار قالباً مختلفاً في كل مرة لتجنب التكرار.\n\n"
                    "📋 <b>أنواع الأحداث المدعومة:</b>\n"
                    "• <code>war_start</code> — إعلان حرب (4 قوالب)\n"
                    "• <code>war_end</code> — نهاية حرب: فوز/خسارة/تعادل (4 قوالب)\n"
                    "• <code>war_betrayal</code> — انسحاب/خيانة (3 قوالب)\n"
                    "• <code>alliance_victory</code> — سلسلة انتصارات (3 قوالب)\n"
                    "• <code>alliance_collapse</code> — انهيار تحالف (3 قوالب)\n"
                    "• <code>richest_change</code> — تغيير أثرى لاعب (2 قوالب)\n"
                    "• <code>treasury_milestone</code> — إنجاز خزينة (2 قوالب)\n"
                    "• <code>economy_shock</code> — صدمة اقتصادية (3 قوالب)\n"
                    "• <code>rebellion</code> — تمرد مدينة (3 قوالب)\n"
                    "• <code>global_event</code> — حدث عالمي (3 قوالب)\n"
                    "• <code>rankings_weekly/monthly</code> — ترتيبات (3 قوالب لكل)"
                ),
            },
            {
                "title": "⚡ إضافة حدث جديد",
                "content": (
                    "📌 <b>4 خطوات فقط لإضافة حدث جديد:</b>\n\n"
                    "1️⃣ <b>قالب في</b> <code>news_templates.py</code>:\n"
                    "<code>_TEMPLATES['my_event'] = [\n"
                    "    ('عنوان {param}', 'نص {param}'),\n"
                    "    ('عنوان بديل {param}', 'نص بديل {param}'),\n"
                    "]</code>\n\n"
                    "2️⃣ <b>cooldown في</b> <code>news_db.py</code>:\n"
                    "<code>EVENT_COOLDOWNS['my_event'] = 600</code>\n\n"
                    "3️⃣ <b>دالة في</b> <code>news_generator.py</code>:\n"
                    "<code>def on_my_event(param):\n"
                    "    _post('my_event', f'key_{param}',\n"
                    "          'HIGH', 'war', param=param)</code>\n\n"
                    "4️⃣ <b>استدعاء من الكود المناسب:</b>\n"
                    "<code>from modules.magazine.news_generator import on_my_event\n"
                    "on_my_event(value)</code>\n\n"
                    "✅ <b>ملاحظة:</b> القوالب تستخدم <code>str.format(**kwargs)</code>\n"
                    "تأكد أن أسماء المتغيرات في القالب تطابق kwargs في _post()"
                ),
            },
            {
                "title": "🔔 البث والـ Anti-Spam",
                "content": (
                    "📌 <b>البث للمجموعات:</b>\n"
                    "• فقط HIGH و CRITICAL تُبثّ تلقائياً\n"
                    "• المجموعات تحتاج <code>enable_news = 1</code>\n"
                    "• يُفعَّل/يُعطَّل من إعدادات المجموعة\n\n"
                    "📌 <b>Anti-Spam (Cooldown):</b>\n"
                    "• كل حدث له مفتاح فريد: <code>event_type:event_ref</code>\n"
                    "• مثال: <code>war_start:war_5</code> — لا يتكرر لنفس الحرب\n"
                    "• الـ cooldown محفوظ في <code>news_cooldowns</code>\n"
                    "• cooldown = 0 يعني لا قيود (للترتيبات المجدولة)\n\n"
                    "📌 <b>التوافق مع المجلة القديمة:</b>\n"
                    "كل خبر يُضاف تلقائياً لـ <code>magazine_posts</code>\n"
                    "للتوافق مع الأوامر القديمة."
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


def _page_buttons(action: str, extra: dict, total: int, current: int, owner: tuple) -> tuple:
    """
    Builds numbered page buttons (1-based display, 0-based index).
    Returns (buttons_list, layout_list). 4 per row.
    Current page uses 'success' style; all others use default 'primary'.
    """
    page_btns = []
    for i in range(total):
        color = _GR if i == current else _B
        page_btns.append(btn(str(i + 1), action, {**extra, "p": i}, owner=owner, color=color))

    rows = []
    for i in range(0, len(page_btns), 4):
        rows.append(page_btns[i:i + 4])

    layout = [len(r) for r in rows]
    return [b for r in rows for b in r], layout


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

    pg_btns, pg_layout = _page_buttons("devguide_section", {"sid": sid}, total, page, owner)

    buttons = pg_btns + [
        btn("🔙 القائمة الرئيسية", "devguide_back", owner=owner, color=_RD),
    ]
    layout = pg_layout + [1]
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
