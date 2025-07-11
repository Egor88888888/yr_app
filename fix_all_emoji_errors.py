#!/usr/bin/env python3
"""
Скрипт для исправления ВСЕХ синтаксических ошибок с эмодзи в bot/main.py
"""

import re


def contains_emoji(text):
    """Проверяет содержит ли текст эмодзи"""
    emoji_pattern = re.compile("["
                               "\U0001F600-\U0001F64F"  # emoticons
                               "\U0001F300-\U0001F5FF"  # symbols & pictographs
                               "\U0001F680-\U0001F6FF"  # transport & map symbols
                               "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               "\U00002500-\U00002BEF"  # chinese char
                               "\U00002702-\U000027B0"
                               "\U00002702-\U000027B0"
                               "\U000024C2-\U0001F251"
                               "\U0001f926-\U0001f937"
                               "\U00010000-\U0010ffff"
                               "\u2640-\u2642"
                               "\u2600-\u2B55"
                               "\u200d"
                               "\u23cf"
                               "\u23e9"
                               "\u231a"
                               "\ufe0f"  # dingbats
                               "\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.search(text) is not None


def is_inside_string(line, emoji_pos):
    """Проверяет находится ли эмодзи внутри строкового литерала"""
    # Ищем все строковые литералы в строке
    patterns = [
        r'""".*?"""',  # тройные кавычки
        r"'''.*?'''",  # тройные апострофы
        r'f""".*?"""',  # f-строки с тройными кавычками
        r"f'''.*?'''",  # f-строки с тройными апострофами
        r'f".*?"',     # f-строки с обычными кавычками
        r"f'.*?'",     # f-строки с апострофами
        r'".*?"',      # обычные строки в кавычках
        r"'.*?'"       # обычные строки в апострофах
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, line):
            if match.start() <= emoji_pos <= match.end():
                return True
    return False


def fix_all_emoji_errors():
    """Исправляет все синтаксические ошибки с эмодзи"""
    print("🔧 Поиск и исправление всех эмодзи...")

    # Читаем файл
    try:
        with open('bot/main.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return False

    fixed_count = 0
    in_multiline_string = False

    # Обрабатываем каждую строку
    for i, line in enumerate(lines):
        line_num = i + 1

        # Пропускаем уже закомментированные строки
        if line.strip().startswith('#'):
            continue

        # Проверяем состояние многострочных строк
        triple_quote_count = line.count('"""') + line.count("'''")
        if triple_quote_count % 2 == 1:
            in_multiline_string = not in_multiline_string

        # Если мы внутри многострочной строки, пропускаем
        if in_multiline_string:
            continue

        # Ищем эмодзи в строке
        if contains_emoji(line):
            # Проверяем каждый эмодзи
            problem_found = False
            for match in re.finditer(r'[\U0001F000-\U0001F9FF]', line):
                emoji_pos = match.start()
                if not is_inside_string(line, emoji_pos):
                    problem_found = True
                    break

            if problem_found:
                # Закомментируем проблемную строку
                lines[i] = f"# {line}"
                print(
                    f"Line {line_num}: Найден эмодзи вне строки - закомментирована")
                fixed_count += 1

    # Записываем исправленный файл
    try:
        with open('bot/main.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✅ Исправлено {fixed_count} строк с эмодзи!")
        return True
    except Exception as e:
        print(f"❌ Ошибка записи файла: {e}")
        return False


if __name__ == "__main__":
    fix_all_emoji_errors()
