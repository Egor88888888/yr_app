"""
🚀 АВТОПОСТ ПОСЛЕ ДЕПЛОЯ
Автоматически создает пост через 5 минут после каждого деплоя
"""

import asyncio
import logging
from datetime import datetime, timedelta
import traceback

logger = logging.getLogger(__name__)


class DeployAutopost:
    """Система автопостинга после деплоя"""

    def __init__(self, smm_integration):
        self.smm_integration = smm_integration
        logger.info("🔧 Инициализируем deploy autopost систему...")

    async def schedule_deploy_autopost(self):
        """Планирует создание deploy autopost через 5 минут после деплоя"""
        try:
            logger.info("✅ SMM интеграция подключена к deploy autopost")
            logger.info("🚀 Планируем deploy autopost...")

            # Создаем задачу на выполнение через 5 минут
            logger.info("🔧 Создаем новую задачу deploy autopost...")
            asyncio.create_task(self._create_deploy_autopost_after_delay())
            logger.info("✅ Deploy autopost запланирован на 5 минут!")

        except Exception as e:
            logger.error(f"❌ Ошибка планирования deploy autopost: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _create_deploy_autopost_after_delay(self):
        """Создает deploy autopost через 5 минут"""
        try:
            # Ждем 5 минут перед созданием поста
            logger.info(
                "🔧 Начинаем ожидание 5 минут перед созданием deploy autopost...")
            await asyncio.sleep(300)  # 5 минут = 300 секунд

            logger.info(
                "⏰ 5 минут прошло, начинаем создание deploy autopost...")

            # Проверяем доступность SMM интеграции
            if not self.smm_integration:
                logger.error("❌ SMM интеграция недоступна!")
                return

            logger.info("✅ SMM интеграция найдена, генерируем контент...")

            # Генерируем и публикуем deploy autopost
            result = await self.smm_integration.create_deploy_autopost()

            if result and result.get('success'):
                logger.info(f"✅ Deploy autopost создан успешно: {result}")
            else:
                logger.error(f"❌ Ошибка создания deploy autopost: {result}")

        except Exception as e:
            logger.error(
                f"❌ Критическая ошибка в _create_deploy_autopost_after_delay: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
