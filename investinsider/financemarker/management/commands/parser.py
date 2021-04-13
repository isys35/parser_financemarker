import sys
import json
import time
import requests
from django.core.management.base import BaseCommand
from datetime import datetime
from financemarker.models import Insider, NewsItem, TelegraphAccount
from django.db.models import Q
from django.conf import settings

AUTHORIZATION = 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2MTc5Njc1MjQsIm5iZiI6MTYxNzk2NzUyNCwianRpIjoiM2UyZWQwN2EtMDY1Mi00ODVjLWI4ZGItNGQ4MDhhMTA4ZmI4IiwiZXhwIjoxNjE4NTcyMzI0LCJpZGVudGl0eSI6MzYxNjcsImZyZXNoIjp0cnVlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsiYWNjZXNzX2xldmVsIjo2LCJkYXRhX2xldmVsIjo2fSwiY3NyZiI6ImUxZGM5YmMwLTY4MjYtNDg3Ny1iY2M1LTMyYTI4NjRjOGRjNyJ9.MtaSpZMqLIVyDkibuzxYuOtwvP_tPDzTEnU-s-DdtQ4'

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Host': 'financemarker.ru',
    'Referer': 'https://financemarker.ru/insiders/?transaction_type=P',
    'Authorization': AUTHORIZATION,
    'TE': 'Trailers',
    'UI-Language': 'ru'
}


def get_response(url, headers=None):
    """
    Получение ответа на завпрос
    """
    if headers is None:
        response = requests.get(url)
        if response.status_code == 200:
            return response
        return response
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response
    return response


def update_insiders_from_json(json_data):
    insiders_to_create = []
    for insider in json_data['data']:
        insider_id = insider['id']
        insider_in_db = Insider.objects.filter(fm_id=insider_id)
        if insider_in_db:
            continue
        transaction_date = datetime.strptime(insider['transaction_date'], "%Y-%m-%d")
        if transaction_date.month != datetime.now().month or transaction_date.year != datetime.now().year:
            continue
        print(f'ID {insider_id} to create in DB')
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
        insiders_to_create.append(insider_model)
    Insider.objects.bulk_create(insiders_to_create)


def update_last_news_item_from_json(json_data: dict, insider: Insider):
    """
    Достаём последнюю новость из json
    """
    if not json_data['data']:
        return
    last_news_json = json_data['data'][0]
    fm_id = last_news_json['id']
    filtered_id = NewsItem.objects.filter(fm_id=fm_id)
    if filtered_id:
        return filtered_id[0]
    else:
        publicated = datetime.strptime(last_news_json['pub_date'], "%Y-%m-%d %M:%H:%S")
        news_item = NewsItem.objects.create(fm_id=last_news_json['id'], title=last_news_json['title'],
                                            content=last_news_json['text'], link=last_news_json['link'],
                                            publicated=publicated, insider=insider)
        return news_item


def update_insiders():
    """
    Парсинг инсайдеров
    """
    response = get_response('https://financemarker.ru/api/insiders?transaction_type=P', headers=HEADERS)
    if response.status_code == 401:
        print('[ERROR] Истёк токен пользователя')
        sys.exit()
    json_data = json.loads(response.text)
    json_data = json.loads(json_data)
    update_insiders_from_json(json_data)


def get_last_news(insider: Insider):
    """
    Парсинг новостей
    """
    headers = HEADERS
    headers['Referer'] = 'https://financemarker.ru/stocks/{}/{}'.format(insider.exchange, insider.code)
    url = 'https://financemarker.ru/api/news?query={}:{}&type=&page=1'.format(insider.exchange, insider.code)
    response = get_response(url, headers=headers)
    json_data = json.loads(response.text)
    json_data = json.loads(json_data)
    last_news_item = update_last_news_item_from_json(json_data, insider)
    return last_news_item


def create_tph_account():
    url = 'https://api.telegra.ph/createAccount?short_name={}&author_name={}'
    response = requests.get(url.format(settings.TELEGRAPH_SHORT_NAME, settings.TELEGRAPH_AUTHOR_NAME))
    if response.status_code == 200:
        if response.json()['ok']:
            result = response.json()['result']
            author_url = result['author_url']
            access_token = result['access_token']
            auth_url = result['auth_url']
            acount = TelegraphAccount.objects.create(short_name=settings.TELEGRAPH_SHORT_NAME,
                                                     author_name=settings.TELEGRAPH_AUTHOR_NAME,
                                                     author_url=author_url,
                                                     access_token=access_token,
                                                     auth_url=auth_url)
            return acount
        else:
            print('[ERROR] {}'.format(response.json()['error']))
            sys.exit()


def get_tph_account():
    account_filter = TelegraphAccount.objects.filter(short_name=settings.TELEGRAPH_SHORT_NAME)
    if account_filter:
        return account_filter[0]
    else:
        return create_tph_account()


class Command(BaseCommand):
    help = 'Parser'

    def handle(self, *args, **kwargs):
        tph_account = get_tph_account()
        print(tph_account)
        while True:
            update_insiders()
            q_filter = Q(tg_messaged=False) & Q(transaction_date__month=datetime.now().month) & Q(
                transaction_date__year=datetime.now().year)
            filtered_insiders = Insider.objects.filter(q_filter)
            for insider in filtered_insiders:
                news_item = get_last_news(insider)

                if news_item:
                    pass
            time.sleep(180)
