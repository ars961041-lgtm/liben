from core.bot import bot
import random

USER_LINK = "<a href='tg://user?id={userID}'>{firstName}</a>"

WELCOME_TEMPLATE = "<b>{msg} {user}</b>"
LEFT_TEMPLATE = "<b>{msg} {user}</b>"


welcome_msgs = [
"يا هلا وسهلا 👋 نورت المجموعة",
"مرحبا 🌟 القروب ازداد نور",
"هلا وغلا 😄 حياك بين اخوانك",
"حي الله 🔥 نورت المكان",
"أهلاً 🤝 تفضل البيت بيتك",
"يا مرحبا مليون ✨ نورت القروب",
"ياهلا 😎 شد حيلك معنا",
"مرحبا 🌹 وصلت الدار",
"هلا 👀 القروب نور يوم دخلت",
"يا أهلاً 🔥 القروب صار أخطر",
"يا أهلاً 🔥 توه القروب اكتمل",
"يا أهلاً 👀 انتبه لا تتعود علينا",
]

left_msgs = [
"مع السلامة 👋 الله يكتب لك الخير",
"طلع 😔 الباب يفوت جمل",
"ودعنا 🌙 الله يسهّل دربك",
"غادر 👀 شكله ما تحملنا",
"راح 🚶‍♂️ الله معه",
"انقلع 😂 نمزح ارجع بس",
"وداعا 🌹 نتمنى نشوفك مرة ثانية",
"خرج 👋 القروب بيشتاق لك",
"اختفى 🫡 الله يحفظه",
"غادر ✨ نتمنى له التوفيق",
]


def welcome_message(userID, firstName):
    user = USER_LINK.format(userID=userID, firstName=firstName)
    msg = random.choice(welcome_msgs)
    return WELCOME_TEMPLATE.format(msg=msg, user=user)


def left_message(userID, firstName):
    user = USER_LINK.format(userID=userID, firstName=firstName)
    msg = random.choice(left_msgs)
    return LEFT_TEMPLATE.format(msg=msg, user=user)

def welcome_member(message):

    for member in message.new_chat_members:
        text = welcome_message(member.id, member.first_name)
        bot.reply_to(message, text, parse_mode="HTML")

def left_member(message):
    user = message.left_chat_member
    text = left_message(user.id, user.first_name)
    bot.reply_to(message, text, parse_mode="HTML")