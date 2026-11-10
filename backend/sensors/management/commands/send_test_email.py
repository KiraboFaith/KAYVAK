from django.core.management.base import BaseCommand, CommandError

from sensors.mailer import send_email


class Command(BaseCommand):
    help = 'Sends one test email so you can check that mail reaches your phone'

    def handle(self, *args, **options):
        try:
            send_email('KAYVAK test', 'If you can read this on your phone, KAYVAK email works.')
        except Exception as error:
            raise CommandError(f'Email failed: {error}')
        self.stdout.write('Sent. Check your phone.')