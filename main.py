import requests
import json
import time

HEADERS_TRANSACTION_P = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Host': 'financemarker.ru',
    'Referer': 'https://financemarker.ru/insiders/?transaction_type=P',
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
        transaction_type = insider['transaction_type']
        if transaction_type == transaction_type_filter and transaction_date.split('.')[1] == month_filter:
            total_insiders.append(
                {'code': code,
                 'transaction_date': transaction_date,
                 'name': name,
                 'owner': owner,
                 'amount': amount,
                 'price': price,
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
    print(insiders_s)


if __name__ == '__main__':
    parser()
