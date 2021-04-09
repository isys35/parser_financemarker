import sys
import json
import time
import requests
from django.core.management.base import BaseCommand
from datetime import datetime
from financemarker.models import Insider

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
    """
    Достаем из json данные по фильтрам
    """
    insiders_to_create = []
    for insider in json_data['data']:
        insider_id = insider['id']
        insider_in_db = Insider.objects.filter(fm_id=insider_id)
        if insider_in_db:
            print(f'ID {insider_id} in DB')
            continue
        print(f'ID {insider_id} to create in DB')
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
        insiders_to_create.append(insider_model)
    Insider.objects.bulk_create(insiders_to_create)


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


class Command(BaseCommand):
    help = 'Parser'

    def handle(self, *args, **kwargs):
        while True:
            update_insiders()

            time.sleep(180)

