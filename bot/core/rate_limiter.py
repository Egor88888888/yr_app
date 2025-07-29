#!/usr/bin/env python3
"""
Rate limiting functionality for the bot.
Prevents spam and abuse by limiting requests per user.
"""

import time
import logging
from typing import Dict, List
from collections import defaultdict

from bot.config.settings import (
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, 
    user_request_counts, blocked_users
)

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiting for user requests"""
    
    def __init__(self):
        self.request_counts = user_request_counts
        self.blocked_users = blocked_users
        
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        if user_id in self.blocked_users:
            return True
            
        current_time = time.time()
        user_requests = self.request_counts[user_id]
        
        # Remove old requests outside the time window
        cutoff_time = current_time - RATE_LIMIT_WINDOW
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
        
        # Check if user exceeded the limit
        if len(user_requests) >= RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return True
            
        return False
    
    def record_request(self, user_id: int) -> None:
        """Record a request for rate limiting"""
        if user_id not in self.blocked_users:
            self.request_counts[user_id].append(time.time())
    
    def block_user(self, user_id: int) -> None:
        """Block user from making requests"""
        self.blocked_users.add(user_id)
        logger.warning(f"User {user_id} has been blocked")
    
    def unblock_user(self, user_id: int) -> None:
        """Unblock user"""
        self.blocked_users.discard(user_id)
        logger.info(f"User {user_id} has been unblocked")
    
    def get_user_request_count(self, user_id: int) -> int:
        """Get current request count for user"""
        current_time = time.time()
        user_requests = self.request_counts[user_id]
        
        # Remove old requests
        cutoff_time = current_time - RATE_LIMIT_WINDOW
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
        
        return len(user_requests)
    
    def get_stats(self) -> Dict:
        """Get rate limiting statistics"""
        return {
            "active_users": len(self.request_counts),
            "blocked_users": len(self.blocked_users),
            "total_requests": sum(len(reqs) for reqs in self.request_counts.values())
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

def check_rate_limit(user_id: int) -> bool:
    """Convenience function to check rate limit"""
    return rate_limiter.is_rate_limited(user_id)

def record_user_request(user_id: int) -> None:
    """Convenience function to record request"""
    rate_limiter.record_request(user_id)