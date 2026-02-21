from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
import os
from config import *

bot = TeleBot(API_TOKEN)

def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=id))
    return markup

@bot.message_handler(commands=['rating'])
def handle_rating(message):
    res = db_manager.get_rating() #
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    bot.send_message(message.chat.id, res)

# НОВЫЙ ХЕНДЛЕР
@bot.message_handler(commands=['get_my_score'])
def get_my_score(message):
    user_id = message.from_user.id
    
    try:
        # Получаем картинки пользователя
        user_winners = db_manager.get_winners_img(user_id)
        
        # Получаем все картинки
        all_prizes = os.listdir('img')
        
        # Формируем пути: полученные - из img, неполученные - из hidden_img
        image_paths = []
        for prize in all_prizes:
            if prize in user_winners:
                image_paths.append(f'img/{prize}')
            else:
                image_paths.append(f'hidden_img/{prize}')
        
        # Создаем и отправляем коллаж
        collage = create_collage(image_paths)
        collage_path = save_collage(collage, f'collage_{user_id}.jpg')
        
        with open(collage_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, 
                          caption=f"🏆 Ваши достижения!\nПолучено: {len(user_winners)}/{len(all_prizes)}")
        
        os.remove(collage_path)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = call.data
    user_id = call.message.chat.id

    if winners < 3:
        res = db_manager.add_winner()
        if res:
            img = get_random_image()
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравляем! Ты получил картинку!")
        else:
            bot.send_message(user_id, 'Ты уже получил картинку!')
    else:
        bot.send_message(user_id, "К сожалению, ты не успел получить картинку! Попробуй в следующий раз!)")

def send_message():
    prize_id, img = manager.get_random_prize()[:2]
    manager.mark_prize_used(prize_id)
    hide_img(img)
    for user in manager.get_users():
        with open(f'hidden_img/{img}', 'rb') as photo:
            bot.send_photo(user, photo, reply_markup=gen_markup(id=prize_id))

def shedule_thread():
    schedule.every().minute.do(send_message)
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегестрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать! 
Тебя успешно зарегистрировали!
Каждый час тебе будут приходить новые картинки и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Только три первых пользователя получат картинку!)""")

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()

    polling_thread = threading.Thread(target=polling_thread)
    polling_shedule = threading.Thread(target=shedule_thread)

    polling_thread.start()
    polling_shedule.start()
