from financemarker.models import Insider, NewsItem, TelegraphAccount, TelegraphPage
import requests
from django.conf import settings
import sys


class TelegraphManager:
    CREATE_ACCOUNT_URL = 'https://api.telegra.ph/createAccount?short_name={}&author_name={}'
    CREATE_PAGE_URL = 'https://api.telegra.ph/createPage?access_token={}&title={}&content={}&return_content=true'

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

    def create_page(self, title) -> TelegraphPage:
        account = self.get_account()
        access_token = account.access_token
        content = '[{"tag": "p", "children": ["Новая страница"]}]'
        response = requests.get(self.CREATE_PAGE_URL.format(access_token, title, content))
        if response.status_code == 200:
            if response.json()['ok']:
                return TelegraphPage()
            else:
                print('[ERROR] {}'.format(response.json()['error']))
                sys.exit()


class Formater:
    def telegraph_format(self, news_item: NewsItem):
        pass
