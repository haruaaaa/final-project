#Устанавливаем библиотеку telebot (pip3 install pyTelegramBotAPI)
import telebot
import csv
from telebot import types

#Создали бот
token = 'СЮДА'
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
    if call.data == 'yes':
        reg = user_registration[call.message.chat.id]
        reg.save_to_file()
        bot.send_message(call.message.chat.id, f'Приятно познакомиться {reg.name} {reg.surname}!')
    elif call.data == 'no':
        bot.send_message(call.message.chat.id, 'Жаль :(')

bot.polling(none_stop=True)