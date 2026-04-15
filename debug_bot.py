#!/usr/bin/env python3
"""
Debug bot to identify why group messages aren't being processed
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bot import bot
from core.config import TOKEN

print(f"Debug bot with token: {TOKEN[:10]}...")

@bot.message_handler(func=lambda message: True)
def debug_all_messages(message):
    """Debug handler to see all incoming messages"""
    print(f"\n=== MESSAGE DEBUG ===")
    print(f"Chat ID: {message.chat.id}")
    print(f"Chat Type: {message.chat.type}")
    print(f"User ID: {message.from_user.id if message.from_user else 'None'}")
    print(f"Username: {message.from_user.username if message.from_user else 'None'}")
    print(f"Text: {message.text}")
    print(f"Message ID: {message.message_id}")
    print(f"Date: {message.date}")
    
    # Check if it's a group
    is_group = message.chat.type in ("group", "supergroup")
    print(f"Is Group: {is_group}")
    
    # Try to respond
    try:
        if is_group:
            bot.send_message(message.chat.id, f"✅ Group message received: '{message.text}'")
        else:
            bot.send_message(message.chat.id, f"✅ Private message received: '{message.text}'")
    except Exception as e:
        print(f"Error sending response: {e}")
    
    print("===================\n")

if __name__ == "__main__":
    print("🔍 Starting debug bot...")
    print("Send any message to see debug info")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Debug bot stopped.")