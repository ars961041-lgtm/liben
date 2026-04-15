#!/usr/bin/env python3
"""
Simple bot test script to verify the bot is responding
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bot import bot
from core.config import TOKEN

print(f"Testing bot with token: {TOKEN[:10]}...")

@bot.message_handler(commands=['test'])
def test_command(message):
    bot.reply_to(message, "✅ Bot is working! Test successful.")
    print(f"Test command received from user {message.from_user.id}")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == 'test')
def test_text(message):
    bot.reply_to(message, "✅ Bot is responding to text messages!")
    print(f"Test text received from user {message.from_user.id}")

if __name__ == "__main__":
    print("🧪 Starting test bot...")
    print("Send /test or 'test' to verify the bot is working")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Bot stopped.")