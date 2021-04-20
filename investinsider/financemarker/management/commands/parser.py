import sys
import json
import time
import requests
from django.core.management.base import BaseCommand
from datetime import datetime
from financemarker.models import Insider, NewsItem, TelegraphAccount, TelegraphPage
from django.db.models import Q

from abc import abstractmethod

from . import telegraph

AUTHORIZATION = 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2MTc5Njc1MjQsIm5iZiI6MTYxNzk2NzUyNCwianRpIjoiM2UyZWQwN2EtMDY1Mi00ODVjLWI4ZGItNGQ4MDhhMTA4ZmI4IiwiZXhwIjoxNjE4NTcyMzI0LCJpZGVudGl0eSI6MzYxNjcsImZyZXNoIjp0cnVlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsiYWNjZXNzX2xldmVsIjo2LCJkYXRhX2xldmVsIjo2fSwiY3NyZiI6ImUxZGM5YmMwLTY4MjYtNDg3Ny1iY2M1LTMyYTI4NjRjOGRjNyJ9.MtaSpZMqLIVyDkibuzxYuOtwvP_tPDzTEnU-s-DdtQ4'

INSIDERS_URL = 'https://financemarker.ru/api/insiders?transaction_type=P'
REFERER_URL = 'https://financemarker.ru/stocks/{}/{}'  # {insider.exchange} {insider.code}
NEWS_URL = 'https://financemarker.ru/api/news?query={}:{}&type=&page=1'  # {insider.exchange} {insider.code}


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
                                    code=insider['code'],
                                    name=insider['name'],
                                    owner=insider['owner'],
                                    amount=int(insider['amount']),
                                    price=float(insider['price']),
                                    exchange=insider['exchange'],
                                    full_exchange=insider['exchange'],
                                    value=float(insider['value'])
                                    )
            if insider['spb']:
                insider_model.full_exchange += ' SPB'
            insiders.append(insider_model)
        return insiders


class JSONParserLastNewsItem(JSONParser):
    def __init__(self, response: str):
        super().__init__(response)

    def get(self) -> NewsItem:
        if not self.json_dict['data']:
            return
        last_news_json = self.json_dict['data'][0]
        publicated = datetime.strptime(last_news_json['pub_date'], "%Y-%m-%d %M:%H:%S")
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
        insiders = InsidersFilter(insiders).filter()
        Insider.objects.bulk_create(insiders)


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
        if not NewsItem.objects.filter(fm_id=last_news_item.fm_id):
            last_news_item.insider = insider
            last_news_item.save()


class UpdaterTelegraphPages(Updater):
    def update(self, insiders: list):
        for insider in insiders:
            self.update_telegraph_page(insider)

    def update_telegraph_page(self, insider: Insider):
        news_items = NewsItem.objects.filter(insider=insider)
        if news_items:
            news_item = news_items.earliest('-published')
            telegraph_pages_with_news_item = TelegraphPage.objects.filter(news_item=news_item)
            if telegraph_pages_with_news_item:
                return
            else:
                telegraph_pages_with_insider = TelegraphPage.objects.filter(insider=insider)
                if telegraph_pages_with_insider:
                    telegraph_page = telegraph_pages_with_insider[0]
                    # content = telegraph.Formater().telegraph_format(news_item)
                    # telegraph.TelegraphManager().edit_page(telegraph_page, content)
                else:
                    telegraph_page = telegraph.TelegraphManager().create_page(str(insider.code))




# def create_tph_account():
#     url = 'https://api.telegra.ph/createAccount?short_name={}&author_name={}'
#     response = requests.get(url.format(settings.TELEGRAPH_SHORT_NAME, settings.TELEGRAPH_AUTHOR_NAME))
#     if response.status_code == 200:
#         if response.json()['ok']:
#             result = response.json()['result']
#             author_url = result['author_url']
#             access_token = result['access_token']
#             auth_url = result['auth_url']
#             acount = TelegraphAccount.objects.create(short_name=settings.TELEGRAPH_SHORT_NAME,
#                                                      author_name=settings.TELEGRAPH_AUTHOR_NAME,
#                                                      author_url=author_url,
#                                                      access_token=access_token,
#                                                      auth_url=auth_url)
#             return acount
#         else:
#             print('[ERROR] {}'.format(response.json()['error']))
#             sys.exit()


# def get_tph_account():
#     account_filter = TelegraphAccount.objects.filter(short_name=settings.TELEGRAPH_SHORT_NAME)
#     if account_filter:
#         return account_filter[0]
#     else:
#         return create_tph_account()


def parser():
    UpdaterInsiders().update()
    q_filter = Q(tg_messaged=False) & Q(transaction_date__month=datetime.now().month) & Q(
        transaction_date__year=datetime.now().year)
    filtered_insiders = Insider.objects.filter(q_filter)
    UpdaterLastNewsItems().update(filtered_insiders)
    UpdaterTelegraphPages().update(filtered_insiders)


class Command(BaseCommand):
    help = 'Parser'

    def handle(self, *args, **kwargs):
        while True:
            parser()
            time.sleep(180)
