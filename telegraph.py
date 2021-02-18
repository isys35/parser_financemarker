import requests
import json

TELEGRAPH_ACCOUNT_FILE = 'telegraph_account.json'
TELEGRAPH_PAGE_FILE = 'telegraph_page.json'


def create_account(short_name, author_name):
    url = 'https://api.telegra.ph/createAccount?short_name={}&author_name={}'
    response = requests.get(url.format(short_name, author_name))
    if response.status_code == 200:
        with open(TELEGRAPH_ACCOUNT_FILE, 'w') as json_file:
            json.dump(response.json(), json_file, indent=4)
        print('[INFO] Аккаунт создан')


def create_page(access_token, title, content):
    url = 'https://api.telegra.ph/createPage?access_token={}&title={}&content={}&return_content=true'
    response = requests.get(url.format(access_token, title, content))
    if response.status_code == 200:
        if response.status_code == 200:
            with open(TELEGRAPH_PAGE_FILE, 'w') as json_file:
                json.dump(response.json(), json_file, indent=4)


def get_account():
    with open(TELEGRAPH_ACCOUNT_FILE, 'r') as json_file:
        return json.load(json_file)


def get_page():
    with open(TELEGRAPH_PAGE_FILE, 'r') as json_file:
        return json.load(json_file)


if __name__ == '__main__':
    print(get_account())
