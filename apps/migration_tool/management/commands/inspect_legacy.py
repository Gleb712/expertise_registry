from collections import Counter
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import TextField
from django.db.models.functions import Cast

from apps.migration_tool.legacy_models import NsiObjects, NsiOpo, Register, Scans, Users

from apps.migration_tool.converters import parse_legacy_date


LEGACY = 'legacy'

# Слова для поиска объектов, предположительно, выведенных из эксплуатации
DECOMMISSION_KEYWORDS = ('выведен', 'не эксплуат', 'демонтир')


class Command(BaseCommand):
    help = 'Разведка старой базы: что в ней лежит и с чем могут возникнуть проблемы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=30,
            help='Сколько уникальных значений показывать в каждом списке',
        )

        parser.add_argument(
            '--out',
            type=str,
            default=None,
            help='Файл для записи отчета (в UTF-8)',
        )
    
    def handle(self, *args, **options):
        self.out_file = None
        if options['out']:
            self.out_file = open(options['out'], 'w', encoding='utf-8')

        self.limit = options['limit']

        rows = list(
            Register.objects.using(LEGACY)
            .defer('date_entry_register', 'date_expluatation_by')
            .annotate(
                entry_date_text=Cast('date_entry_register', TextField()),
                valid_until_text=Cast('date_expluatation_by', TextField()),
            )
        )

        self._section('Объемы')
        self._w(f'Записей в register: {len(rows)}')
        self._w(f'Из них помечены удаленными: {sum(1 for r in rows if r.is_deleted)}')
        self._w(f'Справочник ОПО: {NsiOpo.objects.using(LEGACY).count()}')
        self._w(f'Справочник типов объектов: {NsiObjects.objects.using(LEGACY).count()}')
        self._w(f'Пользователей: {Users.objects.using(LEGACY).count()}')
        self._w(f'Сканов: {Scans.objects.using(LEGACY).count()}')

        self._section('Типы объектов (nsi_objects)')
        for obj in NsiObjects.objects.using(LEGACY).all():
            mark = ' [удален]' if obj.is_deleted else ''
            self._w(f' {obj.id:>4} {obj.value!r}{mark}')

        self._section('Цеха (division)')
        self._distinct(rows, 'division')
        self._divisions_analysis(rows)

        self._section('Решение комиссии (conclusion)')
        self._distinct(rows, 'conclusion')

        self._section('Год ввода в эксплуатацию (year_expluatation)')
        self._numeric(rows, 'year_expluatation')
        self._year_patterns(rows)

        self._section('Срок службы (service_time)')
        self._numeric(rows, 'service_time')

        self._section('Номера ОПО (opo_number)')
        self._opo_numbers(rows)
        
        self._section('Наименование сооружения (product_name)')
        self._text_stats(rows, 'product_name')
        
        self._section('Примечание (note)')
        self._text_stats(rows, 'note')

        self._section('Заполненность ключевых полей')
        self._filled(rows)

        self._section('Даты')
        self._date_stats(rows)

        self._section('Противоречия')
        self._contradictions(rows)

        self._w('')
        self._w('Разведка завершена.', self.style.SUCCESS)

        if self.out_file:
            self.out_file.close()

    # Вспомогательное
    def _section(self, title):
        self._w('')
        self._w(f'=== {title} ===', self.style.MIGRATE_HEADING)

    def _distinct(self, rows, field):
        # Уникальные значения поля с их частотой
        counter = Counter(getattr(r, field) or '(пусто)' for r in rows)
        self._w(f'Уникальных значений: {len(counter)}')

        for value, count in counter.most_common(self.limit):
            self._w(f' {count:>5} {value!r}')

        if len(counter) > self.limit:
            self._w(f' ... еще {len(counter) - self.limit} значений')

    def _numeric(self, rows, field):
        # Сколько значений превращается в число и сколько нет
        good = 0
        bad = []
        empty = 0

        for r in rows:
            raw = getattr(r, field)
            if raw is None or str(raw).strip() == '':
                empty += 1
                continue
            try:
                int(str(raw).strip())
                good += 1
            except ValueError:
                bad.append(str(raw))

        self._w(f'Пусто: {empty}')
        self._w(f'Разбирается как число: {good}')
        self._w(f'Не разбирается совсем: {len(bad)}')

        for value, count in Counter(bad).most_common(self.limit):
            self._w(f' {count:>5} {value!r}')

    def _opo_numbers(self, rows):
        # Разбор строки с номерами ОПО и сверка со справочником
        known = set(NsiOpo.objects.using(LEGACY).values_list('value', flat=True))

        empty = 0
        single = 0
        multiple = 0
        max_count = 0
        separators = Counter()
        unknown = Counter()

        for r in rows:
            raw = (r.opo_number or '').strip()
            if not raw:
                empty += 1
                continue
            
            for sep in (',', ';', '/', '\n'):
                if sep in raw:
                    separators[sep] += 1

            parts = [p.strip() for p in raw.split(',') if p.strip()]
            if len(parts) > 1:
                multiple += 1
            else:
                single += 1
            max_count = max(max_count, len(parts))

            for part in parts:
                if part not in known:
                    unknown[part] += 1

        self._w(f'Пусто: {empty}')
        self._w(f'Один номер: {single}')
        self._w(f'Несколько номеров: {multiple}')
        self._w(f'Максимум номеров в одной записи: {max_count}')

        if separators:
            self._w(f'Встреченные разделители:')
            for sep, count in separators.items():
                self._w(f' {count:>5} {sep!r}')

        self._w(f'Номеров, отсутствующих в справочнике: {len(unknown)}')
        for value, count in unknown.most_common(self.limit):
            self._w(f' {count:>5} {value!r}')

    def _text_stats(self, rows, field):
        # Длина текстового поля - чтобы понять хватает ли max_length
        lengths = [len(getattr(r, field) or '') for r in rows]
        filled = [n for n in lengths if n > 0]

        self._w(f'Заполнено: {len(filled)} из {len(rows)}')
        if filled:
            self._w(f'Максимальная длина: {max(filled)}')
            self._w(f'Средняя длина: {sum(filled) // len(filled)}')

    def _filled(self, rows):
        # Сколько записей имеет значение в каждом поле
        fields = [
            'division', 'product_name', 'year_expluatation', 'service_time',
            'registration_number', 'conclusion', 'is_necessary_expertise_after_delay',
            'is_necessary_action_after_delay', 'is_in_register_opo', 'is_operational',
            'note', 'object_id', 'opo_number', 'expertise_schedule'
        ]
        total = len(rows)

        for field in fields:
            filled = sum(1 for r in rows if getattr(r, field) is not None and str(getattr(r, field)).strip() != '')
            percent = (filled * 100 // total) if total else 0
            self._w(f' {field:<40} {filled:>5} ({percent}%)')

        for label, attr in (('date_entry_register', 'entry_date_text'),
                            ('date_expluatation_by', 'valid_until_text')):
            filled = sum(1 for r in rows if parse_legacy_date(getattr(r, attr)))
            percent = (filled * 100 // total) if total else 0
            self._w(f' {label:<40} {filled:>5} ({percent}%)')

    def _contradictions(self, rows):
        # Записи, которые лучше проверить вручную
        threshold = date.today() - timedelta(days=365 * 3)

        old_but_operational = []
        note_says_decommissioned = []
        no_valid_date = 0
        null_operational = 0

        for r in rows:
            if r.is_deleted:
                continue

            valid_until = parse_legacy_date(r.valid_until_text)

            if r.is_operational is None:
                null_operational += 1

            if not valid_until:
                no_valid_date += 1
            
            if r.is_operational and valid_until and valid_until < threshold:
                old_but_operational.append(r.id)

            note = (r.note or '').lower()
            if r.is_operational and any(k in note for k in DECOMMISSION_KEYWORDS):
                note_says_decommissioned.append(r.id)

        self._w(f'is_operational не заполнено: {null_operational}')
        self._w(f'Без срока безопасной эксплуатации: {no_valid_date}')
        self._w(f'По имеющимся данным эксплуатируется, но срок безопасной эксплуатации истек более 3 лет назад: {len(old_but_operational)}')
        self._w(f'По имеющимся данным эксплуатируется, но в примечании есть признаки вывода из эксплуатации: {len(note_says_decommissioned)}')

        if note_says_decommissioned:
            preview = note_says_decommissioned[:self.limit]
            self._w(f' ID для проверки: {', '.join(map(str, preview))}')

    def _date_stats(self, rows):
        # диапазон дат и количество пустых
        for label, attr in (('Дата внесения в реестр', 'entry_date_text'),
                            ('Срок безопасной эксплуатации', 'valid_until_text')):
            parsed = [parse_legacy_date(getattr(r, attr)) for r in rows]
            real = [d for d in parsed if d]
            empty = len(parsed) - len(real)

            self._w(f'{label}')
            self._w(f' Осмысленных дат: {len(real)}')
            self._w(f' Пустых (0001-01-01, NULL): {empty}')
            if real:
                self._w(f' Самая ранняя: {min(real)}')
                self._w(f' Самая поздняя: {max(real)}')

    def _w(self, text='', style=None):
        # Вывод в консоль
        self.stdout.write(style(text) if style else text)
        if self.out_file:
            self.out_file.write(f'{text}\n')

    def _divisions_analysis(self, rows):
        import re

        def normalize(value):
            v = (value or '').lower().strip()
            v = v.replace('№', '').replace('#', '')
            v = v.replace('ё', 'е')
            v = re.sub(r'[\s\-_.]+', ' ', v)
            return v.strip()
        
        groups = {}
        for r in rows:
            key = normalize(r.division)
            groups.setdefault(key, set()).add(r.division)

        collapsed = {k: v for k, v in groups.items() if len(v) > 1}

        self._w(f'После нормализации групп: {len(groups)}')
        self._w(f'Групп с несколькими названиями: {len(collapsed)}')
        for key, variants in list(collapsed.items())[:self.limit]:
            self._w(f' {sorted(variants)}')

    def _year_patterns(self, rows):
        import re

        patterns = Counter()
        samples = {}

        for r in rows:
            raw = (r.year_expluatation or '').strip()
            if not raw:
                continue
            try:
                int(raw)
                continue
            except ValueError:
                pass

            if re.fullmatch(r'\d{4}[-./]\d{2}[-./]\d{2}', raw):
                key = 'дата ГГГГ-ММ-ДД'
            elif re.fullmatch(r'\d{2}[-./]\d{2}[-./]\d{4}', raw):
                key = 'дата ДД-ММ-ГГГГ'
            elif re.fullmatch(r'\d{4}\s*[--]\s*\d{4}', raw):
                key = 'диапазон годов'
            elif re.fullmatch(r'\d{4}', raw):
                key = 'есть 4 цифры подряд + текст'
            elif re.fullmatch(r'\d', raw):
                key = 'есть цифры, но не год'
            else:
                key = 'цифр вообще нет'

            patterns[key] += 1
            samples.setdefault(key, raw)

        for key, count in patterns.most_common():
            self._w(f' {count:>5} {key}')
