"""
Galochka-napominalochka - Telegram бот для управления заметками с функциями:
- Регистрация пользователей
- Создание заметок (с дедлайном и без)
- Просмотр и удаление заметок
- Ежедневные напоминания с фото NASA
- Напоминания за день до дедлайна
"""

import telebot
import csv
import os
from telebot import types
import datetime
import time
import schedule
import requests
import threading

# Инициализация бота с использованием переменной окружения для токена
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    # print("Ошибка: Не найден токен телеграм-бота в переменных окружения.")
    exit()
bot = telebot.TeleBot(token)

# API ключ для сервиса NASA (в реальном проекте лучше вынести в переменные окружения)
NASA_API_KEY = "XIvrocqXsocigfch2H8fHPVnZgSsgy1RnIbPgH8m"

# Словарь для хранения данных пользователей во время регистрации
user_registration = {}

class Registration:
    """Класс для обработки процесса регистрации пользователей"""
    
    def __init__(self):
        self.name = ""  # Имя пользователя
        self.age = 0    # Возраст пользователя

    def get_name(self, message):
        """Метод для получения имени пользователя"""
        self.name = message.text
        # Запрашиваем возраст после получения имени
        bot.send_message(message.chat.id, "Сколько тебе лет?")
        bot.register_next_step_handler(message, self.get_age)

    def get_age(self, message):
        """Метод для получения возраста с валидацией ввода"""
        try:
            self.age = int(message.text)
            # Создаем кнопки для подтверждения данных
            keyboard = types.InlineKeyboardMarkup()
            key_yes = types.InlineKeyboardButton(text="Да", callback_data="yes")
            keyboard.add(key_yes)
            key_no = types.InlineKeyboardButton(text="Нет", callback_data="no")
            keyboard.add(key_no)

            question = f"Тебе {self.age} лет, тебя зовут {self.name}?"
            bot.send_message(message.chat.id, question, reply_markup=keyboard)
        except ValueError:
            # Обработка нечислового ввода возраста
            bot.send_message(
                message.chat.id,
                f"Прошу прощения, я не понимаю 🥹 \nНапиши, пожалуйста, цифрами.",
            )
            bot.register_next_step_handler(message, self.get_age)

    def save_to_file(self, chat_id):
        """Сохранение данных пользователя в CSV файл"""
        with open("users.csv", mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([chat_id, self.name, self.age])


class Note:
    """Базовый класс для заметок"""
    
    def __init__(self, chat_id, text):
        self.chat_id = chat_id  # ID чата пользователя
        self.text = text        # Текст заметки

    def save_to_file(self):
        """Абстрактный метод для сохранения заметки (должен быть реализован в подклассах)"""
        raise NotImplementedError(
            "Метод save_to_file должен быть переопределён в подклассе"
        )


class NoteWithDeadline(Note):
    """Класс для заметок с дедлайном (наследуется от Note)"""
    
    def __init__(self, chat_id, text, deadline):
        super().__init__(chat_id, text)
        self.deadline = deadline  # Срок выполнения заметки
        # Генерация уникального ID на основе текущего времени
        self.note_id = f"dd_{int(time.time())}"

    def save_to_file(self):
        """Сохранение заметки с дедлайном в CSV файл"""
        with open("notes_dd.csv", mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [self.chat_id, self.text, self.deadline, self.note_id]
            )


class NoteWithoutDeadline(Note):
    """Класс для заметок без дедлайна (наследуется от Note)"""
    
    def __init__(self, chat_id, text):
        super().__init__(chat_id, text)
        # Генерация уникального ID на основе текущего времени
        self.note_id = f"wo_{int(time.time())}"

    def save_to_file(self):
        """Сохранение заметки без дедлайна в CSV файл"""
        with open("notes_wo_dd.csv", mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [self.chat_id, self.text, self.note_id]
            )


# Константа с именем файла для зарегистрированных пользователей
REGISTERED_USERS_FILE = "users.csv"

def get_nasa_image():
    """
    Получение изображения дня от NASA API
    
    Returns:
        str: URL изображения или None, если получить не удалось
    """
    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "url" in data and data["media_type"] == "image":
            return data["url"]
    return None


def send_daily_reminders():
    """Функция для отправки ежедневных уведомлений всем зарегистрированным пользователям"""
    try:
        # Чтение списка зарегистрированных пользователей
        with open(REGISTERED_USERS_FILE, "r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                chat_id = row[0]

                # Получение изображения дня от NASA
                image_url = get_nasa_image()
                if image_url:
                    # Получение списка задач пользователя
                    tasks = get_tasks_for_user(chat_id)

                    # Формирование сообщения с задачами
                    task_message = "Не забудь выполнить сегодняшние задачи:\n" + tasks

                    # Отправка сообщения с изображением
                    bot.send_photo(int(chat_id), image_url, caption=task_message)
                else:
                    # Если изображение недоступно
                    bot.send_message(
                        int(chat_id), "Сегодняшнее изображение недоступно."
                    )
    except FileNotFoundError:
        pass
    except Exception as e:
        pass


# Настройка ежедневного напоминания на 10:00
schedule.every().day.at("10:00").do(send_daily_reminders)


def get_tasks_for_user(chat_id):
    """
    Получение списка задач для конкретного пользователя
    
    Args:
        chat_id (int): ID чата пользователя
        
    Returns:
        str: Форматированный список задач или сообщение об их отсутствии
    """
    tasks = []

    # Чтение задач с дедлайном
    try:
        with open("notes_dd.csv", "r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == chat_id:
                    tasks.append(f"- {row[1]}: {row[2]}")
    except FileNotFoundError:
        pass

    # Чтение задач без дедлайна
    try:
        with open("notes_wo_dd.csv", "r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == chat_id:
                    tasks.append(f"- {row[1]}")
    except FileNotFoundError:
        pass

    return "\n".join(tasks) if tasks else "На сегодня задач нет."


def delete_note_from_file(chat_id, note_id, filename):
    """
    Удаление заметки из файла
    
    Args:
        chat_id (int): ID чата пользователя
        note_id (str): ID заметки для удаления
        filename (str): Имя файла с заметками
        
    Returns:
        bool: True если удаление прошло успешно, False в случае ошибки
    """
    try:
        # Чтение всех заметок из файла
        with open(filename, mode="r", newline="", encoding="utf-8") as file:
            notes = list(csv.reader(file))

        # Фильтрация заметок - оставляем все кроме удаляемой
        updated_notes = []
        for note in notes:
            if int(note[0]) == chat_id:
                if note_id != note[-1]:
                    updated_notes.append(note)
            else:
                updated_notes.append(note)

        # Перезапись файла без удаленной заметки
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(updated_notes)

        return True

    except FileNotFoundError:
        return False
    except Exception as e:
        return False


# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start_message(message):
    """Обработка команды /start - начало работы с ботом"""
    user_registration[message.chat.id] = Registration()
    bot.send_photo(
        message.chat.id,
        open("image.jpeg", "rb"),
        caption=f"Привет! Я Галочка, твоя персональная выручалочка 🚀 \nМожешь смело доверять мне все свои планы, встречи и задачи, я всё аккуратно разложу по полочкам и не дам тебе ничего забыть! \nРада помочь! Давай познакомимся! ✨",
    )
    bot.send_message(message.chat.id, "Какое у тебя имя?")
    bot.register_next_step_handler(message, user_registration[message.chat.id].get_name)


def show_main_menu(chat_id):
    """Отображение главного меню с кнопками"""
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_add_note = types.KeyboardButton("Создать заметку")
    button_delete_note = types.KeyboardButton("Удалить заметку")
    button_show_notes = types.KeyboardButton("Показать заметки")
    keyboard.add(button_add_note, button_delete_note, button_show_notes)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Обработка callback-запросов от кнопок"""
    chat_id = call.message.chat.id

    if call.data == "yes":
        # Подтверждение регистрации
        reg = user_registration[chat_id]
        reg.save_to_file(chat_id)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"Приятно познакомиться, {reg.name} 🥰",
        )
        show_main_menu(chat_id)
        del user_registration[chat_id]

    elif call.data == "no":
        # Отмена регистрации
        bot.edit_message_text(
            chat_id=chat_id, message_id=call.message.message_id, text="Жаль :("
        )
        del user_registration[chat_id]

    elif call.data.startswith("delete|"):
        # Удаление заметки
        note_id = call.data.split("|")[1]
        filename = "notes_dd.csv" if note_id.startswith("dd") else "notes_wo_dd.csv"

        if delete_note_from_file(chat_id, note_id, filename):
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="Заметка успешно удалена ✅",
            )
        else:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="Ошибка: Заметка не найдена.",
            )

        show_main_menu(chat_id)


@bot.message_handler(commands=["add_note"])
def add_note(message):
    """Обработка команды добавления заметки"""
    chat_id = message.chat.id

    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_with_deadline = types.KeyboardButton("С дедлайном")
    button_without_deadline = types.KeyboardButton("Без дедлайна")
    keyboard.add(button_with_deadline, button_without_deadline)

    bot.send_message(
        chat_id, "Хотите создать заметку с дедлайном или без?", reply_markup=keyboard
    )
    bot.register_next_step_handler(message, process_note_type)


def process_note_type(message):
    """Обработка выбора типа заметки"""
    chat_id = message.chat.id
    if message.text == "С дедлайном":
        bot.send_message(
            chat_id, "Введите текст заметки:", reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, process_note_with_deadline_text)
    elif message.text == "Без дедлайна":
        bot.send_message(
            chat_id, "Введите текст заметки:", reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, process_note_without_deadline_text)
    else:
        bot.send_message(
            chat_id, "Пожалуйста, выберите один из вариантов с помощью кнопок."
        )
        add_note(message)


def process_note_with_deadline_text(message):
    """Обработка текста заметки с дедлайном"""
    chat_id = message.chat.id
    text = message.text
    bot.send_message(chat_id, "Введите дедлайн (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
    bot.register_next_step_handler(message, process_note_with_deadline_deadline, text)


def process_note_with_deadline_deadline(message, text):
    """Обработка дедлайна заметки с валидацией формата"""
    chat_id = message.chat.id
    deadline = message.text
    try:
        datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        note = NoteWithDeadline(chat_id, text, deadline)
        note.save_to_file()
        bot.send_message(
            chat_id,
            "Заметка с дедлайном успешно сохранена ✅",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        show_main_menu(chat_id)
    except ValueError:
        bot.send_message(chat_id, "Неверный формат даты. Попробуйте ещё раз.")
        bot.register_next_step_handler(
            message, process_note_with_deadline_deadline, text
        )


def process_note_without_deadline_text(message):
    """Обработка заметки без дедлайна"""
    chat_id = message.chat.id
    text = message.text
    note = NoteWithoutDeadline(chat_id, text)
    note.save_to_file()
    bot.send_message(
        chat_id,
        "Заметка без дедлайна успешно сохранена ✅",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    show_main_menu(chat_id)


@bot.message_handler(func=lambda message: message.text == "Удалить заметку")
def handle_delete_note(message):
    """Обработка запроса на удаление заметки"""
    chat_id = message.chat.id
    notes = NoteManager.get_user_notes(chat_id)
    if not notes:
        bot.send_message(
            chat_id,
            "У вас нет заметок для удаления. Надеюсь, это значит, что вы счастливы 😊",
        )
        show_main_menu(chat_id)
        return

    keyboard = types.InlineKeyboardMarkup()
    for note in notes:
        button_text = f"{note['text']} ({note['type']})"
        callback_data = f"delete|{note['id']}"
        keyboard.add(
            types.InlineKeyboardButton(text=button_text, callback_data=callback_data)
        )

    bot.send_message(chat_id, "Выберите заметку для удаления:", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Создать заметку")
def handle_add_note(message):
    """Обработка запроса на создание заметки через кнопку"""
    add_note(message)


@bot.message_handler(func=lambda message: message.text == "Показать заметки")
def handle_show_notes(message):
    """Обработка запроса на просмотр заметок"""
    chat_id = message.chat.id
    notes = NoteManager.get_user_notes(chat_id)
    if not notes:
        bot.send_message(
            chat_id, "У вас нет заметок. Надеюсь, это значит, что вы счастливы 😊"
        )
    else:
        response = "Ваши заметки:\n"
        for note in notes:
            response += f"- {note['text']} ({note['type']})"
            if note["type"] == "С дедлайном":
                response += f", дедлайн: {note['deadline']}"
            response += "\n"
        bot.send_message(chat_id, response)
    show_main_menu(chat_id)


def check_deadlines_and_notify():
    """Проверка дедлайнов и отправка напоминаний"""
    with open(REGISTERED_USERS_FILE, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            chat_id = row[0]
            notes_reminder = []
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)

            with open("notes_dd.csv", "r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) >= 4:
                        note_chat_id, text, deadline_str, note_id = (
                            row[0], row[1], row[2], row[3])
                        if chat_id is not None and int(note_chat_id) != int(chat_id):
                            continue
                        try:
                            deadline_date = datetime.datetime.strptime(
                                deadline_str.split()[0], "%Y-%m-%d"
                            ).date()
                            if deadline_date == tomorrow:
                                notes_reminder.append(f"-{text}\n")
                            if len(notes_reminder) != 0:
                                notes_remind = "\n".join(notes_reminder)
                                message = (
                                    f"🔔 Напоминание! Завтра дедлайн по задаче:\n"
                                    + notes_remind
                                )
                                bot.send_message(int(note_chat_id), message)
                        except (ValueError, IndexError):
                            pass


# Настройка ежедневной проверки дедлайнов в 16:00
schedule.every().day.at("19:00").do(check_deadlines_and_notify)


def run_scheduler():
    """Запуск планировщика задач в отдельном потоке"""
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    # Запуск планировщика в фоновом режиме
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
    
    # Запуск бота
    print("Бот запущен и готов к работе!")
    bot.polling(none_stop=True)