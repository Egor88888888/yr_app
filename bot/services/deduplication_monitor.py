"""
🔍 МОНИТОР И УПРАВЛЕНИЕ СИСТЕМОЙ ДЕДУПЛИКАЦИИ
Предоставляет интерфейс для контроля уникальности контента
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .content_deduplication import get_deduplication_system

logger = logging.getLogger(__name__)

class DeduplicationMonitor:
    """Монитор системы дедупликации контента"""
    
    def __init__(self):
        self.dedup_system = get_deduplication_system()
    
    async def get_full_status_report(self) -> Dict[str, Any]:
        """Полный отчет о состоянии системы дедупликации"""
        
        if not self.dedup_system:
            return {"error": "Deduplication system not available"}
        
        try:
            # Основная статистика
            stats = self.dedup_system.get_content_statistics()
            
            # Анализируем эффективность по системам
            effectiveness_by_system = self._analyze_system_effectiveness(stats['by_system'])
            
            # Проверяем проблемные темы
            problem_topics = self._identify_problem_topics()
            
            # Рекомендации по оптимизации
            recommendations = self._generate_recommendations(stats)
            
            return {
                "status": "active",
                "timestamp": datetime.now().isoformat(),
                "basic_statistics": stats,
                "effectiveness_by_system": effectiveness_by_system,
                "problem_topics": problem_topics,
                "recommendations": recommendations,
                "health_score": self._calculate_health_score(stats),
                "next_maintenance": self._get_next_maintenance_time()
            }
            
        except Exception as e:
            logger.error(f"Error generating status report: {e}")
            return {"error": str(e), "status": "error"}
    
    def _analyze_system_effectiveness(self, by_system_data: List) -> Dict[str, Any]:
        """Анализ эффективности по системам автопостинга"""
        
        analysis = {}
        
        for system_name, content_count, last_activity in by_system_data:
            # Парсим последнюю активность
            try:
                last_activity_dt = datetime.fromisoformat(last_activity)
                hours_since_activity = (datetime.now() - last_activity_dt).total_seconds() / 3600
            except:
                hours_since_activity = 999
            
            # Определяем статус системы
            if hours_since_activity < 24:
                activity_status = "active"
            elif hours_since_activity < 72:
                activity_status = "moderate"
            else:
                activity_status = "inactive"
            
            # Анализ производительности
            if content_count > 100:
                performance = "high"
            elif content_count > 30:
                performance = "medium"
            else:
                performance = "low"
            
            analysis[system_name] = {
                "content_generated": content_count,
                "last_activity_hours": round(hours_since_activity, 1),
                "activity_status": activity_status,
                "performance_level": performance,
                "recommendation": self._get_system_recommendation(system_name, content_count, hours_since_activity)
            }
        
        return analysis
    
    def _identify_problem_topics(self) -> List[Dict[str, Any]]:
        """Выявление проблемных тем"""
        
        problems = []
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.dedup_system.db_path)
            cursor = conn.cursor()
            
            # Темы с высоким количеством блокировок
            cursor.execute('''
                SELECT topic_original, block_reason, usage_count, blocked_at
                FROM blocked_topics
                WHERE usage_count > 5
                ORDER BY usage_count DESC
                LIMIT 10
            ''')
            
            high_conflict_topics = cursor.fetchall()
            
            for topic, reason, count, blocked_at in high_conflict_topics:
                problems.append({
                    "type": "high_conflict_topic",
                    "topic": topic,
                    "reason": reason,
                    "conflict_count": count,
                    "blocked_since": blocked_at,
                    "severity": "high" if count > 15 else "medium"
                })
            
            # Системы с низкой уникальностью
            cursor.execute('''
                SELECT source_system, COUNT(*) as total_attempts
                FROM content_fingerprints
                WHERE created_at > ?
                GROUP BY source_system
                HAVING total_attempts < 5
            ''', ((datetime.now() - timedelta(days=7)).isoformat(),))
            
            low_activity_systems = cursor.fetchall()
            
            for system, attempts in low_activity_systems:
                problems.append({
                    "type": "low_activity_system",
                    "system": system,
                    "attempts_last_week": attempts,
                    "severity": "medium"
                })
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error identifying problems: {e}")
        
        return problems
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """Генерация рекомендаций по улучшению системы"""
        
        recommendations = []
        
        # Анализируем общую статистику
        total_content = stats.get('total_registered_content', 0)
        blocked_permanently = stats.get('permanently_blocked_topics', 0)
        blocked_temporarily = stats.get('temporarily_blocked_topics', 0)
        
        # Рекомендации на основе данных
        if total_content < 50:
            recommendations.append("📈 Система только начинает работу. Рекомендуется активировать все источники контента.")
        
        if blocked_permanently > total_content * 0.1:
            recommendations.append("⚠️ Слишком много заблокированных тем. Рассмотрите возможность разблокировки или создания новых тем.")
        
        if blocked_temporarily > 10:
            recommendations.append("🔄 Высокое количество временных блокировок указывает на необходимость расширения базы контента.")
        
        if stats.get('source_systems', 0) < 3:
            recommendations.append("🎯 Добавьте больше источников контента для повышения разнообразия.")
        
        # Рекомендации по настройкам
        similarity_threshold = stats.get('similarity_threshold', 0.7)
        if similarity_threshold > 0.8:
            recommendations.append("⚙️ Порог сходства очень высокий - можно немного снизить для большего разнообразия.")
        elif similarity_threshold < 0.5:
            recommendations.append("⚙️ Порог сходства низкий - возможны дубликаты, рекомендуется повысить.")
        
        # Обслуживание
        try:
            last_activity = datetime.fromisoformat(stats.get('last_activity', '1970-01-01'))
            hours_inactive = (datetime.now() - last_activity).total_seconds() / 3600
            
            if hours_inactive > 48:
                recommendations.append("🔧 Система неактивна более 2 дней. Проверьте работу автопостинга.")
            elif hours_inactive < 1:
                recommendations.append("✅ Система активна и работает стабильно.")
        except:
            pass
        
        if not recommendations:
            recommendations.append("✅ Система работает оптимально. Регулярно проверяйте статистику.")
        
        return recommendations
    
    def _calculate_health_score(self, stats: Dict) -> float:
        """Вычисление общего индекса здоровья системы (0-100)"""
        
        score = 100.0
        
        # Штрафы за проблемы
        total_content = stats.get('total_registered_content', 0)
        blocked_permanently = stats.get('permanently_blocked_topics', 0)
        blocked_temporarily = stats.get('temporarily_blocked_topics', 0)
        
        # Недостаток контента
        if total_content < 10:
            score -= 30
        elif total_content < 50:
            score -= 15
        
        # Слишком много блокировок
        if blocked_permanently > total_content * 0.2:
            score -= 25
        elif blocked_permanently > total_content * 0.1:
            score -= 10
        
        if blocked_temporarily > 20:
            score -= 15
        elif blocked_temporarily > 10:
            score -= 5
        
        # Разнообразие источников
        source_systems = stats.get('source_systems', 0)
        if source_systems < 2:
            score -= 20
        elif source_systems < 3:
            score -= 10
        
        # Активность
        try:
            last_activity = datetime.fromisoformat(stats.get('last_activity', '1970-01-01'))
            hours_inactive = (datetime.now() - last_activity).total_seconds() / 3600
            
            if hours_inactive > 72:
                score -= 30
            elif hours_inactive > 24:
                score -= 15
        except:
            score -= 20
        
        return max(0.0, min(100.0, score))
    
    def _get_system_recommendation(self, system_name: str, content_count: int, hours_inactive: float) -> str:
        """Рекомендации для конкретной системы"""
        
        if hours_inactive > 72:
            return "Система неактивна. Проверьте работоспособность."
        elif hours_inactive > 24:
            return "Система работает нерегулярно. Рекомендуется диагностика."
        elif content_count < 10:
            return "Низкая производительность. Увеличьте частоту генерации контента."
        elif content_count > 200:
            return "Высокая активность. Отлично!"
        else:
            return "Система работает стабильно."
    
    def _get_next_maintenance_time(self) -> str:
        """Время следующего обслуживания"""
        next_maintenance = datetime.now() + timedelta(days=7)
        return next_maintenance.isoformat()
    
    async def cleanup_system(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Очистка системы от старых данных"""
        
        if not self.dedup_system:
            return {"error": "Deduplication system not available"}
        
        try:
            result = self.dedup_system.cleanup_old_data(days_to_keep)
            
            logger.info(f"🧹 System cleanup completed: {result}")
            
            return {
                "status": "completed",
                "cleanup_results": result,
                "timestamp": datetime.now().isoformat(),
                "days_kept": days_to_keep
            }
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def unblock_topic(self, topic: str) -> Dict[str, Any]:
        """Разблокировка темы"""
        
        if not self.dedup_system:
            return {"error": "Deduplication system not available"}
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.dedup_system.db_path)
            cursor = conn.cursor()
            
            # Удаляем блокировку
            cursor.execute('DELETE FROM blocked_topics WHERE topic_original = ?', (topic,))
            removed_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if removed_count > 0:
                logger.info(f"✅ Topic unblocked: {topic}")
                return {"status": "success", "message": f"Topic '{topic}' has been unblocked"}
            else:
                return {"status": "not_found", "message": f"Topic '{topic}' was not blocked"}
        
        except Exception as e:
            logger.error(f"Error unblocking topic: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def get_blocked_topics_list(self) -> List[Dict[str, Any]]:
        """Список заблокированных тем"""
        
        if not self.dedup_system:
            return []
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.dedup_system.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT topic_original, block_reason, usage_count, blocked_at, blocked_until
                FROM blocked_topics
                ORDER BY blocked_at DESC
            ''')
            
            blocked_topics = []
            for row in cursor.fetchall():
                topic, reason, count, blocked_at, blocked_until = row
                
                # Определяем тип блокировки
                if blocked_until is None:
                    block_type = "permanent"
                    status = "blocked"
                else:
                    block_type = "temporary"
                    try:
                        blocked_until_dt = datetime.fromisoformat(blocked_until)
                        status = "blocked" if blocked_until_dt > datetime.now() else "expired"
                    except:
                        status = "unknown"
                
                blocked_topics.append({
                    "topic": topic,
                    "reason": reason,
                    "conflict_count": count,
                    "blocked_at": blocked_at,
                    "blocked_until": blocked_until,
                    "block_type": block_type,
                    "status": status
                })
            
            conn.close()
            return blocked_topics
        
        except Exception as e:
            logger.error(f"Error getting blocked topics: {e}")
            return []


# Глобальный экземпляр монитора
_monitor_instance = None

def get_deduplication_monitor() -> DeduplicationMonitor:
    """Получить экземпляр монитора дедупликации"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = DeduplicationMonitor()
    return _monitor_instance


# Удобные функции для использования
async def get_deduplication_status() -> Dict[str, Any]:
    """Получить статус системы дедупликации"""
    monitor = get_deduplication_monitor()
    return await monitor.get_full_status_report()


async def cleanup_deduplication_data(days: int = 90) -> Dict[str, Any]:
    """Очистка старых данных дедупликации"""
    monitor = get_deduplication_monitor()
    return await monitor.cleanup_system(days)


async def unblock_content_topic(topic: str) -> Dict[str, Any]:
    """Разблокировка заблокированной темы"""
    monitor = get_deduplication_monitor()
    return await monitor.unblock_topic(topic)


async def get_blocked_topics() -> List[Dict[str, Any]]:
    """Получить список заблокированных тем"""
    monitor = get_deduplication_monitor()
    return await monitor.get_blocked_topics_list()