from telebot import TeleBot, types
import threading
import schedule
import time
import re
from logger import Logger
from data.CONFIG import BOT_TOKEN
from data.ASSETS import help_text, admin_help
from api_processing.db_api import DbAPI
from api_processing.giphy_api import GiphyAPI
from api_processing.jokes_api import JokesAPI
from api_processing.GigaChat_api import GigaChatAPI


# Инициализируем нужные классы
bot = TeleBot(BOT_TOKEN)
db = DbAPI()
logger = Logger(db)
giga_chat = GigaChatAPI(logger)
gif = GiphyAPI(logger)
joke = JokesAPI(logger)

# Загружаем вопросы из бд
questions = db.load_questions


@bot.message_handler(commands=['start'])
def start_handler(message):  # Обработчик команды /start
    # Создаем клавиатуру
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    help_button = types.KeyboardButton('/help')  # Создаем и добавляем в клавиатуру кнопку help
    keyboard.add(help_button)
    # Отправляем приветственное сообщение пользователю
    bot.send_message(message.from_user.id,
                     f"Привет, {message.from_user.first_name}!\nЯ помогу тебе ответить на часто задаваемые вопросы по нашему курсу.",
                     reply_markup=keyboard)


@bot.message_handler(commands=['help'])
def help_handler(message):  # Обработчик команды /help
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)  # Создаем клавиатуру и добавляем в нее доступные команды
    keyboard.row(types.KeyboardButton('/FAQ'), types.KeyboardButton('/registration'))
    keyboard.row(types.KeyboardButton('/gif'), types.KeyboardButton('/joke'))
    keyboard.row(types.KeyboardButton('/feedback'), types.KeyboardButton('/ask'))

    # Отправляем пользователю справку и клавиатуру для ответа
    bot.send_message(message.from_user.id, '\n'.join(help_text), reply_markup=keyboard)


@bot.message_handler(commands=['registration'])
def registration_handler(message):  # Обработчик команды /registration
    user_id = message.from_user.id

    if is_in_table('users', user_id):  # Если пользователь уже есть в базе
        bot.send_message(user_id, "Вы уже зарегистрированы.")
    else:  # Иначе запрашиваем ФИО и регистрируем следующий обработчик для продолжения регистрации
        bot.send_message(user_id, "Введите ваше ФИО.")
        bot.register_next_step_handler(message, get_name)


def get_name(message):  # Обработчик ФИО пользователя
    user_id = message.from_user.id

    if message.text is not None:  # Если отзыв это текст
        name = message.text.rstrip().title()

        if re.fullmatch(r'^[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+$', name):  # Если ФИО пользователя соответствует паттерну
            user_data = {  # Создаем словарь с данными пользователя
                'tag': message.from_user.username,
                'name': name,
                'group': None,
                'is_mailing': False
            }

            bot.send_message(user_id, "Введите вашу группу в формате ББИ___")
            bot.register_next_step_handler(message, get_group, user_data)
        else:  # Иначе перезапускаем функцию
            bot.send_message(user_id, "Введите ваше ФИО корректно")
            bot.register_next_step_handler(message, get_name)
    else:
        bot.send_message(user_id, 'ФИО должно содержать только текст')
        bot.register_next_step_handler(message, get_name)  # Перезапускаем обработчик


def get_group(message, user_data):  # Обработчик группы пользователя
    user_id = message.from_user.id

    if message.text is not None:  # Если отзыв это текст
        group = message.text.rstrip()  # Очищаем строку от лишних пробелов

        if re.fullmatch(r'ББИ\d{3}', group):  # Если группа пользователя соответствует паттерну
            user_data['group'] = group  # Записываем группу в словарь
            db.add_data_to_table('users', str(user_id), user_data)

            bot.send_message(user_id, 'Вы успешно зарегистрированы!')
        else:  # Иначе перезапускаем функцию
            bot.send_message(message.from_user.id, "Введите вашу группу в формате ББИ___")
            bot.register_next_step_handler(message, get_group, user_data)
    else:
        bot.send_message(user_id, 'Группа должна содержать только текст')
        bot.register_next_step_handler(message, get_group, user_data)  # Перезапускаем обработчик


@bot.message_handler(commands=['faq'])
def faq_handler(message):  # Обработчик команды /faq
    user_id = message.from_user.id

    if is_in_table('users', user_id):  # Если пользователь зарегистрирован, то запускаем процедуру сбора фидбека
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)  # Создаем клавиатуру
        for question in questions.keys():  # Заполняем клавиатуру ключами из questions (часто задаваемыми вопросами)
            keyboard.add(types.KeyboardButton(question))

        bot.send_message(message.from_user.id, 'Выберите интересующий вас вопрос из списка: ', reply_markup=keyboard)
    else:  # Иначе просим его зарегистрироваться
        bot.send_message(user_id, 'Сначала используй /registration для регистрации.')


@bot.message_handler(commands=['joke'])
def joke_handler(message):  # Обработчик команды /joke
    user_id = message.from_user.id
    users = db.load_data_from_table('users')  # Загружаем словарь с пользователями

    if str(user_id) in users:  # Если пользователь зарегистрирован, то вызываем функцию для отправки шутки
        send_random_joke(user_id, users[str(user_id)]['is_mailing'])  # Передаем флаг подписки для генерации кнопки
    else:  # Иначе просим его зарегистрироваться
        bot.send_message(user_id, 'Сначала используй /registration для регистрации.')


@bot.message_handler(commands=['gif'])
def gif_handler(message):  # Обработчик команды /gif
    user_id = message.from_user.id

    if is_in_table('users', user_id):  # Если пользователь зарегистрирован, то запускаем процедуру сбора фидбека
        bot.send_animation(message.from_user.id, gif.get_gif())  # Отправляем пользователю полученную гифку
    else:  # Иначе просим его зарегистрироваться
        bot.send_message(user_id, 'Сначала используй /registration для регистрации.')


@bot.message_handler(commands=['feedback'])
def feedback_handler(message):  # Обработчик команды /feedback
    user_id = message.from_user.id

    if is_in_table('users', user_id):  # Если пользователь зарегистрирован, то запускаем процедуру сбора фидбека
        bot.send_message(user_id,
                         'Напиши свое предложения/претензии по курсу.')
        bot.register_next_step_handler(message, get_feedback)
    else:  # Иначе просим его зарегистрироваться
        bot.send_message(user_id, 'Сначала используй /registration для регистрации.')


def get_feedback(message):  # Сохранение обратной связи от пользователя
    user_id = message.from_user.id

    if message.text is not None:  # Если отзыв это текст
        user_feedback = {'feedback': message.text}
        db.add_data_to_table('feedback', str(user_id), user_feedback)  # Сохраняем в бд
        bot.send_message(user_id, 'Спасибо за твой отзыв!')
    else:
        bot.send_message(user_id, 'Отзыв должен содержать только текст')
        bot.register_next_step_handler(message, get_feedback)  # Перезапускаем обработчик


@bot.message_handler(commands=['myfeedback'])
def my_feedback_handler(message):  # Обработчик команды /myfeedback
    user_id = message.from_user.id
    feedbacks = db.load_data_from_table('feedback')

    if is_in_table('feedback', user_id):
        bot.send_message(user_id, f"Твой текущий отзыв:\n{feedbacks[str(user_id)]['feedback']}")
    else:
        bot.send_message(user_id, 'Ты ещё не оставлял отзыв.')


@bot.message_handler(commands=['deletefeedback'])
def delete_feedback_handler(message):  # Обработчик команды /deletefeedback
    user_id = message.from_user.id
    
    if is_in_table('feedback', user_id):
        db.delete_data_from_table('feedback', str(user_id))
        bot.send_message(user_id, 'Твой отзыв успешно удален.')
    else:
        bot.send_message(user_id, 'Ты ещё не оставлял отзыв.')


@bot.message_handler(commands=['ask'])
def ask_handler(message):  # Обработчик команды /ask
    user_id = message.from_user.id

    if is_in_table('users', user_id):  # Если пользователь зарегистрирован, то вызываем функцию для обработки вопроса
        bot.send_message(user_id, 'Задай свой вопрос знатоку.')
        bot.register_next_step_handler(message, get_answer)
    else:  # Иначе просим его зарегистрироваться
        bot.send_message(user_id, 'Сначала используй /registration для регистрации.')


def get_answer(message):  # Выводим ответ от GPT пользователю
    user_id = message.from_user.id

    if message.text is not None:  # Если отзыв это текст
        bot.send_message(message.from_user.id, giga_chat.get_answer(message.text))
    else:
        bot.send_message(user_id, 'Вопрос должен содержать только текст')
        bot.register_next_step_handler(message, get_answer)  # Перезапускаем обработчик


@bot.message_handler(commands=['deleteaccount'])
def delete_account_handler(message):  # Обработчик команды /deleteaccount
    user_id = message.from_user.id
    db.delete_data_from_table('users', str(user_id))
    bot.send_message(user_id, 'Ваш аккаунт успешно удален.')


@bot.message_handler(commands=['admin'])
def admin_handler(message):  # Обработчик команды /admin
    user_id = message.from_user.id
    user_tag = message.from_user.username

    if is_in_table('admins', user_tag):
        bot.send_message(user_id, '\n'.join(admin_help))
    else:
        bot.send_message(user_id, 'У Вас нет прав для использования этой команды.')


@bot.message_handler(commands=['newadmin'])
def new_admin_handler(message):  # Обработчик команды /newadmin
    user_id = message.from_user.id
    user_tag = message.from_user.username

    if is_in_table('admins', user_tag):
        bot.send_message(user_id, 'Введите тег нового админа в формате @...')
        bot.register_next_step_handler(message, get_admin_tag)
    else:
        bot.send_message(user_id, 'У Вас нет прав для использования этой команды.')


def get_admin_tag(message):
    user_id = message.from_user.id
    tag = message.text.rstrip()  # Очищаем строку от лишних пробелов

    if re.fullmatch(r'@\w+', tag):  # Если тег пользователя соответствует паттерну
        if is_in_table('admins', tag[1:]):
            bot.send_message(user_id, 'Этот пользователь уже является администратором.')
        else:
            db.add_data_to_table('admins', tag[1:], {'level': 0})
            bot.send_message(user_id, 'Новый администратор успешно добавлен.')
    else:  # Иначе перезапускаем функцию
        bot.send_message(user_id, "Введите тег нового админа в формате @...")
        bot.register_next_step_handler(message, get_admin_tag)


@bot.message_handler(commands=['addquestion'])
def add_question_handler(message):  # Обработчик команды /addquestion
    user_id = message.from_user.id
    user_tag = message.from_user.username

    if is_in_table('admins', user_tag):
        bot.send_message(user_id, 'Введите данные в формате вопрос: ответ')
        bot.register_next_step_handler(message, get_new_question)
    else:
        bot.send_message(user_id, 'У Вас нет прав для использования этой команды.')


def get_new_question(message):
    global questions
    question, answer = message.text.rstrip().split(': ')

    db.add_data_to_table('questions', str(len(questions) + 1), {'question': question, 'answer': answer})
    questions = db.load_questions
    bot.send_message(message.from_user.id, 'Вопрос успешно добавлен.')


@bot.message_handler(commands=['sendtogroup'])
def send_to_group_handler(message):  # Обработчик команды /sendtogroup
    user_id = message.from_user.id
    user_tag = message.from_user.username

    if is_in_table('admins', user_tag):
        bot.send_message(user_id, 'Введите данные в формате ББИ___: сообщение')
        bot.register_next_step_handler(message, get_message_for_group)
    else:
        bot.send_message(user_id, 'У Вас нет прав для использования этой команды.')


def get_message_for_group(message):
    group, text = message.text.rstrip().split(': ')

    users = db.load_data_from_table('users')
    for user_id, data in users.items():
        if data['group'] == group:
            bot.send_message(user_id, text + f' (от @{message.from_user.username})')

    bot.send_message(message.from_user.id, f'Ваше сообщение успешно отправлено студентам {group}.')


@bot.callback_query_handler(func=lambda call: 'mailing' in call.data)
def mailing_callback(call):  # Обработчик Inline кнопки подписки на рассылку
    user_id = call.from_user.id
    user_data = db.load_data_from_table('users', str(user_id))  # Загружаем нажавшего пользователя из бд

    user_data['is_mailing'] = call.data == 'subscribe_mailing'  # Изменяем флаг согласия на рассылку
    db.update_table_data('users', str(user_id), user_data)  # Сохраняем данные в бд

    bot.edit_message_text(call.message.text,
                          call.message.chat.id,
                          call.message.message_id,
                          reply_markup=None)  # Убираем нажатую пользователем кнопку


@bot.callback_query_handler(func=lambda call: call.data == '/faq')
def next_question_callback(call):  # Обработчик Inline кнопки 'Другой вопрос'
    faq_handler(call)  # Перезапускаем обработчик /faq


@bot.message_handler(content_types=['text'])
def text_handler(message):  # Обработчик текстовых сообщений от пользователя
    user_id = message.from_user.id
    text = message.text

    if text in questions.keys():  # Если пользователь отправил вопрос из списка
        keyboard = types.InlineKeyboardMarkup()  # Создаем кнопку для возможности задать другой вопрос
        next_question_button = types.InlineKeyboardButton(text="Другой вопрос", callback_data="/faq")
        keyboard.add(next_question_button)
        # Если ответ содержит ссылку, то отправляем ее с помощью parse_mode 'Markdown'
        if questions[text].startswith('https'):
            bot.send_message(user_id,
                             f'[Ответ на твой вопрос тут]({questions[text]})',
                             parse_mode='Markdown',
                             reply_markup=keyboard)
        else:  # Если ответ не содержит ссылку, то просто отправляем его пользователю
            bot.send_message(user_id, questions[text], reply_markup=keyboard)
    else:  # Если получаем что-то не из списка вопросов, то перезапускаем обработчик /faq
        faq_handler(message)


def is_in_table(table, key):  # Проверка есть ли запись в таблице
    return str(key) in db.load_data_from_table(table)


def send_random_joke(user_id, is_mailing):  # Отправка случайной шутки
    keyboard = types.InlineKeyboardMarkup()

    if is_mailing:  # Если пользователь подписан на рассылку, то даем ему возможность отписаться
        reject_button = types.InlineKeyboardButton(text="Отписаться от рассылки", callback_data="reject_mailing")
        keyboard.add(reject_button)
    else:  # Иначе предлагаем ему подписаться на рассылку
        subscribe_button = types.InlineKeyboardButton(text="Подписаться на рассылку", callback_data="subscribe_mailing")
        keyboard.add(subscribe_button)

    bot.send_message(user_id, joke.get_joke(), reply_markup=keyboard)  # Получаем шутку и отправляем пользователю


def joke_mailing():  # Рассылка шуток для подписчиков
    def send():
        users = db.load_data_from_table('users')

        for user in users.keys():  # Проходимся по всем пользователям
            if users[str(user)]['is_mailing']:  # Проверяем флаг подписки на рассылку
                send_random_joke(int(user), True)  # Отправляем шутку подписчику

    schedule.every().hour.do(send)  # Задаем промежутки для рассылки
    while True:
        schedule.run_pending()  # Запускаем рассылку
        time.sleep(1)


if __name__ == '__main__':
    thread = threading.Thread(target=joke_mailing)  # Создание и запуск дополнительного потока с рассылкой
    thread.start()

    bot.infinity_polling()  # Запуск бота
