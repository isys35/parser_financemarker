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
    exchange = models.CharField(max_length=20, verbose_name='Биржа')
    full_exchange = models.CharField(max_length=40, verbose_name='Биржа полное название')
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPE,blank=False, null=False, verbose_name='Тип транзакции')
    code = models.CharField(max_length=10, verbose_name='Тикер компании')
    owner = models.CharField(max_length=20, verbose_name='Название компании')
    transaction_date = models.DateField(verbose_name='Дата транзакции')
    name = models.CharField(max_length=20, verbose_name='Название')
    amount = models.IntegerField(verbose_name='Количество')
    price = models.FloatField(verbose_name='Цена')
    value = models.FloatField(verbose_name='Cумма сделки')
    trades_curr = models.CharField(max_length=5, choices=TRADES_CURR,blank=False, null=False, verbose_name='Валюта')
