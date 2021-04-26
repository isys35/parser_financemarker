from django.db import models


class Insider(models.Model):
    TRANSACTION_TYPE = (
        ('P', 'Покупка'),
        ('S', 'Продажа'),
        ('M', 'Опцион')
    )
    TRADES_CURR = (
        ('RUB', '₽'),
        ('USD', '$'),
    )
    fm_id = models.CharField(max_length=30, verbose_name='financemarker ID', unique=True)
    exchange = models.ForeignKey('Exchange', null=False, on_delete=models.PROTECT, verbose_name='Биржа')
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPE, blank=False, null=False,
                                        verbose_name='Тип транзакции')
    company = models.ForeignKey('Company', null=False, on_delete=models.PROTECT, verbose_name='Компания')
    transaction_date = models.DateField(verbose_name='Дата транзакции')
    name = models.CharField(null=True, max_length=20, verbose_name='Название')
    amount = models.IntegerField(null=True, verbose_name='Количество')
    price = models.FloatField(null=True, verbose_name='Цена')
    value = models.FloatField(null=True, verbose_name='Cумма сделки')
    trades_curr = models.CharField(max_length=5, choices=TRADES_CURR, blank=False, null=False, verbose_name='Валюта')
    tg_messaged = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Инсайдеры'
        verbose_name = 'Инсайдер'
        ordering = ['transaction_date']


class Company(models.Model):
    code = models.CharField(null=False, unique=True, max_length=10, verbose_name='Тикер компании')
    name = models.CharField(null=False, max_length=20, verbose_name='Название компании')
    image = models.ImageField(null=True, verbose_name='Изображение')
    exchange = models.ForeignKey('Exchange', verbose_name='Биржа', null=False, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = 'Компании'
        verbose_name = 'Компания'


class Exchange(models.Model):
    name = models.CharField(null=False, max_length=20, verbose_name='Название')
    full_name = models.CharField(unique=True, max_length=40, verbose_name='Полное название')


class NewsItem(models.Model):
    fm_id = models.CharField(max_length=30, verbose_name='financemarker ID', unique=True)
    title = models.CharField(null=True, max_length=20, verbose_name='Заголовок')
    content = models.TextField(null=True, verbose_name='Текст')
    link = models.CharField(null=True, max_length=50, verbose_name='Ссылка')
    publicated = models.DateTimeField(verbose_name='Время и дата публикации')
    insider = models.ForeignKey('Insider', null=False, on_delete=models.PROTECT, verbose_name='Инсайдер')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = 'Новости'
        verbose_name = 'Новость'
        ordering = ['-publicated']


class TelegraphAccount(models.Model):
    short_name = models.CharField(null=False, max_length=20, verbose_name='Короткое имя')
    author_name = models.CharField(null=False, max_length=20, verbose_name='Имя автора')
    author_url = models.CharField(null=True, max_length=40, verbose_name='Ссылка на автора')
    access_token = models.CharField(null=False, max_length=60, verbose_name='Токен аккаунта')
    auth_url = models.CharField(null=True, max_length=60, verbose_name='Url авторизации')

    class Meta:
        verbose_name_plural = 'Аккаунты Telegraph'
        verbose_name = 'Аккаунт Telegraph'


class TelegraphPage(models.Model):
    path = models.CharField(null=False, max_length=40, verbose_name='Путь')
    url = models.URLField(null=False, verbose_name='Ссылка')
    title = models.CharField(null=False, max_length=40, verbose_name='Заголовок')
    description = models.TextField(null=True, verbose_name='Описание')
    content = models.TextField(null=False, verbose_name='Контент')
    account = models.ForeignKey('TelegraphAccount', null=False, on_delete=models.PROTECT, verbose_name='Аккаунт')
    insider = models.ForeignKey('Insider', null=False, on_delete=models.PROTECT, verbose_name='Инсайдер')
    news_item = models.ForeignKey('NewsItem', null=False, on_delete=models.PROTECT, verbose_name='Новость')

    class Meta:
        verbose_name_plural = 'Страницы Telegraph'
        verbose_name = 'Страницa Telegraph'


class TelegramUser(models.Model):
    tg_id = models.CharField(null=False, unique=True, max_length=40, verbose_name='id telegram')
