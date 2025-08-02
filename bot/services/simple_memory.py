"""Simple conversation memory using in-memory storage"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SimpleConversationMemory:
    """Simple conversation memory management"""
    
    def __init__(self, max_messages=8, session_timeout_hours=2):
        self.max_messages = max_messages
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.conversations = {}  # user_id -> conversation data
    
    async def get_conversation_history(self, user_id: int) -> List[Dict[str, str]]:
        """Get recent conversation history for user"""
        if user_id not in self.conversations:
            self.conversations[user_id] = {
                "messages": [],
                "last_activity": datetime.now()
            }
        
        session = self.conversations[user_id]
        
        # Check if session expired
        if datetime.now() - session["last_activity"] > self.session_timeout:
            session["messages"] = []
            logger.info(f"🔄 Cleared expired conversation for user {user_id}")
        
        return session["messages"][-self.max_messages:]
    
    async def add_message(self, user_id: int, role: str, content: str):
        """Add message to conversation history"""
        if user_id not in self.conversations:
            self.conversations[user_id] = {
                "messages": [],
                "last_activity": datetime.now()
            }
        
        session = self.conversations[user_id]
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only recent messages
        if len(session["messages"]) > self.max_messages:
            session["messages"] = session["messages"][-self.max_messages:]
        
        session["last_activity"] = datetime.now()
        logger.info(f"💭 Added {role} message to conversation for user {user_id} (total: {len(session['messages'])})")
    
    async def clear_session(self, user_id: int):
        """Clear conversation history for user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"🗑️ Cleared conversation for user {user_id}")
    
    def get_session_info(self, user_id: int) -> Dict:
        """Get session information for debugging"""
        if user_id not in self.conversations:
            return {"exists": False}
        
        session = self.conversations[user_id]
        return {
            "exists": True,
            "message_count": len(session["messages"]),
            "last_activity": session["last_activity"].isoformat(),
            "messages": [f"{msg['role']}: {msg['content'][:50]}..." for msg in session["messages"]]
        }

# Global instance
simple_memory = SimpleConversationMemory()