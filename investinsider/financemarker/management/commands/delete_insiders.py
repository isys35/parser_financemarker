from financemarker.models import Insider
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Delete all insider'

    def handle(self, *args, **kwargs):
        insiders = Insider.objects.all()
        for insider in insiders:
            print(f'{insider.fm_id} deleting')
            insider.delete()