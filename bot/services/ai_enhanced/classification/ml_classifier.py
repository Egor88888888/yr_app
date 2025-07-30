"""
DUMMY ML CLASSIFIER - NO AZURE
Простая заглушка без Azure Embeddings API
"""

import logging

logger = logging.getLogger(__name__)

HAS_NUMPY = False

class MLClassifier:
    """Простой классификатор без Azure API"""
    
    def __init__(self):
        self.initialized = False
        self.ml_enabled = False
        logger.info("🔢 ML Classifier: DISABLED - using simple keyword fallback only")
    
    async def initialize(self):
        """Инициализация заглушки"""
        self.initialized = True
        logger.info("🔢 ML Classifier: Initialized in DISABLED mode")
    
    async def classify_category(self, message: str):
        """Простая классификация по ключевым словам"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["развод", "алимент", "брак", "семья", "дети"]):
            return {"category": "Семейное право", "confidence": 0.8}
        elif any(word in message_lower for word in ["работ", "труд", "увольнен", "зарплат", "отпуск"]):
            return {"category": "Трудовые споры", "confidence": 0.8}
        elif any(word in message_lower for word in ["наследств", "завещан", "наследник", "имущество"]):
            return {"category": "Наследство", "confidence": 0.8}
        elif any(word in message_lower for word in ["жкх", "квартир", "дом", "жиль", "коммунальн"]):
            return {"category": "Жилищные вопросы", "confidence": 0.8}
        elif any(word in message_lower for word in ["долг", "кредит", "банкрот"]):
            return {"category": "Банкротство физлиц", "confidence": 0.8}
        elif any(word in message_lower for word in ["налог", "ндфл", "ифнс"]):
            return {"category": "Налоговые консультации", "confidence": 0.8}
        else:
            return {"category": "Общие вопросы", "confidence": 0.5}
    
    def get_status(self):
        """Статус системы"""
        return {
            "status": "disabled",
            "categories_loaded": 8,
            "embeddings_ready": 0,
            "ml_available": False
        }