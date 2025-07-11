#!/usr/bin/env python3
"""
Test script for Mini App /submit endpoint
"""
import asyncio
import aiohttp
import json

async def test_submit_endpoint():
    """Test the /submit endpoint with sample data"""
    
    # Sample form data matching Mini App structure
    test_data = {
        "category_id": 1,
        "category_name": "Семейное право",
        "subcategory": "Развод",
        "description": "Нужна консультация по разводу и разделу имущества",
        "name": "Тест Тестович",
        "phone": "+7 (999) 123-45-67",
        "email": "test@example.com",
        "contact_method": "telegram",
        "contact_time": "morning",
        "files": [
            {
                "name": "document.pdf",
                "data": "base64encodeddata...",
                "size": 1024
            }
        ],
        "tg_user_id": 12345678,
        "utm_source": "test"
    }
    
    # Test URL (replace with your actual URL)
    url = "http://localhost:8080/submit"
    
    async with aiohttp.ClientSession() as session:
        try:
            print(f"🧪 Testing submit endpoint: {url}")
            print(f"📤 Sending data: {json.dumps(test_data, indent=2)}")
            
            async with session.post(
                url,
                json=test_data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as response:
                print(f"📨 Response status: {response.status}")
                print(f"📨 Response headers: {dict(response.headers)}")
                
                response_text = await response.text()
                print(f"📨 Response body: {response_text}")
                
                if response.status == 200:
                    print("✅ Test PASSED - Submit endpoint working!")
                else:
                    print(f"❌ Test FAILED - Status: {response.status}")
                    
        except Exception as e:
            print(f"❌ Connection error: {e}")
            print("💡 Make sure the server is running on localhost:8080")

if __name__ == "__main__":
    asyncio.run(test_submit_endpoint())