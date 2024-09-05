from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage 
from aiogram.dispatcher.filters import Command
from config import API_TOKEN, ADMIN_ID
from users import add_user, load_users, toggle_user_access, get_users_keyboard, save_users
from access import MainKeyboard, AccessMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from board import create_task_start, register_task_handlers, task_title_entered, task_start_time_entered, task_duration_time_entered, task_description_entered, TaskCreation
from kcalendar import register_task_checker
from backlog import show_backlog_tasks, register_backlog_handlers
from active_tasks import register_active_tasks_handlers, show_active_tasks
from completed import register_completed_handlers, show_completed_tasks

bot = Bot(token=API_TOKEN)
storage = MemoryStorage() 
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(Command("start"))

async def send_welcome(message: types.Message):
    add_user(message.from_user)
    try:
        users = load_users()
    except Exception as e:
        await message.reply("Ошибка загрузки данных пользователей. Пожалуйста, попробуйте позже.")
        return

    user_data = users.get(str(message.from_user.id))

    if user_data and user_data['access']:
        if message.from_user.id == ADMIN_ID:
            keyboard = MainKeyboard.admin_menu()
        else:
            keyboard = MainKeyboard.user_menu()
        await message.reply(f"Добро пожаловать, {message.from_user.full_name}! Выберите действие:", reply_markup=keyboard)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        check_status_button = types.KeyboardButton("Проверить статус")
        keyboard.add(check_status_button)
        await message.reply("Запрос на доступ к данному боту отправлен администратору.", reply_markup=keyboard)
        if not user_data.get('request_sent'):
            try:
                user_name = message.from_user.username or message.from_user.full_name or "Неизвестный пользователь"
                admin_keyboard = InlineKeyboardMarkup()
                approve_button = InlineKeyboardButton("Разрешить", callback_data=f"approve_{message.from_user.id}")
                deny_button = InlineKeyboardButton("Запретить", callback_data=f"deny_{message.from_user.id}")
                admin_keyboard.add(approve_button, deny_button)
                
                await bot.send_message(ADMIN_ID, f"{user_name} просит доступ к боту.", reply_markup=admin_keyboard)
                
                user_data['request_sent'] = True
                save_users(users) 
            except Exception as e:
                await message.reply(f"Ошибка при отправке уведомления администратору: {str(e)}")

@dp.message_handler(lambda message: message.text == "Проверить статус")
async def handle_check_status(message: types.Message):
    users = load_users()
    user_data = users.get(str(message.from_user.id))
    
    if user_data:
        if user_data['access']:
            if message.from_user.id == ADMIN_ID:
                keyboard = MainKeyboard.admin_menu()
            else:
                keyboard = MainKeyboard.user_menu()
                
            await message.reply(
                f"Ваш доступ к боту: *разрешен*.\nДобро пожаловать, {message.from_user.full_name}! Выберите действие:",
                parse_mode=types.ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        else:
            await message.reply(
                f"Ваш доступ к боту: *запрещен*. Ожидайте решения администратора.",
                parse_mode=types.ParseMode.MARKDOWN
            )
    else:
        await message.reply("Вы не зарегистрированы в системе. Пожалуйста, попробуйте позже или свяжитесь с администратором.")

@dp.message_handler(lambda message: message.text == "➕ Создать задачу")
async def handle_create_task(message: types.Message):
    await create_task_start(message)

@dp.message_handler(lambda message: message.text == "📋 Помощь")
async def handle_help(message: types.Message):
    await send_help(message)

@dp.message_handler(lambda message: message.text == "📋 Просмотреть задачи")
async def handle_view_tasks(message: types.Message):
    await show_active_tasks(message)

@dp.message_handler(lambda message: message.text == "👥 Список пользователей")
async def handle_list_users(message: types.Message):
    await list_users(message)

@dp.message_handler(lambda message: message.text == "📂 Беклог")
async def handle_backlog(message: types.Message):
    await show_backlog_tasks(message)

@dp.message_handler(lambda message: message.text == "✅ Завершённые")
async def handle_completed_tasks(message: types.Message):
    await show_completed_tasks(message)

@dp.message_handler(Command("help"))
async def send_help(message: types.Message):
    help_text = (
        "📋 *Доступные команды и действия:*\n\n"
        "\\- *Помощь\\:* Показать это сообщение\\.\n"
        "\\- *Создать задачу\\:* Добавить новую задачу\\.\n"
        "\\- *Просмотреть задачи\\:* Посмотреть список ваших задач\\.\n"
        "\\- *Календарь задач\\:* Показать календарь задач\\.\n"
        "\\- *Завершённые\\:* Управление и просмотр завершёнными задачи\\.\n"
        "\\- *Беклог\\:* Управление задачами без даты и времени\\.\n"
    )
    if message.from_user.id == ADMIN_ID:
        help_text += (
            "\\- *Список пользователей\\:* Управление доступом пользователей\\.\n"
        )
    await message.reply(help_text, parse_mode=types.ParseMode.MARKDOWN_V2)

@dp.message_handler(Command("list_users"))
async def list_users(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        keyboard = get_users_keyboard()
        await message.reply("👥 Список пользователей:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("toggle_"))
async def process_access_toggle(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split("_")[1]
    users = load_users()
    user_data = users.get(user_id, None)
    if user_data:
        new_access = not user_data['access']
        toggle_user_access(user_id, new_access)
        updated_keyboard = get_users_keyboard()
        await callback_query.message.edit_reply_markup(reply_markup=updated_keyboard)
        await callback_query.answer(f"Доступ пользователя {user_data['username']} теперь {'разрешен' if new_access else 'запрещен'}.")
    else:
        await callback_query.answer("Пользователь не найден.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("approve_"))
async def process_approve_access(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split("_")[1]
    users = load_users()
    user_data = users.get(user_id, None)
    if user_data:
        user_data['access'] = True
        save_users(users)
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.answer(f"Доступ пользователя {user_data['username']} разрешен.")
    else:
        await callback_query.answer("Пользователь не найден.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("deny_"))
async def process_deny_access(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split("_")[1]
    users = load_users()
    user_data = users.get(user_id, None)
    if user_data:
        user_data['access'] = False
        save_users(users)
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.answer(f"Доступ пользователя {user_data['username']} запрещен.")
    else:
        await callback_query.answer("Пользователь не найден.", show_alert=True)

dp.register_message_handler(task_title_entered, state=TaskCreation.waiting_for_title)
dp.register_message_handler(task_start_time_entered, state=TaskCreation.waiting_for_start_time)
dp.register_message_handler(task_duration_time_entered, state=TaskCreation.waiting_for_time_duration)
dp.register_message_handler(task_description_entered, state=TaskCreation.waiting_for_description)
dp.middleware.setup(AccessMiddleware())

if __name__ == "__main__":
    register_task_handlers(dp)
    register_task_checker(dp)
    register_backlog_handlers(dp)
    register_active_tasks_handlers(dp)
    register_completed_handlers(dp)
    executor.start_polling(dp, skip_updates=True)