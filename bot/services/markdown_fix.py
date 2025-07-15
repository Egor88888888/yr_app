"""
🔧 MARKDOWN PARSER FIX
Исправление проблем с отображением markdown в Telegram
"""

import re
import html
from typing import Optional


def convert_markdown_to_html(text: str) -> str:
    """
    Конвертирует markdown в HTML для корректного отображения в Telegram

    Fixes:
    - **bold** -> <b>bold</b>
    - *italic* -> <i>italic</i>
    - `code` -> <code>code</code>
    - [link](url) -> <a href="url">link</a>
    """
    if not text:
        return text

    # Escape HTML characters first
    text = html.escape(text)

    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Convert *italic* to <i>italic</i> (but not if it's part of **)
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)

    # Convert `code` to <code>code</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)

    # Convert [text](url) to <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # Convert ### headers to bold
    text = re.sub(r'^### (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    return text


def safe_markdown_parse(text: str) -> tuple[str, str]:
    """
    Безопасный парсинг markdown с fallback

    Returns:
        tuple: (processed_text, parse_mode)
    """
    try:
        # Попытка конвертировать в HTML
        html_text = convert_markdown_to_html(text)
        return html_text, 'HTML'
    except Exception as e:
        # Fallback - убираем markdown символы
        clean_text = text.replace('**', '').replace('*', '').replace('`', '')
        return clean_text, None


def fix_channel_mention(text: str) -> str:
    """
    Исправляет упоминания каналов в тексте
    """
    # Заменяем @test_legal_channel на корректное упоминание
    text = text.replace('@test_legal_channel', '@legalcenter_pro')
    return text


def prepare_telegram_message(text: str) -> dict:
    """
    Подготавливает сообщение для отправки в Telegram

    Returns:
        dict: {"text": str, "parse_mode": str}
    """
    # Исправляем каналы
    text = fix_channel_mention(text)

    # Конвертируем markdown
    processed_text, parse_mode = safe_markdown_parse(text)

    result = {"text": processed_text}
    if parse_mode:
        result["parse_mode"] = parse_mode

    return result
