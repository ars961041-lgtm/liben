"""
معالج ألعاب الترفيه — إدارة الألعاب التفاعلية
"""
import random
import time
from core.bot import bot
from database.db_queries.bank_queries import check_bank_account, update_bank_balance
from handlers.games.games_data import ALL_GAMES, GAMES_3_LIBEN, GAMES_5_LIBEN, GAMES_NO_REWARD
from utils.pagination import set_state, get_state, clear_state

# تخزين حالات الألعاب النشطة
ACTIVE_GAMES = {}  # game_id -> {"question": ..., "answer": ..., "start_time": ..., "participants": set()}

def entertainment_games_command(message):
    """
    معالج أوامر ألعاب الترفيه
    يرجع True إذا تم التعامل مع الأمر
    """
    if not message.text:
        return False

    text = message.text.strip().lower()
    user_id = message.from_user.id
    chat_id = message.chat.id

    # التحقق من الألعاب المتاحة
    for game_key, game_data in ALL_GAMES.items():
        if text == game_key:
            _start_game(message, game_key, game_data)
            return True

    # التحقق من الإجابات على الألعاب النشطة
    if _handle_game_answer(message):
        return True

    return False

def _start_game(message, game_key, game_data):
    """بدء لعبة جديدة"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    game_id = f"{chat_id}_{game_key}"

    # إنهاء اللعبة السابقة إذا كانت موجودة
    if game_id in ACTIVE_GAMES:
        _end_game(game_id)

    # اختيار سؤال عشوائي
    questions = game_data["data"]
    if not questions:
        bot.reply_to(message, f"❌ لا توجد أسئلة متاحة للعبة {game_data['name']} حالياً.")
        return

    question_data = random.choice(questions)

    # إعداد بيانات اللعبة
    game_info = {
        "game_key": game_key,
        "game_data": game_data,
        "question": question_data,
        "start_time": time.time(),
        "participants": set(),
        "chat_id": chat_id,
        "message_id": message.message_id
    }

    ACTIVE_GAMES[game_id] = game_info

    # إرسال السؤال
    _send_question(game_info, message)

def _send_question(game_info, original_message):
    """إرسال السؤال للمستخدمين"""
    game_data = game_info["game_data"]
    question_data = game_info["question"]
    game_key = game_info["game_key"]

    if game_data["type"] == "quote":
        # لعبة الحكم
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"🎯 <b>الحكمة:</b>\n<code>{question_data}</code>\n\n"
        text += f"💰 <b>الجائزة:</b> {game_data['reward']} Liben\n\n"
        text += f"اكتب الحكمة كما هي لتحصل على الجائزة!"

    elif game_data["type"] == "unscramble":
        # لعبة فكك
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"🔀 <b>فكك الكلمة:</b>\n<code>{question_data['scrambled']}</code>\n\n"
        text += f"💰 <b>الجائزة:</b> {game_data['reward']} Liben"

    elif game_data["type"] == "reverse":
        # لعبة عكس
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"🔄 <b>اعكس الكلمة:</b>\n<code>{question_data['word']}</code>\n\n"
        text += f"💰 <b>الجائزة:</b> {game_data['reward']} Liben"

    elif game_data["type"] == "connect":
        # لعبة وصل
        parts = question_data['parts']
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"🔗 <b>وصل الكلمة:</b>\n<code>{' + '.join(parts)}</code>\n\n"
        text += f"💰 <b>الجائزة:</b> {game_data['reward']} Liben"

    elif game_data["type"] == "country":
        # لعبة بلد
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"🌍 <b>السؤال:</b>\n{question_data['question']}\n\n"
        text += f"💰 <b>الجائزة:</b> {game_data['reward']} Liben"

    elif game_data["type"] == "capital":
        # لعبة عاصمة
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"🏛️ <b>السؤال:</b>\n{question_data['question']}\n\n"
        text += f"💰 <b>الجائزة:</b> {game_data['reward']} Liben"

    elif game_data["type"] == "fastest":
        # لعبة الأسرع
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"⚡ <b>السؤال:</b>\n{question_data['question']}\n\n"
        text += f"💰 <b>الجائزة:</b> {game_data['reward']} Liben للأسرع في الإجابة الصحيحة!"

    elif game_data["type"] == "question":
        # لعبة سؤال (بدون مكافأة)
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"❓ <b>السؤال:</b>\n{question_data}\n\n"
        text += f"📝 اكتب إجابتك في الرد!"

    elif game_data["type"] == "write":
        # لعبة كت (بدون مكافأة)
        text = f"{game_data['emoji']} <b>لعبة {game_data['name']}</b>\n\n"
        text += f"📝 <b>الموضوع:</b>\n{question_data}\n\n"
        text += f"✍️ اكتب إجابتك في الرد!"

    bot.send_message(
        chat_id=original_message.chat.id,
        text=text,
        parse_mode='HTML',
        reply_to_message_id=original_message.message_id
    )

def _handle_game_answer(message):
    """معالجة إجابة المستخدم على لعبة نشطة"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_answer = message.text.strip()

    # البحث عن لعبة نشطة في هذه المجموعة
    active_game = None
    game_id = None
    for gid, game_info in ACTIVE_GAMES.items():
        if game_info["chat_id"] == chat_id:
            active_game = game_info
            game_id = gid
            break

    if not active_game:
        return False

    game_data = active_game["game_data"]
    question_data = active_game["question"]

    # التحقق من الإجابة
    correct_answer = _get_correct_answer(game_data["type"], question_data)

    if _is_answer_correct(user_answer, correct_answer, game_data["type"]):
        # إجابة صحيحة
        _handle_correct_answer(message, active_game, game_id, user_id)
        return True
    else:
        # إجابة خاطئة
        if game_data["reward"] > 0:  # فقط في الألعاب التي تمنح مكافآت
            bot.reply_to(message, "❌ خطأ! حاول مرة أخرى.", parse_mode='HTML')
            _end_game(game_id)
        return True

    return False

def _get_correct_answer(game_type, question_data):
    """الحصول على الإجابة الصحيحة بناءً على نوع اللعبة"""
    if game_type in ["quote", "unscramble", "reverse", "connect"]:
        return question_data.get("answer", question_data)
    elif game_type in ["country", "capital", "fastest"]:
        return question_data["answer"]
    else:
        return None

def _is_answer_correct(user_answer, correct_answer, game_type):
    """التحقق من صحة الإجابة"""
    if not correct_answer:
        return False

    user_clean = user_answer.strip().lower()
    correct_clean = str(correct_answer).strip().lower()

    # إزالة المسافات والعلامات
    user_clean = ''.join(user_clean.split())
    correct_clean = ''.join(correct_clean.split())

    return user_clean == correct_clean

def _handle_correct_answer(message, game_info, game_id, user_id):
    """معالجة الإجابة الصحيحة"""
    game_data = game_info["game_data"]
    reward = game_data["reward"]

    if reward > 0:
        if not check_bank_account(user_id):
            success_msg = f"✅ <b>صحيح!</b> اكتب '<code>انشاء حساب بنكي</code>' للحصول على جائزة 🎁\n"
        else:
        # منح المكافأة
            update_bank_balance(user_id, reward)
            # رسالة النجاح
            success_msg = f"✅ <b>صحيح!</b> لقد حصلت على جائزتك 🎁\n"
            success_msg += f"💰 +{reward} Liben"

        bot.reply_to(message, success_msg, parse_mode='HTML')

    # إنهاء اللعبة
    _end_game(game_id)

def _end_game(game_id):
    """إنهاء اللعبة وتنظيف البيانات"""
    if game_id in ACTIVE_GAMES:
        del ACTIVE_GAMES[game_id]

# تنظيف الألعاب القديمة كل دقيقة
def cleanup_old_games():
    """تنظيف الألعاب القديمة (أكثر من 10 دقائق)"""
    current_time = time.time()
    to_remove = []

    for game_id, game_info in ACTIVE_GAMES.items():
        if current_time - game_info["start_time"] > 600:  # 10 دقائق
            to_remove.append(game_id)

    for game_id in to_remove:
        del ACTIVE_GAMES[game_id]

# تشغيل التنظيف كل دقيقة
import threading
def _periodic_cleanup():
    while True:
        time.sleep(60)  # كل دقيقة
        cleanup_old_games()

cleanup_thread = threading.Thread(target=_periodic_cleanup, daemon=True)
cleanup_thread.start()