from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import TextField
from django.db.models.functions import Cast

from apps.catalogs.models import Division, ObjectType, Opo
from apps.migration_tool.converters import (
    parse_conclusion,
    parse_int,
    parse_legacy_date,
    parse_opo_numbers,
    parse_year,
)
from apps.migration_tool.legacy_models import Register
from apps.registry.models import Expertise

LEGACY = 'legacy'
SKIP_LAGACY_IDS = {25752}


class Command(BaseCommand):
    """
    Миграция БД производится комнадой:
    python manage.py migrate_registry

    Для проверки можно использовать команду без внесения изменений в БД:
    python manage.py migrate_registry --dry_run

    Для записи результата переноса без внесения изменений в БД можно использовать команду:
    python manage.py migrate_registry --dry-run --out *название_файла.расширение*
    """

    help = 'Перенос реестра экспертиз из старой базы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ничего не записывать, только показать результат',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Обработать только первые N записей (для отладки)',
        )
        parser.add_argument(
            '--out',
            type=str,
            default=None,
            help='Файл для отчёта о проблемах (UTF-8)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.out_file = None
        if options['out']:
            self.out_file = open(options['out'], 'w', encoding='utf-8')

        if self.dry_run:
            self._w('РЕЖИМ ПРОВЕРКИ: записи не будет', self.style.WARNING)

        # Справочники целиком загружаются в память
        self.opo_by_number = {o.number: o for o in Opo.all_objects.all()}
        self.types_by_legacy = {t.legacy_id: t for t in ObjectType.all_objects.all()}
        self.divisions_by_name = {d.name: d for d in Division.all_objects.all()}

        self._w(f'Справочники: ОПО {len(self.opo_by_number)}, '
                f'типов {len(self.types_by_legacy)}, '
                f'цехов {len(self.divisions_by_name)}')
        
        self._w(f'Исключено вручную: {len(SKIP_LAGACY_IDS)}')

        rows = self._read_legacy(options['limit'])
        self._w(f'Записей к переносу: {len(rows)}')

        stats = {'created': 0, 'updated': 0, 'failed': 0}
        problems = []

        for row in rows:
            try:
                with transaction.atomic():
                    is_new = self._migrate_row(row, problems)
                    stats['created' if is_new else 'updated'] += 1

                    if self.dry_run:
                        raise DryRunRollback()

            except DryRunRollback:
                pass
            except Exception as exc:
                stats['failed'] += 1
                problems.append(f'ЗАПИСЬ {row.id}: ОШИБКА — {exc}')

        self._report(stats, problems)

        if self.out_file:
            self.out_file.close()

    # ----- Чтение -----

    def _read_legacy(self, limit):
        """Даты читаем текстом: в базе есть значения вне диапазона Python."""
        qs = (
            Register.objects.using(LEGACY)
            .defer('date_entry_register', 'date_expluatation_by')
            .annotate(
                entry_date_text=Cast('date_entry_register', TextField()),
                valid_until_text=Cast('date_expluatation_by', TextField()),
            )
            .order_by('id')
            .exclude(id__in=SKIP_LAGACY_IDS)
        )
        if limit:
            qs = qs[:limit]
        return list(qs)

    # ----- Перенос одной записи -----

    def _migrate_row(self, row, problems):
        conclusion_raw = (row.conclusion or '').strip()
        conclusion = parse_conclusion(conclusion_raw)
        if conclusion_raw and not conclusion:
            problems.append(f'ЗАПИСЬ {row.id}: решение комиссии не распознано')

        year = parse_year(row.year_expluatation)
        if row.year_expluatation and not year:
            problems.append(f'ЗАПИСЬ {row.id}: год ввода не разобран')

        object_type = self.types_by_legacy.get(row.object_id)
        if row.object_id and not object_type:
            problems.append(f'ЗАПИСЬ {row.id}: тип объекта {row.object_id} не найден')

        expertise, is_new = Expertise.all_objects.update_or_create(
            legacy_id=row.id,
            defaults={
                'structure_name': (row.product_name or '').strip(),
                'object_type': object_type,
                'is_in_opo_register': row.is_in_register_opo,
                'commissioning_year': year,
                'service_life_years': parse_int(row.service_time),
                'valid_until': parse_legacy_date(row.valid_until_text),
                'registration_number': (row.registration_number or '').strip(),
                'date_entry_register': parse_legacy_date(row.entry_date_text),
                'conclusion': conclusion or '',
                'conclusion_raw': conclusion_raw,
                'is_operational': row.is_operational,
                'is_expertise_required_after_delay': row.is_necessary_expertise_after_delay,
                'is_action_required_after_delay': row.is_necessary_action_after_delay,
                'note': (row.note or '').strip(),
                'opo_raw': (row.opo_number or '').strip(),
                'division_raw': (row.division or '').strip(),
                'is_deleted': bool(row.is_deleted),
            },
        )

        self._link_opo(expertise, row, problems)
        self._link_division(expertise, row, problems)

        return is_new

    def _link_opo(self, expertise, row, problems):
        numbers = parse_opo_numbers(row.opo_number)
        objects = []

        for number in numbers:
            opo = self.opo_by_number.get(number)
            if opo:
                objects.append(opo)
            else:
                problems.append(f'ЗАПИСЬ {row.id}: ОПО "{number}" нет в справочнике')

        expertise.opo.set(objects)

    def _link_division(self, expertise, row, problems):
        name = (row.division or '').strip()
        if not name:
            expertise.divisions.set([])
            return

        division = self.divisions_by_name.get(name)
        if division:
            expertise.divisions.set([division])
        else:
            expertise.divisions.set([])
            problems.append(f'ЗАПИСЬ {row.id}: цех "{name}" нет в справочнике')

    # ----- Отчет -----

    def _report(self, stats, problems):
        self._w('')
        self._w('=== Итог ===', self.style.MIGRATE_HEADING)
        self._w(f'Создано:  {stats["created"]}')
        self._w(f'Обновлено: {stats["updated"]}')
        self._w(f'Ошибок:   {stats["failed"]}')
        self._w(f'Замечаний: {len(problems)}')

        if problems:
            self._w('')
            self._w('=== Требуют внимания ===', self.style.MIGRATE_HEADING)
            for line in problems:
                self._w(f'  {line}')

        self._w('')
        if self.dry_run:
            self._w('Изменения отменены (--dry-run)', self.style.WARNING)
        else:
            self._w('Перенос реестра завершён', self.style.SUCCESS)

    def _w(self, text='', style=None):
        self.stdout.write(style(text) if style else text)
        if self.out_file:
            self.out_file.write(f'{text}\n')


class DryRunRollback(Exception):
    """Служебное исключение для отката в режиме проверки."""
    