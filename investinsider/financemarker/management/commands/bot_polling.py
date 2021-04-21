from django.core.management.base import BaseCommand
from . import telegram_bot
import traceback

class Command(BaseCommand):
    help = 'BotPolling'

    def handle(self, *args, **kwargs):
        while True:
            try:
                telegram_bot.bot.polling(interval=1)
            except Exception:
                print(traceback.format_exc())