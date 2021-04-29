import sys
import json
import time
import requests
from django.core.management.base import BaseCommand
from datetime import datetime
from financemarker.models import Insider, NewsItem, TelegraphAccount, \
    TelegraphPage, Exchange, Company, Rate, Source
from django.db.models import Q
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from abc import abstractmethod
from requests import Response

from . import telegraph, telegram_bot

AUTHORIZATION = 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2MTk2ODc1MzEsIm5iZiI6MTYxOTY4NzUzMSwianRpIjoiNDQyMGRkMDYtOTdmMy00OTdmLWIxODAtYWIwZWIzMDI5MTkwIiwiZXhwIjoxNjIwMjkyMzMxLCJpZGVudGl0eSI6MzgwNjMsImZyZXNoIjp0cnVlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsiYWNjZXNzX2xldmVsIjo2LCJkYXRhX2xldmVsIjo2fSwiY3NyZiI6ImVlYjA1NjVjLTk5ZGQtNDUwNC05OWFiLTE2ZjE1ZGY2MDE5YiJ9.ZeSj1qyE4h5THXZvc4Igh5HdJXTSI-OSs0SyFUutcYY'

INSIDERS_URL = 'https://financemarker.ru/api/insiders?transaction_type=P'
REFERER_URL = 'https://financemarker.ru/stocks/{}/{}'  # {insider.exchange.name} {insider.company.code}
NEWS_URL = 'https://financemarker.ru/api/news?query={}:{}&type=&page=1'  # {insider.exchange.name} {insider.company.code}
IMAGE_URL_1 = 'https://financemarker.ru/fa/fa_logos/{}.png'
IMAGE_URL_2 = 'https://financemarker.ru/fa/fa_logos/{}_{}.png'
IMAGE_URL_3 = 'https://financemarker.ru/fa/fa_logos/{}.jpg'
IMAGE_URL_4 = 'https://financemarker.ru/fa/fa_logos/{}_{}.jpg'
IMAGE_URL_5 = 'https://financemarker.ru/fa/fa_logos/{}.PNG'
IMAGE_URL_6 = 'https://financemarker.ru/fa/fa_logos/{}_{}.PNG'
IMAGE_URL_7 = 'https://financemarker.ru/fa/fa_logos/{}.JPG'
IMAGE_URL_8 = 'https://financemarker.ru/fa/fa_logos/{}_{}.JPG'


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
                IMAGE_URL_3.format(company.code), IMAGE_URL_4.format(company.exchange.name, company.code),
                IMAGE_URL_5.format(company.code), IMAGE_URL_6.format(company.exchange.name, company.code),
                IMAGE_URL_7.format(company.code), IMAGE_URL_7.format(company.exchange.name, company.code),]
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
        self.source = DBSource()


class DBInsider:
    def __init__(self):
        self.model = Insider

    def bulk_create(self, instances: list):
        self.model.objects.bulk_create(instances, ignore_conflicts=True)

    def get_or_create(self, instance):
        params = {k: v for k, v in instance.__dict__.items() if k[0] != '_' if k !='id'}
        obj, created = self.model.objects.get_or_create(params)
        return obj

    def filter(self, filter_q: Q):
        return self.model.objects.filter(filter_q)

    @staticmethod
    def save(instance):
        instance.save()


class DBSource(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = Source


class DBExchange(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = Exchange


class DBCompany(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = Company


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

    def get_by_company(self, company: Company):
        if self.model.objects.filter(company=company, source__trusted=True).exists():
            return self.model.objects.filter(company=company)


class DBTelegraphPage(DBInsider):
    def __init__(self):
        super().__init__()
        self.model = TelegraphPage

    def get_by_insider(self, insider: Insider):
        return self.model.objects.filter(insider=insider).first()

    def get_by_company(self, company: Company):
        return self.model.objects.filter(company=company).first()


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
                                    name=insider['owner'],
                                    amount=int(insider['amount']),
                                    price=float(insider['price']),
                                    value=float(insider['value'])
                                    )
            exchnage_name = insider['exchange']
            exchnage_fullname = exchnage_name
            if insider['spb']:
                exchnage_fullname += ' SPB'
            exchange = Exchange(name=exchnage_name, full_name=exchnage_fullname)
            exchange = DBManager().exchange.get_or_create(exchange)
            insider_model.exchange = exchange
            company = Company(name=insider['name'], code=insider['code'], exchange=exchange)
            company = DBManager().company.get_or_create(company)
            insider_model.company = company
            insiders.append(insider_model)
        return insiders


class JSONParserNewsItems(JSONParser):
    def __init__(self, response: str):
        super().__init__(response)

    def get(self) -> NewsItem:
        if not self.json_dict['data']:
            return
        news_items_json = self.json_dict['data']
        news_items = []
        for news_item_json in news_items_json:
            source = DBManager().source.get_or_create(Source(link=news_item_json['link']))
            publicated = datetime.strptime(news_item_json['pub_date'], "%Y-%m-%d %H:%M:%S")
            news_item = NewsItem(fm_id=news_item_json['id'], title=news_item_json['title'],
                                 content=news_item_json['text'], source=source,
                                 publicated=publicated)
            news_items.append(news_item)
        return news_items


class JSONParserLastNewsItem(JSONParserNewsItems):
    def __init__(self, response: str):
        super().__init__(response)

    def get(self) -> NewsItem:
        if not self.json_dict['data']:
            return
        return super().get()[0]


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

    def get_news_response(self, insider: Insider) -> Response:
        financemaker_requests = FinanceMakerRequests()
        financemaker_requests.headers['Referer'] = REFERER_URL.format(insider.exchange.name, insider.company.code)
        url = NEWS_URL.format(insider.exchange.name, insider.company.code)
        response = financemaker_requests.get(url)
        return response

    def update_last_news_item(self, insider: Insider):
        response = self.get_news_response(insider)
        last_news_item = JSONParserLastNewsItem(response.text).get()
        if not last_news_item:
            return
        last_news_item.insider = insider
        DBManager().news_item.get_or_create(last_news_item)


class UpdaterNewsItems(UpdaterLastNewsItems):
    def update(self, insiders: list):
        for insider in insiders:
            self.update_news_items(insider)
            yield insider

    def update_news_items(self, insider: Insider):
        response = self.get_news_response(insider)
        news_items = JSONParserNewsItems(response.text).get()
        if news_items:
            for news_item in news_items:
                news_item.company = insider.company
            DBManager().news_item.bulk_create(news_items)


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
            telegraph_content = telegraph.Formater().telegraph_format(last_news_item)
            telegraph_page = telegraph.TelegraphManager().edit_page(telegraph_page, telegraph_content)
            DBManager().telegraph_page.save(telegraph_page)


class UpdaterTelegraphPageManyNews(UpdaterTelegraphPage):

    @staticmethod
    def update_telegraph_page(insider: Insider):
        news_items = DBManager().news_item.get_by_company(insider.company)
        if news_items:
            telegraph_page = DBManager().telegraph_page.get_by_company(insider.company)
            if not telegraph_page:
                telegraph_page = telegraph.TelegraphManager().create_page(insider.company)
            telegraph_content = telegraph.Formater().telegraph_format_many_items(news_items)
            telegraph_page = telegraph.TelegraphManager().edit_page(telegraph_page, telegraph_content)
            telegraph_page = DBManager().telegraph_page.save(telegraph_page)
            for news_item in news_items:
                news_item.telegraph_page = telegraph_page
                DBManager().news_item.save(news_item)
        else:
            telegraph_page = DBManager().telegraph_page.get_by_company(insider.company)
            if telegraph_page:
                telegraph_page = telegraph.TelegraphManager().edit_page(telegraph_page,
                                                                        telegraph.TelegraphManager().TELEGRAPH_INIT_CONTENT)
                DBManager().telegraph_page.save(telegraph_page)



class UpdaterTelegraphPages(UpdaterTelegraphPage):
    def update(self, insiders: list):
        for insider in insiders:
            self.update_telegraph_page(insider)


class InsidersMessager:
    DELAY = 3

    def send_message(self, insider: Insider):
        telegraph_page = DBManager().telegraph_page.get_by_company(insider.company)
        message = telegram_bot.Formater().telegram_format(insider, telegraph_page)
        if not insider.company.image:
            try:
                image_name, image_content = FinanceMakerImageParser().get_image(insider.company)
                DBManager().company.save_image(insider.company, image_name, image_content)
                DBManager().company.save(insider.company)
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
    news_items_generator = UpdaterNewsItems().update(filtered_insiders)
    for insider in news_items_generator:
        print('[INFO] Update telegraph...')
        UpdaterTelegraphPageManyNews().update(insider)
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
