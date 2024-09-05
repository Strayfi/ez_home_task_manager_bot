import json
import os
from aiogram import types
from config import ADMIN_ID

USERS_FILE = 'data/users/users.json'

os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)

def load_users():
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)  # ensure_ascii=False сохраняет русские символы

def add_user(user: types.User):
    users = load_users()
    if str(user.id) not in users:
        users[str(user.id)] = {
            "user_id": user.id,
            "access": user.id == ADMIN_ID,
            "username": user.full_name or "Unknown",  
            "profile_link": f"https://t.me/{user.username}" if user.username else None
        }
        save_users(users)

def toggle_user_access(user_id, access):
    users = load_users()
    user_id = str(user_id)
    if user_id in users:
        users[user_id]['access'] = access
        save_users(users)
        return users[user_id]['access']
    return None

def get_access_button(user_id, username):
    users = load_users()
    user_id = str(user_id)
    current_access = users[user_id]['access']
    button_text = f"{'Запретить' if current_access else 'Разрешить'} доступ {username}"
    return types.InlineKeyboardButton(button_text, callback_data=f"toggle_access_{user_id}")

def get_users_keyboard():
    users = load_users()
    keyboard = types.InlineKeyboardMarkup()
    for user_id, user_data in users.items():
        access_status = "✅" if user_data["access"] else "❌"
        button_text = f"{user_data['username']} {access_status}"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=f"toggle_{user_id}"))
    return keyboard
