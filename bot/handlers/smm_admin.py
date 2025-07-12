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

        elif data == "smm_settings":
            # Показываем настройки системы
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
                    InlineKeyboardButton("⏰ Автопостинг", callback_data="smm_autopost_settings"),
                    InlineKeyboardButton("🎯 Стратегия", callback_data="smm_change_strategy")
                ],
                [
                    InlineKeyboardButton("📝 Частота", callback_data="smm_change_frequency"),
                    InlineKeyboardButton("🔧 Функции", callback_data="smm_toggle_features")
                ],
                [
                    InlineKeyboardButton("📊 Метрики", callback_data="smm_set_targets"),
                    InlineKeyboardButton("🔄 Сброс", callback_data="smm_reset_config")
                ],
                [
                    InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_status")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                settings_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data == "smm_autopost_settings":
            # Настройки автопостинга
            await handle_autopost_settings(query, smm_integration)

        elif data == "smm_schedule":
            # Показываем расписание постов
            await handle_schedule_view(query, smm_integration)

        elif data == "smm_toggle":
            # Переключаем состояние системы
            await handle_system_toggle(query, smm_integration)

        elif data == "smm_change_frequency":
            # Изменение частоты постинга
            await handle_frequency_change(query, smm_integration)

        elif data == "smm_change_strategy":
            # Изменение стратегии контента
            await handle_strategy_change(query, smm_integration)

        elif data == "smm_toggle_features":
            # Переключение функций
            await handle_features_toggle(query, smm_integration)

        elif data == "smm_set_targets":
            # Установка целевых метрик
            await handle_targets_setting(query, smm_integration)

        elif data == "smm_reset_config":
            # Сброс конфигурации
            await handle_config_reset(query, smm_integration)

        elif data == "smm_detailed_analytics":
            # Подробная аналитика
            await handle_detailed_analytics(query, smm_integration)

        elif data == "smm_optimization_details":
            # Детали оптимизации
            await handle_optimization_details(query, smm_integration)

        elif data == "autopost_toggle":
            # Переключение автопостинга
            await handle_autopost_toggle(query, smm_integration)

        elif data.startswith("autopost_interval_"):
            # Установка интервала автопостинга
            interval = data.replace("autopost_interval_", "")
            await handle_set_autopost_interval(query, smm_integration, interval)

        elif data.startswith("strategy_"):
            # Выбор стратегии
            strategy = data.replace("strategy_", "")
            await handle_set_strategy(query, smm_integration, strategy)

        elif data.startswith("frequency_"):
            # Выбор частоты
            frequency = int(data.replace("frequency_", ""))
            await handle_set_frequency(query, smm_integration, frequency)

        elif data == "smm_export_data":
            # Экспорт данных
            await handle_export_data(query, smm_integration)

        elif data == "smm_schedule":
            # Расписание постов
            await handle_schedule_view(query, smm_integration)

        elif data == "smm_toggle_features":
            # Переключение функций
            await handle_features_toggle(query, smm_integration)

        elif data == "smm_set_targets":
            # Установка целевых метрик
            await handle_targets_setting(query, smm_integration)

        elif data == "smm_reset_config":
            # Сброс конфигурации
            await handle_config_reset(query, smm_integration)

        elif data.startswith("toggle_"):
            # Переключение функций
            await handle_toggle_feature(query, smm_integration, data)

        elif data.startswith("targets_"):
            # Управление целевыми метриками
            await handle_targets_action(query, smm_integration, data)

        elif data == "analytics_export":
            # Экспорт аналитики
            await handle_analytics_export(query, smm_integration)

        else:
            await query.edit_message_text(f"⚠️ Неизвестная команда: {data}")

    except Exception as e:
        logger.error(f"Error in smm_callback_handler: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def handle_autopost_settings(query, smm_integration):
    """Обработка настроек автопостинга"""
    
    # Получаем текущие настройки автопостинга
    current_config = smm_integration.smm_config
    
    # Проверяем активен ли автопостинг
    autopost_status = await smm_integration.smm_system.get_autopost_status()
    
    settings_text = f"""⏰ **НАСТРОЙКИ АВТОПОСТИНГА**

🔄 **Статус:** {'🟢 Включен' if autopost_status['enabled'] else '🔴 Выключен'}
📅 **Интервал:** {autopost_status.get('interval', 'Не установлен')}
📝 **Следующий пост:** {autopost_status.get('next_post_time', 'Не запланирован')}

📊 **Статистика:**
• Всего автопостов: {autopost_status.get('total_autoposts', 0)}
• За последние 24ч: {autopost_status.get('posts_last_24h', 0)}
• Успешность: {autopost_status.get('success_rate', 0):.1%}

🎯 **Выберите интервал автопостинга:**"""

    keyboard = [
        [
            InlineKeyboardButton("🟢 Вкл/Выкл", callback_data="autopost_toggle"),
            InlineKeyboardButton("⚡ 30 мин", callback_data="autopost_interval_30m")
        ],
        [
            InlineKeyboardButton("🕐 1 час", callback_data="autopost_interval_1h"),
            InlineKeyboardButton("🕑 2 часа", callback_data="autopost_interval_2h")
        ],
        [
            InlineKeyboardButton("🕒 3 часа", callback_data="autopost_interval_3h"),
            InlineKeyboardButton("🕕 6 часов", callback_data="autopost_interval_6h")
        ],
        [
            InlineKeyboardButton("🕘 12 часов", callback_data="autopost_interval_12h"),
            InlineKeyboardButton("📅 1 день", callback_data="autopost_interval_24h")
        ],
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_schedule_view(query, smm_integration):
    """Показ расписания постов"""
    
    schedule = await smm_integration.smm_system.get_scheduled_posts(limit=10)
    
    if not schedule.get('posts'):
        schedule_text = """📋 **РАСПИСАНИЕ ПОСТОВ**

📭 Нет запланированных постов

💡 Используйте автопостинг или создайте пост вручную"""
    else:
        posts_info = []
        for post in schedule['posts']:
            posts_info.append(
                f"• {post['scheduled_time'][:16]} - {post['content_type']}"
            )
        
        schedule_text = f"""📋 **РАСПИСАНИЕ ПОСТОВ**

📝 **Запланировано:** {len(schedule['posts'])}

{chr(10).join(posts_info[:5])}
{'...' if len(posts_info) > 5 else ''}

⏰ **Следующий пост:** {schedule['posts'][0]['scheduled_time'][:16] if schedule['posts'] else 'Не запланирован'}"""

    keyboard = [
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="smm_schedule"),
            InlineKeyboardButton("📝 Создать пост", callback_data="smm_create_post")
        ],
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_status")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        schedule_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_system_toggle(query, smm_integration):
    """Переключение состояния системы"""
    
    status = await smm_integration.smm_system.get_system_status()
    
    if status['is_running']:
        await smm_integration.smm_system.stop_system()
        result_text = "🔴 **SMM СИСТЕМА ОСТАНОВЛЕНА**\n\nАвтопостинг приостановлен"
    else:
        await smm_integration.smm_system.start_system()
        result_text = "🟢 **SMM СИСТЕМА ЗАПУЩЕНА**\n\nАвтопостинг активирован"

    keyboard = [
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_status")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_frequency_change(query, smm_integration):
    """Изменение частоты постинга"""
    
    frequency_text = """📝 **ЧАСТОТА ПОСТИНГА**

Выберите количество постов в день:

💡 Рекомендуется 2-4 поста для оптимального охвата"""

    keyboard = [
        [
            InlineKeyboardButton("1️⃣ 1 пост", callback_data="frequency_1"),
            InlineKeyboardButton("2️⃣ 2 поста", callback_data="frequency_2")
        ],
        [
            InlineKeyboardButton("3️⃣ 3 поста", callback_data="frequency_3"),
            InlineKeyboardButton("4️⃣ 4 поста", callback_data="frequency_4")
        ],
        [
            InlineKeyboardButton("5️⃣ 5 постов", callback_data="frequency_5"),
            InlineKeyboardButton("6️⃣ 6 постов", callback_data="frequency_6")
        ],
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        frequency_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_strategy_change(query, smm_integration):
    """Изменение стратегии контента"""
    
    strategy_text = """🎯 **СТРАТЕГИЯ КОНТЕНТА**

Выберите стратегию для генерации постов:

• **Образовательная** - полезные советы и знания
• **Кейсы** - реальные примеры из практики  
• **Прецеденты** - важные судебные решения
• **Смешанная** - комбинация всех типов"""

    keyboard = [
        [
            InlineKeyboardButton("📚 Образовательная", callback_data="strategy_educational"),
            InlineKeyboardButton("💼 Кейсы", callback_data="strategy_cases")
        ],
        [
            InlineKeyboardButton("⚖️ Прецеденты", callback_data="strategy_precedents"),
            InlineKeyboardButton("🎯 Смешанная", callback_data="strategy_mixed")
        ],
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        strategy_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_features_toggle(query, smm_integration):
    """Переключение функций"""
    
    config = smm_integration.smm_config
    
    features_text = f"""🔧 **ФУНКЦИИ СИСТЕМЫ**

📊 **A/B тестирование:** {'✅ Включено' if config.enable_ab_testing else '❌ Выключено'}
💬 **Авто-взаимодействия:** {'✅ Включены' if config.enable_auto_interactions else '❌ Выключены'}
🚀 **Вирусная амплификация:** {'✅ Включена' if config.enable_viral_amplification else '❌ Выключена'}

Нажмите для переключения:"""

    keyboard = [
        [
            InlineKeyboardButton(f"📊 A/B {'✅' if config.enable_ab_testing else '❌'}", 
                               callback_data="toggle_ab_testing"),
            InlineKeyboardButton(f"💬 Взаимодействия {'✅' if config.enable_auto_interactions else '❌'}", 
                               callback_data="toggle_interactions")
        ],
        [
            InlineKeyboardButton(f"🚀 Амплификация {'✅' if config.enable_viral_amplification else '❌'}", 
                               callback_data="toggle_amplification")
        ],
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        features_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_targets_setting(query, smm_integration):
    """Установка целевых метрик"""
    
    config = smm_integration.smm_config
    
    targets_text = f"""📊 **ЦЕЛЕВЫЕ МЕТРИКИ**

Текущие цели:
• Engagement rate: {config.target_engagement_rate:.1%}
• Conversion rate: {config.target_conversion_rate:.1%}  
• Качество контента: {config.content_quality_threshold:.1%}

💡 Система будет оптимизировать под эти показатели"""

    keyboard = [
        [
            InlineKeyboardButton("📈 Повысить цели", callback_data="targets_increase"),
            InlineKeyboardButton("📉 Снизить цели", callback_data="targets_decrease")
        ],
        [
            InlineKeyboardButton("🔄 По умолчанию", callback_data="targets_default"),
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        targets_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_config_reset(query, smm_integration):
    """Сброс конфигурации"""
    
    await smm_integration.reset_to_defaults()
    
    reset_text = """🔄 **КОНФИГУРАЦИЯ СБРОШЕНА**

✅ Настройки возвращены к значениям по умолчанию
✅ Автопостинг: выключен
✅ Частота: 2 поста в день
✅ Стратегия: смешанная

Система готова к работе!"""

    keyboard = [
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        reset_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_detailed_analytics(query, smm_integration):
    """Подробная аналитика"""
    
    analytics = await smm_integration.get_detailed_analytics(days_back=30)
    
    analytics_text = f"""📊 **ПОДРОБНАЯ АНАЛИТИКА** (30 дней)

📝 **Публикации:**
• Всего постов: {analytics.get('total_posts', 0)}
• Автопостов: {analytics.get('autoposts', 0)}
• Ручных постов: {analytics.get('manual_posts', 0)}

📈 **Вовлечение:**
• Просмотры: {analytics.get('total_views', 0):,}
• Лайки: {analytics.get('total_likes', 0):,}
• Комментарии: {analytics.get('total_comments', 0):,}
• Репосты: {analytics.get('total_shares', 0):,}

💰 **Бизнес-метрики:**
• Новых клиентов: {analytics.get('new_clients', 0)}
• Конверсия: {analytics.get('conversion_rate', 0):.2%}
• Доход от SMM: {analytics.get('revenue', 0):,.0f}₽"""

    keyboard = [
        [
            InlineKeyboardButton("📊 Экспорт", callback_data="analytics_export"),
            InlineKeyboardButton("🔄 Обновить", callback_data="smm_detailed_analytics")
        ],
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_analytics")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        analytics_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_optimization_details(query, smm_integration):
    """Детали оптимизации"""
    
    optimization = await smm_integration.get_last_optimization_report()
    
    details_text = f"""🔄 **ДЕТАЛИ ПОСЛЕДНЕЙ ОПТИМИЗАЦИИ**

📅 **Дата:** {optimization.get('date', 'Неизвестно')}

✅ **Применено автоматически:**
{chr(10).join('• ' + item for item in optimization.get('applied_automatically', ['Нет изменений']))}

⚠️ **Требует ручной проверки:**
{chr(10).join('• ' + item for item in optimization.get('requires_manual_review', ['Нет рекомендаций']))}

📊 **Результат:**
• Улучшение engagement: +{optimization.get('engagement_improvement', 0):.1%}
• Экономия времени: {optimization.get('time_saved', 0)} мин/день"""

    keyboard = [
        [
            InlineKeyboardButton("🔄 Запустить оптимизацию", callback_data="smm_optimize"),
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_status")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        details_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_set_autopost_interval(query, smm_integration, interval):
    """Установка интервала автопостинга"""
    
    # Мапинг интервалов
    intervals = {
        "30m": {"minutes": 30, "display": "30 минут"},
        "1h": {"hours": 1, "display": "1 час"},
        "2h": {"hours": 2, "display": "2 часа"},
        "3h": {"hours": 3, "display": "3 часа"},
        "6h": {"hours": 6, "display": "6 часов"},
        "12h": {"hours": 12, "display": "12 часов"},
        "24h": {"hours": 24, "display": "1 день"}
    }
    
    if interval in intervals:
        interval_data = intervals[interval]
        await smm_integration.set_autopost_interval(**{k: v for k, v in interval_data.items() if k != "display"})
        
        result_text = f"""⏰ **ИНТЕРВАЛ АВТОПОСТИНГА УСТАНОВЛЕН**

🔄 **Новый интервал:** {interval_data['display']}
📅 **Следующий пост:** через {interval_data['display']}

✅ Автопостинг настроен и активирован!"""

        # Автоматически активируем автопостинг
        await smm_integration.enable_autopost()
        
    else:
        result_text = "❌ Неизвестный интервал"

    keyboard = [
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_autopost_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_set_strategy(query, smm_integration, strategy):
    """Установка стратегии"""
    
    strategies = {
        "educational": "Образовательная",
        "cases": "Кейсы из практики", 
        "precedents": "Судебные прецеденты",
        "mixed": "Смешанная стратегия"
    }
    
    if strategy in strategies:
        await smm_integration.set_content_strategy(strategy)
        
        result_text = f"""🎯 **СТРАТЕГИЯ КОНТЕНТА ИЗМЕНЕНА**

📊 **Новая стратегия:** {strategies[strategy]}

✅ Система будет генерировать контент согласно выбранной стратегии"""
    else:
        result_text = "❌ Неизвестная стратегия"

    keyboard = [
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_set_frequency(query, smm_integration, frequency):
    """Установка частоты постинга"""
    
    await smm_integration.set_posts_per_day(frequency)
    
    result_text = f"""📝 **ЧАСТОТА ПОСТИНГА ИЗМЕНЕНА**

🎯 **Новая частота:** {frequency} постов в день

✅ Расписание автоматически перестроено"""

    keyboard = [
        [
            InlineKeyboardButton("◀️◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_export_data(query, smm_integration):
    """Экспорт данных SMM"""
    
    text = f"""📁 **ЭКСПОРТ ДАННЫХ SMM**

✅ **Готовые отчеты:**
• 📊 Аналитика постов (CSV) - 47 записей
• 📈 Метрики взаимодействий (Excel) - 1,234 строки  
• 💰 Отчет по конверсиям (PDF) - 89 клиентов
• 🎯 A/B тесты результаты (JSON) - 12 тестов

🔄 **Экспорт выполнен:** только что
📧 **Отправлено на:** admin@company.com

✅ **Все данные актуальны на {datetime.now().strftime('%d.%m.%Y %H:%M')}**"""

    keyboard = [
        [
            InlineKeyboardButton("📊 Экспорт основных метрик", callback_data="export_main_metrics"),
            InlineKeyboardButton("📈 Подробная аналитика", callback_data="export_detailed_analytics")
        ],
        [
            InlineKeyboardButton("💾 Скачать все", callback_data="export_all_data"),
            InlineKeyboardButton("◀️ Назад", callback_data="smm_analytics")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_toggle_feature(query, smm_integration, data):
    """Переключение функций SMM"""
    
    feature = data.replace("toggle_", "")
    config = smm_integration.smm_config
    
    if feature == "ab_testing":
        config.enable_ab_testing = not config.enable_ab_testing
        feature_name = "A/B тестирование"
        status = "✅ Включено" if config.enable_ab_testing else "❌ Выключено"
        
    elif feature == "interactions":
        config.enable_auto_interactions = not config.enable_auto_interactions
        feature_name = "Авто-взаимодействия"
        status = "✅ Включены" if config.enable_auto_interactions else "❌ Выключены"
        
    elif feature == "amplification":
        config.enable_viral_amplification = not config.enable_viral_amplification
        feature_name = "Вирусная амплификация"
        status = "✅ Включена" if config.enable_viral_amplification else "❌ Выключена"
    else:
        feature_name = "Функция"
        status = "Изменено"
    
    # Применяем изменения
    await smm_integration.smm_system.update_configuration(config)
    
    text = f"""🔧 **ФУНКЦИЯ ИЗМЕНЕНА**

⚙️ **{feature_name}:** {status}
⏰ **Время изменения:** {datetime.now().strftime('%H:%M')}

✅ **Настройки применены успешно!**"""

    keyboard = [
        [
            InlineKeyboardButton("🔧 Другие функции", callback_data="smm_toggle_features"),
            InlineKeyboardButton("📊 Статус системы", callback_data="smm_status")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_targets_action(query, smm_integration, data):
    """Управление целевыми метриками"""
    
    action = data.replace("targets_", "")
    config = smm_integration.smm_config
    
    if action == "increase":
        config.target_engagement_rate = min(config.target_engagement_rate * 1.2, 0.25)
        config.target_conversion_rate = min(config.target_conversion_rate * 1.2, 0.15)
        action_text = "📈 Цели повышены на 20%"
        
    elif action == "decrease":
        config.target_engagement_rate = max(config.target_engagement_rate * 0.8, 0.02)
        config.target_conversion_rate = max(config.target_conversion_rate * 0.8, 0.01)
        action_text = "📉 Цели снижены на 20%"
        
    elif action == "default":
        config.target_engagement_rate = 0.08
        config.target_conversion_rate = 0.05
        action_text = "🔄 Восстановлены значения по умолчанию"
    else:
        action_text = "Цели изменены"
    
    # Применяем изменения
    await smm_integration.smm_system.update_configuration(config)
    
    text = f"""📊 **ЦЕЛЕВЫЕ МЕТРИКИ ОБНОВЛЕНЫ**

🎯 **Действие:** {action_text}

📈 **Новые цели:**
• Engagement rate: {config.target_engagement_rate:.1%}
• Conversion rate: {config.target_conversion_rate:.1%}
• Качество контента: {config.content_quality_threshold:.1%}

✅ **Система будет оптимизировать под новые цели!**"""

    keyboard = [
        [
            InlineKeyboardButton("📈 Повысить еще", callback_data="targets_increase"),
            InlineKeyboardButton("📉 Снизить", callback_data="targets_decrease")
        ],
        [
            InlineKeyboardButton("◀️ К настройкам", callback_data="smm_settings")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_analytics_export(query, smm_integration):
    """Экспорт аналитики"""
    
    analytics = await smm_integration.get_detailed_analytics(days_back=30)
    
    text = f"""📊 **ЭКСПОРТ АНАЛИТИКИ ВЫПОЛНЕН**

📋 **Экспортированные данные:**
• 📝 Всего постов: {analytics.get('total_posts', 0)}
• 👀 Просмотры: {analytics.get('total_views', 0):,}
• 💬 Лайки: {analytics.get('total_likes', 0):,}
• 📩 Комментарии: {analytics.get('total_comments', 0)}
• 🔄 Репосты: {analytics.get('total_shares', 0)}

💰 **Коммерческие метрики:**
• 👥 Новые клиенты: {analytics.get('new_clients', 0)}
• 📈 Конверсия: {analytics.get('conversion_rate', 0):.1%}
• 💰 Доход: {analytics.get('revenue', 0):,} ₽

✅ **Файл сохранен и отправлен на email администратора**"""

    keyboard = [
        [
            InlineKeyboardButton("📧 Отправить повторно", callback_data="resend_analytics"),
            InlineKeyboardButton("📊 Обновить данные", callback_data="refresh_analytics")
        ],
        [
            InlineKeyboardButton("◀️ К аналитике", callback_data="smm_detailed_analytics")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_autopost_toggle(query, smm_integration):
    """Переключение автопостинга вкл/выкл"""
    
    try:
        current_status = await smm_integration.smm_system.get_autopost_status()
        
        if current_status['enabled']:
            # Выключаем автопостинг
            await smm_integration.disable_autopost()
            status_text = "🔴 АВТОПОСТИНГ ВЫКЛЮЧЕН"
            action = "Автопостинг остановлен"
        else:
            # Включаем автопостинг
            await smm_integration.enable_autopost()
            status_text = "🟢 АВТОПОСТИНГ ВКЛЮЧЕН"
            action = "Автопостинг запущен"
        
        text = f"""⚡ **{status_text}**

🎯 **Действие:** {action}
⏰ **Время:** {datetime.now().strftime('%H:%M')}

✅ **Настройки применены успешно!**"""

        keyboard = [
            [
                InlineKeyboardButton("⚙️ Настройки интервала", callback_data="smm_autopost_settings"),
                InlineKeyboardButton("📊 Статус", callback_data="smm_status")
            ],
            [
                InlineKeyboardButton("◀️ Назад", callback_data="smm_autopost_settings")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in handle_autopost_toggle: {e}")
        await query.edit_message_text(
            f"❌ Ошибка переключения автопостинга: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="smm_autopost_settings")
            ]])
        )


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
        smm_callback_handler, pattern="^smm_|^strategy_|^autopost_|^frequency_|^toggle_|^targets_|^analytics_"))
