import sys
import json
import time
import requests
from django.core.management.base import BaseCommand
from datetime import datetime
from financemarker.models import Insider, NewsItem, TelegraphAccount, TelegraphPage, Exchange, Company, Rate
from django.db.models import Q
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from abc import abstractmethod

from . import telegraph, telegram_bot

AUTHORIZATION = 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2MTg5ODk1MjMsIm5iZiI6MTYxODk4OTUyMywianRpIjoiMWEzY2U4MjEtMTVlNC00MzYwLWE5NTEtYWE1MDg1Nzk5ODIyIiwiZXhwIjoxNjE5NTk0MzIzLCJpZGVudGl0eSI6Mzc1MjgsImZyZXNoIjp0cnVlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsiYWNjZXNzX2xldmVsIjo2LCJkYXRhX2xldmVsIjo2fSwiY3NyZiI6IjM3NWM1MGEwLTg2NzctNGJiNC1hYTUxLTBlM2I3NzNhZDE5NSJ9.VyuxlqfLsUNfKJb4V9VXfKtL2XnQlgslV49tgUGErus'

INSIDERS_URL = 'https://financemarker.ru/api/insiders?transaction_type=P'
REFERER_URL = 'https://financemarker.ru/stocks/{}/{}'  # {insider.exchange.name} {insider.company.code}
NEWS_URL = 'https://financemarker.ru/api/news?query={}:{}&type=&page=1'  # {insider.exchange.name} {insider.company.code}
IMAGE_URL_1 = 'https://financemarker.ru/fa/fa_logos/{}.png'
IMAGE_URL_2 = 'https://financemarker.ru/fa/fa_logos/{}_{}.png'
IMAGE_URL_3 = 'https://financemarker.ru/fa/fa_logos/{}.jpg'
IMAGE_URL_4 = 'https://financemarker.ru/fa/fa_logos/{}_{}.jpg'


class FinanceMakerRequests:

    def __init__(self):
        self.authorization = AUTHORIZATION
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
            'Host': 'financemarker.ru',
            'Authorization': self.authorization,
            'Referer': 'https://financemarker.ru/insiders/?transaction_type=P',
            'TE': 'Trailers',
            'UI-Language': 'ru'
        }

    def get(self, url):
        response = requests.get(url, headers=self.headers)
        return response


class FinanceMakerImageParser:
    @staticmethod
    def _get_image_content(response):
        extension = 'png'
        f = BytesIO(response.content)
        out = BytesIO()
        image = Image.open(f)
        try:
            image.save(out, extension)
        except OSError:
            return
        content = ContentFile(out.getvalue())
        return content

    def get_image(self, company: Company):
        urls = [IMAGE_URL_1.format(company.code), IMAGE_URL_2.format(company.exchange.name, company.code),
                IMAGE_URL_3.format(company.code), IMAGE_URL_4.format(company.exchange.name, company.code)]
        for url in urls:
            response = requests.get(url)
            if response.status_code == 200:
                image_name = url.split('/')[-1]
                content = self._get_image_content(response)
                if not content:
                    return
                return image_name, content


class DBManager:
    def __init__(self):
        self.insider = DBInsider()
        self.exchange = DBExchange()
        self.company = DBCompany()
        self.news_item = DBNewsItem()
        self.telegraph_page = DBTelegraphPage()
        self.rate = DBTelegramRate()


class DBInsider:
    def __init__(self):
        self.model = Insider

    def bulk_create(self, instances: list):
        self.model.objects.bulk_create(instances, ignore_conflicts=True)

    def create(self, instance, unique_field):
        filter_kwargs = {unique_field: instance.__dict__[unique_field]}
        if not self.model.objects.filter(**filter_kwargs).exists():
            instance.save()
            return instance
        else:
            return self.model.objects.get(**filter_kwargs)

    def filter(self, filter_q: Q):
        return self.model.objects.filter(filter_q)

    @staticmethod
    def save(instance):
        instance.save()


class DBExchange(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = Exchange


class DBCompany(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = Company

    def create(self, instance, unique_field):
        filter_kwargs = {unique_field: instance.__dict__[unique_field]}
        if not self.model.objects.filter(**filter_kwargs).exists():
            # try:
            #     image_content, image_name = FinanceMakerImageParser().get_image(instance)
            # except TypeError:
            #     instance.save()
            #     return instance
            # instance.image.save(image_name, image_content, save=False)
            instance.save()
            return instance
        else:
            return self.model.objects.get(**filter_kwargs)

    @staticmethod
    def save_image(instance, image_name, image_content):
        instance.image.save(image_name, image_content, save=False)


class DBNewsItem(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = NewsItem

    def get_last_by_insider(self, insider: Insider):
        if self.model.objects.filter(insider=insider).exists():
            return self.model.objects.filter(insider=insider).earliest('-publicated')


class DBTelegraphPage(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = TelegraphPage

    def get_by_insider(self, insider: Insider):
        return self.model.objects.filter(insider=insider).first()


class DBTelegramRate(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = Rate

    def is_liked(self, user_id: str, message_id: str):
        if self.model.objects.filter(user_id=user_id, message_id=message_id).exists():
            return True

    def create(self, user_id: str, message_id: str):
        self.model.objects.create(user_id=user_id, message_id=message_id)


class JSONParser:
    def __init__(self, response: str):
        self._response = response
        self._reponse_to_json()

    def _reponse_to_json(self):
        self.json_dict = json.loads(json.loads(self._response))

    @abstractmethod
    def get(self):
        pass


class JSONParserInsiders(JSONParser):
    def __init__(self, response: str):
        super().__init__(response)

    def get(self) -> list:
        insiders = []
        for insider in self.json_dict['data']:
            insider_id = insider['id']
            transaction_date = datetime.strptime(insider['transaction_date'], "%Y-%m-%d")
            insider_model = Insider(fm_id=insider_id,
                                    transaction_date=transaction_date,
                                    transaction_type=insider['transaction_type'],
                                    trades_curr=insider['trades_curr'],
                                    name=insider['name'],
                                    amount=int(insider['amount']),
                                    price=float(insider['price']),
                                    value=float(insider['value'])
                                    )
            exchnage_name = insider['exchange']
            exchnage_fullname = exchnage_name
            if insider['spb']:
                exchnage_fullname += ' SPB'
            exchange = Exchange(name=exchnage_name, full_name=exchnage_fullname)
            exchange = DBManager().exchange.create(exchange, 'full_name')
            insider_model.exchange = exchange
            company = Company(name=insider['owner'], code=insider['code'], exchange=exchange)
            company = DBManager().company.create(company, 'code')
            insider_model.company = company
            insiders.append(insider_model)
        return insiders


class JSONParserLastNewsItem(JSONParser):
    def __init__(self, response: str):
        super().__init__(response)

    def get(self) -> NewsItem:
        if not self.json_dict['data']:
            return
        last_news_json = self.json_dict['data'][0]
        publicated = datetime.strptime(last_news_json['pub_date'], "%Y-%m-%d %H:%M:%S")
        news_item = NewsItem(fm_id=last_news_json['id'], title=last_news_json['title'],
                             content=last_news_json['text'], link=last_news_json['link'],
                             publicated=publicated)
        return news_item


class Updater:
    @abstractmethod
    def update(self, **kwargs):
        pass


class UpdaterInsiders(Updater):
    def update(self):
        response = FinanceMakerRequests().get(INSIDERS_URL)
        if response.status_code == 401:
            print('[ERROR] Истёк токен пользователя')
            sys.exit()
        insiders = JSONParserInsiders(response.text).get()
        DBManager().insider.bulk_create(insiders)


class UpdaterLastNewsItems(Updater):
    def update(self, insiders: list):
        for insider in insiders:
            self.update_last_news_item(insider)
            yield insider

    @staticmethod
    def update_last_news_item(insider: Insider):
        financemaker_requests = FinanceMakerRequests()
        financemaker_requests.headers['Referer'] = REFERER_URL.format(insider.exchange.name, insider.company.code)
        url = NEWS_URL.format(insider.exchange.name, insider.company.code)
        response = financemaker_requests.get(url)
        last_news_item = JSONParserLastNewsItem(response.text).get()
        if not last_news_item:
            return
        last_news_item.insider = insider
        DBManager().news_item.create(last_news_item, 'fm_id')


class UpdaterTelegraphPage(Updater):
    def update(self, insider: Insider):
        self.update_telegraph_page(insider)

    @staticmethod
    def update_telegraph_page(insider: Insider):
        last_news_item = DBManager().news_item.get_last_by_insider(insider)
        if last_news_item:
            telegraph_page = DBManager().telegraph_page.get_by_insider(insider)
            if not telegraph_page:
                telegraph_page = telegraph.TelegraphManager().create_page(insider)
            telegraph_page = telegraph.TelegraphManager().edit_page(telegraph_page, last_news_item)
            DBManager().telegraph_page.save(telegraph_page)


class UpdaterTelegraphPages(UpdaterTelegraphPage):
    def update(self, insiders: list):
        for insider in insiders:
            self.update_telegraph_page(insider)


class InsidersMessager:
    DELAY = 3

    def send_message(self, insider: Insider):
        telegraph_page = DBManager().telegraph_page.get_by_insider(insider)
        message = telegram_bot.Formater().telegram_format(insider, telegraph_page)
        if not insider.company.image:
            try:
                image_name, image_content = FinanceMakerImageParser().get_image(insider.company)
                DBManager().company.save_image(insider.company, image_name, image_content)
            except TypeError:
                telegram_bot.BotManager().send_text_message(message)
        if insider.company.image:
            telegram_bot.BotManager().send_image_message(insider.company.image.path, message)
        insider.tg_messaged = True
        DBManager().insider.save(insider)
        time.sleep(self.DELAY)

    def send_messages(self, insiders: list):
        for insider in insiders:
            self.send_message(insider)


def parser():
    print('[INFO] Update insiders...')
    UpdaterInsiders().update()
    q_filter = Q(tg_messaged=False) & Q(transaction_date__month=datetime.now().month) & Q(
        transaction_date__year=datetime.now().year)
    filtered_insiders = DBManager().insider.filter(q_filter)
    print('[INFO] Update last news...')
    news_items_generator = UpdaterLastNewsItems().update(filtered_insiders)
    for insider in news_items_generator:
        print('[INFO] Update telegraph...')
        UpdaterTelegraphPage().update(insider)
        print('[INFO] Send message...')
        InsidersMessager().send_message(insider)


class Command(BaseCommand):
    help = 'Parser'

    def handle(self, *args, **kwargs):
        bot_thread = telegram_bot.BotThread()
        bot_thread.daemon = True
        bot_thread.start()
        while True:
            parser()
            time.sleep(180)
