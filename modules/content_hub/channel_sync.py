"""
مزامنة القنوات مع مركز المحتوى.
يستقبل منشورات القنوات المرتبطة ويُدرجها تلقائياً.
"""
from core.bot import bot
from modules.content_hub.hub_db import (
    get_linked_channel, insert_content, upsert_content_by_text, create_tables,
)

create_tables()


def _clean(text: str) -> str:
    """تنظيف النص: إزالة الأسطر الفارغة والمسافات الزائدة."""
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines).strip()


def handle_channel_post(message):
    """معالج منشورات القنوات — يُسجَّل في main.py."""
    channel_id = message.chat.id
    link = get_linked_channel(channel_id)
    if not link:
        return

    text = message.text or message.caption or ""
    text = _clean(text)
    if not text:
        return  # تجاهل الوسائط بدون نص

    table = link["content_type"]
    insert_content(table, text)


def handle_channel_post_edit(message):
    """معالج تعديل منشورات القنوات."""
    channel_id = message.chat.id
    link = get_linked_channel(channel_id)
    if not link:
        return

    new_text = message.text or message.caption or ""
    new_text = _clean(new_text)
    if not new_text:
        return

    table = link["content_type"]
    # حاول التحديث أولاً، وإن فشل أدرج كمحتوى جديد
    updated = upsert_content_by_text(table, new_text, new_text)
    if not updated:
        insert_content(table, new_text)
