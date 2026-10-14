import os
import re
import sqlite3
import threading
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ============================================================
# TRADE SESSION — сервер проверки UID
# ============================================================

# ============ НАСТРОЙКИ ============
# Токен и ID канала уже вписаны ниже.
# Если захочешь поменять — просто отредактируй эти строки.
BOT_TOKEN  = os.environ.get("BOT_TOKEN")  or "8637818965:AAGnE9fegjAmZZbiTrJNXsjtitL089qxjT4"
CHANNEL_ID = os.environ.get("CHANNEL_ID") or "-1003589899000"
DB_PATH    = "data.db"

# ============================================================
# БАЗА ДАННЫХ
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS uids (
            uid TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_uid(uid):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT OR IGNORE INTO uids (uid) VALUES (?)", (uid,))
        conn.commit()
        print(f"[SAVE] UID сохранён: {uid}")
    except Exception as e:
        print(f"[ERROR] save_uid: {e}")
    finally:
        conn.close()

def uid_exists(uid):
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT 1 FROM uids WHERE uid = ?", (uid,)).fetchone()
        return row is not None
    finally:
        conn.close()

# ============================================================
# TELEGRAM-БОТ: слушает канал и вытаскивает UID
# ============================================================
async def handle_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post:
        return
    text = update.channel_post.text or update.channel_post.caption or ""
    print(f"[CHANNEL] Новое сообщение: {text[:300]}")
    matches = re.findall(r"\b\d{6,12}\b", text)
    for uid in matches:
        save_uid(uid)

def run_bot():
    if not BOT_TOKEN:
        print("[BOT] BOT_TOKEN не задан — бот не запущен")
        return
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_channel_message))
    print("[BOT] Запущен, слушаю канал...")
    app.run_polling()

# ============================================================
# FLASK API
# ============================================================
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Trade Session UID Checker is running."

@flask_app.route("/check-uid")
def check_uid():
    uid = request.args.get("uid", "").strip()
    if not uid:
        return jsonify({"ok": False, "error": "uid required"}), 400
    return jsonify({"ok": uid_exists(uid), "uid": uid})

# Отладка: сколько всего UID в базе
@flask_app.route("/stats")
def stats():
    conn = sqlite3.connect(DB_PATH)
    try:
        total = conn.execute("SELECT COUNT(*) FROM uids").fetchone()[0]
        return jsonify({"total": total})
    finally:
        conn.close()

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
