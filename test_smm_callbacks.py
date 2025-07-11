#!/usr/bin/env python3
"""
🔍 SMM Callback Coverage Test
Проверяет что все callback'ы SMM системы имеют обработчики
"""

import re


def test_smm_callback_coverage():
    """Проверяет покрытие SMM callback'ов"""

    # Читаем файл main.py
    with open('bot/main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Находим все callback_data="smm_" в кнопках
    button_callbacks = set()
    button_pattern = r'callback_data="(smm_[^"]+)"'
    for match in re.finditer(button_pattern, content):
        button_callbacks.add(match.group(1))

    # Находим все elif data == "smm_" в handle_smm_actions
    handler_callbacks = set()
    elif_pattern = r'elif data == "(smm_[^"]+)":'
    for match in re.finditer(elif_pattern, content):
        handler_callbacks.add(match.group(1))

    # Находим все функции handle_smm_
    functions = set()
    func_pattern = r'async def (handle_smm_[^(]+)'
    for match in re.finditer(func_pattern, content):
        functions.add(match.group(1))

    print("🔍 **SMM CALLBACK COVERAGE ANALYSIS**\n")

    print(f"📊 **Статистика:**")
    print(f"• Кнопки с callback_data: {len(button_callbacks)}")
    print(f"• Elif блоки в handle_smm_actions: {len(handler_callbacks)}")
    print(f"• Функции handle_smm_: {len(functions)}")

    # Проверяем покрытие
    missing_handlers = button_callbacks - handler_callbacks
    missing_functions = handler_callbacks - \
        set(f"handle_{cb}" for cb in handler_callbacks if f"handle_{cb}" not in functions)

    print(f"\n❌ **MISSING HANDLERS:** {len(missing_handlers)}")
    for callback in sorted(missing_handlers):
        print(f"  • {callback}")

    print(f"\n❌ **MISSING FUNCTIONS:** {len(missing_functions)}")
    for func in sorted(missing_functions):
        print(f"  • {func}")

    coverage = (len(handler_callbacks) / len(button_callbacks)) * \
        100 if button_callbacks else 0
    print(f"\n📈 **COVERAGE:** {coverage:.1f}%")

    if coverage >= 95:
        print("✅ **ОТЛИЧНО! Покрытие > 95%**")
    elif coverage >= 80:
        print("⚠️ **ХОРОШО. Покрытие > 80%**")
    else:
        print("❌ **ПЛОХО. Покрытие < 80%**")

    return coverage >= 95


if __name__ == "__main__":
    test_smm_callback_coverage()
