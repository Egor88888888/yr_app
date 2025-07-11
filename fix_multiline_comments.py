#!/usr/bin/env python3
"""
Исправление некорректных многострочных комментариев в bot/main.py
"""

import re


def fix_multiline_comments(file_path):
    """Исправляет некорректные многострочные комментарии"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Проверяем если это начало некорректного многострочного комментария
        if line.strip() == '# """' and i < len(lines) - 1:
            # Ищем конец такого комментария
            j = i + 1
            comment_lines = []

            while j < len(lines):
                if lines[j].strip() == '# """':
                    # Найден конец комментария
                    break
                comment_lines.append(lines[j])
                j += 1

            if j < len(lines) and lines[j].strip() == '# """':
                # Преобразуем в обычный docstring
                fixed_lines.append('    """')
                for comment_line in comment_lines:
                    # Убираем лишние отступы и добавляем правильные
                    cleaned_line = comment_line.strip()
                    if cleaned_line:
                        fixed_lines.append('    ' + cleaned_line)
                    else:
                        fixed_lines.append('')
                fixed_lines.append('    """')
                i = j + 1
                continue

        fixed_lines.append(line)
        i += 1

    # Записываем исправленный контент
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))

    print(f"Исправлены многострочные комментарии в {file_path}")


if __name__ == "__main__":
    fix_multiline_comments('bot/main.py')
    print("✅ Все многострочные комментарии исправлены!")
