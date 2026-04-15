"""
HTML Sanitization Utilities
Provides safe HTML handling for Telegram messages to prevent parsing errors.
"""
import re
from typing import Optional, Union
from core.bot import bot


def escape_html(text: str) -> str:
    """
    Escapes HTML special characters to prevent parsing errors.
    
    Args:
        text: Raw text that may contain HTML special characters
        
    Returns:
        HTML-safe text with escaped characters
    """
    if not text:
        return ""
    
    return (str(text)
            .replace("&", "&amp;")   # Must be first to avoid double-escaping
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


def sanitize_html_tags(text: str) -> str:
    """
    Sanitizes HTML by ensuring all tags are properly closed.
    Removes or fixes malformed HTML tags.
    
    Args:
        text: Text that may contain HTML tags
        
    Returns:
        Text with properly closed HTML tags or tags removed if malformed
    """
    if not text:
        return ""
    
    # Allowed Telegram HTML tags
    allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a']
    
    # Track open tags
    open_tags = []
    result = ""
    i = 0
    
    while i < len(text):
        if text[i] == '<':
            # Find the end of the tag
            tag_end = text.find('>', i)
            if tag_end == -1:
                # Malformed tag, escape it
                result += "&lt;"
                i += 1
                continue
            
            tag_content = text[i+1:tag_end]
            
            # Check if it's a closing tag
            if tag_content.startswith('/'):
                tag_name = tag_content[1:].strip().lower()
                if tag_name in allowed_tags and open_tags and open_tags[-1] == tag_name:
                    # Valid closing tag
                    result += text[i:tag_end+1]
                    open_tags.pop()
                else:
                    # Invalid closing tag, escape it
                    result += "&lt;" + tag_content + "&gt;"
            else:
                # Opening tag
                tag_parts = tag_content.split()
                tag_name = tag_parts[0].lower() if tag_parts else ""
                
                if tag_name in allowed_tags:
                    # Valid opening tag
                    result += text[i:tag_end+1]
                    if tag_name != 'a':  # 'a' tags might be self-closing in some contexts
                        open_tags.append(tag_name)
                else:
                    # Invalid tag, escape it
                    result += "&lt;" + tag_content + "&gt;"
            
            i = tag_end + 1
        else:
            result += text[i]
            i += 1
    
    # Close any remaining open tags
    while open_tags:
        tag = open_tags.pop()
        result += f"</{tag}>"
    
    return result


def safe_format(template: str, **kwargs) -> str:
    """
    Safely formats a template with HTML escaping for user-provided values.
    
    Args:
        template: Format string with placeholders
        **kwargs: Values to insert (will be HTML-escaped)
        
    Returns:
        Formatted string with escaped values
    """
    escaped_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, (str, int, float)):
            escaped_kwargs[key] = escape_html(str(value))
        else:
            escaped_kwargs[key] = value
    
    return template.format(**escaped_kwargs)


def safe_send_message(chat_id: int, text: str, parse_mode: Optional[str] = "HTML", 
                     reply_markup=None, reply_to_message_id: Optional[int] = None,
                     disable_web_page_preview: bool = True) -> Optional[object]:
    """
    Safely sends a message with HTML parsing, falling back to plain text on error.
    
    Args:
        chat_id: Target chat ID
        text: Message text
        parse_mode: Parse mode ("HTML" or None)
        reply_markup: Keyboard markup
        reply_to_message_id: Message ID to reply to
        disable_web_page_preview: Whether to disable link previews
        
    Returns:
        Message object if successful, None otherwise
    """
    try:
        if parse_mode == "HTML":
            # First try with HTML parsing
            return bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
                disable_web_page_preview=disable_web_page_preview
            )
        else:
            return bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
                disable_web_page_preview=disable_web_page_preview
            )
    except Exception as e:
        # If HTML parsing fails, try with plain text
        try:
            # Remove HTML tags for plain text fallback
            plain_text = re.sub(r'<[^>]+>', '', text)
            return bot.send_message(
                chat_id=chat_id,
                text=plain_text,
                parse_mode=None,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
                disable_web_page_preview=disable_web_page_preview
            )
        except Exception:
            print(f"[HTML_SANITIZER] Failed to send message to {chat_id}: {e}")
            return None


def safe_edit_message_text(chat_id: int, message_id: int, text: str, 
                          parse_mode: Optional[str] = "HTML", reply_markup=None,
                          disable_web_page_preview: bool = True) -> bool:
    """
    Safely edits a message with HTML parsing, falling back to plain text on error.
    
    Args:
        chat_id: Target chat ID
        message_id: Message ID to edit
        text: New message text
        parse_mode: Parse mode ("HTML" or None)
        reply_markup: Keyboard markup
        disable_web_page_preview: Whether to disable link previews
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if parse_mode == "HTML":
            # First try with HTML parsing
            bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
        else:
            bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
    except Exception as e:
        # If HTML parsing fails, try with plain text
        try:
            # Remove HTML tags for plain text fallback
            plain_text = re.sub(r'<[^>]+>', '', text)
            bot.edit_message_text(
                text=plain_text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode=None,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
        except Exception:
            print(f"[HTML_SANITIZER] Failed to edit message {message_id} in {chat_id}: {e}")
            return False


def safe_reply_to(message, text: str, parse_mode: Optional[str] = "HTML", 
                 reply_markup=None, disable_web_page_preview: bool = True) -> Optional[object]:
    """
    Safely replies to a message with HTML parsing, falling back to plain text on error.
    
    Args:
        message: Original message object to reply to
        text: Reply text
        parse_mode: Parse mode ("HTML" or None)
        reply_markup: Keyboard markup
        disable_web_page_preview: Whether to disable link previews
        
    Returns:
        Message object if successful, None otherwise
    """
    try:
        if parse_mode == "HTML":
            # First try with HTML parsing
            return bot.reply_to(
                message=message,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
        else:
            return bot.reply_to(
                message=message,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
    except Exception as e:
        # If HTML parsing fails, try with plain text
        try:
            # Remove HTML tags for plain text fallback
            plain_text = re.sub(r'<[^>]+>', '', text)
            return bot.reply_to(
                message=message,
                text=plain_text,
                parse_mode=None,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
        except Exception:
            print(f"[HTML_SANITIZER] Failed to reply to message: {e}")
            return None


def clickable_name(name: str, user_id: int) -> str:
    """
    Creates a safe clickable HTML link for a user name.
    
    Args:
        name: User's display name
        user_id: User's Telegram ID
        
    Returns:
        HTML link with properly escaped name
    """
    safe_name = escape_html(name)
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'


def safe_country_name(name: str) -> str:
    """
    Safely formats a country name for HTML display.
    
    Args:
        name: Country name from database
        
    Returns:
        HTML-safe country name wrapped in <b> tags
    """
    safe_name = escape_html(name)
    return f"<b>{safe_name}</b>"


def safe_alliance_name(name: str) -> str:
    """
    Safely formats an alliance name for HTML display.
    
    Args:
        name: Alliance name from database
        
    Returns:
        HTML-safe alliance name wrapped in <b> tags
    """
    safe_name = escape_html(name)
    return f"<b>{safe_name}</b>"