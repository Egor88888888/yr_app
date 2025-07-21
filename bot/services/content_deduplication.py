"""
🔍 СИСТЕМА ПРЕДОТВРАЩЕНИЯ ДУБЛИРОВАНИЯ КОНТЕНТА
Обеспечивает 100% уникальность постов и тем автопостинга
"""

import hashlib
import re
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import json

logger = logging.getLogger(__name__)

@dataclass
class ContentFingerprint:
    """Отпечаток контента для сравнения"""
    title_hash: str
    content_hash: str
    topic_keywords: Set[str]
    semantic_tokens: Set[str]
    legal_references: Set[str]
    content_type: str
    created_at: datetime
    full_text_hash: str


class ContentDeduplicationSystem:
    """Унифицированная система предотвращения дублирования контента"""
    
    def __init__(self, db_path: str = "content_deduplication.db"):
        self.db_path = db_path
        self.similarity_threshold = 0.7  # Порог семантического сходства
        self.keyword_overlap_threshold = 0.6  # Порог пересечения ключевых слов
        self.legal_ref_weight = 0.9  # Вес совпадения правовых ссылок
        
        self._init_database()
        logger.info("🔍 Content Deduplication System initialized")
    
    def _init_database(self):
        """Инициализация базы данных дедупликации"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица отпечатков контента
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_hash TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                full_text_hash TEXT UNIQUE NOT NULL,
                topic_keywords TEXT NOT NULL,
                semantic_tokens TEXT NOT NULL, 
                legal_references TEXT NOT NULL,
                content_type TEXT NOT NULL,
                source_system TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица блокированных тем
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_normalized TEXT UNIQUE NOT NULL,
                topic_original TEXT NOT NULL,
                block_reason TEXT NOT NULL,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                blocked_until TIMESTAMP,
                usage_count INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица семантических групп
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                keywords TEXT NOT NULL,
                legal_refs TEXT NOT NULL,
                content_count INTEGER DEFAULT 1,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы для производительности
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_full_text_hash ON content_fingerprints(full_text_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON content_fingerprints(content_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON content_fingerprints(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_topic_normalized ON blocked_topics(topic_normalized)')
        
        conn.commit()
        conn.close()
    
    def extract_content_fingerprint(self, title: str, content: str, content_type: str = "post", source_system: str = "unknown") -> ContentFingerprint:
        """Извлечение отпечатка контента для проверки уникальности"""
        
        # Нормализация текста
        normalized_title = self._normalize_text(title)
        normalized_content = self._normalize_text(content)
        full_text = f"{normalized_title} {normalized_content}"
        
        # Хэши
        title_hash = hashlib.md5(normalized_title.encode()).hexdigest()
        content_hash = hashlib.md5(normalized_content.encode()).hexdigest()
        full_text_hash = hashlib.sha256(full_text.encode()).hexdigest()
        
        # Извлечение ключевых слов по темам
        topic_keywords = self._extract_topic_keywords(full_text)
        
        # Семантические токены
        semantic_tokens = self._extract_semantic_tokens(full_text)
        
        # Правовые ссылки
        legal_references = self._extract_legal_references(full_text)
        
        return ContentFingerprint(
            title_hash=title_hash,
            content_hash=content_hash,
            topic_keywords=topic_keywords,
            semantic_tokens=semantic_tokens,
            legal_references=legal_references,
            content_type=content_type,
            created_at=datetime.now(),
            full_text_hash=full_text_hash
        )
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста для сравнения"""
        # Убираем специальные символы, эмодзи и форматирование
        text = re.sub(r'[^\w\s\.\,\!\?\;\:]', ' ', text)
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        # Приводим к нижнему регистру
        text = text.lower().strip()
        return text
    
    def _extract_topic_keywords(self, text: str) -> Set[str]:
        """Извлечение ключевых слов по юридическим темам"""
        
        legal_topics = {
            # Семейное право
            'семейное': ['семейн', 'развод', 'алимент', 'брак', 'супруг', 'ребенок', 'опека'],
            # Трудовое право
            'трудовое': ['труд', 'работ', 'увольн', 'зарплат', 'отпуск', 'больничн', 'сокращен'],
            # Жилищное право
            'жилищное': ['жил', 'квартир', 'дом', 'коммунальн', 'аренд', 'собственн', 'ук'],
            # Потребительские права
            'потребительское': ['потребител', 'товар', 'услуг', 'возврат', 'гарант', 'каче', 'магазин'],
            # Автомобильное право
            'автомобильное': ['дтп', 'авто', 'страхов', 'осаго', 'каско', 'гибдд', 'штраф'],
            # Наследство
            'наследственное': ['наслед', 'завещан', 'наследник', 'нотариус', 'доля'],
            # Административное
            'административное': ['админ', 'штраф', 'коап', 'гос', 'служб', 'ведомств'],
            # Банковское и финансы
            'банковское': ['банк', 'кредит', 'займ', 'депозит', 'процент', 'долг'],
            # Земельное право
            'земельное': ['земельн', 'участок', 'дача', 'межеван', 'кадастр'],
            # Уголовное право
            'уголовное': ['уголовн', 'преступлен', 'статья', 'суд', 'следств']
        }
        
        found_keywords = set()
        text_lower = text.lower()
        
        for category, keywords in legal_topics.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.add(f"{category}:{keyword}")
        
        return found_keywords
    
    def _extract_semantic_tokens(self, text: str) -> Set[str]:
        """Извлечение семантических токенов"""
        
        # Типовые юридические ситуации
        situations = [
            'права нарушены', 'получить компенсацию', 'подать иск', 'обратиться в суд',
            'нарушение закона', 'защита прав', 'возмещение ущерба', 'юридическая помощь',
            'консультация юриста', 'правовая защита', 'судебное решение', 'правовые последствия'
        ]
        
        semantic_tokens = set()
        text_lower = text.lower()
        
        for situation in situations:
            if situation in text_lower:
                semantic_tokens.add(situation.replace(' ', '_'))
        
        # Извлекаем биграммы и триграммы
        words = text_lower.split()
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            if len(bigram) > 10:  # Только значимые биграммы
                semantic_tokens.add(f"bigram:{bigram}")
        
        for i in range(len(words) - 2):
            trigram = f"{words[i]}_{words[i+1]}_{words[i+2]}"
            if len(trigram) > 15:  # Только значимые триграммы
                semantic_tokens.add(f"trigram:{trigram}")
        
        return semantic_tokens
    
    def _extract_legal_references(self, text: str) -> Set[str]:
        """Извлечение правовых ссылок"""
        
        legal_refs = set()
        
        # Статьи кодексов и законов
        patterns = [
            r'ст(?:атья|\.)\s*(\d+(?:\.\d+)?)\s*(гк|тк|ук|коап|ск|жк|нк)\s*рф',
            r'статья\s*(\d+(?:\.\d+)?)\s*(гражданского|трудового|уголовного|семейного|жилищного|налогового)\s*кодекса',
            r'закон[а-я\s]*№\s*(\d+-фз)',
            r'федеральный закон от [\d\.]+ № (\d+-фз)',
            r'постановление.*№\s*(\d+)',
            r'определение.*№\s*([\d\-]+)',
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                legal_refs.add(match.group().strip())
        
        return legal_refs
    
    def is_content_duplicate(self, fingerprint: ContentFingerprint, source_system: str = "unknown") -> Tuple[bool, str, float]:
        """
        Проверка на дублирование контента
        Возвращает: (is_duplicate, reason, similarity_score)
        """
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Проверка точного совпадения по хэшу
        cursor.execute(
            "SELECT title, source_system FROM content_fingerprints WHERE full_text_hash = ?",
            (fingerprint.full_text_hash,)
        )
        exact_match = cursor.fetchone()
        if exact_match:
            conn.close()
            return True, f"Точное совпадение с постом: {exact_match[0]} (система: {exact_match[1]})", 1.0
        
        # 2. Проверка семантического сходства
        cursor.execute('''
            SELECT id, title, topic_keywords, semantic_tokens, legal_references, source_system,
                   created_at, usage_count
            FROM content_fingerprints 
            WHERE content_type = ? 
            AND created_at > ? 
            ORDER BY created_at DESC 
            LIMIT 100
        ''', (fingerprint.content_type, datetime.now() - timedelta(days=30)))
        
        recent_posts = cursor.fetchall()
        
        for post in recent_posts:
            post_id, title, keywords_json, tokens_json, refs_json, post_system, created_at, usage_count = post
            
            # Десериализация данных
            try:
                post_keywords = set(json.loads(keywords_json))
                post_tokens = set(json.loads(tokens_json))
                post_refs = set(json.loads(refs_json))
            except:
                continue
            
            # Вычисляем коэффициент сходства
            similarity = self._calculate_similarity(
                fingerprint.topic_keywords, post_keywords,
                fingerprint.semantic_tokens, post_tokens,
                fingerprint.legal_references, post_refs
            )
            
            if similarity > self.similarity_threshold:
                reason = f"Семантическое сходство {similarity:.2f} с постом: {title} (система: {post_system})"
                conn.close()
                return True, reason, similarity
        
        # 3. Проверка заблокированных тем
        topic_blocked, block_reason = self._is_topic_blocked(fingerprint.topic_keywords)
        if topic_blocked:
            conn.close()
            return True, f"Заблокированная тема: {block_reason}", 0.9
        
        conn.close()
        return False, "", 0.0
    
    def _calculate_similarity(self, keywords1: Set[str], keywords2: Set[str],
                             tokens1: Set[str], tokens2: Set[str],
                             refs1: Set[str], refs2: Set[str]) -> float:
        """Расчет коэффициента сходства контента"""
        
        # Пересечение ключевых слов
        keyword_intersection = len(keywords1.intersection(keywords2))
        keyword_union = len(keywords1.union(keywords2))
        keyword_similarity = keyword_intersection / keyword_union if keyword_union > 0 else 0
        
        # Пересечение семантических токенов
        token_intersection = len(tokens1.intersection(tokens2))
        token_union = len(tokens1.union(tokens2))
        token_similarity = token_intersection / token_union if token_union > 0 else 0
        
        # Пересечение правовых ссылок (высокий вес)
        ref_intersection = len(refs1.intersection(refs2))
        ref_union = len(refs1.union(refs2))
        ref_similarity = ref_intersection / ref_union if ref_union > 0 else 0
        
        # Взвешенная оценка сходства
        total_similarity = (
            keyword_similarity * 0.4 +
            token_similarity * 0.3 +
            ref_similarity * self.legal_ref_weight * 0.3
        )
        
        return total_similarity
    
    def _is_topic_blocked(self, keywords: Set[str]) -> Tuple[bool, str]:
        """Проверка заблокированных тем"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем заблокированные темы
        cursor.execute('''
            SELECT topic_normalized, topic_original, block_reason, blocked_until, usage_count
            FROM blocked_topics
            WHERE blocked_until IS NULL OR blocked_until > ?
        ''', (datetime.now().isoformat(),))
        
        blocked_topics = cursor.fetchall()
        
        for topic_norm, topic_orig, reason, blocked_until, usage_count in blocked_topics:
            # Проверяем вхождение заблокированной темы в ключевые слова или контент
            topic_words = self._normalize_text(topic_orig).split()
            
            # Проверяем пересечение нормализованных слов темы с ключевыми словами
            keyword_text = ' '.join([kw.split(':')[-1] if ':' in kw else kw for kw in keywords])
            
            # Ищем совпадения слов темы в ключевых словах
            matches_found = any(word in keyword_text for word in topic_words if len(word) > 3)
            
            if matches_found:
                # Увеличиваем счетчик попыток использования заблокированной темы
                cursor.execute(
                    'UPDATE blocked_topics SET usage_count = usage_count + 1 WHERE topic_normalized = ?',
                    (topic_norm,)
                )
                conn.commit()
                conn.close()
                return True, f"{reason} (попыток: {usage_count + 1})"
        
        conn.close()
        return False, ""
    
    def register_content(self, fingerprint: ContentFingerprint, title: str, source_system: str = "unknown") -> bool:
        """Регистрация нового уникального контента"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Сериализуем данные
            keywords_json = json.dumps(list(fingerprint.topic_keywords))
            tokens_json = json.dumps(list(fingerprint.semantic_tokens))
            refs_json = json.dumps(list(fingerprint.legal_references))
            
            cursor.execute('''
                INSERT INTO content_fingerprints
                (title_hash, content_hash, full_text_hash, topic_keywords, semantic_tokens,
                 legal_references, content_type, source_system, title, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fingerprint.title_hash,
                fingerprint.content_hash,
                fingerprint.full_text_hash,
                keywords_json,
                tokens_json,
                refs_json,
                fingerprint.content_type,
                source_system,
                title,
                fingerprint.created_at.isoformat()
            ))
            
            conn.commit()
            logger.info(f"✅ Registered unique content: {title[:50]}...")
            return True
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"❌ Failed to register content (duplicate): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error registering content: {str(e)}")
            return False
        finally:
            conn.close()
    
    def block_topic_temporarily(self, topic: str, reason: str, hours: int = 24):
        """Временная блокировка темы"""
        
        normalized_topic = self._normalize_text(topic)
        blocked_until = datetime.now() + timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO blocked_topics
            (topic_normalized, topic_original, block_reason, blocked_until)
            VALUES (?, ?, ?, ?)
        ''', (normalized_topic, topic, reason, blocked_until.isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"⚠️ Topic blocked for {hours}h: {topic} - {reason}")
    
    def block_topic_permanently(self, topic: str, reason: str):
        """Permanent блокировка темы"""
        
        normalized_topic = self._normalize_text(topic)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO blocked_topics
            (topic_normalized, topic_original, block_reason, blocked_until)
            VALUES (?, ?, ?, NULL)
        ''', (normalized_topic, topic, reason))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🚫 Topic permanently blocked: {topic} - {reason}")
    
    def get_content_statistics(self) -> Dict:
        """Статистика системы дедупликации"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM content_fingerprints')
        total_content = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT content_type) FROM content_fingerprints')
        content_types = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT source_system) FROM content_fingerprints')
        source_systems = cursor.fetchone()[0]
        
        # Статистика по системам
        cursor.execute('''
            SELECT source_system, COUNT(*), MAX(created_at)
            FROM content_fingerprints
            GROUP BY source_system
        ''')
        by_system = cursor.fetchall()
        
        # Заблокированные темы
        cursor.execute('SELECT COUNT(*) FROM blocked_topics WHERE blocked_until IS NULL')
        permanently_blocked = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM blocked_topics WHERE blocked_until > ?', 
                      (datetime.now().isoformat(),))
        temporarily_blocked = cursor.fetchone()[0]
        
        # Последняя активность
        cursor.execute('SELECT MAX(created_at) FROM content_fingerprints')
        last_activity = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_registered_content': total_content,
            'content_types': content_types,
            'source_systems': source_systems,
            'by_system': by_system,
            'permanently_blocked_topics': permanently_blocked,
            'temporarily_blocked_topics': temporarily_blocked,
            'last_activity': last_activity,
            'similarity_threshold': self.similarity_threshold
        }
    
    def cleanup_old_data(self, days: int = 90):
        """Очистка старых данных"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Удаляем старые отпечатки
        cursor.execute(
            'DELETE FROM content_fingerprints WHERE created_at < ?',
            (cutoff_date.isoformat(),)
        )
        deleted_fingerprints = cursor.rowcount
        
        # Удаляем истекшие блокировки
        cursor.execute(
            'DELETE FROM blocked_topics WHERE blocked_until IS NOT NULL AND blocked_until < ?',
            (datetime.now().isoformat(),)
        )
        deleted_blocks = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"🧹 Cleanup: deleted {deleted_fingerprints} fingerprints and {deleted_blocks} expired blocks")
        
        return {
            'deleted_fingerprints': deleted_fingerprints,
            'deleted_blocks': deleted_blocks
        }


# Глобальный экземпляр системы дедупликации
_deduplication_system = None

def get_deduplication_system() -> ContentDeduplicationSystem:
    """Получить экземпляр системы дедупликации"""
    global _deduplication_system
    if _deduplication_system is None:
        _deduplication_system = ContentDeduplicationSystem()
    return _deduplication_system


# Удобные функции для интеграции
def check_content_uniqueness(title: str, content: str, content_type: str = "post", 
                           source_system: str = "unknown") -> Tuple[bool, str, float]:
    """
    Проверка уникальности контента
    Возвращает: (is_unique, reason_if_duplicate, similarity_score)
    """
    system = get_deduplication_system()
    fingerprint = system.extract_content_fingerprint(title, content, content_type, source_system)
    is_duplicate, reason, score = system.is_content_duplicate(fingerprint, source_system)
    return not is_duplicate, reason, score


def register_unique_content(title: str, content: str, content_type: str = "post", 
                          source_system: str = "unknown") -> bool:
    """Регистрация уникального контента"""
    system = get_deduplication_system()
    fingerprint = system.extract_content_fingerprint(title, content, content_type, source_system)
    return system.register_content(fingerprint, title, source_system)


def validate_and_register_content(title: str, content: str, content_type: str = "post", 
                                source_system: str = "unknown") -> Tuple[bool, str]:
    """
    Проверка и регистрация контента в одном вызове
    Возвращает: (success, message)
    """
    # Проверяем уникальность
    is_unique, reason, score = check_content_uniqueness(title, content, content_type, source_system)
    
    if not is_unique:
        return False, f"Контент не уникален: {reason} (сходство: {score:.2f})"
    
    # Регистрируем уникальный контент
    registered = register_unique_content(title, content, content_type, source_system)
    
    if registered:
        return True, "Контент прошел проверку и зарегистрирован"
    else:
        return False, "Ошибка при регистрации контента"