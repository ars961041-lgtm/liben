from .config import TOKEN
import telebot

bot = telebot.TeleBot(token=TOKEN)
bot_username = None