import sys


from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from helpdesk.models import CustomerSupportAgent


class Command(BaseCommand):
    help = 'Create customer support agent and optionally provide "Displayed name" and/or "Password"'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
        )

        parser.add_argument(
            '--displayed-name',
            help='Displayed name',
        )

        parser.add_argument(
            '--password',
            help='Password',
        )

    def handle(self, username, password=None, displayed_name=False, **kw):
        try:
            agent = CustomerSupportAgent.objects.create_user(username=username, password=password, displayed_name=displayed_name, admin_staff=True)
        except IntegrityError:
            self.stderr.write("Agent with the same username already exists: %s" % username)
            sys.exit(1)

        self.stdout.write(str(agent.id))
