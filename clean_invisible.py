#!/usr/bin/env python3
"""
Удаление всех невидимых unicode символов
"""

import unicodedata


def clean_invisible_chars(file_path):
    """Удаляет все невидимые unicode символы"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Удаляем невидимые символы
    cleaned = ''
    for char in content:
        # Пропускаем форматирующие и невидимые символы
        if unicodedata.category(char) in ['Cf', 'Mn', 'Me']:
            continue
        # Конкретные проблемные символы
        if ord(char) in [0x200D, 0x200C, 0xFEFF, 0x2060, 0x061C]:
            continue
        cleaned += char

    # Записываем результат
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    print(f"Удалены невидимые символы из {file_path}")


if __name__ == "__main__":
    clean_invisible_chars('bot/main.py')
    print("✅ Невидимые символы удалены!")
