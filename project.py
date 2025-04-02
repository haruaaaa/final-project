import telebot
import csv
import os
from telebot import types
import datetime
import time
import schedule
import requests
import threading

# Создали бот
# Скрываем токен, используя переменные окружения
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    print("Ошибка: Не найден токен телеграм-бота в переменных окружения.")
    exit()
bot = telebot.TeleBot(token)

# Получаем ключ с сайта NASA
NASA_API_KEY = 'XIvrocqXsocigfch2H8fHPVnZgSsgy1RnIbPgH8m'

# Создаем словари для хранения данных пользователей и заметок
user_registration = {}

# Класс для регистрации пользователя
class Registration:
    def __init__(self):
        self.name = ''
        self.age = 0

    # имя
    def get_name(self, message):
        self.name = message.text
        bot.send_message(message.chat.id, 'Сколько тебе лет?')
        bot.register_next_step_handler(message, self.get_age)

    # возраст
    def get_age(self, message):
        try:
            self.age = int(message.text)
            keyboard = types.InlineKeyboardMarkup()
            key_yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
            keyboard.add(key_yes)
            key_no = types.InlineKeyboardButton(text='Нет', callback_data='no')
            keyboard.add(key_no)

            question = f'Тебе {self.age} лет, тебя зовут {self.name}?'
            bot.send_message(message.chat.id, question, reply_markup=keyboard)
        except ValueError:
            bot.send_message(message.chat.id, f'Прошу прощения, я не понимаю 🥹 \nНапиши, пожалуйста, цифрами.')
            bot.register_next_step_handler(message, self.get_age)

    def save_to_file(self, chat_id):
        with open('users.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([chat_id, self.name, self.age])

# Родительский класс для заметки
class Note:
    def __init__(self, chat_id, text):
        self.chat_id = chat_id
        self.text = text

    def save_to_file(self):
        raise NotImplementedError("Метод save_to_file должен быть переопределён в подклассе")

# Подкласс для заметки с дедлайном
class NoteWithDeadline(Note):
    def __init__(self, chat_id, text, deadline):
        super().__init__(chat_id, text)
        self.deadline = deadline
        self.note_id = f"dd_{int(time.time())}"  # Уникальный идентификатор

    def save_to_file(self):
        with open('notes_dd.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([self.chat_id, self.text, self.deadline, self.note_id])  # Добавляем note_id


# Подкласс для заметки без дедлайна
class NoteWithoutDeadline(Note):
    def __init__(self, chat_id, text):
        super().__init__(chat_id, text)
        self.note_id = f"wo_{int(time.time())}"  # Уникальный идентификатор

    def save_to_file(self):
        with open('notes_wo_dd.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([self.chat_id, self.text, self.note_id])  # Добавляем note_id

REGISTERED_USERS_FILE = 'users.csv'
# Функция для получения изображения дня с сайта NASA 
def get_nasa_image():

    #Берем фото дня с сайта NASA
    url = f'https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'url' in data and data['media_type'] == 'image':
            return data['url']
    return None

# Функция для отправки ежедневных уведомлений 
def send_daily_reminders():
    try:
        with open(REGISTERED_USERS_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                chat_id = row[0]

                # Получаем изображение дня от NASA API
                image_url = get_nasa_image()
                if image_url:

                    tasks = get_tasks_for_user(chat_id)

                    # Формируем сообщение
                    task_message = "Не забудь выполнить сегодняшние задачи:\n" + tasks

                    # Отправка ежедневное напоминание
                    bot.send_photo(int(chat_id), image_url,caption=task_message)
                else:
                    # Если не удалось получить изображение, отправляем ошибку
                    bot.send_message(int(chat_id), "Сегодняшнее изображение недоступно.")
    except FileNotFoundError:
        print("Файл с зарегистрированными пользователями не найден.")
    except Exception as e:
        print(f"Ошибка при отправке уведомлений: {e}")

# Задаем время для отправки ежедневных уведомлений
schedule.every().day.at("10:00").do(send_daily_reminders)

# Функция для получения задач пользователя
def get_tasks_for_user(chat_id):
    tasks = []
    
    # Чтение задач из notes_dd.csv
    try:
        with open('notes_dd.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == chat_id:
                    tasks.append(f"- {row[1]}: {row[2]}")  # Второй и третий столбцы
    except FileNotFoundError:
        print("Файл notes_dd.csv не найден.")
    
    # Чтение задач из notes_wo_dd.csv
    try:
        with open('notes_wo_dd.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == chat_id:
                    tasks.append(f"- {row[1]}")  # Второй и третий столбцы
    except FileNotFoundError:
        print("Файл notes_wo_dd.csv не найден.")
    
    # Объединяем задачи в одну строку или выводим нулевой результат
    return "\n".join(tasks) if tasks else "На сегодня задач нет."


# Удаление заметки из файла
def delete_note_from_file(chat_id, note_id, filename):
    try:
        # Читаем все заметки из файла
        with open(filename, mode='r', newline='', encoding='utf-8') as file:
            notes = list(csv.reader(file))

        # Создаем новый список заметок, оставляя только те, которые не нужно удалять
        updated_notes = []
        for note in notes:
            if int(note[0]) == chat_id:  # Проверяем, что заметка принадлежит именно этому пользователю
                # Проверка, что это не та заметка, которую нужно удалить
                if note_id != note[-1]:  
                    updated_notes.append(note)
            else:
                updated_notes.append(note)
        print(note_id)

        # Записываем обновлённый список заметок обратно в файл
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(updated_notes)

        return True  # Успешное удаление
    
    # Ошибки
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return False  
    except Exception as e:
        print(f"Ошибка при удалении заметки: {e}")
        return False


# Обработчик команды /start (начало работы)
@bot.message_handler(commands=['start'])
def start_message(message):
    user_registration[message.chat.id] = Registration()
    bot.send_photo(message.chat.id, open('image.jpeg', 'rb'),
                   caption=f'Привет! Я Галочка, твоя персональная выручалочка 🚀 \nМожешь смело доверять мне все свои планы, встречи и задачи, я всё аккуратно разложу по полочкам и не дам тебе ничего забыть! \nРада помочь! Давай познакомимся! ✨')
    bot.send_message(message.chat.id, 'Какое у тебя имя?')
    bot.register_next_step_handler(message, user_registration[message.chat.id].get_name)


# Функция для считывания заметок пользователя
def get_user_notes(chat_id):
    notes = []
    
    # Читаем заметки с дедлайном
    try:
        with open('notes_dd.csv', mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if int(row[0]) == chat_id:  # Проверяем, что заметка принадлежит пользователю
                    notes.append({
                        "id": row[3],  # Уникальный идентификатор для заметки
                        "text": row[1],
                        "deadline": row[2],
                        "type": "С дедлайном"
                    })
    except FileNotFoundError:
        print("Файл notes_dd.csv не найден.")

    # Читаем заметки без дедлайна
    try:
        with open('notes_wo_dd.csv', mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if int(row[0]) == chat_id:  # Проверяем, что заметка принадлежит пользователю
                    notes.append({
                        "id": row[2],  # Уникальный идентификатор для заметки
                        "text": row[1],
                        "type": "Без дедлайна"
                    })

    except FileNotFoundError:
        print("Файл notes_wo_dd.csv не найден.")

    return notes


# Функция для показа главного меню (основные действия)
def show_main_menu(chat_id):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_add_note = types.KeyboardButton("Создать заметку")
    button_delete_note = types.KeyboardButton("Удалить заметку")
    button_show_notes = types.KeyboardButton("Показать заметки")
    keyboard.add(button_add_note, button_delete_note, button_show_notes)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=keyboard)


# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    chat_id = call.message.chat.id

    if call.data == 'yes':
        reg = user_registration[chat_id]
        reg.save_to_file(chat_id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f'Приятно познакомиться, {reg.name} 🥰')
        show_main_menu(chat_id)
        del user_registration[chat_id]

    elif call.data == 'no':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='Жаль :(')
        del user_registration[chat_id]

    elif call.data.startswith("delete|"):
        note_id = call.data.split("|")[1]  # Получаем идентификатор заметки
        filename = "notes_dd.csv" if note_id.startswith("dd") else "notes_wo_dd.csv"
        
        # Удаляем заметку из файла
        if delete_note_from_file(chat_id, note_id, filename):
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Заметка успешно удалена ✅")
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Ошибка: Заметка не найдена.")
        
        # Показываем главное меню
        show_main_menu(chat_id)


# Обработчик команды /add_note
@bot.message_handler(commands=['add_note'])
def add_note(message):
    chat_id = message.chat.id

    # Создаём клавиатуру с кнопками
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_with_deadline = types.KeyboardButton("С дедлайном")
    button_without_deadline = types.KeyboardButton("Без дедлайна")
    keyboard.add(button_with_deadline, button_without_deadline)

    # Отправляем сообщение с кнопками
    bot.send_message(chat_id, "Хотите создать заметку с дедлайном или без?", reply_markup=keyboard)
    bot.register_next_step_handler(message, process_note_type)

# Выбираем тип заметки
def process_note_type(message):
    chat_id = message.chat.id
    if message.text == "С дедлайном":
        bot.send_message(chat_id, "Введите текст заметки:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_note_with_deadline_text)
    elif message.text == "Без дедлайна":
        bot.send_message(chat_id, "Введите текст заметки:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_note_without_deadline_text)
    else:
        bot.send_message(chat_id, "Пожалуйста, выберите один из вариантов с помощью кнопок.")
        add_note(message)  # Возвращаем к выбору заметки при игнорировании кнопок

# Заметки с дедлайном
def process_note_with_deadline_text(message):
    chat_id = message.chat.id
    text = message.text
    bot.send_message(chat_id, "Введите дедлайн (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
    bot.register_next_step_handler(message, process_note_with_deadline_deadline, text)


def process_note_with_deadline_deadline(message, text):
    chat_id = message.chat.id
    deadline = message.text
    try:
        # Проверяем, что введённый дедлайн соответствует формату
        datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        note = NoteWithDeadline(chat_id, text, deadline)
        note.save_to_file()
        bot.send_message(chat_id, "Заметка с дедлайном успешно сохранена ✅", reply_markup=types.ReplyKeyboardRemove())

        # Показываем главное меню
        show_main_menu(chat_id)

    except ValueError:
        # Если формат даты неверный, отправляем сообщение об ошибке и ждём новую датц
        bot.send_message(chat_id, "Неверный формат даты. Попробуйте ещё раз.")
        bot.register_next_step_handler(message, process_note_with_deadline_deadline, text)

# Заметки без дедлайна
def process_note_without_deadline_text(message):
    chat_id = message.chat.id
    text = message.text
    note = NoteWithoutDeadline(chat_id, text)
    note.save_to_file()
    bot.send_message(chat_id, "Заметка без дедлайна успешно сохранена ✅", reply_markup=types.ReplyKeyboardRemove())

    # Показываем главное меню
    show_main_menu(chat_id)

# Удаление заметок после выбора действия
@bot.message_handler(func=lambda message: message.text == "Удалить заметку")
def handle_delete_note(message):
    chat_id = message.chat.id
    notes = get_user_notes(chat_id)
    if not notes:
        bot.send_message(chat_id, f"У вас нет заметок для удаления. Надеюсь, это значит, что вы счастливы 😊")
        show_main_menu(chat_id)
        return

    keyboard = types.InlineKeyboardMarkup()
    for note in notes:
        button_text = f"{note['text']} ({note['type']})"
        callback_data = f"delete|{note['id']}"
        keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

    bot.send_message(chat_id, "Выберите заметку для удаления:", reply_markup=keyboard)

# Создаём заметку после выбора действия
@bot.message_handler(func=lambda message: message.text == "Создать заметку")
def handle_add_note(message):
    add_note(message)

# Показываем список всех заметок после выбора действия
@bot.message_handler(func=lambda message: message.text == "Показать заметки")
def handle_show_notes(message):
    chat_id = message.chat.id
    notes = get_user_notes(chat_id)
    if not notes:
        bot.send_message(chat_id, "У вас нет заметок. Надеюсь, это значит, что вы счастливы 😊")
    else:
        response = "Ваши заметки:\n"
        for note in notes:
            response += f"- {note['text']} ({note['type']})"
            if note['type'] == "С дедлайном":
                response += f", дедлайн: {note['deadline']}"
            response += "\n"
        bot.send_message(chat_id, response)
    show_main_menu(chat_id)

#Отправляем напоминание за день до дедлайна
def check_deadlines_and_notify():
    
    with open(REGISTERED_USERS_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                chat_id = row[0]
                notes_reminder = []
                today = datetime.date.today()
                tomorrow = today + datetime.timedelta(days=1)
                
                # Читаем заметки с дедлайнами
                with open('notes_dd.csv', 'r', newline='', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    for row in reader:
                        if len(row) >= 4: 
                            note_chat_id, text, deadline_str, note_id = row[0], row[1], row[2], row[3]
                            
                            # Пропускаем заметки других пользователей, если указан chat_id
                            if chat_id is not None and int(note_chat_id) != int(chat_id):
                                continue
                            
                            try:
                                # Преобразуем строку даты в объект date (без времени)
                                deadline_date = datetime.datetime.strptime(deadline_str.split()[0], "%Y-%m-%d").date()
                                
                                if deadline_date == tomorrow:
                                    notes_reminder.append(f"-{text}\n")
                                if len(notes_reminder)!=0:
                                    notes_remind = "\n".join(notes_reminder)
                                    message = f"🔔 Напоминание! Завтра дедлайн по задаче:\n"+ notes_remind
                                    bot.send_message(int(note_chat_id), message)
                                
                            except (ValueError, IndexError):
                                print(f"Неверный формат даты в заметке {note_id}")
    

schedule.every().day.at("16:00").do(check_deadlines_and_notify)

# Запуск планировщика
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
    # Запуск
    bot.polling(none_stop=True)