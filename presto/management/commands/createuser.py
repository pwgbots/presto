from django.core.management.base import BaseCommand

from django.contrib.auth.models import Group, User
from django.db.utils import IntegrityError
from django.contrib.auth.models import Permission
from presto.models import Profile


class Command(BaseCommand):
    def create_superuser(self, netid, email, first_name, last_name):
        try:
            u = User.objects.create_user(netid, email, "B3stM031l1jk")
            u.first_name = first_name
            u.last_name = last_name
            u.is_superuser = True
            u.is_staff = True
            u.save()
            return u
        except Exception as e:
            print(e)
            return None

    def handle(self, *args, **options):
        pb = self.create_superuser('presto', 'p.w.g.bots@tudelft.nl', 'Presto', 'Administrator')
        if pb is not None:
            print('Created superuser: Presto Administrator')
            #Profile.objects.create(user=pb)
 