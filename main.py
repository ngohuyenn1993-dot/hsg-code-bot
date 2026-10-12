
import os
import json
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.environ["BOT_TOKEN"]
DATA_DIR = Path("/data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "codes.json"
LOCK = asyncio.Lock()

def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {"codes": [], "claimed": {}}

def save_data(data):
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎁 Nhận code", callback_data="claim")]]
    await update.message.reply_text(
        "Chào bạn! Bấm nút bên dưới để nhận code riêng.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    async with LOCK:
        data = load_data()
        uid = str(user.id)

        if uid in data["claimed"]:
            await query.message.reply_text(
                "Bạn đã nhận code rồi. Mỗi người chỉ nhận 1 code."
            )
            return

        available = next(
            (c for c in data["codes"] if c not in data["claimed"].values()),
            None
        )
        if not available:
            await query.message.reply_text(
                "Hiện đã hết code. Vui lòng chờ đợt tiếp theo!"
            )
            return

        data["claimed"][uid] = available
        save_data(data)

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"🎁 Code của bạn: {available}\nVui lòng không chia sẻ code này."
        )
        await query.message.reply_text(
            "✅ Đã gửi code riêng cho bạn qua tin nhắn bot!"
        )
    except Exception:
        await query.message.reply_text(
            "Bạn hãy mở chat riêng với bot, bấm Start rồi thử nhận lại."
        )

async def add_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != int(
        os.environ.get("ADMIN_ID", "0")
    ):
        await update.message.reply_text("Bạn không có quyền dùng lệnh này.")
        return

    if not context.args:
        await update.message.reply_text(
            "Cách dùng: /addcodes CODE1 CODE2 CODE3"
        )
        return

    async with LOCK:
        data = load_data()
        existing = set(data["codes"])
        added = 0
        for code in context.args:
            code = code.strip()
            if code and code not in existing:
                data["codes"].append(code)
                existing.add(code)
                added += 1
        save_data(data)

    await update.message.reply_text(f"Đã thêm {added} code mới.")

async def post_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != int(
        os.environ.get("ADMIN_ID", "0")
    ):
        await update.message.reply_text("Bạn không có quyền dùng lệnh này.")
        return

    keyboard = [[InlineKeyboardButton(
        "🎁 Nhận code", callback_data="claim"
    )]]
    await update.message.reply_text(
        "🎁 Bấm nút bên dưới để nhận 1 code riêng!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Mở bot\n"
        "/post - Tạo nút nhận code trong nhóm (admin)\n"
        "/addcodes CODE1 CODE2 - Thêm danh sách code (admin)"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("post", post_button))
    app.add_handler(CommandHandler("addcodes", add_codes))
    app.add_handler(CallbackQueryHandler(claim, pattern="^claim$"))
    app.run_polling()

if __name__ == "__main__":
    main()
