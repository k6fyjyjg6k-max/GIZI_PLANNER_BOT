import asyncio
import logging
import os
import httpx
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import database as db

BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

logging.basicConfig(level=logging.INFO)


async def ask_claude(user_message: str, tasks: list) -> dict:
    """Отправляем сообщение в Claude и получаем структурированный ответ"""
    tasks_text = ""
    if tasks:
        for t in tasks:
            tasks_text += f"- #{t[0]}: {t[2]} ({t[3]})\n"
    else:
        tasks_text = "Задач нет"

    prompt = f"""Ты помощник-планировщик. Пользователь написал тебе сообщение.
    
Текущие задачи пользователя:
{tasks_text}

Сообщение пользователя: {user_message}

Проанализируй сообщение и ответь ТОЛЬКО в формате JSON (без markdown, без ```):
{{
  "action": "add" | "list" | "done" | "delete" | "chat",
  "reply": "твой ответ пользователю на русском",
  "task_title": "название задачи если action=add",
  "task_date": "дата в формате YYYY-MM-DD HH:MM если action=add, иначе null",
  "task_id": число если action=done или delete, иначе null
}}

Примеры:
- "завтра в 10 встреча с врачом" → action=add, task_title="Встреча с врачом", task_date=завтра 10:00
- "что у меня запланировано" → action=list
- "выполнил задачу 3" → action=done, task_id=3
- "привет как дела" → action=chat, reply=дружелюбный ответ"""

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        data = response.json()
        text = data["content"][0]["text"]
        import json
        return json.loads(text)


@dp.message(Command("start"))
async def start(message: Message):
    db.add_user(message.from_user.id)
    await message.answer(
        "👋 Привет! Я твой умный планировщик.\n\n"
        "Просто напиши мне что нужно сделать, например:\n"
        "• «завтра в 10 встреча с врачом»\n"
        "• «в пятницу сдать отчёт»\n"
        "• «что у меня запланировано?»\n"
        "• «выполнил задачу 3»\n\n"
        "Я всё пойму сам! 🤖"
    )


@dp.message()
async def handle_message(message: Message):
    tasks = db.get_all_tasks(message.from_user.id)
    
    try:
        result = await ask_claude(message.text, tasks)
        action = result.get("action")
        reply = result.get("reply", "")

        if action == "add":
            title = result.get("task_title", message.text)
            date_str = result.get("task_date")
            dt = None
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                except:
                    dt = None
            db.add_task(message.from_user.id, title, dt or datetime.now())
            await message.answer(f"✅ {reply}")

        elif action == "list":
            if not tasks:
                await message.answer("📭 У тебя нет задач!")
            else:
                text = "📋 Твои задачи:\n\n"
                for t in tasks:
                    text += f"#{t[0]} 🕐 {t[3]} — {t[2]}\n"
                await message.answer(text)

        elif action == "done":
            task_id = result.get("task_id")
            if task_id:
                db.mark_done(task_id, message.from_user.id)
            await message.answer(f"✅ {reply}")

        elif action == "delete":
            task_id = result.get("task_id")
            if task_id:
                db.delete_task(task_id, message.from_user.id)
            await message.answer(f"🗑 {reply}")

        else:
            await message.answer(reply)

    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("⚠️ Не понял тебя, попробуй ещё раз.")


async def morning_digest():
    users = db.get_all_users()
    for user_id in users:
        tasks = db.get_today_tasks(user_id)
        if tasks:
            text = "☀️ Доброе утро! Твои дела на сегодня:\n\n"
            for t in tasks:
                text += f"🕐 {t[3]} — {t[2]}\n"
            try:
                await bot.send_message(user_id, text)
            except:
                pass


async def check_reminders():
    now = datetime.now()
    target = now + timedelta(minutes=30)
    window_start = target - timedelta(seconds=30)
    window_end = target + timedelta(seconds=30)
    users = db.get_all_users()
    for user_id in users:
        tasks = db.get_tasks_in_window(user_id, window_start, window_end)
        for t in tasks:
            try:
                await bot.send_message(
                    user_id,
                    f"⏰ Напоминание! Через 30 минут: {t[2]}"
                )
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
