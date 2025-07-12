#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 TEST APP - Simplified FastAPI server for Mini App testing
Минимальная версия для тестирования профессионального дизайна
"""

import os
import json
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Legal Mini App - Test Version",
    description="Professional Legal Services Mini App for Telegram",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")

# Data models
class ApplicationData(BaseModel):
    category_id: Optional[int] = None
    category_name: Optional[str] = ""
    subcategory: Optional[str] = ""
    description: Optional[str] = ""
    name: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    contact_method: Optional[str] = ""
    contact_time: Optional[str] = "any"
    files: Optional[List[Dict[str, Any]]] = []
    tg_user_id: Optional[int] = None
    utm_source: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main Mini App HTML"""
    try:
        with open("webapp/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Mini App not found")

@app.post("/submit")
async def submit_application(request: Request):
    """Handle form submission"""
    try:
        # Get JSON data
        data = await request.json()
        logger.info(f"📝 Received application: {data}")
        
        # Validate required fields
        if not data.get('category_id'):
            raise HTTPException(status_code=400, detail="Category is required")
        
        if not data.get('name'):
            raise HTTPException(status_code=400, detail="Name is required")
            
        if not data.get('phone'):
            raise HTTPException(status_code=400, detail="Phone is required")
            
        if not data.get('contact_method'):
            raise HTTPException(status_code=400, detail="Contact method is required")
        
        # Save to file (for testing)
        application_id = f"app_{hash(json.dumps(data, sort_keys=True))}"
        
        # Create applications directory if it doesn't exist
        os.makedirs("applications", exist_ok=True)
        
        # Save application
        with open(f"applications/{application_id}.json", "w", encoding="utf-8") as f:
            json.dump({
                **data,
                "application_id": application_id,
                "timestamp": str(pd.Timestamp.now()) if 'pd' in globals() else "2024-01-01T00:00:00"
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Application saved: {application_id}")
        
        # Return success response
        return {
            "status": "ok",
            "message": "Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.",
            "application_id": application_id,
            "pay_url": "# Платежная система не настроена"
        }
        
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON received")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    except Exception as e:
        logger.error(f"❌ Error processing application: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Mini App Test Server is running"}

@app.get("/applications")
async def list_applications():
    """List all applications (for testing)"""
    try:
        applications = []
        if os.path.exists("applications"):
            for filename in os.listdir("applications"):
                if filename.endswith(".json"):
                    with open(f"applications/{filename}", "r", encoding="utf-8") as f:
                        applications.append(json.load(f))
        return {"applications": applications, "count": len(applications)}
    except Exception as e:
        logger.error(f"❌ Error listing applications: {str(e)}")
        return {"applications": [], "count": 0, "error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Starting Legal Mini App Test Server on port {port}")
    logger.info(f"📱 Mini App URL: http://localhost:{port}")
    logger.info(f"🏥 Health Check: http://localhost:{port}/health")
    logger.info(f"📋 Applications: http://localhost:{port}/applications")
    
    uvicorn.run(
        "test_app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )