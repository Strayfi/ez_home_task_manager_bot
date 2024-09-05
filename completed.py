import os
import json
from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from active_tasks import save_task_to_backlog
from board import initiate_task_timing, save_active_task

COMPLETED_TASKS_DIR = 'data/completed/'

def load_completed_tasks(user_id):
    tasks = []
    for filename in os.listdir(COMPLETED_TASKS_DIR):
        if filename.startswith(f"task_{user_id}_") and filename.endswith('.json'):
            with open(os.path.join(COMPLETED_TASKS_DIR, filename), 'r', encoding='utf-8') as f:
                task = json.load(f)
                tasks.append(task)
    return tasks

async def show_completed_tasks(message: types.Message):
    tasks = load_completed_tasks(message.from_user.id)
    if not tasks:
        await message.reply("Завершённых задач нет.")
        return
    for task in tasks:
        task_text = f"**{task['title']}**\n{task['description']}\nСтатус: {task['status']}"
        keyboard = InlineKeyboardMarkup()
        to_work_button = InlineKeyboardButton("В работу", callback_data=f"completed_to_work_{task['task_id']}")
        to_backlog_button = InlineKeyboardButton("В бэклог", callback_data=f"completed_to_backlog_{task['task_id']}")
        delete_button = InlineKeyboardButton("Удалить", callback_data=f"completed_delete_{task['task_id']}")
        keyboard.add(to_work_button, to_backlog_button, delete_button)
        await message.reply(task_text, reply_markup=keyboard, parse_mode="MarkdownV2")

async def completed_to_work(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        task_id = int(callback_query.data.split("_")[-1])
        user_id = callback_query.from_user.id
        tasks = load_completed_tasks(user_id)
        task = next((t for t in tasks if t['task_id'] == task_id), None)
        if task:
            task['status'] = 'in_work'
            save_active_task(task)
            await state.update_data(task_id=task_id)
            await initiate_task_timing(callback_query.message, state, task)
            task_file = os.path.join(COMPLETED_TASKS_DIR, f"task_{user_id}_{task_id}.json")
            if os.path.exists(task_file):
                os.remove(task_file)
            await callback_query.message.edit_text(f"Задача '{task['title']}' перемещена в работу.")
        else:
            await callback_query.answer("Задача не найдена.", show_alert=True)
    except ValueError as e:
        await callback_query.answer("Ошибка при обработке задачи. Попробуйте еще раз.", show_alert=True)

async def completed_to_backlog(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split("_")[-1])
    user_id = callback_query.from_user.id
    tasks = load_completed_tasks(user_id)
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    if task:
        task['status'] = 'backlog'
        task['start_time'] = None
        task['end_time'] = None
        task['duration'] = None
        task['due_date'] = None
        task['end_date'] = None
        save_task_to_backlog(task)
        task_file = os.path.join(COMPLETED_TASKS_DIR, f"task_{user_id}_{task_id}.json")
        if os.path.exists(task_file):
            os.remove(task_file)
        await callback_query.message.edit_text(f"Задача '{task['title']}' перемещена в бэклог.")
    else:
        await callback_query.answer("Задача не найдена.", show_alert=True)

async def completed_delete(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split("_")[-1])
    user_id = callback_query.from_user.id
    task_file = os.path.join(COMPLETED_TASKS_DIR, f"task_{user_id}_{task_id}.json")
    if os.path.exists(task_file):
        os.remove(task_file)
        await callback_query.message.edit_text(f"Задача '{task_id}' удалена.")
    else:
        await callback_query.answer("Задача не найдена.", show_alert=True)

def register_completed_handlers(dp: Dispatcher):
    dp.register_message_handler(show_completed_tasks, commands="completed_tasks")
    dp.register_callback_query_handler(completed_to_work, lambda c: c.data and c.data.startswith("completed_to_work_"))
    dp.register_callback_query_handler(completed_to_backlog, lambda c: c.data and c.data.startswith("completed_to_backlog_"))
    dp.register_callback_query_handler(completed_delete, lambda c: c.data and c.data.startswith("completed_delete_"))
