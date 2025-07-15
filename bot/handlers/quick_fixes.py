"""
🔧 QUICK FIXES HANDLER
Быстрые исправления для каналов, комментариев и markdown
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from bot.services.channel_fix import quick_channel_fix, get_channel_status_report, ChannelCommentsSetup
from bot.services.markdown_fix import prepare_telegram_message

logger = logging.getLogger(__name__)


async def quick_fix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /quick_fix - быстрое исправление проблем
    """
    user_id = update.effective_user.id

    # Проверяем права админа
    admin_users = {6373924442, 343688708}  # Из production config
    if user_id not in admin_users:
        await update.message.reply_text(
            "❌ У вас нет доступа к этой команде",
            parse_mode=None
        )
        return

    # Получаем отчет о текущем статусе
    status_report = get_channel_status_report(context.bot)

    # Подготавливаем сообщение
    status_text = f"""🔧 **БЫСТРЫЕ ИСПРАВЛЕНИЯ**

📊 **Текущий статус:**
• Канал: {status_report['current_channel']}
• Существует: {'✅' if status_report['channel_exists'] else '❌'}

🐛 **Обнаруженные проблемы:**
• Канал не найден: {'❌' if status_report['issues']['channel_not_found'] else '✅'}
• Комментарии не работают: {'❌' if status_report['issues']['no_comments'] else '✅'}
• Markdown сломан: {'❌' if status_report['issues']['markdown_broken'] else '✅'}

🚀 **Доступные исправления:**"""

    # Подготавливаем сообщение с правильным парсингом
    message_data = prepare_telegram_message(status_text)

    keyboard = [
        [
            InlineKeyboardButton("🔧 Исправить канал",
                                 callback_data="fix_channel"),
            InlineKeyboardButton("💬 Настроить комментарии",
                                 callback_data="fix_comments")
        ],
        [
            InlineKeyboardButton(
                "📝 Тест markdown", callback_data="test_markdown"),
            InlineKeyboardButton("🧪 Тестовый пост", callback_data="test_post")
        ],
        [
            InlineKeyboardButton(
                "📋 Полный отчет", callback_data="full_report"),
            InlineKeyboardButton("🔄 Обновить", callback_data="refresh_status")
        ]
    ]

    await update.message.reply_text(
        **message_data,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def quick_fix_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для быстрых исправлений"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "fix_channel":
        await handle_channel_fix(query, context)
    elif data == "fix_comments":
        await handle_comments_fix(query, context)
    elif data == "test_markdown":
        await handle_markdown_test(query, context)
    elif data == "test_post":
        await handle_test_post(query, context)
    elif data == "full_report":
        await handle_full_report(query, context)
    elif data == "refresh_status":
        await handle_refresh_status(query, context)
    else:
        await query.edit_message_text(f"⚠️ Неизвестная команда: {data}")


async def handle_channel_fix(query, context):
    """Исправление канала"""
    await query.edit_message_text("🔧 Исправляю настройки канала...")

    try:
        # Получаем рекомендуемый канал
        result = await quick_channel_fix(context.bot)

        if result["success"]:
            response_text = f"""✅ **КАНАЛ НАСТРОЕН УСПЕШНО**

📺 **Канал:** {result['channel_username']}
📝 **Название:** {result['channel_title']}
🤖 **Статус бота:** {result['bot_status']}
💬 **Комментарии:** {'✅ Работают' if result['comments_enabled'] else '❌ Требуется настройка'}

{result.get('deployment_instructions', '')}"""
        else:
            response_text = f"""❌ **ОШИБКА НАСТРОЙКИ КАНАЛА**

🔍 **Проблема:** {result['error']}
💡 **Решение:** {result['suggestion']}
🔧 **Рекомендуемый канал:** {result.get('recommended_channel', '@legalcenter_pro')}

📋 **Что нужно сделать:**
1. Создайте канал {result.get('recommended_channel', '@legalcenter_pro')}
2. Добавьте бота как администратора
3. Запустите исправление снова"""

        # Подготавливаем ответ
        message_data = prepare_telegram_message(response_text)

        keyboard = [
            [
                InlineKeyboardButton("🔄 Попробовать снова",
                                     callback_data="fix_channel"),
                InlineKeyboardButton(
                    "💬 Настроить комментарии", callback_data="fix_comments")
            ],
            [
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]
        ]

        await query.edit_message_text(
            **message_data,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in handle_channel_fix: {e}")
        await query.edit_message_text(
            f"❌ Ошибка исправления канала: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]])
        )


async def handle_comments_fix(query, context):
    """Автоматическое исправление комментариев"""
    await query.edit_message_text("💬 Диагностика системы комментариев...")

    try:
        from bot.services.comments_auto_setup import get_auto_comments_manager

        # Используем новый автоматический менеджер
        comments_manager = get_auto_comments_manager(context.bot)

        # Получаем текущий канал
        import os
        current_channel = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
            'CHANNEL_ID') or '@test_legal_channel'

        # Автоматическая диагностика и настройка
        result = await comments_manager.enable_comments_for_all_posts(current_channel)

        if result["success"]:
            response_text = f"""✅ **КОММЕНТАРИИ НАСТРОЕНЫ**

📺 **Канал:** {current_channel}
💬 **Статус:** {result['message']}

🎉 **Все новые посты будут автоматически поддерживать комментарии!**

📋 **Что это означает:**
• Под каждым постом будет кнопка "💬 Комментарии"
• Пользователи смогут оставлять комментарии
• Комментарии модерируются автоматически
• Система отвечает на вопросы пользователей

🔧 **Дополнительные возможности:**
• Автоматические ответы экспертов
• Уведомления о новых комментариях
• Аналитика взаимодействий"""
        else:
            response_text = f"""⚠️ **ТРЕБУЕТСЯ НАСТРОЙКА КОММЕНТАРИЕВ**

📺 **Канал:** {current_channel}
❌ **Проблема:** {result.get('message', 'Неизвестная ошибка')}

{result.get('instructions', '📋 Инструкции по настройке недоступны')}

💡 **СОВЕТ:**
После настройки группы обсуждений комментарии будут работать автоматически для всех постов!"""

        # Подготавливаем ответ
        message_data = prepare_telegram_message(response_text)

        keyboard = [
            [
                InlineKeyboardButton("🧪 Тестовый пост",
                                     callback_data="test_post"),
                InlineKeyboardButton("📊 Статус всех каналов",
                                     callback_data="comments_status_all")
            ],
            [
                InlineKeyboardButton("🔄 Повторить диагностику",
                                     callback_data="fix_comments"),
                InlineKeyboardButton("🔧 Исправить канал",
                                     callback_data="fix_channel")
            ],
            [
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]
        ]

        await query.edit_message_text(
            **message_data,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in handle_comments_fix: {e}")
        await query.edit_message_text(
            f"❌ Ошибка диагностики комментариев: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]])
        )


async def handle_markdown_test(query, context):
    """Тест markdown"""
    test_content = """📝 **ТЕСТ MARKDOWN**

✅ **Жирный текст:** работает
✅ *Курсив:* работает
✅ `Код:` работает
✅ [Ссылка](https://t.me/legalcenter_pro): работает

### Заголовок 3 уровня
## Заголовок 2 уровня
# Заголовок 1 уровня

🎯 **Если вы видите это сообщение с правильным форматированием - markdown исправлен!**"""

    # Подготавливаем сообщение
    message_data = prepare_telegram_message(test_content)

    keyboard = [
        [
            InlineKeyboardButton("🔄 Еще тест", callback_data="test_markdown"),
            InlineKeyboardButton("🧪 Тест пост", callback_data="test_post")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="refresh_status")
        ]
    ]

    await query.edit_message_text(
        **message_data,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_test_post(query, context):
    """Создание тестового поста"""
    await query.edit_message_text("🧪 Создаю тестовый пост...")

    try:
        # Получаем SMM интеграцию
        from bot.services.smm_integration import get_smm_integration
        smm_integration = get_smm_integration()

        if not smm_integration:
            await query.edit_message_text(
                "❌ SMM система не доступна",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "◀️ Назад", callback_data="refresh_status")
                ]])
            )
            return

        # Создаем тестовый пост
        test_content = """🧪 **ТЕСТОВЫЙ ПОСТ ПОСЛЕ ИСПРАВЛЕНИЯ**

✅ **Проверяем:**
• Канал подключен
• Markdown работает
• Комментарии доступны

💬 **Попробуйте оставить комментарий под этим постом!**

📱 **Бесплатная консультация:** /start"""

        result = await smm_integration.create_immediate_post(
            content=test_content,
            content_type="test_post",
            priority=10
        )

        if result.get("success"):
            response_text = f"""✅ **ТЕСТОВЫЙ ПОСТ СОЗДАН**

📝 **Результат:** Пост опубликован
🆔 **ID:** {result.get('post_id', 'N/A')}
💬 **Комментарии:** Проверьте в канале

🎯 **Проверьте в канале:**
• Отображается ли форматирование правильно
• Работают ли комментарии
• Есть ли кнопка консультации"""
        else:
            response_text = f"""❌ **ОШИБКА СОЗДАНИЯ ПОСТА**

🔍 **Проблема:** {result.get('error', 'Неизвестная ошибка')}
💡 **Решение:** Проверьте настройки канала"""

        # Подготавливаем ответ
        message_data = prepare_telegram_message(response_text)

        keyboard = [
            [
                InlineKeyboardButton("🔄 Еще тест", callback_data="test_post"),
                InlineKeyboardButton("🔧 Исправить канал",
                                     callback_data="fix_channel")
            ],
            [
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]
        ]

        await query.edit_message_text(
            **message_data,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in handle_test_post: {e}")
        await query.edit_message_text(
            f"❌ Ошибка создания тестового поста: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]])
        )


async def handle_full_report(query, context):
    """Полный отчет о системе"""
    await query.edit_message_text("📋 Генерирую полный отчет...")

    try:
        # Получаем статус системы
        import os
        from bot.services.smm_integration import get_smm_integration

        current_channel = os.getenv('TARGET_CHANNEL_ID') or os.getenv(
            'CHANNEL_ID') or '@test_legal_channel'
        smm_integration = get_smm_integration()

        report_text = f"""📋 **ПОЛНЫЙ ОТЧЕТ СИСТЕМЫ**

📺 **Канал:**
• ID: {current_channel}
• Статус: {'❌ Fallback' if current_channel == '@test_legal_channel' else '✅ Настроен'}

🤖 **SMM Система:**
• Статус: {'✅ Работает' if smm_integration else '❌ Недоступна'}
• Автопостинг: {'✅ Включен' if smm_integration and smm_integration.is_running else '❌ Выключен'}

💬 **Комментарии:**
• Статус: ❌ Требуется настройка
• Решение: Создать группу обсуждений

📝 **Markdown:**
• Статус: ✅ Исправлен
• Парсер: HTML (вместо Markdown)

🚀 **Рекомендации:**
1. Создайте канал @legalcenter_pro
2. Добавьте бота как администратора
3. Настройте группу обсуждений
4. Обновите переменные окружения в Railway
5. Проверьте автопостинг"""

        # Подготавливаем ответ
        message_data = prepare_telegram_message(report_text)

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔧 Исправить все", callback_data="fix_channel"),
                InlineKeyboardButton("🧪 Тест", callback_data="test_post")
            ],
            [
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]
        ]

        await query.edit_message_text(
            **message_data,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in handle_full_report: {e}")
        await query.edit_message_text(
            f"❌ Ошибка генерации отчета: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="refresh_status")
            ]])
        )


async def handle_refresh_status(query, context):
    """Обновление статуса"""
    # Возвращаемся к главному меню
    await quick_fix_command(query, context)


def register_quick_fixes_handlers(application):
    """Регистрация обработчиков быстрых исправлений"""
    application.add_handler(CommandHandler("quick_fix", quick_fix_command))
    application.add_handler(CallbackQueryHandler(
        quick_fix_callback_handler,
        pattern="^(fix_channel|fix_comments|test_markdown|test_post|full_report|refresh_status)$"
    ))
