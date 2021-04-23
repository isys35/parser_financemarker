from financemarker.models import Insider, NewsItem, TelegraphAccount, TelegraphPage
import requests
from django.conf import settings
import sys


class TelegraphManager:
    CREATE_ACCOUNT_URL = 'https://api.telegra.ph/createAccount?short_name={}&author_name={}'
    CREATE_PAGE_URL = 'https://api.telegra.ph/createPage?access_token={}&title={}&content={}&return_content=true'
    EDIT_PAGE_URL = 'https://api.telegra.ph/editPage/{}'

    def create_account(self):
        response = requests.get(
            self.CREATE_ACCOUNT_URL.format(settings.TELEGRAPH_SHORT_NAME, settings.TELEGRAPH_AUTHOR_NAME))
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

    def get_account(self):
        account_filter = TelegraphAccount.objects.filter(short_name=settings.TELEGRAPH_SHORT_NAME)
        if account_filter:
            return account_filter[0]
        else:
            return self.create_account()

    def create_page(self, insider: Insider) -> TelegraphPage:
        account = self.get_account()
        access_token = account.access_token
        content = '[{"tag": "p", "children": ["Новая страница"]}]'
        response = requests.get(self.CREATE_PAGE_URL.format(access_token, str(insider.owner), content))
        if response.status_code == 200:
            if response.json()['ok']:
                path = response.json()['result']['path']
                url = response.json()['result']['url']
                title = response.json()['result']['title']
                description = response.json()['result']['description']
                content = str(response.json()['result']['content'])
                return TelegraphPage(path=path, url=url, title=title, description=description, content=content,
                                     account=account, insider=insider)
            else:
                print('[ERROR] {}'.format(response.json()['error']))
                sys.exit()

    def edit_page(self, telegraph_page: TelegraphPage, news_item: NewsItem):
        url = self.EDIT_PAGE_URL.format(telegraph_page.path)
        content = Formater().telegraph_format(news_item)
        json_data = {
            'access_token': telegraph_page.account.access_token,
            'title': telegraph_page.title,
            'content': content,
            'return_content': True
        }
        response = requests.post(url, json=json_data)
        if response.status_code == 200:
            if response.json()['ok']:
                telegraph_page.content = str(content)
                telegraph_page.news_item = news_item
                return telegraph_page
            else:
                print('[ERROR] {}'.format(response.json()['error']))


class Formater:
    def telegraph_format(self, news_item: NewsItem):
        return [{'tag': 'p', 'children': [news_item.insider.owner]},
                {'tag': 'p', 'children': [news_item.content]},
                {'tag': 'a', 'attrs': {'href': settings.TELEGRAM_CHAT}, 'children': ['INVEST INSIDER', '']},
                {'tag': 'br'},
                {'tag': 'a', 'attrs': {'href': news_item.link}, 'children': ['Источник']},
                {'tag': 'br'},
                {'tag': 'p', 'children': [news_item.publicated.strftime("%d.%m.%Y")]},
                {'tag': 'hr'}]
