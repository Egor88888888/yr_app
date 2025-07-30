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

async def start_combined():
    """Start both bot and web server concurrently"""
    try:
        print("🚀 Starting CLEAN Legal Center Bot...")
        
        # Import main bot function
        from bot.main import main
        
        # Start bot and web server concurrently
        port = int(os.getenv("PORT", 8000))
        print(f"🌐 Starting web server on port {port}")
        
        # Create uvicorn config for async startup
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_config=None)
        server = uvicorn.Server(config)
        
        # Run bot and server concurrently with exception handling
        async def run_bot():
            try:
                await main()
            except Exception as e:
                print(f"❌ Bot error: {e}")
                
        async def run_server():
            try:
                await server.serve()
            except Exception as e:
                print(f"❌ Server error: {e}")
        
        # Start both services
        await asyncio.gather(
            run_bot(),
            run_server(),
            return_exceptions=True
        )
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(start_combined())
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)