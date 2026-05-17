import os
import secrets
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from apps.core.models import SystemSetting

User = get_user_model()

NICHE_PRICES = {
    'solar-usa':      (45,  95),
    'solar-uk':       (40,  85),
    'solar-ca':       (40,  85),
    'solar-au':       (38,  80),
    'sweeps-auto':    (15,  35),
    'sweeps-health':  (20,  45),
    'sweeps-medicare':(25,  55),
    'sweeps-home':    (18,  40),
    'sweeps-life':    (20,  45),
    'sweeps-debt':    (15,  35),
    'sweeps-generic': (10,  25),
}


class Command(BaseCommand):
    help = 'Seed initial super admin and system settings (idempotent)'

    def handle(self, *args, **options):
        self._create_super_admin()
        self._create_system_settings()

    def _create_super_admin(self):
        email = os.environ.get('SUPER_ADMIN_EMAIL', 'admin@example.com')
        password = os.environ.get('SUPER_ADMIN_PASSWORD', 'changeme123!')
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'role': User.Role.SUPER_ADMIN,
                'status': User.Status.ACTIVE,
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Super',
                'last_name': 'Admin',
            },
        )
        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(f'Created super admin: {email}'))
        else:
            self.stdout.write(f'Super admin already exists: {email}')

    def _create_system_settings(self):
        base_settings = [
            {
                'key': 'lead_ingest_api_key',
                'value': secrets.token_hex(32),
                'value_type': 'string',
                'description': 'API key required to POST leads to the ingest endpoint',
                'is_secret': True,
            },
            {
                'key': 'replacement_window_days',
                'value': '7',
                'value_type': 'int',
                'description': 'Days after allocation within which a replacement can be requested',
            },
            {
                'key': 'max_replacement_rate',
                'value': '0.10',
                'value_type': 'float',
                'description': 'Maximum fraction of leads a client may request replaced per period',
            },
            {
                'key': 'lead_dedup_window_days',
                'value': '30',
                'value_type': 'int',
                'description': 'Days to look back when checking for duplicate leads',
            },
            {
                'key': 'auto_distribute_enabled',
                'value': 'true',
                'value_type': 'bool',
                'description': 'Toggle automatic lead distribution to subscribed clients',
            },
            {
                'key': 'auto_distribute_schedule',
                'value': 'realtime',
                'value_type': 'string',
                'description': 'Distribution cadence: realtime | hourly | daily',
            },
        ]

        price_settings = []
        for niche, (shared, exclusive) in NICHE_PRICES.items():
            slug = niche.replace('-', '_')
            price_settings.append({
                'key': f'price_default_{slug}_shared',
                'value': str(shared),
                'value_type': 'float',
                'description': f'Default shared price per lead for niche: {niche}',
            })
            price_settings.append({
                'key': f'price_default_{slug}_exclusive',
                'value': str(exclusive),
                'value_type': 'float',
                'description': f'Default exclusive price per lead for niche: {niche}',
            })

        for entry in base_settings + price_settings:
            key = entry['key']
            defaults = {k: v for k, v in entry.items() if k != 'key'}
            _, created = SystemSetting.objects.get_or_create(key=key, defaults=defaults)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created setting: {key}'))
            else:
                self.stdout.write(f'  Already exists: {key}')
