import config
import telebot

bot = telebot.TeleBot(config.BOT_TOKEN)


def send_info_in_group(text):
    bot.send_message(config.GROUP_ID, text, parse_mode='html')