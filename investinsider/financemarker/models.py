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
    exchange = models.CharField(null=True, max_length=20, verbose_name='Биржа')
    full_exchange = models.CharField(null=True, max_length=40, verbose_name='Биржа полное название')
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPE, blank=False, null=False,
                                        verbose_name='Тип транзакции')
    code = models.CharField(null=True, max_length=10, verbose_name='Тикер компании')
    owner = models.CharField(null=True, max_length=20, verbose_name='Название компании')
    transaction_date = models.DateField(verbose_name='Дата транзакции')
    name = models.CharField(null=True, max_length=20, verbose_name='Название')
    amount = models.IntegerField(null=True, verbose_name='Количество')
    price = models.FloatField(null=True, verbose_name='Цена')
    value = models.FloatField(null=True, verbose_name='Cумма сделки')
    trades_curr = models.CharField(max_length=5, choices=TRADES_CURR, blank=False, null=False, verbose_name='Валюта')
    parsed = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Инсайдеры'
        verbose_name = 'Инсайдер'
