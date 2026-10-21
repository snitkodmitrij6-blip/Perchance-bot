import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from playwright.async_api import async_playwright

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Напиши что-нибудь вроде «сгенерируй девушку фурри».")

async def generate_with_perchance(prompt: str, style: str, count: str, ratio: str):
    url = (
        f"https://perchance.org/ai-character-generator?bot=1"
        f"&prompt={prompt.replace(' ', '+')}"
        f"&style={style}"
        f"&count={count}"
        f"&ratio={ratio}"
    )
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=120000)
        # Ждём, пока генерация завершится
        await page.wait_for_function("window.__BOT_STATUS__ === 'done'", timeout=180000)
        result = await page.evaluate("window.__BOT_RESULT__")
        await browser.close()
        return result

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user_id = update.effective_user.id

    if any(word in text.lower() for word in ["сгенерируй", "изобрази", "нарисуй", "generate"]):
        user_data[user_id] = {"prompt": text}
        keyboard = [
            [InlineKeyboardButton("Аниме", callback_data="style_anime"),
             InlineKeyboardButton("Фурри", callback_data="style_furry")],
            [InlineKeyboardButton("Реализм", callback_data="style_real"),
             InlineKeyboardButton("Мультяшный", callback_data="style_cartoon")],
            [InlineKeyboardButton("Демон/Крылья", callback_data="style_demon"),
             InlineKeyboardButton("Стикмен", callback_data="style_stickman")]
        ]
        await update.message.reply_text("Выбери стиль:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(f"Ты написал: {text}")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if user_id not in user_data:
        await query.edit_message_text("Начни заново — напиши запрос.")
        return

    if data.startswith("style_"):
        style = data.split("_")[1]
        user_data[user_id]["style"] = style
        keyboard = [
            [InlineKeyboardButton("1", callback_data="count_1"),
             InlineKeyboardButton("2", callback_data="count_2")],
            [InlineKeyboardButton("512x512", callback_data="ratio_512x512"),
             InlineKeyboardButton("512x768", callback_data="ratio_512x768")]
        ]
        await query.edit_message_text(f"Стиль: {style}\nВыбери количество и формат:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("count_") or data.startswith("ratio_"):
        if data.startswith("count_"):
            user_data[user_id]["count"] = data.split("_")[1]
        else:
            user_data[user_id]["ratio"] = data.replace("ratio_", "")

        info = user_data[user_id]
        if "count" in info and "ratio" in info:
            await query.edit_message_text("Генерирую... Это может занять 30–60 секунд.")
            try:
                result = await generate_with_perchance(
                    info["prompt"], info["style"], info["count"], info["ratio"]
                )
                images = result.get("images", [])
                if images:
                    for img_url in images:
                        await context.bot.send_photo(chat_id=query.message.chat_id, photo=img_url)
                    await query.message.reply_text("Готово!")
                else:
                    await query.message.reply_text("Не удалось получить картинки.")
            except Exception as e:
                await query.message.reply_text(f"Ошибка генерации: {e}")

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(button))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/webhook",
        url_path="webhook",
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
