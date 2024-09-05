import os
import json
from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

TASKS_DIR = 'data/tasks/'
BACKLOG_DIR = 'data/backlog/'
COMPLETED_TASKS_DIR = 'data/completed/'

def load_active_tasks(user_id):
    tasks = []
    for filename in os.listdir(TASKS_DIR):
        if filename.startswith(f"task_{user_id}_") and filename.endswith('.json'):
            with open(os.path.join(TASKS_DIR, filename), 'r', encoding='utf-8') as f:
                task = json.load(f)
                tasks.append(task)
    return tasks

async def show_active_tasks(message: types.Message):
    tasks = load_active_tasks(message.from_user.id)
    if not tasks:
        await message.reply("Активных задач нет.")
        return
    for task in tasks:
        start_time = datetime.strptime(task['start_time'], "%H:%M:%S")
        end_time = datetime.strptime(task['end_time'], "%H:%M:%S")
        start_date_str = ""
        end_date_str = ""
        if task['due_date'] != task['end_date']:
            start_date_str = datetime.strptime(task['due_date'], "%Y-%m-%d").strftime("%d.%m.%Y")
            end_date_str = datetime.strptime(task['end_date'], "%Y-%m-%d").strftime("%d.%m.%Y")

        start_str = f"{start_date_str} {start_time.strftime('%H:%M')}".strip()
        end_str = f"{end_date_str} {end_time.strftime('%H:%M')}".strip()
        duration = end_time - start_time
        duration_str = f"{duration.seconds // 3600} ч {duration.seconds % 3600 // 60} мин" if duration.seconds >= 3600 else f"{duration.seconds // 60} мин"
        task_text = (
            f"<b>Имя:</b> {task['title']}\n\n"
            f"<b>Описание:</b> <i>{task['description']}</i>\n"
            f"<b>Время:</b> {start_str} - {end_str}\n"
            f"<b>Продолжительность:</b> {duration_str}"
        )
        keyboard = InlineKeyboardMarkup()
        to_backlog_button = InlineKeyboardButton("В бэклог", callback_data=f"task_to_backlog_{task['task_id']}")
        complete_button = InlineKeyboardButton("Завершить", callback_data=f"task_complete_{task['task_id']}")
        keyboard.add(to_backlog_button, complete_button)
        await message.reply(task_text, reply_markup=keyboard, parse_mode="HTML")

async def task_to_backlog(callback_query: types.CallbackQuery):
    try:
        task_id = int(callback_query.data.split("_")[-1])
        user_id = callback_query.from_user.id
        tasks = load_active_tasks(user_id)
        task = next((t for t in tasks if t['task_id'] == task_id), None)
        if task:
            task['status'] = 'backlog'
            task['start_time'] = None
            task['end_time'] = None
            task['duration'] = None
            task['due_date'] = None
            task['end_date'] = None
            save_task_to_backlog(task)
            task_file = os.path.join(TASKS_DIR, f"task_{user_id}_{task_id}.json")
            if os.path.exists(task_file):
                os.remove(task_file)
            await callback_query.message.edit_text(f"Задача '{task['title']}' перемещена в бэклог.")
        else:
            await callback_query.answer("Задача не найдена.", show_alert=True)
    except ValueError as e:
        await callback_query.answer("Ошибка при обработке задачи. Попробуйте еще раз.", show_alert=True)

def save_task_to_backlog(task):
    if not os.path.exists(BACKLOG_DIR):
        os.makedirs(BACKLOG_DIR)
    task_file = os.path.join(BACKLOG_DIR, f"task_{task['user_id']}_{task['task_id']}.json")
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=4, ensure_ascii=False)

async def task_complete(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split("_")[-1])
    task_file = os.path.join(TASKS_DIR, f"task_{callback_query.from_user.id}_{task_id}.json")
    if os.path.exists(task_file):
        with open(task_file, 'r', encoding='utf-8') as f:
            task = json.load(f)
        task['status'] = 'completed'
        task['end_time'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        completed_task_file = os.path.join(COMPLETED_TASKS_DIR, f"task_{callback_query.from_user.id}_{task_id}.json")
        with open(completed_task_file, 'w', encoding='utf-8') as f:
            json.dump(task, f, indent=4, ensure_ascii=False)
        os.remove(task_file)
        await callback_query.message.edit_text(f"Задача '{task['title']}' завершена и перемещена в архив.")
    else:
        await callback_query.answer("Задача не найдена.", show_alert=True)

def register_active_tasks_handlers(dp: Dispatcher):
    dp.register_message_handler(show_active_tasks, commands="tasks")
    dp.register_callback_query_handler(task_to_backlog, lambda c: c.data and c.data.startswith("task_to_backlog_"))
    dp.register_callback_query_handler(task_complete, lambda c: c.data and c.data.startswith("task_complete_"))
