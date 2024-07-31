import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import threading
from datetime import datetime, timedelta
import time
from time import sleep  # Явно импортируем sleep
import re
import logging
import atexit
import calendar
from telebot.apihelper import ApiException

# config.py
BOT_TOKEN = '7345016752:AAGVrKutq4R5YMI8FYteU0j9y9m7sCDxTMY'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
bot.timeout = 30

ADMIN_IDS = [1413637959, 920711549]

conn = sqlite3.connect('school_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, grade TEXT, notifications INTEGER DEFAULT 1)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS bookings
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                   subject TEXT, date TEXT, time TEXT)''')

conn.commit()

user_data = {}

DISCORD_LINK = "https://discord.gg/PeyHRJMgXT"
PAYMENT_DETAILS = "4276 3802 3952 6044"
Prepod_LINK = "https://t.me/mosmikhailova"

def create_connection():
    return sqlite3.connect('school_bot.db', check_same_thread=False)    #Подключение к БД

def main_menu():    #Главное меню
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Записаться на занятие"))
    markup.add(KeyboardButton("Мои записи"))
    markup.add(KeyboardButton("Отменить запись"))
    markup.add(KeyboardButton("Связь с преподавателем"))
    markup.add(KeyboardButton("Настройки"))
    return markup

def settings_menu():    #Меню настроек
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Discord", callback_data="discord"))
    markup.add(InlineKeyboardButton("Реквизиты для оплаты", callback_data="payment"))
    markup.add(InlineKeyboardButton("Уведомления", callback_data="notifications"))
    return markup

def admin_menu():   #Меню Админа
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Записи на сегодня"))
    markup.add(KeyboardButton("Просмотр записей"))
    markup.add(KeyboardButton("Изменить запись"))
    markup.add(KeyboardButton("Отменить запись"))
    markup.add(KeyboardButton("Главное меню"))
    return markup

def subject_menu(): #Меню выбора предметов
    markup = InlineKeyboardMarkup()
    subjects = ["Русский язык", "Литература", "Общая грамотность", "Консультация"]
    for subject in subjects:
        markup.add(InlineKeyboardButton(subject, callback_data=f"subject_{subject}"))
    return markup

def generate_calendar(year, month):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data="ignore"))
    
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.row(*[InlineKeyboardButton(day, callback_data="ignore") for day in days])
    
    month_calendar = calendar.monthcalendar(year, month)
    today = datetime.now().date()
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                date = datetime(year, month, day).date()
                if date > today:
                    if date.weekday() == 6:  # Воскресенье
                        row.append(InlineKeyboardButton("X", callback_data=f"sunday_{year}-{month:02d}-{day:02d}"))
                    else:
                        row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}-{month:02d}-{day:02d}"))
                else:
                    row.append(InlineKeyboardButton(" ", callback_data="ignore"))
        markup.row(*row)
    
    markup.row(
        InlineKeyboardButton("◀️", callback_data=f"prev_month_{year}_{month}"),
        InlineKeyboardButton("▶️", callback_data=f"next_month_{year}_{month}")
    )
    return markup


def send_notification(user_id, subject, date, time):
    message = f"Напоминание: у вас занятие по предмету {subject} сегодня в {time}."
    try:
        bot.send_message(user_id, message)
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")

def time_menu(date):
    markup = InlineKeyboardMarkup()
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    day_of_week = date_obj.weekday()

    if day_of_week == 4:  # Пятница
        start_time = datetime.strptime("09:00", "%H:%M")
        end_time = datetime.strptime("20:00", "%H:%M")
        interval = timedelta(minutes=60)
    elif day_of_week != 6:  # Все дни, кроме воскресенья
        start_time = datetime.strptime("09:30", "%H:%M")
        end_time = datetime.strptime("20:00", "%H:%M")
        interval = timedelta(minutes=90)
    else:  # Воскресенье
        return markup  # Пустое меню для воскресенья

    current_time = start_time

    while current_time <= end_time:
        time_str = current_time.strftime("%H:%M")
        if is_time_available(date, time_str):
            markup.add(InlineKeyboardButton(time_str, callback_data=f"time_{time_str}"))
        current_time += interval

    return markup

def is_time_available(date, time):
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    time_obj = datetime.strptime(time, "%H:%M").time()
    day_of_week = date_obj.weekday()

    if day_of_week == 6:  # Воскресенье
        return False

    if day_of_week == 4:  # Пятница
        if time_obj < datetime.strptime("09:00", "%H:%M").time() or time_obj > datetime.strptime("21:00", "%H:%M").time():
            return False
        # Проверка, что время соответствует 60-минутным интервалам для пятницы
        minutes_since_start = (time_obj.hour * 60 + time_obj.minute) - (9 * 60)
        if minutes_since_start % 60 != 0:
            return False
    else:
        if time_obj < datetime.strptime("09:30", "%H:%M").time() or time_obj > datetime.strptime("21:30", "%H:%M").time():
            return False
        # Проверка, что время соответствует 90-минутным интервалам для остальных дней
        minutes_since_start = (time_obj.hour * 60 + time_obj.minute) - (9 * 60 + 30)
        if minutes_since_start % 90 != 0:
            return False

    cursor.execute("SELECT * FROM bookings WHERE date = ? AND time = ?", (date, time))
    return cursor.fetchone() is None



def save_booking(user_id, subject, date, time):
    if is_time_available(date, time):
        cursor.execute("INSERT INTO bookings (user_id, subject, date, time) VALUES (?, ?, ?, ?)",
                       (user_id, subject, date, time))
        conn.commit()
        return True
    else:
        return False

def get_user_bookings(user_id):
    today = datetime.now().date()
    cursor.execute("""
        SELECT id, subject, date, time 
        FROM bookings 
        WHERE user_id = ? AND date >= ? 
        ORDER BY date, time
    """, (user_id, today.strftime('%Y-%m-%d')))
    return cursor.fetchall()

def format_date(date_str):
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    if date == today:
        return "Сегодня"
    elif date == today + timedelta(days=1):
        return "Завтра"
    else:
        return date.strftime("%d.%m.%Y")

def cancel_booking(booking_id):
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()

def is_valid_name(name):
    # Проверяем, что имя состоит из 2 или 3 слов (имя и фамилия обязательно, отчество опционально)
    parts = name.split()
    if len(parts) < 2 or len(parts) > 3:
        return False
    
    # Проверяем каждую часть имени
    for part in parts:
        # Каждая часть должна начинаться с заглавной буквы и содержать только буквы
        if not re.match(r'^[А-ЯЁ][а-яё]+(-[А-ЯЁ][а-яё]+)?$', part):
            return False
    
    return True

def is_valid_phone(phone):
    return bool(re.match(r'^\+?7\d{10}$', phone))

def is_valid_grade(grade):
    return grade.isdigit() and 1 <= int(grade) <= 11

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone():
        bot.reply_to(message, "Добро пожаловать! Выберите действие:", reply_markup=main_menu())
    else:
        bot.reply_to(message, "Добро пожаловать! Для начала работы с ботом, пожалуйста, зарегистрируйтесь, используя команду /register")

@bot.message_handler(func=lambda message: message.text == "Настройки")
def settings(message):
    bot.send_message(message.chat.id, "Выберите настройку:", reply_markup=settings_menu())


@bot.message_handler(commands=['register'])
def start_registration(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone():
        bot.reply_to(message, "Вы уже зарегистрированы.")
    else:
        bot.reply_to(message, "Давайте начнем регистрацию. Введите ваше ФИО:")
        bot.register_next_step_handler(message, process_name_step)

def process_name_step(message):
    name = message.text.strip()
    if is_valid_name(name):
        user_id = message.from_user.id
        user_data[user_id] = {'name': name}
        bot.reply_to(message, "Отлично! Теперь введите ваш номер телефона в формате +7XXXXXXXXXX:")
        bot.register_next_step_handler(message, process_phone_step)
    else:
        bot.reply_to(message, "Некорректное ФИО. Пожалуйста, введите ваше полное имя (Фамилия Имя Отчество) на русском языке. Каждое слово должно начинаться с заглавной буквы. Пример: Иванов Иван Иванович. Попробуйте еще раз:")
        bot.register_next_step_handler(message, process_name_step)

def process_phone_step(message):
    phone = message.text
    user_id = message.from_user.id
    if is_valid_phone(phone):
        user_data[user_id]['phone'] = phone
        bot.reply_to(message, "Отлично! Теперь введите ваш класс (с 1 по 11):")
        bot.register_next_step_handler(message, process_grade_step)
    else:
        bot.reply_to(message, "Некорректный номер телефона. Пожалуйста, используйте формат +7XXXXXXXXXX. Попробуйте еще раз:")
        bot.register_next_step_handler(message, process_phone_step)

def process_grade_step(message):
    grade = message.text
    user_id = message.from_user.id
    if is_valid_grade(grade):
        user_data[user_id]['grade'] = grade
        save_user_data(user_id)
        bot.reply_to(message, "Регистрация завершена успешно!", reply_markup=main_menu())
    else:
        bot.reply_to(message, "Некорректный класс. Пожалуйста, введите число от 1 до 11. Попробуйте еще раз:")
        bot.register_next_step_handler(message, process_grade_step)

def save_user_data(user_id):
    name = user_data[user_id]['name']
    phone = user_data[user_id]['phone']
    grade = user_data[user_id]['grade']
    cursor.execute("INSERT OR REPLACE INTO users (id, name, phone, grade, notifications) VALUES (?, ?, ?, ?, 1)",
                   (user_id, name, phone, grade))
    conn.commit()
    del user_data[user_id]








#**********************************************************************************************************
    #
    #
    #
    #



@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "Добро пожаловать в панель администратора. Выберите действие:", reply_markup=admin_menu())
    else:
        bot.reply_to(message, "У вас нет доступа к панели администратора.")

@bot.message_handler(func=lambda message: message.text == "Просмотр записей" and message.from_user.id in ADMIN_IDS)
def admin_view_bookings(message):
    today = datetime.now().date()
    cursor.execute("""
        SELECT bookings.id, users.name, bookings.subject, bookings.date, bookings.time 
        FROM bookings 
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.date >= ? 
        ORDER BY bookings.date, bookings.time
    """, (today.strftime('%Y-%m-%d'),))
    bookings = cursor.fetchall()
    
    if bookings:
        response = "Все активные записи:\n\n"
        for booking in bookings:
            booking_id, name, subject, date, time = booking
            formatted_date = format_date(date)
            response += f"ID: {booking_id} - {name} - {subject} - {formatted_date} в {time}\n"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "Нет активных записей.")

@bot.message_handler(func=lambda message: message.text == "Изменить запись" and message.from_user.id in ADMIN_IDS)
def admin_modify_booking(message):
    bot.reply_to(message, "Введите ID записи, которую хотите изменить:")
    bot.register_next_step_handler(message, process_booking_id_for_modification)

def process_booking_id_for_modification(message):
    booking_id = message.text
    cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()
    if booking:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Изменить дату", callback_data=f"admin_change_date_{booking_id}"))
        markup.add(InlineKeyboardButton("Изменить время", callback_data=f"admin_change_time_{booking_id}"))
        markup.add(InlineKeyboardButton("Изменить предмет", callback_data=f"admin_change_subject_{booking_id}"))
        bot.reply_to(message, "Выберите, что хотите изменить:", reply_markup=markup)
    else:
        bot.reply_to(message, "Запись с таким ID не найдена.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_change_"))
def admin_change_booking(call):
    action, booking_id = call.data.split("_")[2:]
    if action == "date":
        bot.edit_message_text("Введите новую дату в формате YYYY-MM-DD:", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_new_date, booking_id)
    elif action == "time":
        bot.edit_message_text("Введите новое время в формате HH:MM:", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_new_time, booking_id)
    elif action == "subject":
        bot.edit_message_text("Введите новый предмет:", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_new_subject, booking_id)



def process_new_date(message, booking_id):
    new_date = message.text
    cursor.execute("UPDATE bookings SET date = ? WHERE id = ?", (new_date, booking_id))
    conn.commit()
    bot.reply_to(message, "Дата успешно изменена.")

def process_new_time(message, booking_id):
    new_time = message.text
    cursor.execute("UPDATE bookings SET time = ? WHERE id = ?", (new_time, booking_id))
    conn.commit()
    bot.reply_to(message, "Время успешно изменено.")

def process_new_subject(message, booking_id):
    new_subject = message.text
    cursor.execute("UPDATE bookings SET subject = ? WHERE id = ?", (new_subject, booking_id))
    conn.commit()
    bot.reply_to(message, "Предмет успешно изменен.")

@bot.message_handler(func=lambda message: message.text == "Записи на сегодня" and message.from_user.id in ADMIN_IDS)
def admin_today_notifications(message):
    today = datetime.now().date()
    cursor.execute("""
        SELECT bookings.id, users.name, bookings.subject, bookings.time 
        FROM bookings 
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.date = ?
        ORDER BY bookings.time
    """, (today.strftime('%Y-%m-%d'),))
    bookings = cursor.fetchall()
    
    if bookings:
        response = "Записи на сегодня:\n\n"
        for booking in bookings:
            booking_id, name, subject, time = booking
            response += f"ID: {booking_id} - {name} - {subject} в {time}\n"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "На сегодня нет записей.")

@bot.message_handler(func=lambda message: message.text == "Отменить запись" and message.from_user.id in ADMIN_IDS)
def admin_cancel_booking(message):
    bot.reply_to(message, "Введите ID записи, которую хотите отменить:")
    bot.register_next_step_handler(message, process_booking_id_for_cancellation)

def process_booking_id_for_cancellation(message):
    booking_id = message.text
    cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()
    if booking:
        cancel_booking(booking_id)
        bot.reply_to(message, "Запись успешно отменена.")
    else:
        bot.reply_to(message, "Запись с таким ID не найдена.")


def is_valid_date(date_string):
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False
    
def execute_sql(sql, params=()):
    try:
        cursor.execute(sql, params)
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Ошибка базы данных: {e}")
        conn.rollback()


def bot_polling():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except ApiException as e:
            print(f"ApiException: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

def is_valid_time(time_string):
    try:
        datetime.strptime(time_string, "%H:%M")
        return True
    except ValueError:
        return False

def send_admin_notifications():
    # Создаем отдельное соединение для этого потока
    local_conn = create_connection()
    local_cursor = local_conn.cursor()

    while True:
        now = datetime.now()
        today = now.date()
        
        # Проверяем, отправляли ли мы уже уведомления сегодня
        if not hasattr(send_admin_notifications, "last_notification_date") or send_admin_notifications.last_notification_date < today:
            local_cursor.execute("""
                SELECT bookings.id, users.name, bookings.subject, bookings.time 
                FROM bookings 
                JOIN users ON bookings.user_id = users.id
                WHERE bookings.date = ?
            """, (today.strftime('%Y-%m-%d'),))
            bookings = local_cursor.fetchall()
            
            if bookings:
                notification = "Записи на сегодня:\n\n"
                for booking in bookings:
                    booking_id, name, subject, time = booking
                    notification += f"ID: {booking_id} - {name} - {subject} в {time}\n"
                
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(admin_id, notification)
                    except Exception as e:
                        print(f"Ошибка при отправке уведомления администратору {admin_id}: {e}")
            
            # Обновляем дату последнего уведомления
            send_admin_notifications.last_notification_date = today
        
        # Вычисляем время до следующей проверки
        next_check = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        time_to_wait = (next_check - now).total_seconds()
        
        # Ждем до следующей проверки, но не более часа за раз
        sleep(min(3600, time_to_wait))  # Используем sleep вместо time.sleep

    # Закрываем локальное соединение при завершении потока
    local_conn.close()

# Запускаем поток для отправки уведомлений администраторам
admin_notification_thread = threading.Thread(target=send_admin_notifications)
admin_notification_thread.daemon = True
admin_notification_thread.start()


    #
    #
    #
    #

#**********************************************************************************************************











@bot.message_handler(func=lambda message: message.text == "Записаться на занятие")
def book_lesson(message):
    bot.send_message(message.chat.id, "Выберите предмет:", reply_markup=subject_menu())


@bot.message_handler(func=lambda message: message.text == "Мои записи")
def show_bookings(message):
    user_id = message.from_user.id
    now = datetime.now()
    
    # Удаление прошедших записей
    cursor.execute("""
        DELETE FROM bookings
        WHERE user_id = ? AND (date < ? OR (date = ? AND time <= ?))
    """, (user_id, now.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'), now.strftime('%H:%M')))
    conn.commit()
    
    # Получение актуальных записей
    cursor.execute("""
        SELECT id, subject, date, time 
        FROM bookings 
        WHERE user_id = ? AND (date > ? OR (date = ? AND time > ?))
        ORDER BY date, time
    """, (user_id, now.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'), now.strftime('%H:%M')))
    
    bookings = cursor.fetchall()
    
    if bookings:
        response = "Ваши активные записи:\n\n"
        for booking in bookings:
            booking_id, subject, date, time = booking
            formatted_date = format_date(date)
            response += f"ID: {booking_id} - {subject} - {formatted_date} в {time}\n"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "У вас нет активных записей.")

@bot.message_handler(func=lambda message: message.text == "Отменить запись")
def cancel_booking_request(message):
    bookings = get_user_bookings(message.from_user.id)
    today = datetime.now().date()
    future_bookings = [b for b in bookings if datetime.strptime(b[2], "%Y-%m-%d").date() > today]
    
    if future_bookings:
        markup = InlineKeyboardMarkup()
        for booking in future_bookings:
            booking_id, subject, date, time = booking
            formatted_date = format_date(date)
            markup.add(InlineKeyboardButton(f"{subject} - {formatted_date} в {time}", 
                                            callback_data=f"cancel_{booking_id}"))
        bot.send_message(message.chat.id, "Выберите запись для отмены:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "У вас нет активных записей для отмены на будущие даты.")

@bot.message_handler(func=lambda message: message.text == "Discord")
def send_discord_link(message):
    bot.send_message(message.chat.id, f"Вот ссылка на наш Discord сервер: {DISCORD_LINK}")


@bot.message_handler(func=lambda message: message.text == "Связь с преподавателем")
def send_discord_link(message):
    bot.send_message(message.chat.id, f"Ссылка на преподавателя: {Prepod_LINK}")

@bot.message_handler(func=lambda message: message.text == "Реквизиты для оплаты")
def send_payment_details(message):
    bot.send_message(message.chat.id, f"Номер карты для оплаты: {PAYMENT_DETAILS}")

@bot.message_handler(func=lambda message: message.text == "Уведомления")
def notification_settings(message):
    user_id = message.from_user.id
    cursor.execute("SELECT notifications FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    current_status = result[0] if result else 1

    markup = InlineKeyboardMarkup()
    if current_status == 1:
        markup.add(InlineKeyboardButton("Отключить уведомления", callback_data="toggle_notifications"))
        status_text = "включены"
    else:
        markup.add(InlineKeyboardButton("Включить уведомления", callback_data="toggle_notifications"))
        status_text = "отключены"

    bot.send_message(message.chat.id, f"Уведомления сейчас {status_text}. Что вы хотите сделать?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data.startswith("subject_"):
        subject = call.data.split("_")[1]
        user_data[user_id] = {"subject": subject}
        now = datetime.now()
        bot.edit_message_text("Выберите дату:", call.message.chat.id, call.message.message_id,
                              reply_markup=generate_calendar(now.year, now.month))
    
    elif call.data.startswith("date_"):
        if user_id not in user_data:
            bot.answer_callback_query(call.id, "Произошла ошибка. Пожалуйста, начните процесс записи заново.")
            return
        date = call.data.split("_")[1]
        user_data[user_id]["date"] = date
        bot.edit_message_text("Выберите время:", call.message.chat.id, call.message.message_id,
                              reply_markup=time_menu(date))
        
    elif call.data.startswith("sunday_"):
        bot.answer_callback_query(call.id, "Извините, но воскресенье - выходной день. Пожалуйста, выберите другой день.", show_alert=True)
    
    elif call.data.startswith("time_"):
        if user_id not in user_data or "subject" not in user_data[user_id] or "date" not in user_data[user_id]:
            bot.answer_callback_query(call.id, "Произошла ошибка. Пожалуйста, начните процесс записи заново.")
            return
        time = call.data.split("_")[1]
        subject = user_data[user_id]["subject"]
        date = user_data[user_id]["date"]
        if save_booking(user_id, subject, date, time):
            bot.answer_callback_query(call.id, "Запись успешно создана!")
            bot.edit_message_text(f"Вы записаны на {subject} {date} в {time}", call.message.chat.id, call.message.message_id)
            del user_data[user_id]  # Очищаем данные пользователя после успешной записи
        else:
            bot.answer_callback_query(call.id, "К сожалению, это время уже занято. Пожалуйста, выберите другое время.")

    
    elif call.data.startswith("prev_month_") or call.data.startswith("next_month_"):
        year, month = map(int, call.data.split("_")[2:])
        if call.data.startswith("prev_month_"):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        else:
            month += 1
            if month == 13:
                month = 1
                year += 1
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=generate_calendar(year, month))
    
    elif call.data.startswith("cancel_"):
        booking_id = int(call.data.split("_")[1])
        cursor.execute("SELECT date FROM bookings WHERE id = ?", (booking_id,))
        result = cursor.fetchone()
        if result:
            booking_date = result[0]
            if datetime.strptime(booking_date, "%Y-%m-%d").date() > datetime.now().date():
                cancel_booking(booking_id)
                bot.answer_callback_query(call.id, "Запись успешно отменена!")
                bot.edit_message_text("Запись отменена.", call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "Нельзя отменить запись на сегодня или прошедшие даты.")
        else:
            bot.answer_callback_query(call.id, "Запись не найдена.")
    
    elif call.data == "toggle_notifications":
        cursor.execute("SELECT notifications FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        current_status = result[0] if result else 1

        new_status = 1 - current_status  # Переключаем статус
        cursor.execute("UPDATE users SET notifications = ? WHERE id = ?", (new_status, user_id))
        conn.commit()

        status_text = "включены" if new_status == 1 else "отключены"
        bot.answer_callback_query(call.id, f"Уведомления {status_text}")
        bot.edit_message_text(f"Уведомления теперь {status_text}.", call.message.chat.id, call.message.message_id)

    elif call.data == "discord":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"Вот ссылка на наш Discord сервер: {DISCORD_LINK}")
    
    elif call.data == "payment":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"Номер карты для оплаты: {PAYMENT_DETAILS}")
    
    elif call.data == "notifications":
        bot.answer_callback_query(call.id)
        notification_settings(call.message)












#**********************************************************************************************************


    #
    #
    #
    #




@bot.message_handler(func=lambda message: message.text == "Главное меню" and message.from_user.id in ADMIN_IDS)
def admin_to_user_main_menu(message):
    bot.reply_to(message, "Вы вернулись в главное меню пользователя.", reply_markup=main_menu())


@bot.message_handler(func=lambda message: message.text == "Уведомления")
def notification_settings(message):
    user_id = message.from_user.id
    cursor.execute("SELECT notifications FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    current_status = result[0] if result else 1

    markup = InlineKeyboardMarkup()
    if current_status == 1:
        markup.add(InlineKeyboardButton("Отключить уведомления", callback_data="toggle_notifications"))
        status_text = "включены"
    else:
        markup.add(InlineKeyboardButton("Включить уведомления", callback_data="toggle_notifications"))
        status_text = "отключены"

    bot.send_message(message.chat.id, f"Уведомления сейчас {status_text}. Что вы хотите сделать?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data.startswith("subject_"):
        subject = call.data.split("_")[1]
        user_data[user_id] = {"subject": subject}
        now = datetime.now()
        bot.edit_message_text("Выберите дату:", call.message.chat.id, call.message.message_id,
                              reply_markup=generate_calendar(now.year, now.month))
    
    elif call.data.startswith("date_"):
        if user_id not in user_data:
            bot.answer_callback_query(call.id, "Произошла ошибка. Пожалуйста, начните процесс записи заново.")
            return
        date = call.data.split("_")[1]
        user_data[user_id]["date"] = date
        bot.edit_message_text("Выберите время:", call.message.chat.id, call.message.message_id,
                              reply_markup=time_menu(date))
    
    elif call.data.startswith("time_"):
        if user_id not in user_data or "subject" not in user_data[user_id] or "date" not in user_data[user_id]:
            bot.answer_callback_query(call.id, "Произошла ошибка. Пожалуйста, начните процесс записи заново.")
            return
        time = call.data.split("_")[1]
        subject = user_data[user_id]["subject"]
        date = user_data[user_id]["date"]
        save_booking(user_id, subject, date, time)
        bot.answer_callback_query(call.id, "Запись успешно создана!")
        bot.edit_message_text(f"Вы записаны на {subject} {date} в {time}", call.message.chat.id, call.message.message_id)
        del user_data[user_id]  # Очищаем данные пользователя после успешной записи
    
    elif call.data.startswith("prev_month_") or call.data.startswith("next_month_"):
        year, month = map(int, call.data.split("_")[2:])
        if call.data.startswith("prev_month_"):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        else:
            month += 1
            if month == 13:
                month = 1
                year += 1
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=generate_calendar(year, month))
    
    elif call.data.startswith("cancel_"):
        booking_id = int(call.data.split("_")[1])
        cursor.execute("SELECT date FROM bookings WHERE id = ?", (booking_id,))
        result = cursor.fetchone()
        if result:
            booking_date = result[0]
            if datetime.strptime(booking_date, "%Y-%m-%d").date() > datetime.now().date():
                cancel_booking(booking_id)
                bot.answer_callback_query(call.id, "Запись успешно отменена!")
                bot.edit_message_text("Запись отменена.", call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "Нельзя отменить запись на сегодня или прошедшие даты.")
        else:
            bot.answer_callback_query(call.id, "Запись не найдена.")
    
    elif call.data == "toggle_notifications":
        cursor.execute("SELECT notifications FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        current_status = result[0] if result else 1

        new_status = 1 - current_status  # Переключаем статус
        cursor.execute("UPDATE users SET notifications = ? WHERE id = ?", (new_status, user_id))
        conn.commit()

        status_text = "включены" if new_status == 1 else "отключены"
        bot.answer_callback_query(call.id, f"Уведомления {status_text}")
        bot.edit_message_text(f"Уведомления теперь {status_text}.", call.message.chat.id, call.message.message_id)

    elif call.data == "discord":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"Вот ссылка на наш Discord сервер: {DISCORD_LINK}")
    
    elif call.data == "payment":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"Номер карты для оплаты: {PAYMENT_DETAILS}")
    
    elif call.data == "notifications":
        bot.answer_callback_query(call.id)
        notification_settings(call.message)



def send_notification(user_id, subject, date, time):
    message = f"Напоминание: у вас занятие по предмету {subject} сегодня в {time}."
    try:
        bot.send_message(user_id, message)
    except Exception as e:
        print(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")

def check_and_send_notifications():
    local_conn = create_connection()
    local_cursor = local_conn.cursor()
    while True:
        now = datetime.now()
        today = now.date()
        
        # Отправка уведомлений в 7:00
        if now.hour == 6 and now.minute == 0:
            cursor.execute("""
                SELECT bookings.user_id, bookings.subject, bookings.time
                FROM bookings
                JOIN users ON bookings.user_id = users.id
                WHERE users.notifications = 1
                AND bookings.date = ?
            """, (today.strftime('%Y-%m-%d'),))
            
            today_bookings = cursor.fetchall()
            for user_id, subject, booking_time in today_bookings:
                send_notification(user_id, subject, today, booking_time)
        
        # Отправка уведомлений за 30 минут до занятия
        thirty_minutes_later = now + timedelta(minutes=30)
        cursor.execute("""
            SELECT bookings.user_id, bookings.subject, bookings.time
            FROM bookings
            JOIN users ON bookings.user_id = users.id
            WHERE users.notifications = 1
            AND bookings.date = ? AND bookings.time = ?
        """, (today.strftime('%Y-%m-%d'), thirty_minutes_later.strftime('%H:%M')))
        
        upcoming_bookings = cursor.fetchall()
        for user_id, subject, booking_time in upcoming_bookings:
            message = f"Напоминание: у вас занятие по предмету {subject} через 30 минут (в {booking_time})."
            try:
                bot.send_message(user_id, message)
            except Exception as e:
                print(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
        
        time.sleep(60)  # Проверяем каждую минуту
    local_conn.close()




    #
    #
    #
    #







#**********************************************************************************************************










# Запускаем поток для проверки и отправки уведомлений
notification_thread = threading.Thread(target=check_and_send_notifications)
notification_thread.daemon = True
notification_thread.start()

# Запуск бота
if __name__ == "__main__":
    bot_polling()
    
@atexit.register
def close_connection():
    conn.close()
    logger.info("Соединение с базой данных закрыто")
