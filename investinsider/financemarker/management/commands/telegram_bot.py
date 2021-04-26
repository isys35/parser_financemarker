from django.conf import settings
import telebot
from financemarker.models import Insider, NewsItem, TelegraphAccount, TelegraphPage
from django.template.loader import render_to_string
from threading import Thread
from . import parser

bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)


@bot.callback_query_handler(func=lambda c: c.data)
def process_callback_select_example(callback_query: telebot.types.CallbackQuery):
    if parser.DBManager().rate.is_liked(str(callback_query.from_user.id), str(callback_query.message.message_id)):
        bot.answer_callback_query(callback_query_id=callback_query.id, text='Вы уже оценили сообщение')
        return
    count_like = int(callback_query.data.split('_')[1])
    count_dislike = int(callback_query.data.split('_')[2])
    if callback_query.data.startswith('like'):
        count_like += 1
    if callback_query.data.startswith('dislike'):
        count_dislike += 1
    keyboard = telebot.types.InlineKeyboardMarkup()
    btn_1 = telebot.types.InlineKeyboardButton('👍 {}'.format(count_like),
                                               callback_data='like_{}_{}'.format(count_like, count_dislike))
    btn_2 = telebot.types.InlineKeyboardButton('👎 {}'.format(count_dislike),
                                               callback_data='dislike_{}_{}'.format(count_like, count_dislike))
    keyboard.add(btn_1, btn_2)
    bot.edit_message_reply_markup(callback_query.message.chat.id, callback_query.message.message_id,
                                  reply_markup=keyboard)
    parser.DBManager().rate.create(str(callback_query.from_user.id), str(callback_query.message.message_id))


class BotManager:

    @staticmethod
    def keyboard():
        keyboard = telebot.types.InlineKeyboardMarkup()
        like_btn = telebot.types.InlineKeyboardButton('👍', callback_data='like_0_0')
        dislike_btn = telebot.types.InlineKeyboardButton('👎', callback_data='dislike_0_0')
        keyboard.add(like_btn, dislike_btn)
        return keyboard

    def send_text_message(self, text):
        keyboard = self.keyboard()
        bot.send_message(settings.TELEGRAM_GROUP_ID, text=text, parse_mode='html',
                         disable_web_page_preview=True, reply_markup=keyboard)

    def send_image_message(self, image_path, text):
        keyboard = self.keyboard()
        with open(image_path, 'rb') as img:
            bot.send_photo(chat_id=settings.TELEGRAM_GROUP_ID, photo=img, caption=text, parse_mode='HTML',
                           reply_markup=keyboard)


class Formater:
    def telegram_format(self, insider: Insider, telegraph_page: TelegraphPage):
        context = {'insider': insider, 'price': '{0:,}'.format(insider.price).replace(',', ' '),
                   'value': '{0:,}'.format(insider.value).replace(',', ' '), 'telegraph_page': telegraph_page,
                   'amount': abs(insider.amount)}
        return render_to_string('telegram_message/message.html', context=context)


class BotThread(Thread):

    def run(self) -> None:
        bot.polling(interval=1)
