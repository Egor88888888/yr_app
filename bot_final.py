#!/usr/bin/env python3
"""
Telegram bot with Mini-App launched via a single MenuButtonWebApp.
Works on Railway automatically: no manual steps after deploy.
– aiohttp web-server handles both Telegram webhook POST /<TOKEN>
  and POST /submit from the mini-app.
– /submit parses payload, notifies admin, answers WebAppQuery to
  close the mini-app.
"""
import asyncio
import json
import logging
import os
import uuid
from aiohttp import web
from telegram import (
    Update,
    WebAppInfo,
    MenuButtonWebApp,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import timedelta
import openai
from typing import Optional
from telegram.constants import ChatAction

########################### CONFIG ###########################
TOKEN = os.getenv("YOUR_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # string
# e.g. poetic-simplicity-production-xxx.up.railway.app
PUBLIC_HOST = os.getenv("MY_RAILWAY_PUBLIC_URL")
WEB_APP_URL = "https://egor88888888.github.io/yr_app/"
PORT = int(os.getenv("PORT", 8080))

# === AI & Autoposting ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # required for AI
# numeric id as string, optional
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")
TARGET_CHANNEL_USERNAME = os.getenv("TARGET_CHANNEL_USERNAME", "@strahsprav")
POST_INTERVAL_HOURS = int(os.getenv("POST_INTERVAL_HOURS", 4))
##############################################################

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# ===================== Telegram handlers =====================


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Нажмите кнопку \"📝 Подать заявку\" рядом со строкой ввода⬇️")


async def debug(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    log.debug("Update: %s", update)

# ====================== HTTP handlers ========================


async def handle_submit(request: web.Request) -> web.Response:
    """Receive data from mini-app, notify admin, answer WebAppQuery."""
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    data = await request.json()
    query_id = data.get("queryId")
    payload = data.get("payload", {})
    log.info("/submit payload=%s", payload)

    # Notify admin
    try:
        problems = ", ".join(payload.get("problems", []))
        name = payload.get("name", "-")
        phone = payload.get("phone", "-")
        desc = payload.get("description", "-")
        text = f"🔔 Заявка\n{name}\n{phone}\n{problems}\n{desc}"
        await request.app["bot"].send_message(chat_id=ADMIN_CHAT_ID, text=text)
    except Exception as e:
        log.error("Admin send failed: %s", e)

    # Close mini-app
    try:
        result = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Заявка принята",
            input_message_content=InputTextMessageContent(
                "✅ Спасибо! Заявка получена."),
        )
        await request.app["bot"].answer_web_app_query(query_id, result)
    except Exception as e:
        log.error("answerWebAppQuery failed: %s", e)

    return web.json_response({"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


async def handle_telegram(request: web.Request) -> web.Response:
    """Telegram sends updates here."""
    update_json = await request.json()
    await request.app["application"].update_queue.put(Update.de_json(update_json, request.app["bot"]))
    return web.Response(text="ok")

# ====================== Setup helpers ========================


async def setup_menu(bot):
    # Сделать MenuButtonWebApp кнопкой по-умолчанию для всех пользователей бота.
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📝 Подать заявку",
                web_app=WebAppInfo(url=WEB_APP_URL),
            ),
        )
    except Exception as e:
        log.error("set_chat_menu_button failed: %s", e)

# ====================== AI helpers ==========================


async def _ai_complete(messages: list[dict], model: str = "gpt-3.5-turbo", max_tokens: int = 800, temperature: float = 0.7):
    """Unified wrapper around OpenRouter chat completion."""
    if not OPENROUTER_API_KEY:
        log.error("OPENROUTER_API_KEY missing; can't generate text")
        return None
    try:
        rsp = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return rsp.choices[0].message.content.strip()
    except Exception as e:
        log.error("AI completion failed: %s", e)
        return None


async def generate_ai_post() -> Optional[str]:
    """Generate a short Telegram post about insurance fairness."""
    messages = [
        {"role": "system", "content": "Ты опытный копирайтер, эксперт в страховых правах. Пиши на русском."},
        {"role": "user",
            "content": "Сгенерируй короткий, полезный и цепляющий пост (до 700 символов) о страховой справедливости."},
    ]
    return await _ai_complete(messages, temperature=0.8, max_tokens=700)


async def ai_private_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Answer private user messages with AI."""
    if update.message is None or update.message.text is None:
        return
    # show typing
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    messages = [
        {"role": "system", "content": "Ты дружелюбный ассистент, помогаешь людям со страховыми вопросами. Отвечай коротко и по существу."},
        {"role": "user", "content": update.message.text},
    ]
    answer = await _ai_complete(messages, temperature=0.5)
    if answer:
        await update.message.reply_text(answer)


async def ai_post_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Periodic job: post AI-generated text to target channel."""
    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        log.warning("TARGET_CHANNEL_ID not resolved; skip posting")
        return
    text = await generate_ai_post()
    if text:
        bot_username = ctx.bot.username or ""  # safe fallback
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📝 Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(
                "🤖 Открыть чат с ботом", url=f"https://t.me/{bot_username}?start=channel")]
        ])
        try:
            await ctx.bot.send_message(chat_id=channel_id, text=text, reply_markup=markup)
            log.info("AI post sent to channel %s", channel_id)
        except Exception as e:
            log.error("Failed to send AI post: %s", e)

# ================== Manual posting command ==================


async def cmd_post_ai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin command to generate and post AI content to channel immediately."""
    log.info("/post command from %s", update.effective_user.id)
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔️ У вас нет прав использовать эту команду")
        return

    channel_id = ctx.bot_data.get("TARGET_CHANNEL_ID")
    if not channel_id:
        await update.message.reply_text("❗ Channel ID неизвестен. Проверьте конфиг.")
        return

    await update.message.reply_text("🤖 Генерирую пост...")
    text = await generate_ai_post()
    if not text:
        await update.message.reply_text("Ошибка генерации текста")
        return

    bot_username = ctx.bot.username or ""
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📝 Подать заявку", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("🤖 Открыть чат с ботом",
                              url=f"https://t.me/{bot_username}?start=channel")]
    ])
    try:
        await ctx.bot.send_message(chat_id=channel_id, text=text, reply_markup=markup)
        await update.message.reply_text("✅ Пост опубликован")
    except Exception as e:
        log.error("Manual post failed: %s", e)
        await update.message.reply_text(f"Ошибка отправки: {e}")

# ========================= Main ==============================


async def main_async():
    if not all([TOKEN, ADMIN_CHAT_ID, PUBLIC_HOST]):
        log.critical(
            "Missing env vars: YOUR_BOT_TOKEN / ADMIN_CHAT_ID / MY_RAILWAY_PUBLIC_URL")
        return

    application = Application.builder().token(TOKEN).updater(None).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler(["postai", "post"], cmd_post_ai))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, ai_private_chat))
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, debug))

    # aiohttp app
    app = web.Application()
    app["bot"] = application.bot
    app["application"] = application
    app.router.add_post(f"/{TOKEN}", handle_telegram)
    app.router.add_route("*", "/submit", handle_submit)

    # === Configure OpenRouter ===
    if OPENROUTER_API_KEY:
        openai.api_key = OPENROUTER_API_KEY
        openai.api_base = "https://openrouter.ai/api/v1"

    # === Resolve channel ID (once) ===
    target_channel_id = None
    if TARGET_CHANNEL_ID:
        target_channel_id = int(TARGET_CHANNEL_ID)
    else:
        try:
            chat = await application.bot.get_chat(TARGET_CHANNEL_USERNAME)
            target_channel_id = chat.id
            log.info("Resolved @%s -> %s",
                     TARGET_CHANNEL_USERNAME, target_channel_id)
        except Exception as e:
            log.error("Cannot resolve channel username %s: %s",
                      TARGET_CHANNEL_USERNAME, e)

    application.bot_data["TARGET_CHANNEL_ID"] = target_channel_id

    # Set webhook & default menu button
    await setup_menu(application.bot)
    await application.bot.set_webhook(url=f"https://{PUBLIC_HOST}/{TOKEN}")
    log.info("Webhook set to https://%s/%s", PUBLIC_HOST, TOKEN)

    # === Schedule autoposting job ===
    if target_channel_id:
        application.job_queue.run_repeating(
            ai_post_job,
            interval=timedelta(hours=POST_INTERVAL_HOURS),
            first=timedelta(minutes=1),
            name="ai_posting",
        )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    async with application:
        await application.start()
        log.info("Bot & HTTP server running on port %s", PORT)
        # run forever
        await asyncio.Event().wait()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
