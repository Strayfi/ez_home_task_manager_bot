import os
import json
import calendar
from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
from access import MainKeyboard  
from config import ADMIN_ID  
from datetime import timedelta

TASKS_DIR = 'data/tasks/'
BACKLOG_DIR = 'data/backlog/'
COUNTERS_DIR = 'data/counters/'
MONTH_TRANSLATION = {
    "Январь": 1,
    "Февраль": 2,
    "Март": 3,
    "Апрель": 4,
    "Май": 5,
    "Июнь": 6,
    "Июль": 7,
    "Август": 8,
    "Сентябрь": 9,
    "Октябрь": 10,
    "Ноябрь": 11,
    "Декабрь": 12
}

class TaskCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_month_selection = State()  
    waiting_for_specific_month = State()  
    waiting_for_day_selection = State()  
    waiting_for_time_duration = State()
    waiting_for_start_time = State()
    waiting_for_description = State()
    waiting_for_status = State()

def load_task_counter(user_id):
    counter_file = os.path.join(COUNTERS_DIR, f"counter_{user_id}.json")
    if os.path.exists(counter_file):
        with open(counter_file, 'r', encoding='utf-8') as f:
            return json.load(f)['counter']
    return 0

def save_task_counter(user_id, counter):
    if not os.path.exists(COUNTERS_DIR):
        os.makedirs(COUNTERS_DIR)
    counter_file = os.path.join(COUNTERS_DIR, f"counter_{user_id}.json")
    with open(counter_file, 'w', encoding='utf-8') as f:
        json.dump({"counter": counter}, f, ensure_ascii=False)

def generate_task_id(user_id):
    counter = load_task_counter(user_id)
    counter += 1
    save_task_counter(user_id, counter)
    return counter

async def create_task_start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)
    
    await message.reply("Введите название задачи:", reply_markup=keyboard)
    await TaskCreation.waiting_for_title.set()

async def task_title_entered(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    
    await state.update_data(title=message.text)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)
    await message.reply("Введите описание задачи:", reply_markup=keyboard)
    await TaskCreation.waiting_for_description.set()

async def task_description_entered(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return

    await state.update_data(description=message.text)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    backlog_button = KeyboardButton("📥 В бэклог")
    in_work_button = KeyboardButton("🚀 В работу")
    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(backlog_button, in_work_button)
    keyboard.add(cancel_button)
    await message.reply("Выберите статус задачи:", reply_markup=keyboard)
    await TaskCreation.waiting_for_status.set()

async def task_status_entered(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    if message.text == "📥 В бэклог":
        await save_task_in_backlog(message, state)
        return
    if message.text == "🚀 В работу":
        user_data = await state.get_data()
        title = user_data['title']
        description = user_data['description']
        user_id = message.from_user.id
        task_id = generate_task_id(user_id)
        task_data = {
            "title": title,
            "description": description,
            "status": "in_work",
            "start_time": None,
            "end_time": None,
            "duration": None,
            "due_date": None,
            "end_date": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "task_id": task_id, 
            "notified_start": False,
            "notified_end": False
        }
        save_active_task(task_data)
        await state.update_data(task_id=task_id)
        await initiate_task_timing(message, state, task_data)

def generate_month_selection_keyboard():
    now = datetime.now()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if now.month < 12:
        current_month_button = KeyboardButton("Текущий месяц")
        next_month_button = KeyboardButton("Следующий месяц")
        keyboard.add(current_month_button, next_month_button)
    other_button = KeyboardButton("Другой")
    keyboard.add(other_button)
    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)
    return keyboard

async def month_selected(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    if message.text == "Текущий месяц":
        await state.update_data(month=datetime.now().month)
        await handle_day_selection(message, state)
    elif message.text == "Следующий месяц":
        await state.update_data(month=(datetime.now().month % 12) + 1)
        await handle_day_selection(message, state)
    elif message.text == "Другой":
        selected_year = datetime.now().year
        keyboard = generate_specific_month_keyboard(selected_year)
        await message.reply("Выберите конкретный месяц:", reply_markup=keyboard)
        await TaskCreation.waiting_for_specific_month.set()

async def specific_year_selected(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Выбор года отменен.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    try:
        selected_year = int(message.text)
        await state.update_data(year=selected_year)
        keyboard = generate_specific_month_keyboard(selected_year)
        await message.reply("Выберите конкретный месяц:", reply_markup=keyboard)
        await TaskCreation.waiting_for_specific_month.set()
    except ValueError:
        await message.reply("Ошибка: Некорректный ввод. Пожалуйста, выберите год из предложенных вариантов.")
        return

async def initiate_task_timing(message: types.Message, state: FSMContext, task_data):
    await state.update_data(task_data=task_data)
    keyboard = generate_month_selection_keyboard()
    await message.reply("Выберите месяц начала задачи:", reply_markup=keyboard)
    await TaskCreation.waiting_for_month_selection.set()

def generate_specific_month_keyboard(selected_year):
    now = datetime.now()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
              "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    for i, month in enumerate(months):
        if selected_year > now.year or (selected_year == now.year and i + 1 >= now.month):
            keyboard.add(KeyboardButton(f"{month} {selected_year}"))
    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)
    return keyboard

def save_active_task(task):
    TASKS_DIR = 'data/tasks/'  
    if not os.path.exists(TASKS_DIR):
        os.makedirs(TASKS_DIR)
    task_file = os.path.join(TASKS_DIR, f"task_{task['user_id']}_{task['task_id']}.json")
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=4, ensure_ascii=False)

async def specific_month_selected(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    if message.text == "Другой год":
        keyboard = generate_year_selection_keyboard()
        await message.reply("Выберите год:", reply_markup=keyboard)
        await TaskCreation.waiting_for_specific_month.set()
        return
    try:
        parts = message.text.split()
        if len(parts) == 2:
            selected_month = parts[0]
            selected_year = int(parts[1])
            if selected_month in MONTH_TRANSLATION:
                month_num = MONTH_TRANSLATION[selected_month]
            else:
                raise ValueError("Некорректный месяц")
            await state.update_data(month=month_num, year=selected_year)
            await handle_day_selection(message, state)
        else:
            await message.reply("Ошибка: Некорректный ввод. Пожалуйста, выберите месяц и год из предложенных вариантов.")
    except (ValueError, IndexError):
        await message.reply("Ошибка: Некорректный ввод. Пожалуйста, выберите месяц и год из предложенных вариантов.")
        return

def generate_year_selection_keyboard():
    now = datetime.now()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    current_year = now.year
    for year in range(current_year, current_year + 10):
        keyboard.add(KeyboardButton(str(year)))
    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)
    return keyboard

async def handle_day_selection(message: types.Message, state: FSMContext):
    data = await state.get_data()
    year = data.get("year", datetime.now().year)
    month = data["month"]

    days_in_month = calendar.monthrange(year, month)[1]
    days_keyboard = generate_days_keyboard(days_in_month, month, year)
    await message.reply("Выберите день:", reply_markup=days_keyboard)
    await TaskCreation.waiting_for_day_selection.set()

def generate_days_keyboard(days_in_month, selected_month, selected_year):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    today = datetime.today()

    row = []
    for day in range(1, days_in_month + 1):
        if selected_year == today.year and selected_month == today.month and day < today.day:
            continue 

        row.append(KeyboardButton(str(day)))
        if len(row) == 3:
            keyboard.add(*row)
            row = []

    if row:
        keyboard.add(*row)

    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)
    return keyboard

async def day_selected(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    try:
        day = int(message.text)
        await state.update_data(day=day)
        user_data = await state.get_data()
        keyboard = generate_start_time_keyboard(year=user_data.get('year'), month=user_data.get('month'), day=day)
        await message.reply("Введите время начала задачи:", reply_markup=keyboard)
        await TaskCreation.waiting_for_start_time.set()
    except ValueError:
        await message.reply("Пожалуйста, выберите день из предложенных вариантов.")
        return

async def task_start_time_entered(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    try:
        start_time = datetime.strptime(message.text, "%H:%M").time()
        await state.update_data(start_time=start_time.strftime("%H:%M"))
    except ValueError:
        await message.reply("Неверный формат времени. Пожалуйста, введите время в формате 'ЧЧ:ММ' или выберите его из списка.")
        return

    keyboard = generate_time_duration_keyboard()
    await message.reply("Введите время, которое будет затрачено на выполнение задачи:", reply_markup=keyboard)
    await TaskCreation.waiting_for_time_duration.set()

async def task_duration_time_entered(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.reply("Создание задачи отменено.", reply_markup=types.ReplyKeyboardRemove())
        await send_main_menu(message)
        return
    try:
        datetime.strptime(message.text, "%H:%M")
        await state.update_data(duration=message.text)
    except ValueError:
        await message.reply("Неверный формат времени. Пожалуйста, введите время в формате 'ЧЧ:ММ' или выберите его из списка.")
        return
    user_data = await state.get_data()
    task_id = user_data.get('task_id')
    user_id = message.from_user.id
    task_file = os.path.join('data/tasks', f"task_{user_id}_{task_id}.json")
    if os.path.exists(task_file):
        with open(task_file, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
    else:
        await message.reply("Ошибка: задача не найдена.")
        return
    year = user_data.get('year', datetime.now().year)
    month = user_data.get('month')
    day = user_data.get('day')
    task_data.update({
        "start_time": f"{user_data['start_time']}:00",
        "duration": user_data['duration'],
        "end_time": calculate_end_time(user_data['start_time'], user_data['duration']),
        "due_date": f"{year}-{month:02d}-{day:02d}",
        "end_date": calculate_end_date(user_data['start_time'], user_data['duration'], year, month, day)
    })
    save_active_task(task_data)
    await message.reply(f"Задача '{task_data['title']}' обновлена и установлена в работу.", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()
    await send_main_menu(message)

def calculate_end_time(start_time, duration):
    start_hour, start_minute = map(int, start_time.split(":"))
    duration_hour, duration_minute = map(int, duration.split(":"))
    end_datetime = datetime(1, 1, 1, start_hour, start_minute) + timedelta(hours=duration_hour, minutes=duration_minute)
    return end_datetime.strftime("%H:%M:%S")

def calculate_end_date(start_time, duration, year, month, day):
    start_hour, start_minute = map(int, start_time.split(":"))
    duration_hour, duration_minute = map(int, duration.split(":"))
    start_datetime = datetime(year, month, day, start_hour, start_minute)
    end_datetime = start_datetime + timedelta(hours=duration_hour, minutes=duration_minute)
    return end_datetime.strftime("%Y-%m-%d")

async def save_task_in_backlog(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    title = user_data['title']
    description = user_data['description']
    user_id = message.from_user.id
    status = "backlog"
    task_id = generate_task_id(user_id)
    
    task_data = {
        "title": title,
        "description": description,
        "status": status,
        "start_time": None,
        "end_time": None,
        "duration": None,
        "due_date": None,
        "end_date": None,
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "user_id": user_id,
        "task_id": task_id,
        "notified_start": False,
        "notified_end": False
    }
    if not os.path.exists(BACKLOG_DIR):
        os.makedirs(BACKLOG_DIR)
    task_file = os.path.join(BACKLOG_DIR, f"task_{user_id}_{task_id}.json")
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task_data, f, indent=4, ensure_ascii=False)
    await message.reply("Задача создана и добавлена в бэклог.", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()
    await send_main_menu(message)

def generate_start_time_keyboard(year=None, month=None, day=None):
    now = datetime.now()
    selected_date = datetime(year, month, day) if year and month and day else None
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    time_intervals = []
    if selected_date and selected_date.date() > now.date():
        for hour in range(0, 24):
            time_intervals.append(f"{hour:02d}:00")
            time_intervals.append(f"{hour:02d}:30")
    else:
        for hour in range(now.hour, 24):
            if hour == now.hour:
                if now.minute < 30:
                    time_intervals.append(f"{hour:02d}:30")
                continue
            time_intervals.append(f"{hour:02d}:00")
            time_intervals.append(f"{hour:02d}:30")
    row = []
    for time in time_intervals:
        row.append(KeyboardButton(time))
        if len(row) == 3:
            keyboard.add(*row)
            row = []
    if row:
        keyboard.add(*row)
    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)
    return keyboard

def generate_time_duration_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    duration_intervals = [f"{hour:02d}:{minute:02d}" for hour in range(0, 24) for minute in (0, 30)]
    
    row = []
    for duration in duration_intervals:
        row.append(KeyboardButton(duration))
        if len(row) == 3:
            keyboard.add(*row)
            row = []

    if row:
        keyboard.add(*row)

    cancel_button = KeyboardButton("❌ Отмена")
    keyboard.add(cancel_button)

    return keyboard

async def send_main_menu(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        keyboard = MainKeyboard.admin_menu()  
    else:
        keyboard = MainKeyboard.user_menu()  
    await message.reply("Вы вернулись в главное меню.", reply_markup=keyboard)

def register_task_handlers(dp: Dispatcher):
    dp.register_message_handler(create_task_start, commands="create_task", state="*")
    dp.register_message_handler(task_title_entered, state=TaskCreation.waiting_for_title)
    dp.register_message_handler(task_description_entered, state=TaskCreation.waiting_for_description)
    dp.register_message_handler(task_status_entered, state=TaskCreation.waiting_for_status)
    dp.register_message_handler(month_selected, state=TaskCreation.waiting_for_month_selection)
    dp.register_message_handler(specific_month_selected, state=TaskCreation.waiting_for_specific_month)
    dp.register_message_handler(day_selected, state=TaskCreation.waiting_for_day_selection)
    dp.register_message_handler(task_start_time_entered, state=TaskCreation.waiting_for_start_time)
    dp.register_message_handler(task_duration_time_entered, state=TaskCreation.waiting_for_time_duration)
