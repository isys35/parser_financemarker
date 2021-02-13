import requests
import json
import time
import bot
import os
import config

DELAY = 180  # Задержка в секундах
HISTORY_FILE_NAME = 'history.txt'

HEADERS_TRANSACTION_P = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Host': 'financemarker.ru',
    'Referer': 'https://financemarker.ru/insiders/?transaction_type=P',
    'Authorization': config.AUTHORIZATION,
    'TE': 'Trailers',
    'UI-Language': 'ru'
}

selected_exchange = ['NASDAQ', 'MOEX', 'NYSE', 'XETRA']


class Insider:
    """
    Класс для работы с данными
    """
    MESSAGE = """
«{}»

Биржа: {}
Компания: {}
Название: {}
Инсайдер: {}
Сделка: {}
Кол-во: {}
Цена: {} {}
Сумма: {} {}
Дата: {}

"""

    def __init__(self, id, exchange, transaction_type, code, transaction_date, name, owner, amount, price,
                 value, trades_curr):
        self.id = str(id)
        self.exchange = exchange
        self.transaction_type = transaction_type
        self.code = code
        self.transaction_date = transaction_date
        self.name = name
        self.owner = owner
        self.amount = int(amount)
        self.price = float(price)
        self.value = float(value)
        self.transaction_name = None
        self.trades_curr = trades_curr

    def get_message(self):
        """
        Подготовка сообщения для телеграм
        """
        if self.transaction_type == 'P':
            self.transaction_name = "Покупка"
        elif self.transaction_type == 'S':
            self.transaction_name = "Продажа"
        elif self.transaction_type == 'M':
            self.transaction_name = "Опцион"
        curr_symbol = ''
        if self.trades_curr == 'RUB':
            curr_symbol = '₽'
        elif self.trades_curr == 'USD':
            curr_symbol = '$'
        price = '{0:,}'.format(self.price).replace(',', ' ')
        value = '{0:,}'.format(self.value).replace(',', ' ')
        return self.MESSAGE.format(self.transaction_name,
                                   self.exchange,
                                   self.code,
                                   self.name,
                                   self.owner,
                                   self.transaction_name,
                                   self.amount,
                                   price,
                                   curr_symbol,
                                   value,
                                   curr_symbol,
                                   self.transaction_date)


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


def get_history():
    """
    Получаем лист с использованными id insider
    """
    if not os.path.isfile(HISTORY_FILE_NAME):
        return []
    else:
        with open(HISTORY_FILE_NAME, 'r') as history_file:
            return history_file.read().split('\n')


def save_history(id):
    """
    Сохранение id в истории
    """
    if not os.path.isfile(HISTORY_FILE_NAME):
        with open(HISTORY_FILE_NAME, 'w') as history_file:
            history_file.write(str(id) + "\n")
    else:
        with open(HISTORY_FILE_NAME, 'a') as history_file:
            history_file.write(str(id) + "\n")


def parse_insiders_from_json(json_data, transaction_type_filter, month_filter, year_filter):
    """
    Достаем из json данные по фильтрам
    """
    total_insiders = []
    for insider in json_data['data']:
        transaction_date = insider['transaction_date']
        transaction_date = change_date_format(transaction_date)
        transaction_type = insider['transaction_type']
        if transaction_type == transaction_type_filter:
            if _is_suitable_by_date(transaction_date, month_filter, year_filter):
                if insider['exchange'] in selected_exchange:
                    total_insiders.append(Insider(id=insider['id'],
                                                  code=insider['code'],
                                                  transaction_date=transaction_date,
                                                  name=insider['name'],
                                                  owner=insider['owner'],
                                                  amount=insider['amount'],
                                                  price=insider['price'],
                                                  transaction_type=transaction_type,
                                                  exchange=insider['exchange'],
                                                  value=insider['value'],
                                                  trades_curr=insider['trades_curr'])
                                          )
    return total_insiders


def _is_suitable_by_date(date, month_filter, year_filter):
    """
    Проверка данных по дате
    """
    if date.split('.')[1] == month_filter:
        if date.split('.')[2] == year_filter:
            return True


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
    year_now = time.strftime("%Y")
    insiders_p = parse_insiders_from_json(json_data, transaction_type_filter='P',
                                          month_filter=month_now,
                                          year_filter=year_now)
    insiders_p.sort(key=lambda ins: int(ins.transaction_date.split('.')[0]))
    insiders_s = parse_insiders_from_json(json_data, transaction_type_filter='S',
                                          month_filter=month_now,
                                          year_filter=year_now)
    insiders_s.sort(key=lambda ins: int(ins.transaction_date.split('.')[0]))
    insiders_m = parse_insiders_from_json(json_data, transaction_type_filter='M',
                                          month_filter=month_now,
                                          year_filter=year_now)
    insiders_m.sort(key=lambda ins: int(ins.transaction_date.split('.')[0]))
    insiders = insiders_p + insiders_s + insiders_m
    for insider in insiders:
        if insider.id not in get_history():
            message = insider.get_message()
            bot.send_info_in_group(message)
            save_history(insider.id)
            time.sleep(3)


if __name__ == '__main__':
    while True:
        parser()
        time.sleep(DELAY)
