from django.contrib import admin

from .models import Insider, NewsItem, TelegraphAccount, TelegraphPage, Source


# class InsiderAdmin(admin.ModelAdmin):
#     list_display = ('fm_id', 'exchange', 'full_exchange', 'transaction_type', 'code',
#                     'owner', 'name', 'amount', 'price', 'value', 'trades_curr', 'transaction_date')

class SourceAdmin(admin.ModelAdmin):
    list_display = ('link', 'trusted')
    list_editable = ('trusted',)
    search_fields = ('link',)

admin.site.register(Source, SourceAdmin)
# admin.site.register(NewsItem)
# admin.site.register(TelegraphAccount)
# admin.site.register(TelegraphPage)
