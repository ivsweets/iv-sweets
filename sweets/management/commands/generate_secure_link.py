from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from lista.models import SecureLink

class Command(BaseCommand):
    help = 'Generate a secure link'

    def add_arguments(self, parser):
        parser.add_argument(
            '--expires',
            type=int,
            help='Expiration time in hours (optional)',
        )

    def handle(self, *args, **options):
        expires_hours = options.get('expires')
        expires_at = None

        if expires_hours:
            expires_at = timezone.now() + timedelta(hours=expires_hours)

        secure_link = SecureLink.objects.create(expires_at=expires_at)

        self.stdout.write(
            self.style.SUCCESS(f'Secure link created: {secure_link.token}')
        )

        if expires_at:
            self.stdout.write(
                f'Expires at: {expires_at}'
            )
        else:
            self.stdout.write('No expiration set')
