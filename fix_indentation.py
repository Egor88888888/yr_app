#!/usr/bin/env python3
"""
Исправление отступов в bot/main.py
"""

import re


def fix_indentation(file_path):
    """Исправляет отступы в Python файле"""

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    indent_level = 0
    in_function = False
    in_class = False
    last_was_def = False
    last_was_if_try_for_while = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Пропускаем пустые строки и комментарии (кроме docstring)
        if not stripped or (stripped.startswith('#') and not stripped.startswith('# """')):
            fixed_lines.append(line)
            continue

        # Проверяем уменьшение отступов
        if (stripped.startswith('except') or stripped.startswith('else:') or
                stripped.startswith('elif') or stripped.startswith('finally')):
            if indent_level > 0:
                indent_level -= 1

        # Определяем начало функции/класса
        if stripped.startswith('def ') or stripped.startswith('async def '):
            indent_level = 0 if not in_class else 1
            in_function = True
            last_was_def = True
        elif stripped.startswith('class '):
            indent_level = 0
            in_class = True
            in_function = False
            last_was_def = True
        elif (stripped.startswith('if ') or stripped.startswith('try:') or
              stripped.startswith('for ') or stripped.startswith('while ') or
              stripped.startswith('with ') or stripped.startswith('async with ')):
            last_was_if_try_for_while = True

        # Применяем отступ
        if stripped:
            new_line = '    ' * indent_level + stripped + '\n'
            fixed_lines.append(new_line)
        else:
            fixed_lines.append('\n')

        # Увеличиваем отступ для следующих строк
        if last_was_def:
            indent_level += 1
            last_was_def = False
        elif last_was_if_try_for_while:
            indent_level += 1
            last_was_if_try_for_while = False
        elif (stripped.endswith(':') and not stripped.startswith('#') and
              'def ' not in stripped and 'class ' not in stripped):
            indent_level += 1

        # Уменьшаем отступ после return, break, continue, pass
        if (stripped in ['return', 'break', 'continue', 'pass'] or
                stripped.startswith('return ') or stripped.startswith('raise ')):
            if indent_level > 1:
                indent_level -= 1

        # Проверяем конец блоков
        if i < len(lines) - 1:
            next_stripped = lines[i + 1].strip()
            if (next_stripped.startswith('def ') or next_stripped.startswith('async def ') or
                next_stripped.startswith('class ') or
                (next_stripped and not next_stripped.startswith('#') and
                 not next_stripped.startswith('if') and not next_stripped.startswith('else') and
                 not next_stripped.startswith('elif') and not next_stripped.startswith('except') and
                 not next_stripped.startswith('finally') and not next_stripped.startswith('try') and
                 indent_level > 0 and
                 (not in_function or next_stripped.startswith('def ') or next_stripped.startswith('async def ')))):
                if next_stripped.startswith('def ') or next_stripped.startswith('async def '):
                    indent_level = 0
                elif next_stripped.startswith('class '):
                    indent_level = 0
                    in_function = False
                elif indent_level > 0:
                    indent_level = 0

    # Записываем исправленный файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"Исправлены отступы в {file_path}")


if __name__ == "__main__":
    fix_indentation('bot/main.py')
    print("✅ Все отступы исправлены!")
