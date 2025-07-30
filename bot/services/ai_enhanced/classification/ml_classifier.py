"""
EMPTY ML CLASSIFIER - NO AZURE CALLS
Полностью пустая заглушка без каких-либо Azure API вызовов.
"""

import logging

logger = logging.getLogger(__name__)

class MLClassifier:
    """Пустой классификатор без Azure"""
    
    def __init__(self):
        self.initialized = True
        self.ml_enabled = False
        logger.info("🚫 ML Classifier: EMPTY STUB - NO AZURE CALLS")
    
    async def initialize(self):
        """Пустая инициализация"""
        logger.info("🚫 ML Classifier: Empty initialization")
    
    async def classify_category(self, message: str):
        """Простейшая классификация"""
        return {"category": "Общие вопросы", "confidence": 0.5}
    
    async def classify_message(self, message: str):
        """Простейшая классификация"""
        return {"category": "Общие вопросы", "confidence": 0.5}
    
    def get_status(self):
        """Статус"""
        return {
            "status": "disabled",
            "ml_available": False,
            "azure_blocked": True
        }