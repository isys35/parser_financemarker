import requests
import json
import time
import bot

DELAY = 180  # Задержка в секундах

HEADERS_TRANSACTION_P = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Host': 'financemarker.ru',
    'Referer': 'https://financemarker.ru/insiders/?transaction_type=P',
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2MTMxNTU2ODksIm5iZiI6MTYxMzE1NTY4OSwianRpIjoiZTY0ZGVlZjYtZjg3Ni00ZTJmLTg3ODQtZjFjODdmZDZlNTJhIiwiZXhwIjoxNjEzNzYwNDg5LCJpZGVudGl0eSI6MzE5ODksImZyZXNoIjp0cnVlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsiYWNjZXNzX2xldmVsIjo2fSwiY3NyZiI6IjM2ZDEyNDI4LThkNWEtNDAxNy1hYjdlLWE3NjA0OWNmNzFhZiJ9.2afDb9kK-AKaXArIv9jh1dj_AfoHYvCLfbBVVeJRMbw',
    'TE': 'Trailers',
    'UI-Language': 'ru'
}

MESSAGE = """«{}»

Биржа: {}
Компания: {}
Название: {}
Инсайдер: {}
Сделка: {}
Кол-во: {}
Цена: {} ₽
Сумма: {} ₽
Дата: {}

"""


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


def parse_insiders_from_json(json_data, transaction_type_filter, month_filter):
    """
    Достаем из json данные по фльтрам
    """
    total_insiders = []
    for insider in json_data['data']:
        code = insider['code']
        transaction_date = insider['transaction_date']
        transaction_date = change_date_format(transaction_date)
        name = insider['name']
        owner = insider['owner']
        amount = insider['amount']
        price = insider['price']
        value = insider['value']
        exchange = insider['exchange']
        transaction_type = insider['transaction_type']
        if transaction_type == transaction_type_filter and transaction_date.split('.')[1] == month_filter:
            total_insiders.append(
                {'code': code,
                 'transaction_date': transaction_date,
                 'name': name,
                 'owner': owner,
                 'amount': amount,
                 'price': price,
                 'transaction_type': transaction_type,
                 'exchange': exchange,
                 'value': value}
            )
    return total_insiders


def change_date_format(date: str):  # initial date format: yyyy-mm-dd
    """
    Изменение формата даты
    """
    splited_date = date.split('-')
    date = '.'.join([splited_date[2], splited_date[1], splited_date[0]])
    return date


def save_page(response: str, file_name='page.html'):
    """
    Для теста.
    Сохранение запроса в файл
    """
    with open(file_name, 'w', encoding='utf-8') as html_file:
        html_file.write(response)


def get_message(insiders: list):
    """Подготовка сообщений для телеграмм бота"""
    messages = []
    for insider in insiders:
        transaction_name = ''
        if insider['transaction_type'] == 'P':
            transaction_name = "Покупка"
        elif insider['transaction_type'] == 'S':
            transaction_name = "Продажа"
        elif insider['transaction_type'] == 'M':
            transaction_name = "Опцион"
        message = MESSAGE.format(transaction_name,
                                 insider['exchange'],
                                 insider['code'],
                                 insider['name'],
                                 insider['owner'],
                                 transaction_name,
                                 insider['amount'],
                                 insider['price'],
                                 insider['value'],
                                 insider['transaction_date'])
        messages.append(message)
    return messages


def parser():
    """
    Парсер данных
    """
    response = get_response('https://financemarker.ru/api/insiders?transaction_type=P', headers=HEADERS_TRANSACTION_P)
    json_data = json.loads(response.text)
    json_data = json.loads(json_data)
    month_now = time.strftime("%m")
    insiders_p = parse_insiders_from_json(json_data, transaction_type_filter='P', month_filter=month_now)
    insiders_s = parse_insiders_from_json(json_data, transaction_type_filter='S', month_filter=month_now)
    insiders_m = parse_insiders_from_json(json_data, transaction_type_filter='M', month_filter=month_now)
    messages = get_message(insiders_p) + get_message(insiders_s) + get_message(insiders_m)
    for message in messages:
        # bot.send_info_in_group(message)
        print(message)
        time.sleep(3)


if __name__ == '__main__':
    while True:
        parser()
        time.sleep(DELAY)
