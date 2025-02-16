#Устанавливаем библиотеку telebot (pip3 install pyTelegramBotAPI)
import telebot
import csv
import os 
from telebot import types

#Создали бот
#Скрываем токен, используя переменные окружения
#Ps: через командную строку надо будет вписать команды и токен, так он будет храниться ток у нас на компьютерахь и в сеть мы его не опубликуем
token = os.environ.get("TELEGRAM_BOT_TOKEN") 
if not token:
    print("Ошибка: Не найден токен телеграм-бота в переменных окружения.")
    exit()
bot = telebot. TeleBot (token)
user_registration = {}

#Регистрация ( наверное потом надо поменять)
class Registration:
    def __init__(self):
        self.name = ''
        self.surname = ''
        self.age = 0

    def get_name(self,message):
        self.name = message.text
        bot.send_message (message.chat.id, 'Какая у тебя фамилия?')
        bot.register_next_step_handler(message, self.get_surname)

    def get_surname(self, message):
        self.surname = message.text
        bot.send_message (message.chat.id, 'Сколько тебе лет?')
        bot.register_next_step_handler(message, self.get_age)

    def get_age(self,message):
        try:
            self.age = int(message.text)
            keyboard = types.InlineKeyboardMarkup()
            key_yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
            keyboard.add(key_yes)
            key_no = types.InlineKeyboardButton(text='Нет', callback_data='no')
            keyboard.add(key_no)

            question = f'Тебе {self.age} лет, тебя зовут {self.name} {self.surname}?'
            bot.send_message(message.chat.id, question, reply_markup=keyboard)
        except ValueError:
            bot.send_message(message.chat.id, 'Прошу прощения, я не понимаю, цифрами, пожалуйста.')
            bot.register_next_step_handler(message, self.get_age)
    def save_to_file(self):
        with open('users.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([self.name, self.surname, self.age])

#Первое сообщение(приветствие)
@bot.message_handler(content_types=['text'])
def start_message (message):
    if message.text == '/start':
        user_registration[message.chat.id] = Registration()
        bot.send_photo(message.chat.id,open('image.jpeg', 'rb'), 
                           caption='Привет, меня зовут Галина и теперь я твой личный секретарь. Мне ты можешь рассказать о своих планах, установить дедлайны и много чего ещё! Давай для начала познакомимся.')
        bot.send_message(message.chat.id, 'Какое у тебя имя?')
        bot.register_next_step_handler(message, user_registration[message.chat.id].get_name)
    else: 
        bot.send_message(message.chat.id, 'Напиши "/start"')

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    chat_id = call.message.chat.id
    reg = user_registration[chat_id]
    if call.data == 'yes':
        reg.save_to_file()
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f'Приятно познакомиться {reg.name} {reg.surname}!')

        del user_registration[chat_id]
        # bot.send_message(call.message.chat.id, f'Приятно познакомиться {reg.name} {reg.surname}!')
    elif call.data == 'no':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='Жаль :(')

        # bot.send_message(call.message.chat.id, 'Жаль :(')
        del user_registration[chat_id]

bot.polling(none_stop=True)