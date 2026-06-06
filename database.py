import sqlite3
from datetime import datetime, timedelta

def get_conn():
    return sqlite3.connect("planner.db")

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task TEXT,
        datetime TEXT,
        done INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    users = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
    conn.close()
    return users

def add_task(user_id, task, dt):
    conn = get_conn()
    conn.execute("INSERT INTO tasks (user_id, task, datetime) VALUES (?, ?, ?)",
                 (user_id, task, dt.strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_today_tasks(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? AND datetime LIKE ? AND done=0 ORDER BY datetime",
        (user_id, f"{today}%")
    ).fetchall()
    conn.close()
    return tasks

def get_week_tasks(user_id):
    now = datetime.now()
    week = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")
    conn = get_conn()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? AND datetime BETWEEN ? AND ? AND done=0 ORDER BY datetime",
        (user_id, today, week)
    ).fetchall()
    conn.close()
    return tasks

def get_all_tasks(user_id):
    conn = get_conn()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? AND done=0 ORDER BY datetime",
        (user_id,)
    ).fetchall()
    conn.close()
    return tasks

def get_tasks_at_time(user_id, dt):
    time_str = dt.strftime("%Y-%m-%d %H:%M")
    conn = get_conn()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? AND datetime=? AND done=0",
        (user_id, time_str)
    ).fetchall()
    conn.close()
    return tasks

def delete_task(task_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
    conn.commit()
    conn.close()
