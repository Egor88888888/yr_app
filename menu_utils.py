# -*- coding: utf-8 -*-
"""
🎛️ PROFESSIONAL MENU UTILITIES
Navigation helpers for comprehensive menu system
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class MenuBuilder:
    """Professional menu builder with breadcrumb navigation"""
    
    @staticmethod
    def create_main_admin_menu(stats_data=None):
        """Create main admin menu with professional design"""
        keyboard = [
            [
                InlineKeyboardButton("📋 Заявки", callback_data="admin_apps"),
                InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
            ],
            [
                InlineKeyboardButton("💳 Платежи", callback_data="admin_payments"),
                InlineKeyboardButton("👥 Клиенты", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("🤖 AI Статус", callback_data="admin_ai_status"),
                InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton("🚀 SMM Система", callback_data="smm_main_panel"),
                InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton("👨‍💼 Управление админами", callback_data="admin_manage_admins"),
                InlineKeyboardButton("📈 Детальная аналитика", callback_data="admin_detailed_analytics")
            ],
            [
                InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh"),
                InlineKeyboardButton("📤 Экспорт данных", callback_data="admin_export")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_client_service_menu():
        """Create client service menu"""
        keyboard = [
            [
                InlineKeyboardButton("📝 Подать заявку", web_app={"url": "YOUR_WEBAPP_URL"}),
                InlineKeyboardButton("📞 Заказать звонок", callback_data="request_call")
            ],
            [
                InlineKeyboardButton("💬 Консультация", callback_data="chat_consultation"),
                InlineKeyboardButton("💳 Узнать стоимость", callback_data="get_price")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_navigation_buttons(back_callback="back_admin", extra_buttons=None):
        """Create standard navigation buttons"""
        buttons = []
        
        if extra_buttons:
            for button_row in extra_buttons:
                buttons.append(button_row)
        
        # Always add back button
        buttons.append([
            InlineKeyboardButton("◀️ Назад в меню", callback_data=back_callback)
        ])
        
        return buttons
    
    @staticmethod
    def create_application_actions_menu(app_id, status):
        """Create application-specific actions menu based on status"""
        if status == "new":
            keyboard = [
                [
                    InlineKeyboardButton("✅ Взять в работу", callback_data=f"app_take_{app_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app_id}")
                ],
                [
                    InlineKeyboardButton("💰 Выставить счет", callback_data=f"app_bill_{app_id}")
                ]
            ]
        elif status == "processing":
            keyboard = [
                [
                    InlineKeyboardButton("✅ Завершить", callback_data=f"app_complete_{app_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app_id}")
                ],
                [
                    InlineKeyboardButton("💰 Выставить счет", callback_data=f"app_bill_{app_id}")
                ]
            ]
        elif status == "completed":
            keyboard = [
                [
                    InlineKeyboardButton("💳 Повторный счет", callback_data=f"app_bill_{app_id}")
                ]
            ]
        else:  # rejected
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Восстановить", callback_data=f"app_take_{app_id}")
                ]
            ]
        
        # Add navigation
        keyboard.extend(MenuBuilder.create_navigation_buttons(
            back_callback="admin_apps",
            extra_buttons=[[
                InlineKeyboardButton("📋 К списку заявок", callback_data="admin_apps")
            ]]
        ))
        
        return InlineKeyboardMarkup(keyboard)


def format_menu_title(title, icon="🎛️"):
    """Format menu title with professional styling"""
    return f"{icon} **{title.upper()}**\n"


def format_stats_section(stats_dict, section_title="📊 СТАТИСТИКА"):
    """Format statistics section"""
    text = f"\n{section_title}:\n"
    for key, value in stats_dict.items():
        text += f"• {key}: {value}\n"
    return text


def create_breadcrumb(path_items):
    """Create breadcrumb navigation text"""
    return " > ".join([f"**{item}**" for item in path_items])