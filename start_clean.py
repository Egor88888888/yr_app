#!/usr/bin/env python3
"""
🔥 CLEAN START - NO AZURE AI 
Absolutely clean startup script that cannot import ai_enhanced
"""

import os
import sys
import asyncio
import logging

# BLOCK any ai_enhanced imports
class BlockedAIEnhanced:
    def __getattr__(self, name):
        raise ImportError("🚫 AI Enhanced is BLOCKED - no Azure allowed!")

# Install import blocker
sys.modules['bot.services.ai_enhanced'] = BlockedAIEnhanced()
sys.modules['bot.services.ai_enhanced.classification.ml_classifier'] = BlockedAIEnhanced()

print("🚫 AI Enhanced imports BLOCKED")
print("🤖 Starting CLEAN bot with OpenAI only...")

# Now import main
from bot.main import main

if __name__ == "__main__":
    try:
        print("🚀 Starting CLEAN Legal Center Bot...")
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)