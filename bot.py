import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Напиши что-нибудь вроде «сгенерируй девушку фурри».")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    user_id = update.effective_user.id

    if any(word in text.lower() for word in ["сгенерируй", "изобрази", "нарисуй", "generate"]):
        user_data[user_id] = {"prompt": text}
        keyboard = [
            [InlineKeyboardButton("Аниме", callback_data="style_anime"),
             InlineKeyboardButton("Фурри", callback_data="style_furry")],
            [InlineKeyboardButton("Реализм", callback_data="style_real"),
             InlineKeyboardButton("Мультяшный", callback_data="style_cartoon")]
        ]
        await update.message.reply_text(
            "Выбери стиль:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
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
             InlineKeyboardButton("2", callback_data="count_2"),
             InlineKeyboardButton("4", callback_data="count_4")],
            [InlineKeyboardButton("1:1", callback_data="ratio_1"),
             InlineKeyboardButton("16:9", callback_data="ratio_16"),
             InlineKeyboardButton("9:16", callback_data="ratio_9")]
        ]
        await query.edit_message_text(
            f"Стиль: {style}\nСколько картинок и какой формат?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data.startswith("count_") or data.startswith("ratio_"):
        if data.startswith("count_"):
            user_data[user_id]["count"] = data.split("_")[1]
        else:
            user_data[user_id]["ratio"] = data.split("_")[1]

        info = user_data[user_id]
        await query.edit_message_text(
            f"Готово!\n"
            f"Запрос: {info.get('prompt')}\n"
            f"Стиль: {info.get('style')}\n"
            f"Количество: {info.get('count', 'не выбрано')}\n"
            f"Формат: {info.get('ratio', 'не выбран')}\n\n"
            f"(Пока что просто показываю выбор. Генерация на Perchance будет следующим шагом.)"
        )

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
