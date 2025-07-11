#!/usr/bin/env python3
"""
Скрипт для исправления поломанных многострочных строк после комментирования эмодзи
"""


def fix_broken_strings():
    """Исправляет поломанные многострочные строки"""
    print("🔧 Исправление поломанных многострочных строк...")

    # Читаем файл
    try:
        with open('bot/main.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return False

    # Заменяем проблемные конструкции
    fixes = [
        # Исправляем незакрытые тройные кавычки после комментирования
        ('            "intro": """💸', '            # "intro": """💸'),
        ('            "key_points": """🎯', '            # "key_points": """🎯'),

        # Другие потенциальные проблемы
        ('"intro": """', '# "intro": """'),
        ('"key_points": """', '# "key_points": """'),
        ('"content": """', '# "content": """'),

        # Исправляем одинокие тройные кавычки
        ('            """', '            # """'),
        ('        """', '        # """'),
    ]

    fixed_count = 0
    original_content = content

    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            fixed_count += 1
            print(f"Исправлено: {old[:30]}... → {new[:30]}...")

    # Дополнительно ищем и исправляем оставшиеся проблемы
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Если строка начинается с пробелов и содержит незакрытые тройные кавычки
        if line.strip().startswith('"') and '"""' in line and not line.strip().startswith('#'):
            lines[i] = line.replace(line.strip(), f"# {line.strip()}")
            print(f"Line {i+1}: Закомментирована строка с кавычками")
            fixed_count += 1

    content = '\n'.join(lines)

    # Записываем исправленный файл
    try:
        with open('bot/main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Исправлено {fixed_count} проблемных конструкций!")
        return True
    except Exception as e:
        print(f"❌ Ошибка записи файла: {e}")
        return False


if __name__ == "__main__":
    fix_broken_strings()
