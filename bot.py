import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import database as db
import os

BOT_TOKEN = "8971560314:AAH0O6MD5zMu1i3qUrl8FupqjvpLzYhG-Xw"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

@dp.message(Command("start"))
async def start(message: Message):
    db.add_user(message.from_user.id)
    await message.answer(
        "👋 Привет! Я твой планировщик.\n\n"
        "📌 Команды:\n"
        "/add 15.06 10:00 Звонок врачу — добавить дело\n"
        "/today — дела на сегодня\n"
        "/week — дела на неделю\n"
        "/delete — удалить дело\n"
        "/list — все дела"
    )

@dp.message(Command("add"))
async def add_task(message: Message):
    try:
        parts = message.text.split(" ", 3)
        date_str = parts[1]
        time_str = parts[2]
        task = parts[3]
        year = datetime.now().year
        dt = datetime.strptime(f"{date_str}.{year} {time_str}", "%d.%m.%Y %H:%M")
        db.add_task(message.from_user.id, task, dt)
        await message.answer(f"✅ Добавлено: {task}\n📅 {dt.strftime('%d.%m %H:%M')}")
    except:
        await message.answer("❌ Неверный формат!\nИспользуй: /add 15.06 10:00 Текст дела")

@dp.message(Command("today"))
async def today_tasks(message: Message):
    tasks = db.get_today_tasks(message.from_user.id)
    if not tasks:
        await message.answer("📭 На сегодня дел нет!")
        return
    text = "📋 *Дела на сегодня:*\n\n"
    for t in tasks:
        text += f"🕐 {t[3]} — {t[2]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("week"))
async def week_tasks(message: Message):
    tasks = db.get_week_tasks(message.from_user.id)
    if not tasks:
        await message.answer("📭 На эту неделю дел нет!")
        return
    text = "📅 *Дела на неделю:*\n\n"
    for t in tasks:
        text += f"📌 {t[3]} — {t[2]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("list"))
async def list_tasks(message: Message):
    tasks = db.get_all_tasks(message.from_user.id)
    if not tasks:
        await message.answer("📭 У тебя нет дел!")
        return
    text = "📋 *Все дела:*\n\n"
    for t in tasks:
        text += f"#{t[0]} | {t[3]} — {t[2]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("delete"))
async def delete_task(message: Message):
    try:
        task_id = int(message.text.split()[1])
        db.delete_task(task_id, message.from_user.id)
        await message.answer(f"🗑 Дело #{task_id} удалено!")
    except:
        await message.answer("❌ Используй: /delete 5 (номер из /list)")

async def morning_digest():
    users = db.get_all_users()
    for user_id in users:
        tasks = db.get_today_tasks(user_id)
        if tasks:
            text = "☀️ *Доброе утро! Твои дела на сегодня:*\n\n"
            for t in tasks:
                text += f"🕐 {t[3]} — {t[2]}\n"
            try:
                await bot.send_message(user_id, text, parse_mode="Markdown")
            except:
                pass

async def check_reminders():
    now = datetime.now()
    soon = now + timedelta(minutes=30)
    users = db.get_all_users()
    for user_id in users:
        tasks = db.get_tasks_at_time(user_id, soon)
        for t in tasks:
            try:
                await bot.send_message(user_id, f"⏰ *Напоминание!*\nЧерез 30 минут: {t[2]}", parse_mode="Markdown")
            except:
                pass

async def main():
    db.init_db()
    scheduler.add_job(morning_digest, "cron", hour=8, minute=0)
    scheduler.add_job(check_reminders, "interval", minutes=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
