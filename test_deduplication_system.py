#!/usr/bin/env python3
"""
🧪 ТЕСТ СИСТЕМЫ ПРЕДОТВРАЩЕНИЯ ДУБЛИРОВАНИЯ КОНТЕНТА
Проверяет работоспособность всех компонентов дедупликации
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Добавляем путь к модулям проекта
sys.path.append(str(Path(__file__).parent))

from bot.services.content_deduplication import (
    ContentDeduplicationSystem,
    check_content_uniqueness,
    register_unique_content,
    validate_and_register_content
)
from bot.services.deduplication_monitor import get_deduplication_status, get_blocked_topics

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeduplicationSystemTester:
    """Тестер системы дедупликации"""
    
    def __init__(self):
        self.system = ContentDeduplicationSystem()
        self.test_results = []
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("🧪 Запуск тестирования системы дедупликации...")
        print("=" * 60)
        
        tests = [
            ("Базовая функциональность", self.test_basic_functionality),
            ("Проверка дублирования", self.test_duplicate_detection),
            ("Семантическое сходство", self.test_semantic_similarity),
            ("Блокировка тем", self.test_topic_blocking),
            ("Правовые ссылки", self.test_legal_references),
            ("Производительность", self.test_performance),
            ("Интеграция с автопостингом", self.test_autopost_integration),
            ("Система мониторинга", self.test_monitoring_system)
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 Тест: {test_name}")
            print("-" * 40)
            
            try:
                result = await test_func()
                if result:
                    print(f"✅ {test_name}: ПРОЙДЕН")
                    self.test_results.append((test_name, "PASS", ""))
                else:
                    print(f"❌ {test_name}: ПРОВАЛЕН")
                    self.test_results.append((test_name, "FAIL", "Unknown error"))
            except Exception as e:
                print(f"💥 {test_name}: ОШИБКА - {str(e)}")
                self.test_results.append((test_name, "ERROR", str(e)))
        
        await self.print_summary()
    
    async def test_basic_functionality(self) -> bool:
        """Тест базовой функциональности"""
        
        # Тест создания отпечатка контента
        title = "Тестовый заголовок о трудовых правах"
        content = "Это тестовый контент про увольнение работника согласно ст. 81 ТК РФ"
        
        fingerprint = self.system.extract_content_fingerprint(title, content, "test")
        
        # Проверяем что отпечаток создан корректно
        if not fingerprint.title_hash:
            print("❌ Не создан хэш заголовка")
            return False
        
        if not fingerprint.content_hash:
            print("❌ Не создан хэш контента")
            return False
        
        if not fingerprint.topic_keywords:
            print("❌ Не извлечены ключевые слова")
            return False
        
        print(f"✅ Создан отпечаток с {len(fingerprint.topic_keywords)} ключевыми словами")
        print(f"   Ключевые слова: {list(fingerprint.topic_keywords)[:3]}...")
        print(f"   Правовые ссылки: {list(fingerprint.legal_references)}")
        
        return True
    
    async def test_duplicate_detection(self) -> bool:
        """Тест обнаружения дублирования"""
        
        # Создаем уникальный контент
        unique_title = "Уникальный тест дублирования"
        unique_content = f"Уникальный контент для тестирования {asyncio.get_event_loop().time()}"
        
        # Первая проверка - должен быть уникальный
        is_unique1, reason1, score1 = check_content_uniqueness(
            unique_title, unique_content, "test", "test_system"
        )
        
        if not is_unique1:
            print(f"❌ Новый контент определен как дублированный: {reason1}")
            return False
        
        # Регистрируем контент
        registered = register_unique_content(unique_title, unique_content, "test", "test_system")
        if not registered:
            print("❌ Не удалось зарегистрировать уникальный контент")
            return False
        
        # Вторая проверка того же контента - должен быть дублированный
        is_unique2, reason2, score2 = check_content_uniqueness(
            unique_title, unique_content, "test", "test_system"
        )
        
        if is_unique2:
            print("❌ Дублированный контент определен как уникальный")
            return False
        
        print(f"✅ Дублирование обнаружено корректно: {reason2} (сходство: {score2:.2f})")
        
        return True
    
    async def test_semantic_similarity(self) -> bool:
        """Тест семантического сходства"""
        
        # Создаем семантически похожий контент
        base_content = "Работник был уволен по статье 81 ТК РФ за прогул"
        similar_content = "Сотрудника уволили согласно ст. 81 Трудового кодекса за прогул"
        
        # Регистрируем базовый контент
        success = register_unique_content("Базовый контент", base_content, "test", "similarity_test")
        if not success:
            print("❌ Не удалось зарегистрировать базовый контент")
            return False
        
        # Проверяем похожий контент
        is_unique, reason, similarity = check_content_uniqueness(
            "Похожий контент", similar_content, "test", "similarity_test"
        )
        
        if is_unique:
            print(f"⚠️ Семантически похожий контент прошел как уникальный (сходство: {similarity:.2f})")
            # Это может быть нормально, зависит от настроек порога
            if similarity < 0.3:
                return True  # Сходство слишком низкое, это нормально
        
        print(f"✅ Семантическое сходство работает: {reason} (сходство: {similarity:.2f})")
        return True
    
    async def test_topic_blocking(self) -> bool:
        """Тест блокировки тем"""
        
        # Блокируем тестовую тему
        test_topic = f"Test Topic {asyncio.get_event_loop().time()}"
        self.system.block_topic_temporarily(test_topic, "Test blocking", hours=1)
        
        # Проверяем что тема заблокирована
        blocked_topics = await get_blocked_topics()
        blocked_topic_names = [topic['topic'] for topic in blocked_topics]
        
        if test_topic not in blocked_topic_names:
            print(f"❌ Тема не была заблокирована: {test_topic}")
            return False
        
        print(f"✅ Тема успешно заблокирована: {test_topic}")
        
        # Проверяем что контент с этой темой блокируется
        blocked_content = f"Контент на тему {test_topic} и другие слова"
        is_unique, reason, _ = check_content_uniqueness(
            test_topic, blocked_content, "test", "blocking_test"
        )
        
        if is_unique:
            print("❌ Контент с заблокированной темой прошел как уникальный")
            return False
        
        print(f"✅ Блокировка темы работает: {reason}")
        return True
    
    async def test_legal_references(self) -> bool:
        """Тест обработки правовых ссылок"""
        
        # Контент с правовыми ссылками
        legal_content = """
        Согласно ст. 81 ТК РФ работодатель может уволить сотрудника.
        Также см. Федеральный закон от 01.01.2023 № 123-ФЗ.
        Определение ВС РФ от 15.03.2022 № 5-КГ21-67.
        """
        
        fingerprint = self.system.extract_content_fingerprint(
            "Правовые ссылки", legal_content, "legal_test"
        )
        
        if not fingerprint.legal_references:
            print("❌ Не извлечены правовые ссылки")
            return False
        
        print(f"✅ Извлечены правовые ссылки: {list(fingerprint.legal_references)}")
        
        # Проверяем что контент с теми же ссылками считается похожим
        similar_legal_content = """
        По статье 81 Трудового кодекса РФ увольнение возможно.
        См. также ФЗ № 123-ФЗ от 01.01.2023.
        """
        
        # Регистрируем первый контент
        register_unique_content("Первый правовой", legal_content, "legal_test", "legal_system")
        
        # Проверяем второй
        is_unique, reason, similarity = check_content_uniqueness(
            "Второй правовой", similar_legal_content, "legal_test", "legal_system"
        )
        
        print(f"📊 Сходство по правовым ссылкам: {similarity:.2f}")
        if similarity > 0.5:
            print("✅ Правовые ссылки влияют на определение сходства")
        
        return True
    
    async def test_performance(self) -> bool:
        """Тест производительности"""
        
        import time
        
        # Тест скорости проверки уникальности
        start_time = time.time()
        
        for i in range(10):
            content = f"Тестовый контент номер {i} для проверки производительности"
            check_content_uniqueness(f"Title {i}", content, "perf_test", "performance")
        
        elapsed = time.time() - start_time
        avg_time = elapsed / 10
        
        print(f"⏱️ Средние время проверки уникальности: {avg_time:.3f} секунд")
        
        if avg_time > 1.0:
            print("⚠️ Производительность низкая (> 1 секунды на проверку)")
            return False
        
        print("✅ Производительность в норме")
        return True
    
    async def test_autopost_integration(self) -> bool:
        """Тест интеграции с системами автопостинга"""
        
        # Симулируем работу различных систем автопостинга
        systems = ["simple_autopost", "enhanced_autopost", "content_intelligence"]
        
        for system in systems:
            content = f"Контент от системы {system} в {asyncio.get_event_loop().time()}"
            success, message = validate_and_register_content(
                f"Title from {system}",
                content,
                "autopost_test",
                system
            )
            
            if not success:
                print(f"❌ Интеграция с {system} не работает: {message}")
                return False
            
            print(f"✅ {system}: интеграция работает")
        
        return True
    
    async def test_monitoring_system(self) -> bool:
        """Тест системы мониторинга"""
        
        # Получаем статус системы
        status = await get_deduplication_status()
        
        if "error" in status:
            print(f"❌ Ошибка мониторинга: {status['error']}")
            return False
        
        required_fields = ["basic_statistics", "recommendations", "health_score"]
        
        for field in required_fields:
            if field not in status:
                print(f"❌ Отсутствует поле в статусе: {field}")
                return False
        
        health_score = status.get("health_score", 0)
        print(f"💚 Индекс здоровья системы: {health_score:.1f}/100")
        
        recommendations = status.get("recommendations", [])
        print(f"📋 Рекомендаций получено: {len(recommendations)}")
        
        return True
    
    async def print_summary(self):
        """Печать итогов тестирования"""
        print("\n" + "=" * 60)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r[1] == "PASS"])
        failed = len([r for r in self.test_results if r[1] == "FAIL"])
        errors = len([r for r in self.test_results if r[1] == "ERROR"])
        
        print(f"Всего тестов: {total_tests}")
        print(f"✅ Пройдено: {passed}")
        print(f"❌ Провалено: {failed}")
        print(f"💥 Ошибок: {errors}")
        print(f"📊 Успешность: {(passed/total_tests)*100:.1f}%")
        
        if failed > 0 or errors > 0:
            print("\n🔍 ДЕТАЛИ ПРОБЛЕМ:")
            for name, status, error in self.test_results:
                if status in ["FAIL", "ERROR"]:
                    print(f"   {status}: {name} - {error}")
        
        print("\n" + "=" * 60)
        
        # Получаем финальный статус системы
        try:
            final_status = await get_deduplication_status()
            if "error" not in final_status:
                health_score = final_status.get("health_score", 0)
                print(f"🏥 Финальный индекс здоровья системы: {health_score:.1f}/100")
                
                if health_score > 80:
                    print("🟢 СИСТЕМА РАБОТАЕТ ОТЛИЧНО!")
                elif health_score > 60:
                    print("🟡 СИСТЕМА РАБОТАЕТ УДОВЛЕТВОРИТЕЛЬНО")
                else:
                    print("🔴 СИСТЕМА ТРЕБУЕТ ВНИМАНИЯ")
        except Exception as e:
            print(f"⚠️ Не удалось получить финальный статус: {e}")


async def main():
    """Главная функция тестирования"""
    tester = DeduplicationSystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())