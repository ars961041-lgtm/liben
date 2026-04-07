"""
محرك ألعاب الترفيه الموحد
- تتبع الحالة بـ (chat_id, game_key) لمنع التداخل بين المجموعات
- تحقق موحد من الإجابات مع معالجة خاصة لكل نوع
- سؤال/كت: بدون تحقق، فقط عرض
"""
import re
import random
import time
import threading
from core.bot import bot
from database.db_queries.bank_queries import check_bank_account, update_bank_balance
from handlers.games.games_data import ALL_GAMES
from modules.bank.utils.constants import CURRENCY_ARABIC_NAME

# ══════════════════════════════════════════
# حالات الألعاب النشطة
# key: (chat_id, game_key) → game_info dict
# ══════════════════════════════════════════
ACTIVE_GAMES: dict[tuple, dict] = {}
_LOCK = threading.Lock()

# أنواع الألعاب التي لا تحتاج تحققاً (عرض فقط)
NO_CHECK_TYPES = {"question", "write"}

# أنواع الألعاب المقيدة بصاحبها فقط
OWNED_GAME_TYPES = {"unscramble", "reverse", "connect", "country", "capital"}

# مهلة انتهاء اللعبة (ثواني)
GAME_TIMEOUT = 120


# ══════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════

def entertainment_games_command(message) -> bool:
    if not message.text:
        return False

    text    = message.text.strip().lower()
    user_id = message.from_user.id
    chat_id = message.chat.id

    # تشغيل لعبة
    for game_key, game_data in ALL_GAMES.items():
        if text == game_key:
            _start_game(message, game_key, game_data)
            return True

    # محاولة إجابة
    return _handle_game_answer(message)


# ══════════════════════════════════════════
# بدء اللعبة
# ══════════════════════════════════════════

def _start_game(message, game_key: str, game_data: dict):
    chat_id = message.chat.id
    user_id = message.from_user.id
    key     = (chat_id, game_key)

    with _LOCK:
        if key in ACTIVE_GAMES:
            del ACTIVE_GAMES[key]

        questions = game_data.get("data", [])
        if not questions:
            bot.reply_to(message, f"❌ لا توجد أسئلة متاحة لـ {game_data['name']} حالياً.")
            return

        question_data = random.choice(questions)
        ACTIVE_GAMES[key] = {
            "game_key":   game_key,
            "game_data":  game_data,
            "question":   question_data,
            "start_time": time.time(),
            "chat_id":    chat_id,
            "owner_uid":  user_id,
        }

    _send_question(message, game_data, question_data)

    # جدولة انتهاء تلقائي لجميع الأنواع
    threading.Timer(GAME_TIMEOUT, _timeout_game, args=(key,)).start()


# ══════════════════════════════════════════
# إرسال السؤال
# ══════════════════════════════════════════

def _send_question(message, game_data: dict, question_data):
    gtype   = game_data["type"]
    emoji   = game_data["emoji"]
    name    = game_data["name"]
    reward  = game_data["reward"]
    reward_line = f"\n💰 <b>الجائزة:</b> {reward} {CURRENCY_ARABIC_NAME}" if reward > 0 else ""

    if gtype == "quote":
        text = (f"{emoji} <b>لعبة {name}</b>\n\n"
                f"🎯 <b>الحكمة:</b>  {question_data}"
                f"{reward_line}\n\nاكتب الحكمة كما هي!")

    elif gtype == "unscramble":
        text = (f"{emoji} <b>لعبة {name}</b>\n\n"
                f"🔀 <b>فكك الكلمة:</b> {question_data['scrambled']}"
                f"{reward_line}")

    elif gtype == "reverse":
        text = (f"{emoji} <b>لعبة {name}</b>\n\n"
                f"🔄 <b>اعكس الكلمة:</b> {question_data['word']}"
                f"{reward_line}")

    elif gtype == "connect":
        parts = question_data["parts"]
        text = (f"{emoji} <b>لعبة {name}</b>\n\n"
                f"🔗 <b>وصل الكلمة:</b> {' + '.join(parts)}"
                f"{reward_line}")

    elif gtype == "country":
        text = (f"{emoji} <b>لعبة {name}</b>\n\n"
                f"🌍 ما اسم هذه الدولة "
                f"{question_data['question']} ؟\n\n"
                f"اكتب اسم الدولة بالعربي"
                f"{reward_line}")
        
    elif gtype == "capital":
        text = (f"{emoji} <b>لعبة {name}</b>\n\n"
                f"🏛️ <b>عاصمة </b> {question_data['question']}؟"
                f"{reward_line}")
    
    elif gtype == "fastest":
        text = (f"{emoji} <b>لعبة {name}</b>\n\n"
                f"⚡ <b>السؤال:</b> {question_data['question']}"
                f"{reward_line}")

    elif gtype == "question":
        text = (f"{emoji} {question_data}")

    elif gtype == "write":
        text = (f"{emoji} {question_data}")

    else:
        text = f"{emoji} <b>لعبة {name}</b>\n\n{question_data}"

    bot.send_message(message.chat.id, text, parse_mode="HTML",
                     reply_to_message_id=message.message_id)


# ══════════════════════════════════════════
# معالجة الإجابة
# ══════════════════════════════════════════

def _handle_game_answer(message) -> bool:
    chat_id = message.chat.id
    user_id = message.from_user.id

    with _LOCK:
        matching = [(k, v) for k, v in ACTIVE_GAMES.items()
                    if k[0] == chat_id]

    if not matching:
        return False

    # سرّب الألعاب من الأحدث للأقدم
    matching.sort(key=lambda x: x[1]["start_time"], reverse=True)

    for key, game_info in matching:
        game_data = game_info["game_data"]
        gtype     = game_data["type"]

        # سؤال/كت: لا تحقق — لا تستهلك الرسالة
        if gtype in NO_CHECK_TYPES:
            continue

        # فحص الملكية — استهلك الرسالة بصمت (لا تمررها لـ chat_responses)
        if gtype in OWNED_GAME_TYPES and user_id != game_info["owner_uid"]:
            return True  # الرسالة تخص لعبة نشطة — ابتلعها

        # استخرج الإجابة الصحيحة لهذه اللعبة تحديداً
        correct = _get_correct_answer(gtype, game_info["question"])
        if correct is None:
            # بيانات اللعبة تالفة — أنهِ اللعبة
            _end_game(key)
            continue

        if _is_correct(message.text, correct, gtype):
            _award_and_end(message, game_info, key, user_id)
        else:
            if game_data["reward"] > 0:
                bot.reply_to(message,
                             f"❌ إجابة خاطئة! الإجابة الصحيحة: <b>{correct}</b>",
                             parse_mode="HTML")
            _end_game(key)
        return True  # تمت المعالجة — لا تمرر الرسالة

    return False


# ══════════════════════════════════════════
# استخراج الإجابة الصحيحة
# ══════════════════════════════════════════

def _get_correct_answer(gtype: str, question_data) -> str | None:
    """استخراج الإجابة الصحيحة بأمان حسب نوع اللعبة."""
    try:
        if gtype == "quote":
            # question_data هو نص مباشر
            if isinstance(question_data, str):
                return question_data
            return None
        if gtype in ("unscramble", "reverse", "connect", "country", "capital", "fastest"):
            if isinstance(question_data, dict):
                return str(question_data.get("answer", "")) or None
            return None
    except Exception:
        pass
    return None


# ══════════════════════════════════════════
# التحقق من الإجابة
# ══════════════════════════════════════════

def _normalize(text: str) -> str:
    """تنظيف عام: lowercase + إزالة الرموز غير الأبجدية مع الحفاظ على المسافات"""
    text = text.strip().lower()
    # أزل الرموز غير الأبجدية وغير المسافات
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
    # اختزل المسافات المتعددة
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _normalize_no_spaces(text: str) -> str:
    """تنظيف بدون مسافات — للمقارنة الصارمة (وصل، عكس، عاصمة، بلد)"""
    return re.sub(r'[\s\W]+', '', text.strip().lower(), flags=re.UNICODE)


def _normalize_split(text: str) -> str:
    """
    تنظيف لعبة فكك: يحافظ على المسافات بين الحروف.
    يُحوّل المسافات المتعددة إلى مسافة واحدة، ويزيل الرموز غير الأبجدية.
    "م  ك ت ب ة" → "م ك ت ب ة"
    """
    # أزل الرموز غير الأبجدية (غير المسافات)
    text = re.sub(r'[^\w\s]', '', text.strip(), flags=re.UNICODE)
    # اختزل المسافات المتعددة إلى مسافة واحدة
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _is_correct(user_answer: str, correct: str, gtype: str) -> bool:
    if not user_answer or not correct:
        return False

    # ── فكك: مقارنة بالتنسيق المقسّم (م ك ت ب ة) ──
    if gtype == "unscramble":
        return _normalize_split(user_answer) == _normalize_split(correct)

    # ── حكيمة: مقارنة مع الحفاظ على المسافات ──
    if gtype == "quote":
        return _normalize(user_answer) == _normalize(correct)

    # ── باقي الأنواع: بدون مسافات ──
    return _normalize_no_spaces(user_answer) == _normalize_no_spaces(correct)


# ══════════════════════════════════════════
# منح المكافأة وإنهاء اللعبة
# ══════════════════════════════════════════

def _award_and_end(message, game_info: dict, key: tuple, user_id: int):
    reward = game_info["game_data"]["reward"]

    if reward > 0:
        if not check_bank_account(user_id):
            msg = "✅ <b>إجابة صحيحة!</b>\n\nاكتب <code>انشاء حساب بنكي</code> للحصول على جائزتك 🎁"
        else:
            update_bank_balance(user_id, reward)
            msg = f"✅ <b>إجابة صحيحة!</b>\n\n💰 +{reward} {CURRENCY_ARABIC_NAME} أُضيفت لرصيدك!"
        bot.reply_to(message, msg, parse_mode="HTML")

    _end_game(key)


# ══════════════════════════════════════════
# إنهاء اللعبة
# ══════════════════════════════════════════

def _end_game(key: tuple):
    with _LOCK:
        ACTIVE_GAMES.pop(key, None)


def _timeout_game(key: tuple):
    with _LOCK:
        info = ACTIVE_GAMES.pop(key, None)
    if info:
        try:
            bot.send_message(info["chat_id"],
                             "⏰ انتهى وقت اللعبة! لم يُجب أحد بشكل صحيح.",
                             parse_mode="HTML")
        except Exception:
            pass


# ══════════════════════════════════════════
# تنظيف دوري للألعاب المنتهية
# ══════════════════════════════════════════

def cleanup_old_games():
    now = time.time()
    with _LOCK:
        expired = [k for k, v in ACTIVE_GAMES.items()
                   if now - v["start_time"] > GAME_TIMEOUT + 30]
        for k in expired:
            del ACTIVE_GAMES[k]


def _periodic_cleanup():
    while True:
        time.sleep(60)
        cleanup_old_games()


threading.Thread(target=_periodic_cleanup, daemon=True).start()
