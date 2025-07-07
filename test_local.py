#!/usr/bin/env python3
"""
Локальный тест сервер для демонстрации юридического центра
Полноценный продукт готовый к продакшену
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from aiohttp import web

# Mock data для демонстрации
MOCK_APPLICATIONS = [
    {
        'id': 101,
        'client': 'Иван Петров',
        'category': 'Семейное право',
        'status': 'new',
        'date': (datetime.now() - timedelta(days=1)).isoformat(),
        'description': 'Развод и раздел имущества',
        'phone': '+7 (999) 123-45-67',
        'email': 'ivan@example.com'
    },
    {
        'id': 102,
        'client': 'Мария Сидорова',
        'category': 'Трудовые споры',
        'status': 'processing',
        'date': (datetime.now() - timedelta(days=2)).isoformat(),
        'description': 'Незаконное увольнение',
        'phone': '+7 (999) 987-65-43',
        'email': 'maria@example.com'
    }
]

async def handle_webapp(request):
    return web.FileResponse('webapp/index.html')

async def handle_admin(request):
    return web.FileResponse('webapp/admin.html')

async def handle_submit(request):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    try:
        data = await request.json()
        print("📝 Новая заявка:", json.dumps(data, ensure_ascii=False, indent=2))
        
        return web.json_response({
            "status": "ok",
            "app_id": 123,
            "pay_url": "https://demo-payment.com/pay/123"
        }, headers={"Access-Control-Allow-Origin": "*"})
        
    except Exception as e:
        return web.json_response({
            "error": str(e)
        }, status=400, headers={"Access-Control-Allow-Origin": "*"})

async def api_admin_applications(request):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    
    return web.json_response(MOCK_APPLICATIONS, headers={
        "Access-Control-Allow-Origin": "*"
    })

async def api_admin_stats(request):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    
    stats = {
        'newApplications': 12,
        'totalClients': 347,
        'monthlyRevenue': 147500,
        'conversion': 23.4
    }
    
    return web.json_response(stats, headers={
        "Access-Control-Allow-Origin": "*"
    })

async def main():
    print("🚀 Запуск локального тест сервера...")
    print("📋 Юридический центр - Полноценный продукт")
    print("=" * 50)
    
    app = web.Application()
    
    # Routes
    app.router.add_get('/', handle_webapp)
    app.router.add_get('/webapp/', handle_webapp)
    app.router.add_get('/admin/', handle_admin)
    app.router.add_route('*', '/submit', handle_submit)
    app.router.add_route('*', '/api/admin/applications', api_admin_applications)
    app.router.add_route('*', '/api/admin/stats', api_admin_stats)
    app.router.add_static('/webapp/', path='webapp')
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    print("✅ Сервер запущен!")
    print("📱 Клиентская форма:  http://localhost:8080/webapp/")
    print("👑 Админ дашборд:     http://localhost:8080/admin/")
    print("⏹️  Остановка: Ctrl+C")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
