#!/usr/bin/env python3
"""
Скрипт для исправления синтаксических ошибок с эмодзи в bot/main.py
"""

import re


def fix_syntax_errors():
    """Исправляет все синтаксические ошибки с эмодзи"""
    print("🔧 Исправление синтаксических ошибок...")

    # Читаем файл
    try:
        with open('bot/main.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return False

    # Проблемные строки которые нужно закомментировать
    problem_line_numbers = [3, 296, 5543]  # Основные проблемные строки

    fixed_count = 0

    # Исправляем каждую строку
    for i, line in enumerate(lines):
        line_num = i + 1
        original_line = line

        # Проверяем проблемные строки по номерам
        if line_num in problem_line_numbers:
            if not line.strip().startswith('#') and '🏛' in line:
                # Закомментируем строку
                lines[i] = f"# {line}"
                print(f"Line {line_num}: Закомментирована")
                fixed_count += 1

        # Дополнительная проверка: ищем строки с эмодзи вне строк
        elif '🏛' in line:
            # Проверяем, если это действительно проблемная строка
            clean_line = line.strip()

            # Пропускаем если это уже комментарий
            if clean_line.startswith('#'):
                continue

            # Пропускаем если это в docstring
            if clean_line.startswith('"""') or clean_line.startswith("'''"):
                continue

            # Пропускаем если это явно в строке
            if (('f"""' in line or 'f"' in line or "f'" in line or
                 '"""' in line or '"' in line or "'" in line) and
                    ('🏛' in line)):
                continue

            # Если дошли сюда, возможно это проблемная строка
            # Попробуем определить автоматически
            # Убираем строки в кавычках
            test_line = re.sub(r'["\'].*?["\']', '', line)
            if '🏛' in test_line and not test_line.strip().startswith('#'):
                # Это проблемная строка - закомментируем
                lines[i] = f"# {line}"
                print(f"Line {line_num}: Автоматически закомментирована")
                fixed_count += 1

    # Записываем исправленный файл
    try:
        with open('bot/main.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✅ Исправлено {fixed_count} строк!")
        return True
    except Exception as e:
        print(f"❌ Ошибка записи файла: {e}")
        return False


if __name__ == "__main__":
    fix_syntax_errors()
