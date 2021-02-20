import requests
import json
import os
import sys

TELEGRAPH_ACCOUNT_FILE = 'telegraph_account.json'
TELEGRAPH_PAGE_FILE = 'telegraph_page.json'


class Account:
    def __init__(self, json_file):
        self.json_file = json_file
        if not os.path.isfile(self.json_file):
            self.create_json()
        self._init_data()

    def get_data(self):
        with open(self.json_file, 'r') as json_file:
            return json.load(json_file)

    def _init_data(self):
        data = self.get_data()
        self.short_name = data['result']['short_name']
        self.author_name = data['result']['author_name']
        self.access_token = data['result']['access_token']
        self.auth_url = data['result']['auth_url']

    def create_json(self):
        short_name = input('Введите короткое имя: ')
        author_name = input('Введите имя автора: ')
        self.create_account(short_name, author_name)

    def create_account(self, short_name, author_name):
        url = 'https://api.telegra.ph/createAccount?short_name={}&author_name={}'
        response = requests.get(url.format(short_name, author_name))
        if response.status_code == 200:
            if response.json()['ok']:
                with open(self.json_file, 'w') as json_file:
                    json.dump(response.json(), json_file, indent=4)
                print('[INFO] Аккаунт создан')
            else:
                print('[ERROR] {}'.format(response.json()['error']))
                sys.exit()


class Page(Account):
    def __init__(self, json_file):
        super(Page, self).__init__(json_file)

    def _init_data(self):
        data = self.get_data()
        self.path = data['result']['path']
        self.url = data['result']['url']
        self.title = data['result']['title']
        self.description = data['result']['description']
        self.content = data['result']['content']
        self.views = data['result']['views']
        if 'can_edit' in data['result']:
            self.can_edit = data['result']['can_edit']

    def create_json(self):
        title = input('Введите заголовок: ')
        self.create_page(title)

    def create_page(self, title):
        access_token = Account(TELEGRAPH_ACCOUNT_FILE).access_token
        content = '[{"tag": "p", "children": ["Новая страница"]}]'
        url = 'https://api.telegra.ph/createPage?access_token={}&title={}&content={}&return_content=true'
        response = requests.get(url.format(access_token, title, content))
        if response.status_code == 200:
            if response.json()['ok']:
                with open(self.json_file, 'w') as json_file:
                    json.dump(response.json(), json_file, indent=4)
                print('[INFO] Ссылка на tegra.ph страницу: {}'.format(response.json()['result']['url']))
            else:
                print('[ERROR] {}'.format(response.json()['error']))
                sys.exit()


def edit_page(access_token, path, title, content):
    url = 'https://api.telegra.ph/editPage/{}'.format(path)
    json_data = {
        'access_token': access_token,
        'title': title,
        'content': content,
        'return_content': True
    }
    response = requests.post(url, json=json_data)
    if response.status_code == 200:
        if response.json()['ok']:
            with open(TELEGRAPH_PAGE_FILE, 'w') as json_file:
                json.dump(response.json(), json_file, indent=4)
        else:
            print('[ERROR] {}'.format(response.json()['error']))


def update_page_json(path):
    url = 'https://api.telegra.ph/getPage/{}?return_content=true'
    response = requests.get(url.format(path))
    if response.status_code == 200:
        if response.json()['ok']:
            with open(TELEGRAPH_PAGE_FILE, 'w') as json_file:
                json.dump(response.json(), json_file, indent=4)
        else:
            print('[ERROR] {}'.format(response.json()['error']))


def init_news_item(content: list):
    account = Account(TELEGRAPH_ACCOUNT_FILE)
    page = Page(TELEGRAPH_PAGE_FILE)
    edit_page(account.access_token, page.path, page.title, content)


def add_news_item(content: list):
    account = Account(TELEGRAPH_ACCOUNT_FILE)
    page = Page(TELEGRAPH_PAGE_FILE)
    content = page.content + content
    edit_page(account.access_token, page.path, page.title, content)
