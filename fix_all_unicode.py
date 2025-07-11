#!/usr/bin/env python3
"""
Универсальная замена всех проблемных unicode символов
"""

import re


def fix_all_unicode(file_path):
    """Заменяет все проблемные unicode символы"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Большой словарь замен
    replacements = {
        # Emoji
        '🔧': 'FIX:',
        '🚀': 'ROCKET:',
        '💸': 'MONEY:',
        '🏛️': 'BUILDING:',
        '📋': 'CLIPBOARD:',
        '📊': 'CHART:',
        '👥': 'USERS:',
        '💳': 'CARD:',
        '📈': 'GROWTH:',
        '📦': 'PACKAGE:',
        '⚠️': 'WARNING:',
        '✅': 'SUCCESS:',
        '❌': 'ERROR:',
        '🎯': 'TARGET:',
        '🤖': 'BOT:',
        '💬': 'CHAT:',
        '📞': 'PHONE:',
        '📝': 'MEMO:',
        '🎛️': 'CONTROL:',
        '🆕': 'NEW:',
        '🔍': 'SEARCH:',
        '📲': 'MOBILE:',
        '💰': 'DOLLAR:',
        '💼': 'BRIEFCASE:',
        '📄': 'DOCUMENT:',
        '🔒': 'LOCK:',
        '🛡️': 'SHIELD:',
        '⭐': 'STAR:',
        '📱': 'PHONE:',
        '🔗': 'LINK:',
        '🌐': 'GLOBE:',
        '📜': 'SCROLL:',
        '⚖️': 'SCALES:',
        '🏢': 'OFFICE:',
        '🎭': 'MASKS:',
        '🌟': 'SPARKLE:',
        '🎓': 'GRADUATION:',
        '📍': 'LOCATION:',
        '🔥': 'FIRE:',
        '🎪': 'TENT:',
        '🎮': 'GAME:',
        '📺': 'TV:',
        '📷': 'CAMERA:',
        '🎵': 'MUSIC:',
        '🎸': 'GUITAR:',
        '🎤': 'MIC:',
        '⏰': 'CLOCK:',
        '⌚': 'WATCH:',
        '🕰️': 'CLOCK:',
        '📅': 'CALENDAR:',
        '📆': 'CALENDAR:',
        '🗓️': 'CALENDAR:',
        '📚': 'BOOKS:',
        '📖': 'BOOK:',
        '📑': 'PAGES:',
        '📃': 'PAGE:',
        '📰': 'NEWSPAPER:',
        '🗞️': 'NEWS:',
        '📸': 'PHOTO:',
        '🎨': 'ART:',
        '🎉': 'PARTY:',
        '💡': 'IDEA:',
        '🔄': 'CHANGES:',

        # Другие символы
        '•': '-',
        '№': 'No.',
        '₽': ' rubles',
        '–': '-',
        '—': '-',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '…': '...',
        '©': '(c)',
        '®': '(R)',
        '™': '(TM)',
        '°': ' degrees',
        '±': '+/-',
        '×': 'x',
        '÷': '/',
        '≈': '~',
        '≠': '!=',
        '≤': '<=',
        '≥': '>=',
        '²': '^2',
        '³': '^3',
        '¼': '1/4',
        '½': '1/2',
        '¾': '3/4',
        'α': 'alpha',
        'β': 'beta',
        'γ': 'gamma',
        'δ': 'delta',
        'λ': 'lambda',
        'μ': 'mu',
        'π': 'pi',
        'σ': 'sigma',
        'φ': 'phi',
        'ω': 'omega',
    }

    # Применяем все замены
    for old, new in replacements.items():
        content = content.replace(old, new)

    # Дополнительно убираем все оставшиеся проблемные символы
    # Заменяем любые символы вне ASCII и основных unicode диапазонов
    content = re.sub(
        r'[^\x00-\x7F\u0080-\u00FF\u0100-\u017F\u0180-\u024F\u1E00-\u1EFF\u2000-\u206F\u20A0-\u20CF\u2100-\u214F]', '?', content)

    # Записываем результат
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Заменены все unicode символы в {file_path}")


if __name__ == "__main__":
    fix_all_unicode('bot/main.py')
    print("✅ Все unicode символы заменены!")
