import os
import json
from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from board import initiate_task_timing, save_active_task

BACKLOG_DIR = 'data/backlog/'
TASKS_DIR = 'data/tasks/'
COMPLETED_TASKS_DIR = 'data/completed/'

def load_backlog_tasks():
    tasks = []
    for filename in os.listdir(BACKLOG_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(BACKLOG_DIR, filename), 'r', encoding='utf-8') as f:
                task = json.load(f)
                tasks.append(task)
    return tasks

def load_user_backlog_tasks(user_id):
    tasks = []
    for filename in os.listdir(BACKLOG_DIR):
        if filename.startswith(f"task_{user_id}_") and filename.endswith('.json'):
            with open(os.path.join(BACKLOG_DIR, filename), 'r', encoding='utf-8') as f:
                task = json.load(f)
                tasks.append(task)
    return tasks

async def show_backlog_tasks(message: types.Message):
    tasks = load_user_backlog_tasks(message.from_user.id)
    if not tasks:
        await message.reply("В бэклоге нет задач.")
        return
    for task in tasks:
        task_text = f"**{task['title']}**\n{task['description']}"
        keyboard = InlineKeyboardMarkup()
        in_work_button = InlineKeyboardButton("В работу", callback_data=f"backlog_to_work_{task['task_id']}")
        complete_button = InlineKeyboardButton("Завершить", callback_data=f"backlog_complete_{task['task_id']}")
        keyboard.add(in_work_button, complete_button)
        await message.reply(task_text, reply_markup=keyboard, parse_mode="Markdown")

async def backlog_to_work(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        task_id = int(callback_query.data.split("_")[-1])
        user_id = callback_query.from_user.id
        tasks = load_user_backlog_tasks(user_id)
        task = next((t for t in tasks if t['task_id'] == task_id), None)
        if task:
            task['status'] = 'in_work'
            save_active_task(task)
            await state.update_data(task_id=task_id)
            await initiate_task_timing(callback_query.message, state, task)
            task_file = os.path.join(BACKLOG_DIR, f"task_{user_id}_{task_id}.json")
            if os.path.exists(task_file):
                os.remove(task_file)
            await callback_query.message.edit_text(f"Задача '{task['title']}' перемещена в работу.")
        else:
            await callback_query.answer("Задача не найдена.", show_alert=True)
    except ValueError as e:
        await callback_query.answer("Ошибка при обработке задачи. Попробуйте еще раз.", show_alert=True)

async def backlog_complete(callback_query: types.CallbackQuery):
    task_id = callback_query.data.split("_")[-1]
    task_file = os.path.join(BACKLOG_DIR, f"task_{callback_query.from_user.id}_{task_id}.json")
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

def register_backlog_handlers(dp: Dispatcher):
    dp.register_message_handler(show_backlog_tasks, commands="backlog")
    dp.register_callback_query_handler(backlog_to_work, lambda c: c.data and c.data.startswith("backlog_to_work_"))
    dp.register_callback_query_handler(backlog_complete, lambda c: c.data and c.data.startswith("backlog_complete_"))
