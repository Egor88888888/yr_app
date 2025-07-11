#!/usr/bin/env python3
"""
Точечное исправление emoji проблем в bot/main.py
"""

import re


def fix_emoji_issues(file_path):
    """Исправляет только emoji проблемы, не трогая структуру"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Паттерн для поиска emoji вне строк
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF\U0001F018-\U0001F0F5\U0001F0A0-\U0001F0AE\U0001F0B1-\U0001F0BF\U0001F0C1-\U0001F0CF\U0001F0D1-\U0001F0FF\U0001F30D-\U0001F567\U0001F600-\U0001F636\U0001F681-\U0001F6C5\U0001F30E-\U0001F195\U0001F197-\U0001F1AC\U0001F1AE-\U0001F1FF\U0001F300-\U0001F579\U0001F57B-\U0001F5A3\U0001F5A5-\U0001F5FF]+'

    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Проверяем если строка содержит emoji вне кавычек
        if re.search(emoji_pattern, line):
            # Проверяем если emoji НЕ внутри строки
            in_string = False
            quote_char = None
            i = 0

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

                i += 1

            # Если emoji найден вне строки и строка не комментарий docstring
            if (re.search(emoji_pattern, line) and
                not line.strip().startswith('"""') and
                not line.strip().endswith('"""') and
                not (line.strip().startswith('"') and line.strip().endswith('"')) and
                    not (line.strip().startswith("'") and line.strip().endswith("'"))):
                # Комментируем строку
                if line.strip() and not line.strip().startswith('#'):
                    fixed_lines.append('    # ' + line.strip())
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # Записываем исправленный файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))

    print(f"Исправлены emoji проблемы в {file_path}")


if __name__ == "__main__":
    fix_emoji_issues('bot/main.py')
    print("✅ Emoji проблемы исправлены!")
