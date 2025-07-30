#!/usr/bin/env python3
"""
🔥 CLEAN START - NO AZURE AI 
Absolutely clean startup script that cannot import ai_enhanced
"""

import os
import sys
import asyncio
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
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

# Create simple FastAPI app for health check
app = FastAPI(title="Clean Legal Bot")

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy", "ai_enhanced": "blocked"})

# Now import main
from bot.main import main

def start_bot():
    """Start Telegram bot in separate thread"""
    try:
        print("🚀 Starting CLEAN Legal Center Bot...")
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Bot Error: {e}")

def start_web():
    """Start FastAPI web server"""
    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Starting web server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    try:
        # Start bot in background thread
        bot_thread = threading.Thread(target=start_bot, daemon=True)
        bot_thread.start()
        
        # Start web server in main thread
        start_web()
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)