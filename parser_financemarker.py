import requests
import json
import time
import bot
import sys
import os
import config
import telegraph

DELAY = 180  # Задержка в секундах
HISTORY_INSIDER_FILE_NAME = 'history_insider.txt'
HISTORY_NEWS_FILE_NAME = 'history_news.txt'

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

selected_exchange = ['SPB', 'MOEX', 'NASDAQ', 'NYSE']
selected_transaction_type = ['P', 'S', 'M']


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
        self.full_exchange = exchange
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

    def get_prepared_message(self):
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
                                   self.full_exchange,
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


class NewsItem:
    def __init__(self, id, title, text, link, pub_date):
        self.id = str(id)
        self.title = title
        self.text = text
        self.link = link
        self.pub_date = pub_date

    def __str__(self):
        return f'{self.title}\n{self.text}\n{self.pub_date}\n{self.link}'

    def get_prepared_news_item(self):
        prepared_news = [{'tag': 'p', 'children': [self.title]},
                         {'tag': 'p', 'children': [self.text]},
                         {'tag': 'a', 'attrs': {'href': config.TELEGRAM_CHAT}, 'children': ['INVEST INSIDER', '']},
                         {'tag': 'br'},
                         {'tag': 'a', 'attrs': {'href': self.link}, 'children': ['Источник']},
                         {'tag': 'br'},
                         {'tag': 'p', 'children': [self.pub_date]},
                         {'tag': 'hr'}]
        return prepared_news


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


def get_history(history_file_name):
    """
    Получаем лист с использованными id insider
    """
    if not os.path.isfile(history_file_name):
        return []
    else:
        with open(history_file_name, 'r') as history_file:
            return history_file.read().split('\n')


def save_history(history_file_name, id):
    """
    Сохранение id в истории
    """
    if not os.path.isfile(history_file_name):
        with open(history_file_name, 'w') as history_file:
            history_file.write(str(id) + "\n")
    else:
        with open(history_file_name, 'a') as history_file:
            history_file.write(str(id) + "\n")


def parse_insiders_from_json(json_data, month_filter, year_filter):
    """
    Достаем из json данные по фильтрам
    """
    total_insiders = []
    for insider in json_data['data']:
        transaction_date = insider['transaction_date']
        transaction_date = change_date_format(transaction_date)
        transaction_type = insider['transaction_type']
        if transaction_type in selected_transaction_type:
            if _is_suitable_by_date(transaction_date, month_filter, year_filter):
                insider_object = Insider(id=insider['id'],
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
                if insider['spb']:
                    insider_object.full_exchange += ' SPB'
                if insider['exchange'] in selected_exchange:
                    total_insiders.append(insider_object)
                else:
                    if 'SPB' in selected_exchange and insider['spb']:
                        total_insiders.append(insider_object)
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


def get_insiders():
    """
    Парсинг инсайдеров
    """
    response = get_response('https://financemarker.ru/api/insiders?transaction_type=P', headers=HEADERS_TRANSACTION_P)
    if response.status_code == 401:
        print('[ERROR] Истёк токен пользователя')
        sys.exit()
    json_data = json.loads(response.text)
    json_data = json.loads(json_data)
    month_now = time.strftime("%m")
    year_now = time.strftime("%Y")
    insiders = parse_insiders_from_json(json_data,
                                        month_filter=month_now,
                                        year_filter=year_now)

    return insiders


def get_news_item(insider: Insider):
    """
    Парсинг новостей
    """
    headers = HEADERS_TRANSACTION_P
    headers['Referer'] = 'https://financemarker.ru/stocks/{}/{}'.format(insider.code, insider.exchange)
    url = 'https://financemarker.ru/api/news?query={}&type=&page=1'.format(insider.code)
    response = get_response(url, headers=headers)
    json_data = json.loads(response.text)
    json_data = json.loads(json_data)
    last_news_item = parse_last_news_item_from_json(json_data)
    return last_news_item


def parse_last_news_item_from_json(json_data):
    """
    Достаём последнюю новость из json
    """
    if not json_data['data']:
        return
    last_news_json = json_data['data'][0]
    news_date, news_time = last_news_json['pub_date'].split(' ')
    news_date = change_date_format(news_date)
    date = '{} {}'.format(news_date, news_time)
    news_item = NewsItem(id=last_news_json['id'],
                         title=last_news_json['title'],
                         text=last_news_json['text'],
                         link=last_news_json['link'],
                         pub_date=date)
    return news_item


def parser():
    """
    Парсер данных
    """
    insiders = get_insiders()
    insiders.sort(key=lambda ins: int(ins.transaction_date.split('.')[0]))
    for insider in insiders:
        if insider.id not in get_history(HISTORY_INSIDER_FILE_NAME):
            message = insider.get_prepared_message()
            news_item = get_news_item(insider)
            if news_item:
                print(news_item)
                if news_item.id not in get_history(HISTORY_NEWS_FILE_NAME):
                    news_content = news_item.get_prepared_news_item()
                    telegraph.update_news(news_content, insider.code)
                    save_history(HISTORY_NEWS_FILE_NAME, news_item.id)
            if news_item:
                json_path_insider = telegraph.get_json_path_insider(insider.code)
                message += '<a href="{}">Новости</a>'.format(telegraph.Page(json_path_insider, insider.code).url)
            print(message)
            bot.send_info_in_group(message)
            save_history(HISTORY_INSIDER_FILE_NAME, insider.id)
            time.sleep(3)


if __name__ == '__main__':
    while True:
        parser()
        time.sleep(DELAY)
