# handlers/mention_handler.py

from core.bot import bot
from database.db_queries.mention_queries import get_active_members, add_updated_at_column, update_member_activity
from utils.helpers import send_result
import html
import time
import threading

# Initialize the updated_at column on import
add_updated_at_column()

# In-memory cooldown to reduce database writes
_activity_cooldown = {}
_cooldown_lock = threading.Lock()
ACTIVITY_COOLDOWN_SECONDS = 30  # Only update DB every 30 seconds per user


def handle_mention_command(message) -> bool:
    """
    Handle mention commands: نداء, نادي, ping, call
    Returns True if command was handled.
    """
    text = message.text.strip()
    normalized_text = text.lower()
    
    # Check if it's a mention command
    mention_triggers = ["نداء", "نادي", "ping", "call"]
    
    command_word = None
    for trigger in mention_triggers:
        if normalized_text.startswith(trigger.lower()):
            command_word = trigger
            break
    
    if not command_word:
        return False
    
    # Extract reason (text after command)
    reason = text[len(command_word):].strip()
    if len(reason) > 100:  # Limit reason length
        reason = reason[:100] + "..."
    
    # Get active members
    members = get_active_members(message.chat.id)
    
    if not members:
        send_result(
            chat_id=message.chat.id,
            text="❌ لا توجد أعضاء نشطون في المجموعة.",
            reply_to_id=message.message_id
        )
        return True
    
    # Send mentions in batches of 5
    batch_size = 5
    total_batches = (len(members) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(members))
        batch_members = members[start_idx:end_idx]
        
        # Build message
        message_lines = []
        
        # Add reason only to first message
        if batch_num == 0 and reason:
            message_lines.append(f"📢 <b>{html.escape(reason)}</b>\n")
        
        message_lines.append("━━━━━━━━━━━━")
        
        # Add members with proper numbering
        for i, member in enumerate(batch_members):
            member_num = start_idx + i + 1
            mention_text = format_user_mention(member)
            message_lines.append(f"{member_num} - {mention_text}")
        
        # Join all lines and ensure LTR formatting
        final_message = "\n".join(message_lines)
        final_message = f"\u202D{final_message}\u202C"  # LTR override
        
        try:
            send_result(
                chat_id=message.chat.id,
                text=final_message,
                reply_to_id=message.message_id if batch_num == 0 else None
            )
        except Exception as e:
            # If HTML parsing fails, send without formatting
            plain_message = "\n".join([
                "━━━━━━━━━━━━",
                *[f"{start_idx + i + 1} - {member['name']}" for i, member in enumerate(batch_members)]
            ])
            send_result(
                chat_id=message.chat.id,
                text=f"\u202D{plain_message}\u202C",
                reply_to_id=message.message_id if batch_num == 0 else None
            )
    
    return True


def format_user_mention(member: dict) -> str:
    """
    Format a user mention based on available information.
    Returns clickable mention if username exists, otherwise name with tg://user link.
    """
    user_id = member['user_id']
    name = member['name'] or "Unknown"
    username = member.get('username')
    
    if username:
        # Use clickable @username mention
        return f"@{username}"
    else:
        # Use name with tg://user link
        escaped_name = html.escape(name)
        return f'<a href="tg://user?id={user_id}">{escaped_name}</a>'
