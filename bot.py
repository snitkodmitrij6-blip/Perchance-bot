import os
import re
import asyncio
from collections import deque
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

NEGATIVE = "low quality, blurry, deformed, distorted, bad anatomy, bad hands, extra limbs, missing limbs, ugly, poorly drawn, watermark, text, signature, censored"

recent_prompts = deque(maxlen=8)

def build_prompt(user_text: str) -> str:
    base = user_text.strip()
    style = "highly detailed, masterpiece, best quality"
    return f"{base}, {style}"

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Аниме", callback_data="style_anime"),
            InlineKeyboardButton("Реализм", callback_data="style_real"),
            InlineKeyboardButton("Фурри", callback_data="style_furry"),
        ],
        [
            InlineKeyboardButton("Квадрат", callback_data="shape_square"),
            InlineKeyboardButton("Альбом", callback_data="shape_landscape"),
            InlineKeyboardButton("Портрет", callback_data="shape_portrait"),
        ],
        [
            InlineKeyboardButton("Последние", callback_data="show_recent"),
            InlineKeyboardButton("Очистить", callback_data="clear_recent"),
        ],
        [InlineKeyboardButton("Открыть Perchance", url="https://perchance.org/in1shhj717")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text or "@" not in message.text:
        return

    user_text = re.sub(r'@\w+', '', message.text).strip()
    if not user_text:
        await message.reply_text("Напиши, что сгенерировать.", reply_markup=get_main_keyboard())
        return

    prompt = build_prompt(user_text)
    recent_prompts.append(prompt)

    reply = (
        f"**Промпт:**\n`{prompt}`\n\n"
        f"**Негативный:**\n`{NEGATIVE}`"
    )
    await message.reply_text(reply, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    style_map = {
        "style_anime": ", anime style, vibrant colors",
        "style_real": ", photorealistic, realistic lighting, sharp focus",
        "style_furry": ", furry, anthropomorphic, detailed fur",
        "shape_square": " (квадрат)",
        "shape_landscape": " (альбомная ориентация)",
        "shape_portrait": " (портретная ориентация)",
    }

    if data == "show_recent":
        if not recent_prompts:
            await query.message.reply_text("Нет сохранённых промптов.")
            return
        text = "**Последние промпты:**\n\n"
        for i, p in enumerate(reversed(recent_prompts), 1):
            short = p[:100] + "..." if len(p) > 100 else p
            text += f"{i}. `{short}`\n\n"
        await query.message.reply_text(text, parse_mode="Markdown")
        return

    if data == "clear_recent":
        recent_prompts.clear()
        await query.message.reply_text("История очищена.")
        return

    if data in style_map and recent_prompts:
        new_prompt = recent_prompts[-1] + style_map[data]
        recent_prompts.append(new_prompt)
        await query.message.reply_text(
            f"**Обновлённый промпт:**\n`{new_prompt}`\n\n**Негативный:**\n`{NEGATIVE}`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напиши запрос и упомяни меня. Я сделаю промпт и дам кнопки.",
        reply_markup=get_main_keyboard()
    )

async def health(request):
    return web.Response(text="OK")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    web_app = web.Application()
    web_app.router.add_get("/", health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
