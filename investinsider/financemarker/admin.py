from django.contrib import admin

from .models import Insider, NewsItem


class InsiderAdmin(admin.ModelAdmin):
    list_display = ('fm_id', 'exchange', 'full_exchange', 'transaction_type', 'code',
                    'owner', 'name', 'amount', 'price', 'value', 'trades_curr', 'transaction_date')


admin.site.register(Insider, InsiderAdmin)
admin.site.register(NewsItem)
