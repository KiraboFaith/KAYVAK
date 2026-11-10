import platform

from django.core.management.base import BaseCommand, CommandError

from sensors.blackout_report import build_report, last_known_state
from sensors.models import BlackoutEvent, NotificationSetting
from sensors.notify import show_windows_toast
from sensors.outbox import flush_queue, send_or_queue
from sensors.shutdown_events import group_into_blackouts, read_shutdown_events


class Command(BaseCommand):
    help = 'Looks for unexpected shutdowns since the last check, saves a report and emails it'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='how far back to look')

    def handle(self, *args, **options):
        if platform.system() != 'Windows':
            raise CommandError('This check only works on Windows.')
        sent = flush_queue()   # emails that were waiting from a time with no internet
        if sent:
            self.stdout.write(f'Sent {sent} waiting email(s).')
        try:
            blackouts = group_into_blackouts(read_shutdown_events(options['days']))
        except Exception as error:
            raise CommandError(f'Could not read the Windows event log: {error}')

        new = [b for b in blackouts if not BlackoutEvent.objects.filter(event_time=b['time']).exists()]
        if not new:
            self.stdout.write('No new unexpected shutdowns.')
            return

        # Newest first. Save them all, but only tell the owner about the newest one,
        # so the first run does not send a week of old news.
        for number, blackout in enumerate(new):
            cause, subject, body = build_report(
                blackout['time'], blackout['bugcheck'], last_known_state(blackout['time']))
            BlackoutEvent.objects.create(
                event_time=blackout['time'], bugcheck=blackout['bugcheck'] or '',
                cause=cause, summary=body)
            if number > 0:
                continue
            self.stdout.write(subject + '\n' + body)
            self.stdout.write(f'Email: {send_or_queue(subject, body)}')
            if NotificationSetting.current().enabled:
                try:
                    show_windows_toast(subject, body.split('\n')[2] if len(body.split('\n')) > 2 else body)
                except Exception as error:
                    self.stderr.write(f'Could not show the pop-up: {error}')