import json
from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram import Dispatcher
from config import ADMIN_ID

USERS_FILE = 'data/users.json'

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

async def list_users(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        users = load_users()
        if users:
            users_list = "\n".join([
                f"ID: {user_id}, Никнейм: @{user_data['username']}, "
                f"Доступ: {'Да' if user_data['access'] else 'Нет'}, "
                f"Профиль: {user_data['profile_link']}"
                for user_id, user_data in users.items()
            ])
            await message.reply(f"Список пользователей:\n{users_list}")
        else:
            await message.reply("Список пользователей пуст.")
    else:
        await message.reply("У вас нет прав для выполнения этой команды.")

def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(list_users, Command("list_users"))
