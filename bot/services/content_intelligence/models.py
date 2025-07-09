"""
🧠 CONTENT INTELLIGENCE MODELS
Модели данных для системы умного контента
"""

import hashlib
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from ..db import Base

@dataclass
class NewsItem:
    """Структура новостного элемента"""
    title: str
    content: str
    url: str
    source: str
    publish_date: datetime
    category: str
    relevance_score: float = 0.0
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self.generate_hash()
    
    def generate_hash(self) -> str:
        content = f"{self.title}{self.content}{self.source}"
        return hashlib.sha256(content.encode()).hexdigest()

class ContentItem(Base):
    """Модель контента в БД"""
    __tablename__ = 'content_items'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    source = Column(String(100), nullable=False)
    publish_date = Column(DateTime, nullable=False)
    category = Column(String(100), nullable=False)
    relevance_score = Column(Float, default=0.0)
    content_hash = Column(String(64), unique=True, nullable=False)
    processed = Column(Boolean, default=False)
    used_in_post = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class PostHistory(Base):
    """История постов"""
    __tablename__ = 'post_history'
    
    id = Column(Integer, primary_key=True)
    post_text = Column(Text, nullable=False)
    post_hash = Column(String(64), unique=True, nullable=False)
    channel_id = Column(String(50), nullable=False)
    posted_at = Column(DateTime, default=datetime.now)
