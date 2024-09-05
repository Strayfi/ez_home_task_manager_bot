from config import ADMIN_ID  
from aiogram import types
from users import toggle_user_access, get_access_button, load_users
from main import bot, dp

async def notify_admin_access_request(user: types.User):
    if user.id == ADMIN_ID:
        return
    
    keyboard = types.InlineKeyboardMarkup()
    button = get_access_button(user.id, user.username or "Unknown")
    keyboard.add(button)
    
    await bot.send_message(ADMIN_ID, f"Пользователь {user.username or 'Unknown'} просит доступ к боту.", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("toggle_access_"))
async def process_access_toggle(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split("_")[2]
    user_data = load_users().get(user_id, None)

    if user_data:
        new_access = toggle_user_access(user_id, not user_data['access'])
        response_text = f"Доступ пользователя {user_data['username']} {'разрешен' if new_access else 'запрещен'}."
        button = get_access_button(user_id, user_data['username'])
        keyboard = types.InlineKeyboardMarkup().add(button)
        await callback_query.message.edit_text(text=response_text, reply_markup=keyboard)
    else:
        await callback_query.answer("Пользователь не найден.", show_alert=True)

    await callback_query.answer()
