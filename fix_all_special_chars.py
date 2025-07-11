#!/usr/bin/env python3
"""
Исправление всех специальных символов в bot/main.py
"""

import re


def fix_special_chars(file_path):
    """Исправляет все специальные символы в Python файле"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    fixed_lines = []

    for line_num, line in enumerate(lines, 1):
        # Проверяем, является ли строка кодом (не строковым литералом)
        stripped = line.strip()

        # Пропускаем комментарии
        if stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # Проверяем наличие специальных символов
        special_chars = ['🔧', '🚀', '💸', '🏛️', '📋', '📊', '👥', '💳', '📈', '📦',
                         '⚠️', '✅', '❌', '🎯', '🤖', '💬', '📞', '📝', '🎛️', '•']

        has_special = any(char in line for char in special_chars)

        if has_special:
            # Проверяем, находится ли в строковом литерале
            in_string = False
            quote_char = None
            i = 0
            special_outside_string = False

            while i < len(line):
                char = line[i]

                # Отслеживаем состояние строк
                if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        quote_char = char
                    elif char == quote_char:
                        in_string = False
                        quote_char = None
                elif char == '\\' and in_string:
                    i += 1  # пропускаем экранированный символ

                # Проверяем специальные символы вне строк
                if not in_string and char in special_chars:
                    special_outside_string = True
                    break

                i += 1

            # Если специальный символ найден вне строки - комментируем
            if special_outside_string:
                if not stripped.startswith('#'):
                    # Определяем отступ
                    indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * indent + '# ' + line.strip())
                    print(
                        f"Line {line_num}: Закомментирована строка со спецсимволом")
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # Записываем исправленный файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))

    print(f"Исправлены специальные символы в {file_path}")


if __name__ == "__main__":
    fix_special_chars('bot/main.py')
    print("✅ Все специальные символы исправлены!")
