import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
import sqlite3
import threading
from datetime import datetime, timedelta
import time
from time import sleep
import re
import logging
import atexit
import calendar
from telebot.apihelper import ApiException
import hashlib


from PIL import Image, ImageDraw, ImageFont
import imageio
import os
from datetime import datetime, timedelta
import math

# config.py
BOT_TOKEN = '7323942446:AAEMq1ckcO2jK70DTOMUpPbMVtjqwyta0_g'
PAYMENT_TOKEN = '284685063:TEST:ZWY0M2ZhYjZmZjM0'  # Замените на ваш тестовый токен Stripe от Telegram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
bot.timeout = 30





"""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def test_hashing():
    test_password = "Bastion1@"
    hashed = hash_password(test_password)
    print(f"Тестовый пароль: {test_password}")
    print(f"Хеш тестового пароля: {hashed}")
    print(f"Длина хеша: {len(hashed)} символов")
    print(f"Используемый алгоритм: SHA-256")

# Вызовем тестовую функцию
test_hashing()

# Теперь давайте проверим ваш реальный пароль
your_password = "ВашПарольЗдесь"  # Замените на ваш реальный пароль
your_hash = hash_password(your_password)
print(f"\nВаш пароль: {your_password}")
print(f"Хеш вашего пароля: {your_hash}")



"""







ADMIN_IDS = [1413637959, 920711549]

ADMIN_PASSWORD_HASH = "4b921f81eac536d771630abc9ec353302256e1a17e4a9bde4d1ab8c40873c52c"

conn = sqlite3.connect('school_bot.db', check_same_thread=False)
cursor = conn.cursor()

MAX_PASSWORD_ATTEMPTS = 5
password_attempts = {}

# Создание таблиц
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, grade TEXT, notifications INTEGER DEFAULT 1)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS bookings
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                   subject TEXT, date TEXT, time TEXT, paid INTEGER DEFAULT 0)''')

conn.commit()

user_data = {}

DISCORD_LINK = "https://discord.gg/your-discord-invite-link"
PAYMENT_DETAILS = "1234 5678 9012 3456"
Prepod_LINK = "https://t.me/mosmikhailova"


def get_lesson_price(grade):
    if 1 <= int(grade) <= 8:
        return 1500
    elif 9 <= int(grade) <= 11:
        return 2500
    else:
        return 0


def create_connection():
    return sqlite3.connect('school_bot.db', check_same_thread=False)    #Подключение к БД

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Записаться на занятие"))
    markup.row(KeyboardButton("Мои записи"))
    markup.row(KeyboardButton("Оплатить занятие"))
    markup.row(KeyboardButton("Отменить запись"))
    markup.row(KeyboardButton("Связь с преподавателем"))
    markup.row(KeyboardButton("Настройки"))
    return markup

def settings_menu():    #Меню настроек
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Discord", callback_data="discord"))
    markup.add(InlineKeyboardButton("Реквизиты для оплаты", callback_data="payment"))
    markup.add(InlineKeyboardButton("Уведомления", callback_data="notifications"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Записи на сегодня"))
    markup.add(KeyboardButton("Просмотр записей"))
    markup.add(KeyboardButton("Изменить запись"))
    markup.add(KeyboardButton("Отменить запись"))
    markup.add(KeyboardButton("Проверка оплаты"))
    markup.add(KeyboardButton("Внести оплату"))
    markup.add(KeyboardButton("Распечатать календарь"))
    markup.add(KeyboardButton("Написать сообщение"))
    markup.add(KeyboardButton("Скачать базу данных"))
    markup.add(KeyboardButton("Вернуть базу данных"))
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



@bot.message_handler(func=lambda message: message.text == "Оплатить занятие")
def pay_for_lesson(message):
    user_id = message.from_user.id
    cursor.execute("""
        SELECT id, subject, date, time, paid
        FROM bookings 
        WHERE user_id = ?
        ORDER BY date DESC, time DESC
    """, (user_id,))
    all_bookings = cursor.fetchall()
    
    if not all_bookings:
        bot.send_message(message.chat.id, "У вас нет занятий для оплаты.")
        return

    markup = InlineKeyboardMarkup()
    for booking in all_bookings:
        booking_id, subject, date, time, paid = booking
        status = "Оплачено" if paid else "Не оплачено"
        button_text = f"{subject} - {date} {time} - {status}"
        callback_data = f"pay_{booking_id}"
        markup.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    bot.send_message(message.chat.id, "Выберите занятие для оплаты:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment_selection(call):
    booking_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    
    cursor.execute("SELECT subject, date, time, paid FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()
    
    if booking:
        subject, date, time, paid = booking
        if paid:
            bot.answer_callback_query(call.id, "Это занятие уже оплачено.")
            return
        
        cursor.execute("SELECT grade FROM users WHERE id = ?", (user_id,))
        user_grade = cursor.fetchone()[0]
        price = get_lesson_price(user_grade)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Да", callback_data=f"confirm_payment_{booking_id}"))
        markup.add(InlineKeyboardButton("Нет", callback_data=f"pay_{booking_id}"))
        markup.add(InlineKeyboardButton("Отмена", callback_data="cancel_payment"))
        
        bot.edit_message_text(
            f"Вы подтверждаете, что перевели {price} руб. за занятие {subject} {date} в {time} на карту {PAYMENT_DETAILS}?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "Ошибка: занятие не найдено.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_payment_"))
def confirm_payment(call):
    booking_id = int(call.data.split("_")[2])
    user_id = call.from_user.id
    
    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    user_name = cursor.fetchone()[0]
    
    cursor.execute("SELECT subject, date, time FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()
    
    if booking:
        subject, date, time = booking
        
        # Отправка сообщения админу
        admin_markup = InlineKeyboardMarkup()
        admin_markup.add(InlineKeyboardButton("Подтверждаю", callback_data=f"admin_confirm_{booking_id}"))
        admin_markup.add(InlineKeyboardButton("Не подтверждаю", callback_data=f"admin_reject_{booking_id}"))
        admin_markup.add(InlineKeyboardButton("Ответить позже", callback_data=f"admin_later_{booking_id}"))
        
        for admin_id in ADMIN_IDS:
            bot.send_message(
                admin_id,
                f"Ученик {user_name} подтверждает оплату за занятие:\n"
                f"{subject} {date} в {time}\n"
                f"Подтвердите получение оплаты:",
                reply_markup=admin_markup
            )
        
        bot.edit_message_text(
            "Информация передана преподавателю. Ожидайте подтверждения.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "Ошибка: занятие не найдено.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_payment_action(call):
    action, booking_id = call.data.split("_")[1:]
    booking_id = int(booking_id)
    
    cursor.execute("SELECT user_id, subject, date, time FROM bookings WHERE id = ?", (booking_id,))
    booking = cursor.fetchone()
    
    if booking:
        user_id, subject, date, time = booking
        
        if action == "confirm":
            cursor.execute("UPDATE bookings SET paid = 1 WHERE id = ?", (booking_id,))
            conn.commit()
            bot.send_message(user_id, f"Оплата за занятие {subject} {date} в {time} подтверждена преподавателем.")
            bot.answer_callback_query(call.id, "Оплата подтверждена.")
        
        elif action == "reject":
            bot.send_message(user_id, f"Преподаватель не получил оплату за занятие {subject} {date} в {time}. Пожалуйста, проверьте еще раз.")
            bot.answer_callback_query(call.id, "Оплата отклонена.")
        
        elif action == "later":
            # Напоминание на следующий рабочий день
            next_work_day = datetime.now() + timedelta(days=1)
            while next_work_day.weekday() >= 5:  # 5 - суббота, 6 - воскресенье
                next_work_day += timedelta(days=1)
            
            bot.answer_callback_query(call.id, f"Напоминание отложено до {next_work_day.strftime('%d.%m.%Y')}.")
            
            # Здесь можно добавить логику для создания отложенного напоминания
            # Например, сохранить информацию в базе данных и создать задачу для отправки напоминания в нужное время
    
    else:
        bot.answer_callback_query(call.id, "Ошибка: занятие не найдено.")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_payment")
def cancel_payment(call):
    bot.edit_message_text(
        "Оплата отменена. Вы вернулись в главное меню.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu()
    )




@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    booking_id = int(message.successful_payment.invoice_payload.split(':')[1])
    logger.info(f"Обработка успешного платежа для booking_id={booking_id}")
    
    cursor.execute("UPDATE bookings SET paid = 1 WHERE id = ?", (booking_id,))
    conn.commit()
    
    # Проверим, обновился ли статус
    cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    updated_booking = cursor.fetchone()
    logger.info(f"Обновленное бронирование: {updated_booking}")
    
    bot.send_message(message.chat.id, "Спасибо за оплату! Ваше занятие подтверждено.")



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
        cursor.execute("INSERT INTO bookings (user_id, subject, date, time, paid) VALUES (?, ?, ?, ?, 0)",
                       (user_id, subject, date, time))
        conn.commit()
        
        # Получим id только что созданного бронирования
        cursor.execute("SELECT last_insert_rowid()")
        new_booking_id = cursor.fetchone()[0]
        
        logger.info(f"Создано новое бронирование: id={new_booking_id}, user_id={user_id}, subject={subject}, date={date}, time={time}")
        
        return True
    else:
        logger.warning(f"Попытка забронировать недоступное время: user_id={user_id}, date={date}, time={time}")
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
        bot.reply_to(message, "Добро пожаловать! Давайте начнем регистрацию. Введите ваше ФИО:")
        bot.register_next_step_handler(message, process_name_step)


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













# Функция для хеширования пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Функция для проверки пароля
def check_password(user_id, password):
    hashed_password = hash_password(password)
    # Сравниваем с предварительно вычисленным хешем
    return hashed_password == ADMIN_PASSWORD_HASH

@bot.message_handler(func=lambda message: message.text == "Скачать базу данных" and message.from_user.id in ADMIN_IDS)
def send_database(message):
    user_id = message.from_user.id
    if user_id not in password_attempts:
        password_attempts[user_id] = 0
    
    if password_attempts[user_id] >= MAX_PASSWORD_ATTEMPTS:
        bot.reply_to(message, "Превышено максимальное количество попыток. Доступ заблокирован.")
        return

    bot.reply_to(message, "Введите пароль для скачивания базы данных:")
    bot.register_next_step_handler(message, check_password_and_send_database)

def check_password_and_send_database(message):
    user_id = message.from_user.id
    password = message.text

    if check_password(user_id, password):
        password_attempts[user_id] = 0  # Сбрасываем счетчик попыток
        try:
            with open('school_bot.db', 'rb') as db_file:
                bot.send_document(message.chat.id, db_file, caption="База данных школьного бота")
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка при отправке базы данных: {str(e)}")
    else:
        password_attempts[user_id] += 1
        remaining_attempts = MAX_PASSWORD_ATTEMPTS - password_attempts[user_id]
        if remaining_attempts > 0:
            bot.reply_to(message, f"Неверный пароль. Осталось попыток: {remaining_attempts}")
            bot.register_next_step_handler(message, check_password_and_send_database)
        else:
            bot.reply_to(message, "Превышено максимальное количество попыток. Доступ заблокирован.")





@bot.message_handler(func=lambda message: message.text == "Скачать базу данных" and message.from_user.id in ADMIN_IDS)
def download_database(message):
    user_id = message.from_user.id
    if user_id not in password_attempts:
        password_attempts[user_id] = 0
    
    if password_attempts[user_id] >= MAX_PASSWORD_ATTEMPTS:
        bot.reply_to(message, "Превышено максимальное количество попыток. Доступ заблокирован.")
        return

    bot.reply_to(message, "Введите пароль:")
    bot.register_next_step_handler(message, check_password_and_download)


@bot.message_handler(func=lambda message: message.text == "Вернуть базу данных" and message.from_user.id in ADMIN_IDS)
def check_password_and_download(message):
    user_id = message.from_user.id
    password = message.text

    if check_password(user_id, password):
        password_attempts[user_id] = 0  # Сбрасываем счетчик попыток
        bot.reply_to(message, "Я ожидаю, отправьте файл в формате .db")
        bot.register_next_step_handler(message, save_new_database)
    else:
        password_attempts[user_id] += 1
        remaining_attempts = MAX_PASSWORD_ATTEMPTS - password_attempts[user_id]
        if remaining_attempts > 0:
            bot.reply_to(message, f"Неверный пароль. Осталось попыток: {remaining_attempts}")
            bot.register_next_step_handler(message, check_password_and_download)
        else:
            bot.reply_to(message, "Превышено максимальное количество попыток. Доступ заблокирован.")

def save_new_database(message):
    if message.document and message.document.file_name.endswith('.db'):
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open('school_bot.db', 'wb') as new_file:
                new_file.write(downloaded_file)
            bot.reply_to(message, "База данных успешно обновлена.")
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка при сохранении базы данных: {str(e)}")
    else:
        bot.reply_to(message, "Пожалуйста, отправьте файл базы данных в формате .db")

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

@bot.message_handler(func=lambda message: message.text == "Проверка оплаты" and message.from_user.id in ADMIN_IDS)
def check_payments(message):
    bot.reply_to(message, "Выберите период для проверки оплаты:", reply_markup=payment_period_menu())

def payment_period_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Сегодня", callback_data="payment_check_today"))
    markup.add(InlineKeyboardButton("Текущая неделя", callback_data="payment_check_week"))
    markup.add(InlineKeyboardButton("Текущий месяц", callback_data="payment_check_month"))
    markup.add(InlineKeyboardButton("Прошлый месяц", callback_data="payment_check_lastmonth"))
    markup.add(InlineKeyboardButton("Все время", callback_data="payment_check_all"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_check_"))
def handle_payment_check(call):
    period = call.data.split("_")[-1]  # Изменено здесь
    today = datetime.now().date()
    
    print(f"Выбранный период: {period}")  # Отладочная информация
    
    if period == "today":
        start_date = today
        end_date = today
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == "month":
        start_date = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
    elif period == "lastmonth":
        # Находим первый день текущего месяца
        first_day_of_current_month = today.replace(day=1)
        # Находим первый день предыдущего месяца
        first_day_of_last_month = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
        # Находим последний день предыдущего месяца
        _, last_day = calendar.monthrange(first_day_of_last_month.year, first_day_of_last_month.month)
        start_date = first_day_of_last_month
        end_date = first_day_of_last_month.replace(day=last_day)
    elif period == "all":
        start_date = datetime(2000, 1, 1).date()  # Используем более реалистичную начальную дату
        end_date = today
    else:
        bot.answer_callback_query(call.id, "Неверный период")
        print(f"Неверный период: {period}")  # Отладочная информация
        return

    print(f"Выбранный период: с {start_date} по {end_date}")  # Отладочная информация

    generate_payment_report(call.message.chat.id, start_date, end_date)
    bot.answer_callback_query(call.id, f"Отчет сгенерирован за период: {start_date} - {end_date}")




def generate_payment_report(chat_id, start_date, end_date):
    cursor.execute("""
        SELECT bookings.id, users.name, bookings.subject, bookings.date, bookings.time, bookings.paid, users.grade
        FROM bookings
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.date BETWEEN ? AND ?
        ORDER BY bookings.date, bookings.time
    """, (start_date, end_date))
    
    bookings = cursor.fetchall()
    
    if not bookings:
        bot.send_message(chat_id, "Нет записей за выбранный период.")
        return

    response = f"Отчет об оплате за период с {start_date} по {end_date}:\n\n"
    total_paid = 0
    total_unpaid = 0

    for booking in bookings:
        booking_id, name, subject, date, time, paid, grade = booking
        price = get_lesson_price(grade)
        status = "Оплачено" if paid else "Не оплачено"
        response += f"ID: {booking_id} - {name} - {subject} - {date} {time} - {status} - {price} руб.\n"
        if paid:
            total_paid += price
        else:
            total_unpaid += price

    response += f"\nИтого оплачено: {total_paid} руб.\n"
    response += f"Итого не оплачено: {total_unpaid} руб.\n"
    response += f"Общая сумма: {total_paid + total_unpaid} руб."

    # Разделяем сообщение на части, если оно слишком длинное
    max_message_length = 4096
    for i in range(0, len(response), max_message_length):
        bot.send_message(chat_id, response[i:i+max_message_length])

@bot.message_handler(func=lambda message: message.text == "Внести оплату" and message.from_user.id in ADMIN_IDS)
def admin_mark_payment(message):
    bot.reply_to(message, "Введите ID записи, для которой хотите внести оплату:")
    bot.register_next_step_handler(message, process_payment_marking)

def process_payment_marking(message):
    try:
        booking_id = int(message.text)
        cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        booking = cursor.fetchone()
        if booking:
            cursor.execute("UPDATE bookings SET paid = 1 WHERE id = ?", (booking_id,))
            conn.commit()
            bot.reply_to(message, f"Оплата для записи с ID {booking_id} успешно внесена.")
        else:
            bot.reply_to(message, "Запись с таким ID не найдена.")
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите корректный ID записи (целое число).")

@bot.message_handler(func=lambda message: message.text == "Просмотр записей" and message.from_user.id in ADMIN_IDS)
def admin_view_bookings(message):
    now = datetime.now()
    today = now.date()

    # Получаем все активные (будущие) записи
    cursor.execute("""
        SELECT bookings.id, users.name, bookings.subject, bookings.date, bookings.time 
        FROM bookings 
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.date >= ? OR (bookings.date = ? AND bookings.time > ?)
        ORDER BY bookings.date, bookings.time
    """, (today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), now.strftime('%H:%M')))
    active_bookings = cursor.fetchall()

    # Получаем последние 10 прошедших записей
    cursor.execute("""
        SELECT bookings.id, users.name, bookings.subject, bookings.date, bookings.time 
        FROM bookings 
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.date < ? OR (bookings.date = ? AND bookings.time <= ?)
        ORDER BY bookings.date DESC, bookings.time DESC
        LIMIT 10
    """, (today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), now.strftime('%H:%M')))
    past_bookings = cursor.fetchall()

    response = ""

    if active_bookings:
        response += "Активные записи:\n\n"
        for booking in active_bookings:
            booking_id, name, subject, date, time = booking
            formatted_date = format_date(date)
            response += f"ID: {booking_id} - {name} - {subject} - {formatted_date} в {time}\n"
    else:
        response += "Нет активных записей.\n"

    if past_bookings:
        response += "\nПоследние 10 прошедших записей:\n\n"
        for booking in past_bookings:
            booking_id, name, subject, date, time = booking
            formatted_date = format_date(date)
            response += f"ID: {booking_id} - {name} - {subject} - {formatted_date} в {time}\n"
    else:
        response += "\nНет прошедших записей."

    # Разделяем сообщение на части, если оно слишком длинное
    max_message_length = 4096
    for i in range(0, len(response), max_message_length):
        bot.send_message(message.chat.id, response[i:i+max_message_length])


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








def generate_calendar_image(year, month):
    # Создаем соединение с базой данных
    conn = sqlite3.connect('school_bot.db')
    cursor = conn.cursor()

    # Получаем все записи на выбранный месяц
    cursor.execute("""
        SELECT date, 
               GROUP_CONCAT(time || ' ' || users.name || ' ' || bookings.subject || ' ' || 
                            CASE WHEN bookings.paid = 1 THEN 'ОПЛ' ELSE 'ДОЛГ' END, '|') as bookings,
               SUM(CASE WHEN bookings.paid = 1 THEN 
                        CASE 
                            WHEN CAST(users.grade AS INTEGER) BETWEEN 1 AND 8 THEN 1500
                            WHEN CAST(users.grade AS INTEGER) BETWEEN 9 AND 11 THEN 2500
                            ELSE 0
                        END
                    ELSE 0 END) as earned,
               SUM(CASE WHEN bookings.paid = 0 THEN 
                        CASE 
                            WHEN CAST(users.grade AS INTEGER) BETWEEN 1 AND 8 THEN 1500
                            WHEN CAST(users.grade AS INTEGER) BETWEEN 9 AND 11 THEN 2500
                            ELSE 0
                        END
                    ELSE 0 END) as unpaid,
               COUNT(CASE WHEN bookings.paid = 0 THEN 1 END) as unpaid_lessons
        FROM bookings 
        JOIN users ON bookings.user_id = users.id
        WHERE strftime('%Y-%m', date) = ?
        GROUP BY date
    """, (f"{year}-{month:02d}",))
    bookings_data = cursor.fetchall()
    bookings = {row[0]: row[1] for row in bookings_data}
    
    # Подсчет общей суммы заработанных денег и неоплаченных занятий
    total_earned = sum(row[2] for row in bookings_data)
    total_unpaid = sum(row[3] for row in bookings_data)
    total_unpaid_lessons = sum(row[4] for row in bookings_data)

    # Получаем информацию о неоплаченных занятиях
    cursor.execute("""
        SELECT users.name, users.phone, bookings.date, bookings.time, bookings.subject
        FROM bookings 
        JOIN users ON bookings.user_id = users.id
        WHERE strftime('%Y-%m', date) = ? AND bookings.paid = 0
        ORDER BY bookings.date, bookings.time
    """, (f"{year}-{month:02d}",))
    unpaid_lessons = cursor.fetchall()

    # Получаем информацию об оплаченных занятиях
    cursor.execute("""
        SELECT users.name, users.phone, bookings.date, bookings.time, bookings.subject
        FROM bookings 
        JOIN users ON bookings.user_id = users.id
        WHERE strftime('%Y-%m', date) = ? AND bookings.paid = 1
        ORDER BY bookings.date, bookings.time
    """, (f"{year}-{month:02d}",))
    paid_lessons = cursor.fetchall()

    # Создаем календарь
    cal = calendar.monthcalendar(year, month)

    # Создаем изображение
    width, height = 2920, 2800  # Увеличиваем высоту изображения
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # Загружаем шрифты
    try:
        font = ImageFont.truetype("arial.ttf", 36)
        small_font = ImageFont.truetype("arial.ttf", 24)
        tiny_font = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        tiny_font = ImageFont.load_default()

    # Рисуем заголовок
    header = f"{calendar.month_name[month]} {year}"
    draw.text((width//2, 10), header, fill='black', font=font, anchor='mt')

    # Рисуем дни недели
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    cell_width = width // 7
    for i, day in enumerate(days):
        draw.text((i*cell_width + cell_width//2, 50), day, fill='black', font=small_font, anchor='mt')

    # Рисуем календарь
    calendar_height = 1830  # Фиксированная высота для календаря
    cell_height = calendar_height // 6  # Максимум 6 недель в месяце
    for week_num, week in enumerate(cal):
        for day_num, day in enumerate(week):
            if day != 0:
                x = day_num * cell_width + 60
                y = week_num * cell_height + 100
                date_str = f"{year}-{month:02d}-{day:02d}"

                # Определяем цвет ячейки
                if date_str in bookings:
                    cell_color = 'orange'
                elif datetime.strptime(date_str, '%Y-%m-%d').weekday() == 6:  # Воскресенье
                    cell_color = 'lightgray'
                else:
                    cell_color = 'lightgreen'

                # Рисуем ячейку
                draw.rectangle([x, y, x+cell_width, y+cell_height], fill=cell_color, outline='black')
                draw.text((x+5, y+5), str(day), fill='black', font=small_font)
                
                if date_str in bookings:
                    # Разбиваем текст на строки
                    bookings_text = bookings[date_str].split('|')
                    for i, booking in enumerate(bookings_text):
                        if i < 15:  # Ограничиваем до 15 строк
                            y_offset = y + 30 + i * 20
                            draw.text((x+5, y_offset), booking, fill='black', font=tiny_font)
                    
                    if len(bookings_text) > 15:
                        draw.text((x+5, y+cell_height-20), f"...и еще {len(bookings_text)-15}", fill='black', font=tiny_font)

     # Рисуем информацию о финансах
    finance_info = f"Заработано: {total_earned} руб. | Не оплачено: {total_unpaid} руб. ({total_unpaid_lessons} занятий)"
    draw.text((width//2, calendar_height + 120), finance_info, fill='black', font=small_font, anchor='ms')

    # Рисуем информацию об оплаченных и неоплаченных занятиях
    left_column_x = 20
    right_column_x = width // 2 + 20
    y = calendar_height + 150

    # Неоплаченные занятия (слева, красным цветом)
    draw.text((left_column_x, y), "Неоплаченные занятия:", fill='red', font=small_font)
    y += 30
    for lesson in unpaid_lessons:
        name, phone, date, time, subject = lesson
        lesson_info = f"{date} {time} - {name} ({phone}) - {subject}"
        draw.text((left_column_x, y), lesson_info, fill='red', font=tiny_font)
        y += 20
        if y > height - 20:  # Если информация не помещается, прерываем цикл
            draw.text((left_column_x, y), "... и другие", fill='red', font=tiny_font)
            break

    # Сбрасываем y для правой колонки
    y = calendar_height + 150

    # Оплаченные занятия (справа, зеленым цветом)
    draw.text((right_column_x, y), "Оплаченные занятия:", fill='green', font=small_font)
    y += 30
    for lesson in paid_lessons:
        name, phone, date, time, subject = lesson
        lesson_info = f"{date} {time} - {name} ({phone}) - {subject}"
        draw.text((right_column_x, y), lesson_info, fill='green', font=tiny_font)
        y += 20
        if y > height - 20:  # Если информация не помещается, прерываем цикл
            draw.text((right_column_x, y), "... и другие", fill='green', font=tiny_font)
            break

    # Сохраняем изображение
    image_path = f"calendar_{year}_{month}.png"
    image.save(image_path)
    
    return image_path










@bot.message_handler(func=lambda message: message.text == "Распечатать календарь" and message.from_user.id in ADMIN_IDS)
def send_calendar(message):
    if message.from_user.id in ADMIN_IDS:
        now = datetime.now()
        image_path = generate_calendar_image(now.year, now.month)
        
        # Отправляем изображение как фото
        with open(image_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"Календарь на {now.strftime('%B %Y')}")
        
        # Отправляем изображение как файл
        with open(image_path, 'rb') as file:
            bot.send_document(message.chat.id, file, caption="Календарь в виде файла")
        
        # Удаляем файл после отправки
        os.remove(image_path)
    else:
        bot.reply_to(message, "У вас нет доступа к этой команде.")


@bot.message_handler(func=lambda message: message.text == "Написать сообщение" and message.from_user.id in ADMIN_IDS)
def write_message_to_all(message):
    bot.reply_to(message, "Введите сообщение, которое нужно отправить всем пользователям:")
    bot.register_next_step_handler(message, send_message_to_all)

def send_message_to_all(message):
    admin_message = message.text
    cursor.execute("SELECT id FROM users")
    all_users = cursor.fetchall()
    
    success_count = 0
    fail_count = 0
    
    for user in all_users:
        try:
            bot.send_message(user[0], admin_message)
            success_count += 1
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user[0]}: {e}")
            fail_count += 1
    
    bot.reply_to(message, f"Сообщение отправлено {success_count} пользователям. Не удалось отправить {fail_count} пользователям.")


















































@bot.message_handler(func=lambda message: message.text == "Записаться на занятие")
def book_lesson(message):
    bot.send_message(message.chat.id, "Выберите предмет:", reply_markup=subject_menu())


@bot.message_handler(func=lambda message: message.text == "Мои записи")
def show_bookings(message):
    user_id = message.from_user.id
    now = datetime.now()
    
    # Получение всех записей пользователя
    cursor.execute("""
        SELECT id, subject, date, time, paid
        FROM bookings 
        WHERE user_id = ?
        ORDER BY date, time
    """, (user_id,))
    
    bookings = cursor.fetchall()
    
    if bookings:
        future_bookings = []
        past_bookings = []
        for booking in bookings:
            booking_id, subject, date, time, paid = booking
            booking_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            if booking_datetime > now:
                future_bookings.append(booking)
            else:
                past_bookings.append(booking)
        
        response = "Ваши будущие записи:\n\n"
        for booking in future_bookings:
            booking_id, subject, date, time, paid = booking
            formatted_date = format_date(date)
            payment_status = "Оплачено" if paid else "Не оплачено"
            response += f"ID: {booking_id} - {subject} - {formatted_date} в {time} - {payment_status}\n"
        
        if past_bookings:
            response += "\nВаши прошедшие записи:\n\n"
            for booking in past_bookings[-5:]:  # Показываем только последние 5 прошедших записей
                booking_id, subject, date, time, paid = booking
                formatted_date = format_date(date)
                payment_status = "Оплачено" if paid else "Не оплачено"
                response += f"ID: {booking_id} - {subject} - {formatted_date} в {time} - {payment_status}\n"
        
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "У вас нет записей.")


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







@bot.message_handler(func=lambda message: message.text == "Оплатить занятие")
def pay_for_lesson(message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, subject, date, time FROM bookings WHERE user_id = ? AND paid = 0", (user_id,))
    unpaid_bookings = cursor.fetchall()
    
    if not unpaid_bookings:
        bot.send_message(message.chat.id, "У вас нет неоплаченных занятий.")
        return

    logger.info(f"Неоплаченные бронирования для user_id={user_id}: {unpaid_bookings}")

    markup = InlineKeyboardMarkup()
    for booking in unpaid_bookings:
        booking_id, subject, date, time = booking
        button_text = f"{subject} - {date} {time}"
        callback_data = f"pay_{booking_id}"
        markup.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    bot.send_message(message.chat.id, "Выберите занятие для оплаты:", reply_markup=markup)





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

@bot.message_handler(func=lambda message: message.text == "Записаться на занятие")
def book_lesson(message):
    bot.send_message(message.chat.id, "Выберите предмет:", reply_markup=subject_menu())


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
