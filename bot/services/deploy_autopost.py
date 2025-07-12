"""
🚀 АВТОПОСТ ПОСЛЕ ДЕПЛОЯ
Автоматически создает пост через 5 минут после каждого деплоя
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class DeployAutopost:
    """Система автопостинга после деплоя"""
    
    def __init__(self, smm_integration=None):
        self.smm_integration = smm_integration
        self.deploy_task: Optional[asyncio.Task] = None
        
    async def schedule_deploy_post(self, deploy_info: dict = None):
        """Запланировать автопост через 5 минут после деплоя"""
        
        if self.deploy_task and not self.deploy_task.done():
            self.deploy_task.cancel()
            
        self.deploy_task = asyncio.create_task(
            self._create_deploy_post_delayed(deploy_info)
        )
        
        logger.info("🚀 Запланирован автопост через 5 минут после деплоя")
        
    async def _create_deploy_post_delayed(self, deploy_info: dict = None):
        """Создать пост через 5 минут"""
        
        try:
            # Ждем 5 минут
            await asyncio.sleep(300)  # 5 минут = 300 секунд
            
            if not self.smm_integration:
                logger.warning("SMM интеграция не настроена")
                return
                
            # Создаем специальный пост о новых возможностях
            post_content = await self._generate_deploy_post(deploy_info)
            
            # Публикуем пост
            result = await self.smm_integration.create_immediate_post(
                content=post_content,
                content_type="deploy_announcement",
                priority=10  # Высокий приоритет
            )
            
            logger.info(f"✅ Автопост после деплоя создан: {result.get('post_id')}")
            
        except asyncio.CancelledError:
            logger.info("Автопост после деплоя отменен")
        except Exception as e:
            logger.error(f"Ошибка создания автопоста после деплоя: {e}")
            
    async def _generate_deploy_post(self, deploy_info: dict = None) -> str:
        """Генерация контента поста о деплое"""
        
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Базовый пост о новых возможностях
        deploy_post = f"""🚀 **СИСТЕМА ОБНОВЛЕНА!**

⚡ **Время обновления:** {current_time}

✨ **Новые возможности:**
• Улучшенная стабильность работы
• Оптимизация производительности  
• Обновленные алгоритмы генерации контента
• Исправлены мелкие ошибки

🎯 **Результат для пользователей:**
• Быстрее отвечаем на запросы
• Качественнее генерируем контент
• Стабильнее работает автопостинг
• Лучше аналитика и отчеты

💼 **Для бизнеса:**
• Повышенная конверсия
• Более точная аналитика
• Автоматизированные процессы
• Профессиональный подход

🔧 **Что дальше:**
Продолжаем развивать систему и добавлять новые возможности!

📱 **Консультация:** /start
⚖️ **Профессиональная помощь 24/7**"""

        # Если есть информация о деплое, добавляем ее
        if deploy_info:
            if deploy_info.get('version'):
                deploy_post += f"\n\n🔄 **Версия:** {deploy_info['version']}"
            if deploy_info.get('features'):
                features_text = "\n".join(f"• {feature}" for feature in deploy_info['features'])
                deploy_post += f"\n\n🆕 **Новые функции:**\n{features_text}"
                
        return deploy_post
        
    async def cancel_deploy_post(self):
        """Отменить запланированный автопост"""
        
        if self.deploy_task and not self.deploy_task.done():
            self.deploy_task.cancel()
            logger.info("Автопост после деплоя отменен")


# Глобальный экземпляр
_deploy_autopost = None


def get_deploy_autopost() -> DeployAutopost:
    """Получить экземпляр DeployAutopost"""
    global _deploy_autopost
    
    if _deploy_autopost is None:
        _deploy_autopost = DeployAutopost()
        
    return _deploy_autopost


async def init_deploy_autopost(smm_integration):
    """Инициализация автопостинга после деплоя"""
    
    deploy_autopost = get_deploy_autopost()
    deploy_autopost.smm_integration = smm_integration
    
    # Запускаем автопост после инициализации (считаем это деплоем)
    await deploy_autopost.schedule_deploy_post({
        "type": "system_init",
        "version": "latest",
        "features": [
            "Полная админка автопостинга",
            "Настройка интервалов из Telegram",
            "Автопост после каждого деплоя",
            "Расширенная аналитика SMM"
        ]
    })
    
    logger.info("🚀 Система автопостинга после деплоя инициализирована")


async def trigger_deploy_autopost(deploy_info: dict = None):
    """Триггер автопоста после деплоя"""
    
    deploy_autopost = get_deploy_autopost()
    await deploy_autopost.schedule_deploy_post(deploy_info)