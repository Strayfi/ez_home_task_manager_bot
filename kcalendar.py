import os
import json
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from config import API_TOKEN
import shutil

COMPLETED_TASKS_DIR = 'data/completed/'
TASKS_DIR = 'data/tasks/'
CHECK_INTERVAL = 30 
NOTIFICATION_TIME_BEFORE_END = timedelta(minutes=5)
NOTIFICATION_TIME_BEFORE_START = timedelta(minutes=5)

bot = Bot(token=API_TOKEN)

def load_tasks():
    tasks = []
    for filename in os.listdir(TASKS_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(TASKS_DIR, filename), 'r', encoding='utf-8') as f:
                task = json.load(f)
                if 'due_date' not in task:
                    print(f"Задача без due_date: {filename}, task_id: {task.get('task_id', 'Unknown')}")
                tasks.append(task)
    return tasks

async def check_tasks():
    now = datetime.now()
    tasks = load_tasks()

    for task in tasks:
        start_date = task.get('due_date', None)
        if not start_date:
            print(f"В задаче '{task['title']}' отсутствует due_date, пропуск задачи.")
            continue 
        try:
            start_time = datetime.strptime(f"{start_date} {task['start_time']}", "%Y-%m-%d %H:%M:%S")
            end_date = task.get('end_date', start_date) 
            end_time = datetime.strptime(f"{end_date} {task['end_time']}", "%Y-%m-%d %H:%M:%S")
        except KeyError as e:
            continue
        user_id = task['user_id']
        if now + NOTIFICATION_TIME_BEFORE_START >= start_time > now and task.get('notified_start', False) == False:
            time_left = start_time - now
            minutes_left = time_left.seconds // 60
            await bot.send_message(user_id, f"🚀 Задача '{task['title']}' начинается через {minutes_left} минут.")
            task['notified_start'] = True  
            save_task(task)
        if now + NOTIFICATION_TIME_BEFORE_END >= end_time > now and task.get('notified_end', False) == False:
            time_left = end_time - now
            minutes_left = time_left.seconds // 60
            await bot.send_message(user_id, f"⏰ Внимание! До завершения задачи '{task['title']}' осталось {minutes_left} минут.")
            task['notified_end'] = True  
            save_task(task)
        if now >= end_time:
            await bot.send_message(user_id, f"❗️ Задача '{task['title']}' завершена.")
            move_task_to_completed(task)

def move_task_to_completed(task):
    if not os.path.exists(COMPLETED_TASKS_DIR):
        os.makedirs(COMPLETED_TASKS_DIR)
    
    task_file = os.path.join(TASKS_DIR, f"task_{task['user_id']}_{task['task_id']}.json")
    completed_task_file = os.path.join(COMPLETED_TASKS_DIR, f"task_{task['user_id']}_{task['task_id']}.json")
    shutil.move(task_file, completed_task_file)
    task['status'] = "completed"
    with open(completed_task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=4, ensure_ascii=False)

def save_task(task):
    task_file = os.path.join(TASKS_DIR, f"task_{task['user_id']}_{task['task_id']}.json")
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=4, ensure_ascii=False)

async def scheduled_task_check(dp):
    while True:
        await check_tasks()
        await asyncio.sleep(CHECK_INTERVAL)

def register_task_checker(dp):
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_task_check(dp))