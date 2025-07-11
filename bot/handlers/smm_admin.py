"""
🎛️ SMM ADMIN PANEL
Administrative commands for Professional SMM System management
"""

import logging
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..services.smm_integration import get_smm_integration

logger = logging.getLogger(__name__)

# Список админов (добавьте свой Telegram ID)
ADMIN_IDS = [
    343688708,  # Egor D. - Администратор бота
    439952839,  # Дмитрий Носов - Администратор бота
]


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in ADMIN_IDS


async def smm_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smm_status - показать статус SMM системы"""

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return

    try:
        smm_integration = get_smm_integration()

        if not smm_integration:
            await update.message.reply_text("❌ SMM система не инициализирована")
            return

        # Получаем статус системы
        status = await smm_integration.smm_system.get_system_status()

        status_text = f"""🎯 **СТАТУС SMM СИСТЕМЫ**

🔄 **Состояние:** {'🟢 Активна' if status['is_running'] else '🔴 Остановлена'}
⚙️ **Режим:** {status['system_mode']}
📊 **Стратегия:** {status['content_strategy']}

📝 **Запланированные посты (24ч):** {status['upcoming_posts_24h']}
💬 **Активные сессии взаимодействия:** {status['active_interaction_sessions']}
💡 **Рекомендации к оптимизации:** {status['optimization_suggestions_count']}

🕐 **Последняя оптимизация:** {status['last_optimization'][:19]}

🎛️ **Управление:**"""

        # Создаем клавиатуру управления
        keyboard = [
            [
                InlineKeyboardButton(
                    "📊 Аналитика", callback_data="smm_analytics"),
                InlineKeyboardButton(
                    "🎯 Создать пост", callback_data="smm_create_post")
            ],
            [
                InlineKeyboardButton(
                    "⚙️⚙️ Настройки", callback_data="smm_settings"),
                InlineKeyboardButton(
                    "🔄 Оптимизация", callback_data="smm_optimize")
            ],
            [
                InlineKeyboardButton("🟢 Старт" if not status['is_running'] else "🔴 Стоп",
                                     callback_data="smm_toggle"),
                InlineKeyboardButton("🔄 Обновить", callback_data="smm_status")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in smm_status_command: {e}")
        await update.message.reply_text(f"❌ Ошибка получения статуса: {str(e)}")


async def smm_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smm_analytics - показать аналитику"""

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return

    try:
        smm_integration = get_smm_integration()

        if not smm_integration:
            await update.message.reply_text("❌ SMM система не инициализирована")
            return

        # Получаем аналитику за последние 7 дней
        analytics = await smm_integration.get_smm_analytics_report(days_back=7)

        if 'error' in analytics:
            await update.message.reply_text(f"❌ Ошибка получения аналитики: {analytics['error']}")
            return

        smm_perf = analytics.get('smm_performance', {})
        bot_integration = analytics.get('bot_integration', {})

        analytics_text = f"""📊 **АНАЛИТИКА SMM СИСТЕМЫ** (7 дней)

📝 **Контент:**
• Опубликовано постов: {smm_perf.get('total_posts', 0)}
• Общее вовлечение: {smm_perf.get('total_engagement', 0):,}
• Средний engagement rate: {smm_perf.get('engagement_rate', 0):.2%}
• Вирусные хиты: {smm_perf.get('viral_hits', 0)}

🎯 **Конверсии:**
• Всего конверсий: {smm_perf.get('conversions', 0)}
• Conversion rate: {smm_perf.get('conversion_rate', 0):.2%}
• Атрибутированный доход: {smm_perf.get('revenue_attributed', 0):,.0f}₽

📈 **Рост аудитории:** {smm_perf.get('audience_growth', 0):+.1%}

🤖 **Интеграция с ботом:**
• Новые пользователи из канала: {bot_integration.get('new_users_from_channel', 0)}
• Запросы консультаций: {bot_integration.get('consultations_requested', 0)}
• Конверсия канал→бот: {bot_integration.get('conversion_rate_channel_to_bot', 0):.1%}

🔥 **Топ типы контента:**"""

        # Добавляем топ типы контента
        top_types = smm_perf.get('top_content_types', [])
        for i, content_type in enumerate(top_types[:3], 1):
            analytics_text += f"\n{i}. {content_type}"

        # Добавляем рекомендации
        recommendations = analytics.get('recommendations', [])
        if recommendations:
            analytics_text += "\n\n💡 **Рекомендации:**"
            for i, rec in enumerate(recommendations[:3], 1):
                rec_title = rec.get('title', 'Рекомендация')
                analytics_text += f"\n{i}. {rec_title}"

        # Клавиатура с дополнительными опциями
        keyboard = [
            [
                InlineKeyboardButton(
                    "📈 Детальная аналитика", callback_data="smm_detailed_analytics"),
                InlineKeyboardButton("📊 Экспорт данных",
                                     callback_data="smm_export_data")
            ],
            [
                InlineKeyboardButton(
                    "🔄 Обновить", callback_data="smm_analytics"),
                InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_status")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            analytics_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in smm_analytics_command: {e}")
        await update.message.reply_text(f"❌ Ошибка получения аналитики: {str(e)}")


async def smm_create_post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smm_create_post - создать умный пост"""

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return

    try:
        smm_integration = get_smm_integration()

        if not smm_integration:
            await update.message.reply_text("❌ SMM система не инициализирована")
            return

        # Генерируем и планируем пост
        await update.message.reply_text("🤖 Генерирую оптимизированный контент...")

        result = await smm_integration.schedule_smart_post()

        success_text = f"""✅ **ПОСТ СОЗДАН И ЗАПЛАНИРОВАН**

🆔 **ID поста:** {result['post_id']}
⏰ **Время публикации:** {result['scheduled_time'][:19]}
📊 **Ожидаемое вовлечение:** {result['expected_engagement']:.2%}
🧪 **A/B тест:** {'✅ Включен' if result['ab_test_enabled'] else '❌ Выключен'}
💬 **Управление взаимодействиями:** {'✅ Включено' if result['interaction_session_started'] else '❌ Выключено'}

🎯 Пост будет опубликован автоматически в оптимальное время!"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "📝 Создать еще", callback_data="smm_create_post"),
                InlineKeyboardButton(
                    "📋 Расписание", callback_data="smm_schedule")
            ],
            [
                InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_status")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            success_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in smm_create_post_command: {e}")
        await update.message.reply_text(f"❌ Ошибка создания поста: {str(e)}")


async def smm_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smm_settings - настройки SMM системы"""

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return

    try:
        smm_integration = get_smm_integration()

        if not smm_integration:
            await update.message.reply_text("❌ SMM система не инициализирована")
            return

        config = smm_integration.smm_config

        settings_text = f"""⚙️ **НАСТРОЙКИ SMM СИСТЕМЫ**

🎯 **Текущая конфигурация:**
• Режим работы: {config.system_mode.value}
• Стратегия контента: {config.content_strategy.value}
• Постов в день: {config.posts_per_day}
• Уровень оптимизации: {config.optimization_level.value}

🔧 **Функции:**
• A/B тестирование: {'✅' if config.enable_ab_testing else '❌'}
• Авто-взаимодействия: {'✅' if config.enable_auto_interactions else '❌'}
• Вирусная амплификация: {'✅' if config.enable_viral_amplification else '❌'}

📊 **Целевые метрики:**
• Engagement rate: {config.target_engagement_rate:.1%}
• Conversion rate: {config.target_conversion_rate:.1%}
• Порог качества контента: {config.content_quality_threshold:.1%}"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 Изменить стратегию",
                                     callback_data="smm_change_strategy"),
                InlineKeyboardButton(
                    "📝 Постов в день", callback_data="smm_change_frequency")
            ],
            [
                InlineKeyboardButton(
                    "🔧 Функции", callback_data="smm_toggle_features"),
                InlineKeyboardButton(
                    "📊 Метрики", callback_data="smm_set_targets")
            ],
            [
                InlineKeyboardButton("🔄 Сброс к умолчаниям",
                                     callback_data="smm_reset_config"),
                InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_status")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in smm_settings_command: {e}")
        await update.message.reply_text(f"❌ Ошибка получения настроек: {str(e)}")


async def smm_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов для SMM панели"""

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет доступа к этой функции")
        return

    try:
        smm_integration = get_smm_integration()

        if not smm_integration:
            await query.edit_message_text("❌ SMM система не инициализирована")
            return

        data = query.data

        if data == "smm_status":
            # Обновляем статус
            status = await smm_integration.smm_system.get_system_status()

            status_text = f"""🎯 **СТАТУС SMM СИСТЕМЫ**

🔄 **Состояние:** {'🟢 Активна' if status['is_running'] else '🔴 Остановлена'}
⚙️ **Режим:** {status['system_mode']}
📊 **Стратегия:** {status['content_strategy']}

📝 **Запланированные посты (24ч):** {status['upcoming_posts_24h']}
💬 **Активные сессии взаимодействия:** {status['active_interaction_sessions']}
💡 **Рекомендации к оптимизации:** {status['optimization_suggestions_count']}

🕐 **Последняя оптимизация:** {status['last_optimization'][:19]}"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📊 Аналитика", callback_data="smm_analytics"),
                    InlineKeyboardButton(
                        "🎯 Создать пост", callback_data="smm_create_post")
                ],
                [
                    InlineKeyboardButton(
                        "⚙️⚙️ Настройки", callback_data="smm_settings"),
                    InlineKeyboardButton(
                        "🔄 Оптимизация", callback_data="smm_optimize")
                ],
                [
                    InlineKeyboardButton("🟢 Старт" if not status['is_running'] else "🔴 Стоп",
                                         callback_data="smm_toggle"),
                    InlineKeyboardButton(
                        "🔄 Обновить", callback_data="smm_status")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                status_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data == "smm_analytics":
            # Показываем аналитику
            analytics = await smm_integration.get_smm_analytics_report(days_back=7)
            smm_perf = analytics.get('smm_performance', {})

            analytics_text = f"""📊 **АНАЛИТИКА SMM** (7 дней)

📝 **Контент:** {smm_perf.get('total_posts', 0)} постов
💬 **Вовлечение:** {smm_perf.get('total_engagement', 0):,}
📈 **Engagement rate:** {smm_perf.get('engagement_rate', 0):.2%}
🎯 **Конверсии:** {smm_perf.get('conversions', 0)}
💰 **Доход:** {smm_perf.get('revenue_attributed', 0):,.0f}₽"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📈 Подробнее", callback_data="smm_detailed_analytics"),
                    InlineKeyboardButton(
                        "🔄 Обновить", callback_data="smm_analytics")
                ],
                [
                    InlineKeyboardButton(
                        "◀️◀️ Назад", callback_data="smm_status")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                analytics_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data == "smm_create_post":
            # Создаем новый пост
            await query.edit_message_text("🤖 Генерирую оптимизированный контент...")

            result = await smm_integration.schedule_smart_post()

            success_text = f"""✅ **ПОСТ СОЗДАН**

🆔 {result['post_id']}
⏰ {result['scheduled_time'][:19]}
📊 Ожидаемое вовлечение: {result['expected_engagement']:.2%}"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📝 Создать еще", callback_data="smm_create_post"),
                    InlineKeyboardButton(
                        "◀️◀️ Назад", callback_data="smm_status")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                success_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data == "smm_change_strategy":
            # Меню смены стратегии
            strategy_text = """🎯 **ВЫБЕРИТЕ СТРАТЕГИЮ КОНТЕНТА:**

🔥 **Вирусная** - фокус на максимальное распространение
💰 **Конверсионная** - фокус на привлечение клиентов  
💬 **Вовлечение** - фокус на взаимодействие с аудиторией
⚖️ **Сбалансированная** - универсальный подход
📚 **Образовательная** - фокус на обучающий контент"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔥 Вирусная", callback_data="strategy_viral_focused"),
                    InlineKeyboardButton(
                        "💰 Конверсионная", callback_data="strategy_conversion_focused")
                ],
                [
                    InlineKeyboardButton(
                        "💬 Вовлечение", callback_data="strategy_engagement_focused"),
                    InlineKeyboardButton(
                        "⚖️ Сбалансированная", callback_data="strategy_balanced")
                ],
                [
                    InlineKeyboardButton(
                        "📚 Образовательная", callback_data="strategy_educational"),
                    InlineKeyboardButton(
                        "◀️◀️ Назад", callback_data="smm_settings")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                strategy_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data.startswith("strategy_"):
            # Применяем новую стратегию
            strategy_map = {
                "strategy_viral_focused": "viral_focused",
                "strategy_conversion_focused": "conversion_focused",
                "strategy_engagement_focused": "engagement_focused",
                "strategy_balanced": "balanced",
                "strategy_educational": "educational"
            }

            new_strategy = strategy_map.get(data)
            if new_strategy:
                # Переключаем режим SMM системы
                result = await smm_integration.switch_smm_mode(new_strategy)

                if result['success']:
                    await query.edit_message_text(
                        f"✅ Стратегия изменена на: **{result['new_mode']}**\n\n"
                        f"🔄 Новые настройки:\n"
                        f"• Постов в день: {result['config_changes']['posts_per_day']}\n"
                        f"• A/B тесты: {'✅' if result['config_changes']['ab_testing_enabled'] else '❌'}\n"
                        f"• Вирусная амплификация: {'✅' if result['config_changes']['viral_amplification_enabled'] else '❌'}",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text(f"❌ Ошибка смены стратегии: {result['error']}")

        elif data == "smm_optimize":
            # Запускаем оптимизацию
            await query.edit_message_text("🔄 Анализирую и оптимизирую систему...")

            optimization_result = await smm_integration.optimize_smm_strategy()

            if 'error' in optimization_result:
                await query.edit_message_text(f"❌ Ошибка оптимизации: {optimization_result['error']}")
            else:
                applied = len(optimization_result.get(
                    'applied_automatically', []))
                manual = len(optimization_result.get(
                    'requires_manual_review', []))

                result_text = f"""🔄 **ОПТИМИЗАЦИЯ ЗАВЕРШЕНА**

✅ Применено автоматически: {applied}
⚠️ Требует ручной проверки: {manual}

💡 Система проанализирована и оптимизирована!"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📋 Подробности", callback_data="smm_optimization_details"),
                        InlineKeyboardButton(
                            "◀️◀️ Назад", callback_data="smm_status")
                    ]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    result_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

        else:
            await query.edit_message_text("⚠️ Функция пока не реализована")

    except Exception as e:
        logger.error(f"Error in smm_callback_handler: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


# Регистрация обработчиков
def register_smm_admin_handlers(application):
    """Регистрация админских обработчиков SMM"""

    application.add_handler(CommandHandler("smm_status", smm_status_command))
    application.add_handler(CommandHandler(
        "smm_analytics", smm_analytics_command))
    application.add_handler(CommandHandler(
        "smm_create_post", smm_create_post_command))
    application.add_handler(CommandHandler(
        "smm_settings", smm_settings_command))

    # Callback обработчик для всех SMM команд
    application.add_handler(CallbackQueryHandler(
        smm_callback_handler, pattern="^smm_|^strategy_"))
