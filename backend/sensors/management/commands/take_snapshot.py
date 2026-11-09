import platform

from django.core.management.base import BaseCommand, CommandError

from sensors.identifiers import SECTIONS, collect_snapshot_from_windows
from sensors.models import Snapshot


class Command(BaseCommand):
    help = 'Scans the parts of this laptop and saves the result as a snapshot.'

    def add_arguments(self, parser):
        parser.add_argument('--label', default='scan', help='for example: before or after')

    def handle(self, *args, **options):
        if platform.system() != 'Windows':
            raise CommandError('Snapshots can only be taken on a Windows laptop.')
        data = collect_snapshot_from_windows()
        snapshot = Snapshot.objects.create(label=options['label'].strip()[:60] or 'scan', data=data)
        read = [s for s in SECTIONS if data.get(s) is not None]
        missed = [s for s in SECTIONS if data.get(s) is None]
        self.stdout.write(f'Saved snapshot {snapshot.id} ({snapshot.label}). Read: {", ".join(read) or "nothing"}.')
        for name in missed:
            self.stdout.write(f'  Not read: {name} ({data["errors"].get(name, "unknown reason")})')