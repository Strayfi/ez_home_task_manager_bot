from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from users import load_users, save_users
from aiogram import types
from config import ADMIN_ID

class MainKeyboard:
    @staticmethod
    def admin_menu():
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        help_button = KeyboardButton("📋 Помощь")
        list_users_button = KeyboardButton("👥 Список пользователей")
        create_task_button = KeyboardButton("➕ Создать задачу")
        view_tasks_button = KeyboardButton("📋 Просмотреть задачи")
        calendar_button = KeyboardButton("📅 Календарь задач ()")
        completed_button = KeyboardButton("✅ Завершённые")
        backlog_button = KeyboardButton("📂 Беклог")
        keyboard.add(help_button, view_tasks_button)
        keyboard.add(create_task_button, backlog_button)
        keyboard.add(calendar_button, completed_button)
        keyboard.add(list_users_button)
        return keyboard

    @staticmethod
    def user_menu():
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        help_button = KeyboardButton("📋 Помощь")
        create_task_button = KeyboardButton("➕ Создать задачу")
        view_tasks_button = KeyboardButton("📋 Просмотреть задачи")
        calendar_button = KeyboardButton("📅 Календарь задач")
        completed_button = KeyboardButton("✅ Завершённые")
        backlog_button = KeyboardButton("📂 Беклог")
        keyboard.add(help_button, view_tasks_button)
        keyboard.add(create_task_button, backlog_button)
        keyboard.add(calendar_button, completed_button)
        return keyboard

class AccessMiddleware(BaseMiddleware):
    async def on_process_message(self, message: types.Message, data: dict):
        users = load_users()
        user_id = str(message.from_user.id)
        user_data = users.get(user_id)
        if user_id == str(ADMIN_ID):
            if user_data and not user_data.get("access", False):
                user_data["access"] = True
                save_users(users) 
            return 
        if user_data and not user_data.get("access", False):
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            check_status_button = types.KeyboardButton("Проверить статус")
            keyboard.add(check_status_button)
            await message.reply("Извините, ваш доступ к боту ограничен.", reply_markup=keyboard)
            raise CancelHandler()