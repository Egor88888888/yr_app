#!/usr/bin/env python3
"""
Универсальное исправление всех синтаксических ошибок
"""

import re


def fix_syntax_errors(file_path):
    """Исправляет все синтаксические ошибки"""

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    in_multiline_string = False
    string_delimiter = None

    for i, line in enumerate(lines):
        original_line = line
        line_num = i + 1

        # Отслеживаем многострочные строки
        if '"""' in line or "'''" in line:
            quote_count_3 = line.count('"""')
            apos_count_3 = line.count("'''")

            if quote_count_3 % 2 == 1:
                if not in_multiline_string:
                    in_multiline_string = True
                    string_delimiter = '"""'
                elif string_delimiter == '"""':
                    in_multiline_string = False
                    string_delimiter = None

            if apos_count_3 % 2 == 1:
                if not in_multiline_string:
                    in_multiline_string = True
                    string_delimiter = "'''"
                elif string_delimiter == "'''":
                    in_multiline_string = False
                    string_delimiter = None

        stripped = line.strip()

        # Пропускаем уже закомментированные строки
        if stripped.startswith('#'):
            fixed_lines.append(original_line)
            continue

        # Пропускаем строки внутри многострочных строк
        if in_multiline_string:
            fixed_lines.append(original_line)
            continue

        # Пропускаем пустые строки
        if not stripped:
            fixed_lines.append(original_line)
            continue

        # Проверяем строки с кириллицей вне кавычек
        if re.search(r'[а-яё]', stripped, re.IGNORECASE):
            # Проверяем что это не часть строки
            in_quotes = False
            quote_char = None

            for j, char in enumerate(stripped):
                if char in ['"', "'"] and (j == 0 or stripped[j-1] != '\\'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None

            # Если кириллица вне кавычек - комментируем строку
            has_cyrillic_outside = False
            in_quotes = False
            quote_char = None

            for j, char in enumerate(stripped):
                if char in ['"', "'"] and (j == 0 or stripped[j-1] != '\\'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                elif not in_quotes and re.match(r'[а-яё]', char, re.IGNORECASE):
                    has_cyrillic_outside = True
                    break

            if has_cyrillic_outside:
                # Определяем отступ
                indent = len(original_line) - len(original_line.lstrip())
                fixed_line = ' ' * indent + '# ' + stripped + '\n'
                fixed_lines.append(fixed_line)
                print(f"Line {line_num}: Закомментирована строка с кириллицей")
                continue

        # Проверяем SQL запросы вне строк
        if any(keyword in stripped.upper() for keyword in ['SELECT ', 'FROM ', 'WHERE ', 'JOIN ', 'GROUP BY', 'HAVING']):
            if not (stripped.startswith('"') or stripped.startswith("'") or
                    '"""' in stripped or "'''" in stripped):
                # Это SQL запрос вне строки - комментируем
                indent = len(original_line) - len(original_line.lstrip())
                fixed_line = ' ' * indent + '# ' + stripped + '\n'
                fixed_lines.append(fixed_line)
                print(f"Line {line_num}: Закомментирована строка с SQL")
                continue

        # Оставляем строку как есть
        fixed_lines.append(original_line)

    # Записываем результат
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"Исправлены синтаксические ошибки в {file_path}")


if __name__ == "__main__":
    fix_syntax_errors('bot/main.py')
    print("✅ Все синтаксические ошибки исправлены!")
