from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogs.models import Division, ObjectType, Opo
from apps.migration_tool.legacy_models import NsiObjects, NsiOpo, Register

LEGACY = 'legacy'


class Command(BaseCommand):
    help = 'Перенос справочников из старой базы: ОПО, типы объектов, цеха'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, что будет сделано, ничего не записывая',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']

        if self.dry_run:
            self.stdout.write(self.style.WARNING('РЕЖИМ ПРОВЕРКИ: без записи'))

        try:
            with transaction.atomic():
                self._migrate_opo()
                self._migrate_object_types()
                self._migrate_divisions()

                if self.dry_run:
                    raise DryRunRollback()

        except DryRunRollback:
            self.stdout.write(self.style.WARNING('Изменения отменены (--dry-run)'))
            return

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Перенос справочников завершён'))

    # ----- ОПО -----

    def _migrate_opo(self):
        self._section('ОПО')

        created = updated = 0

        for row in NsiOpo.objects.using(LEGACY).all():
            number = (row.value or '').strip()
            if not number:
                self.stdout.write(f'  Пропуск: запись {row.id} без номера')
                continue

            obj, is_new = Opo.all_objects.update_or_create(
                legacy_id=row.id,
                defaults={
                    'number': number,
                    'is_deleted': bool(row.is_deleted),
                },
            )
            created += is_new
            updated += not is_new

        self.stdout.write(f'  Создано: {created}, обновлено: {updated}')

    # ----- Типы объектов -----

    def _migrate_object_types(self):
        self._section('Типы объектов')

        created = updated = 0

        for row in NsiObjects.objects.using(LEGACY).all():
            name = (row.value or '').strip()
            if not name:
                self.stdout.write(f'  Пропуск: запись {row.id} без наименования')
                continue

            obj, is_new = ObjectType.all_objects.update_or_create(
                legacy_id=row.id,
                defaults={
                    'name': name,
                    'is_deleted': bool(row.is_deleted),
                },
            )
            created += is_new
            updated += not is_new

        self.stdout.write(f'  Создано: {created}, обновлено: {updated}')

    # ----- Цеха -----

    def _migrate_divisions(self):
        """Цеха в старой базе не справочник, а текстовое поле в register.
        Собираем уникальные значения и заводим справочник из них."""
        self._section('Цеха')

        raw_values = Register.objects.using(LEGACY).values_list('division', flat=True)

        names = set()
        for raw in raw_values:
            name = (raw or '').strip()
            if name:
                names.add(name)

        self.stdout.write(f'  Уникальных значений в register: {len(names)}')

        created = updated = 0

        for name in sorted(names):
            obj, is_new = Division.all_objects.update_or_create(
                name=name,
                defaults={'is_deleted': False},
            )
            created += is_new
            updated += not is_new

        self.stdout.write(f'  Создано: {created}, обновлено: {updated}')

    # ----- Вспомогательное -----

    def _section(self, title):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(f'=== {title} ==='))


class DryRunRollback(Exception):
    """Служебное исключение для отката транзакции в режиме проверки."""
    