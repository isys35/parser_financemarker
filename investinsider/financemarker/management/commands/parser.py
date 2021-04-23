import sys
import json
import time
import requests
from django.core.management.base import BaseCommand
from datetime import datetime
from financemarker.models import Insider, NewsItem, TelegraphAccount, TelegraphPage, Exchange, Company
from django.db.models import Q
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from abc import abstractmethod

from . import telegraph, telegram_bot

AUTHORIZATION = 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2MTg5ODk1MjMsIm5iZiI6MTYxODk4OTUyMywianRpIjoiMWEzY2U4MjEtMTVlNC00MzYwLWE5NTEtYWE1MDg1Nzk5ODIyIiwiZXhwIjoxNjE5NTk0MzIzLCJpZGVudGl0eSI6Mzc1MjgsImZyZXNoIjp0cnVlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsiYWNjZXNzX2xldmVsIjo2LCJkYXRhX2xldmVsIjo2fSwiY3NyZiI6IjM3NWM1MGEwLTg2NzctNGJiNC1hYTUxLTBlM2I3NzNhZDE5NSJ9.VyuxlqfLsUNfKJb4V9VXfKtL2XnQlgslV49tgUGErus'

INSIDERS_URL = 'https://financemarker.ru/api/insiders?transaction_type=P'
REFERER_URL = 'https://financemarker.ru/stocks/{}/{}'  # {insider.exchange} {insider.code}
NEWS_URL = 'https://financemarker.ru/api/news?query={}:{}&type=&page=1'  # {insider.exchange} {insider.code}
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
    def get_image(self, company: Company):
        url = IMAGE_URL_1.format(company.code)
        response = requests.get(url)
        if response.status_code != 200:
            url = IMAGE_URL_2.format(company.exchange.name, company.code)
            response = requests.get(url)
        if response.status_code != 200:
            url = IMAGE_URL_3.format(company.code)
            response = requests.get(url)
        if response.status_code != 200:
            url = IMAGE_URL_4.format(company.exchange.name, company.code)
            response = requests.get(url)
        if response.status_code == 200:
            image_name = url.split('/')[-1]
            extension = 'png'
            f = BytesIO(response.content)
            out = BytesIO()
            image = Image.open(f)
            try:
                image.save(out, extension)
            except OSError:
                return
            content = ContentFile(out.getvalue())
            return content, image_name


class DB:
    @staticmethod
    def create_insiders(insiders: list):
        Insider.objects.bulk_create(insiders)

    @staticmethod
    def get_or_create_exchange(exchange_name: str, exchange_fullname: str):
        return Exchange.objects.get_or_create(name=exchange_name, full_name=exchange_fullname)[0]

    @staticmethod
    def get_or_create_company(company_name, company_code, exchange):
        search_filter = Company.objects.filter(code=company_code)
        if search_filter:
            return search_filter[0]
        company = Company(name=company_name, code=company_code, exchange=exchange)
        try:
            image_content, image_name = FinanceMakerImageParser().get_image(company)
        except TypeError:
            company.save()
            return company
        company.image.save(image_name, image_content, save=False)
        company.save()
        return company

    @staticmethod
    def get_or_create_last_news_item(last_news_item: NewsItem):
        search_filter = NewsItem.objects.filter(fm_id=last_news_item.fm_id)
        if not search_filter:
            last_news_item.save()
            return last_news_item
        else:
            return search_filter[0]

    @staticmethod
    def insiders_filter_to_create(insiders: list):
        return InsidersFilter(insiders).filter()

    @staticmethod
    def insiders_filter_to_update_news():
        q_filter = Q(tg_messaged=False) & Q(transaction_date__month=datetime.now().month) & Q(
            transaction_date__year=datetime.now().year)
        filtered_insiders = Insider.objects.filter(q_filter).order_by('transaction_date')
        return filtered_insiders


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
            exchange = DB().get_or_create_exchange(exchnage_name, exchnage_fullname)
            insider_model.exchange = exchange
            company = DB().get_or_create_company(insider['owner'], insider['code'], exchange)
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


class InsidersFilter:
    def __init__(self, insiders):
        self.insiders = insiders

    def filter(self):
        filtered_list = []
        for insider in self.insiders:
            insider_in_db = Insider.objects.filter(fm_id=insider.fm_id)
            if insider_in_db:
                continue
            if insider.transaction_date.month != datetime.now().month or insider.transaction_date.year != datetime.now().year:
                continue
            filtered_list.append(insider)
        return filtered_list


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
        insiders = DB().insiders_filter_to_create(insiders)
        DB().create_insiders(insiders)


class UpdaterLastNewsItems(Updater):
    def update(self, insiders: list):
        for insider in insiders:
            self.update_last_news_item(insider)

    def update_last_news_item(self, insider: Insider):
        financemaker_requests = FinanceMakerRequests()
        financemaker_requests.headers['Referer'] = REFERER_URL.format(insider.exchange, insider.code)
        url = NEWS_URL.format(insider.exchange, insider.code)
        response = financemaker_requests.get(url)
        last_news_item = JSONParserLastNewsItem(response.text).get()
        if not last_news_item:
            return
        last_news_item.insider = insider
        DB().get_or_create_last_news_item(last_news_item)


class UpdaterTelegraphPages(Updater):
    def update(self, insiders: list):
        for insider in insiders:
            self.update_telegraph_page(insider)

    def check_last_news_item(self, insider: Insider):
        news_items = NewsItem.objects.filter(insider=insider)
        if news_items:
            news_item = news_items.earliest('-publicated')
            telegraph_pages_with_news_item = TelegraphPage.objects.filter(news_item=news_item)
            if not telegraph_pages_with_news_item:
                return True

    def update_telegraph_page(self, insider: Insider):
        if self.check_last_news_item(insider):
            telegraph_pages_with_insider = TelegraphPage.objects.filter(insider=insider)
            if telegraph_pages_with_insider:
                telegraph_page = telegraph_pages_with_insider[0]
            else:
                telegraph_page = telegraph.TelegraphManager().create_page(insider)
            news_item = NewsItem.objects.filter(insider=insider).earliest('-publicated')
            telegraph.TelegraphManager().edit_page(telegraph_page, news_item)


class InsidersMessager:
    DELAY = 3

    def send_messages(self, insiders: list):
        for insider in insiders:
            telegraph_pages = TelegraphPage.objects.filter(insider=insider)
            if telegraph_pages:
                telegraph_page = telegraph_pages[0]
            else:
                telegraph_page = None
            message = telegram_bot.Formater().telegram_format(insider, telegraph_page)
            telegram_bot.BotManager().send_text_message(message)
            time.sleep(self.DELAY)


def parser():
    print('[INFO] Update insiders...')
    UpdaterInsiders().update()
    filtered_insiders = DB().insiders_filter_to_update_news()
    print('[INFO] Update last news...')
    UpdaterLastNewsItems().update(filtered_insiders)
    print('[INFO] Update telegraph...')
    UpdaterTelegraphPages().update(filtered_insiders)
    # InsidersMessager().send_messages(filtered_insiders)
    # message = render_to_string('telegram_message/message.html')
    # telegram_bot.send_message(message)


class Command(BaseCommand):
    help = 'Parser'

    def handle(self, *args, **kwargs):
        bot_thread = telegram_bot.BotThread()
        bot_thread.daemon = True
        bot_thread.start()
        while True:
            parser()
            time.sleep(180)
