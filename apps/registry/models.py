from datetime import date, timedelta
from django.db import models
from apps.core.models import BaseModel

EXPIRING_SOON_DAYS = 90


class Conclusion(models.TextChoices):
    """
    Решение экспертной комиссии
    """

    COMPLIANT = 'compliant', 'Соответствует требованиям ПБ'
    PARTIALLY = 'partially', 'Не в полной мере соответствует требованиям ПБ'
    NON_COMPLIANT = 'non_compliant', 'Не соответствует требованиям ПБ'


class ExpertiseStatus(models.TextChoices):
    """
    Статус объекта, в котором он отображается в таблице.
    Само значение не хранится в БД.
    """
    DECOMMISSIONED = 'decommissioned', 'Выведено из эксплуатации'
    SUSPENDED_ACTION = 'suspended_action', 'ЭПБ приостановлено, требуются действия'
    SUSPENDED = 'suspended', 'ЭПБ приостановлено'
    EXPIRED = 'expired', 'Истек срок эксплуатации'
    EXPIRING_SOON = 'expiring_soon', 'Заканчивается в течение 3 месяцев'
    ACTIVE = 'active', 'Действующее'


class ExpertiseQuerySet(models.QuerySet):
    """
    Независимые выборки - каждая отвечает за свою часть (НЕ взаимоисключающие)
    """

    def decommissioned(self):
        return self.filter(is_operational=False)

    def operational(self):
        return self.filter(is_operational=True)

    def expired(self):
            return self.filter(valid_until__lt=date.today())
    
    def expiring_soon(self):
        limit = date.today() + timedelta(days=EXPIRING_SOON_DAYS)
        return self.filter(valid_until__gte=date.today(), valid_until__lte=limit)

    def suspended(self):
        """Срок истек и требуется проведение ЭПБ"""
        return self.expired().filter(is_expertise_required_after_delay=True)
    
    def suspended_with_action(self):
        """Тоже истек срок, требуется проведение ЭПБ, а также дополнительные действия"""
        return self.suspended().filter(is_action_required_after_delay=True)

    def valid(self):
        """Срок не истек и объект эксплуатируется"""
        return self.filter(is_operational=True, valid_until__gte=date.today())

    def contradictory(self):
        """
        Числится эксплуатируемым, но срок истек более 3 лет назад
        (Вероятно, объект не эксплуатируется, но у него не проставлена отметка о выводе из эксплуатации)
        """
        threshold = date.today() - timedelta(days=365 * 3)
        return self.filter(is_operational=True, valid_until__lt=threshold)
    

class AliveExpertiseManager(models.Manager):
    def get_queryset(self):
        return ExpertiseQuerySet(self.model, using=self._db).filter(is_deleted=False)
     

class Expertise(BaseModel):
    """Запись реестра экспертиз промышленной безопасности"""

    legacy_id = models.IntegerField(
        'ID в старой системе',
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text='Заполняется при переносе. Нужен для повторного запуска',
    )

    #-----Объект-----
    divisions = models.ManyToManyField(
        'catalogs.Division',
        verbose_name='Цеха',
        related_name='expertises',
        blank=True,
    )
    division_raw = models.CharField(
        'Цех (исходная строка)',
        max_length=255,
        blank=True,
        help_text='Значение из старой БД. Записывается для проверки',
    )
    structure_name = models.CharField('Наименование сооружения', max_length=500, blank=True)
    object_type = models.ForeignKey(
        'catalogs.ObjectType',
        verbose_name='Тип объекта',
        on_delete=models.PROTECT,
        related_name='expertises',
        null=True,
        blank=True,
    )
    opo = models.ManyToManyField(
        'catalogs.Opo',
        verbose_name='Номера ОПО',
        related_name='expertises',
        blank=True,
    )
    opo_raw = models.CharField(
        'Номера ОПО (Исходная строка)',
        max_length=255,
        blank=True,
        help_text='Значение из старой БД. Сохраняется на случай проверки',
    )
    is_in_opo_register = models.BooleanField(
        'Зарегистрировано в реестре ОПО',
        null=True,
        blank=True,
    )

    #-----Сроки-----
    commissioning_year = models.PositiveSmallIntegerField(
        'Год ввода в эксплуатацию',
        null=True,
        blank=True,
    )
    service_life_years = models.PositiveSmallIntegerField(
        'Срок службы, лет',
        null=True,
        blank=True,
    )
    valid_until = models.DateField(
        'Срок безопасной эксплуатации до',
        null=True,
        blank=True,
        db_index=True,
    )

    #-----Заключение-----
    registration_number = models.CharField(
        "Регистрационный номер заключения",
        max_length=128,
        blank=True,
    )
    date_entry_register = models.DateField(
        'Дата внесения в реестр',
        null=True,
        blank=True,
    )
    conclusion = models.CharField(
        'Решение комиссии',
        max_length=20,
        choices=Conclusion.choices,
        blank=True,
    )
    conclusion_raw = models.CharField(
        'Решение комиссии (исходный текст)',
        max_length=255,
        blank=True,
    )

    #-----Состояние-----
    is_operational = models.BooleanField(
        'Эксплуатируется',
        null=True,
        blank=True,
        default=True,
    )
    is_expertise_required_after_delay = models.BooleanField(
        'При просрочке требуется проведение ЭПБ',
        null=True,
        blank=True,
    )
    is_action_required_after_delay = models.BooleanField(
        'При просрочке требуются иные действия',
        null=True,
        blank=True,
    )

    # Примечание
    note = models.TextField(
        'Примечание',
        blank=True,
    )

    objects = AliveExpertiseManager()
    all_objects = ExpertiseQuerySet.as_manager()

    class Meta:
        verbose_name = 'Экспертиза'
        verbose_name_plural = 'Реестр экспертиз'
        ordering = ['structure_name']
        indexes = [
            models.Index(fields=['is_deleted', 'valid_until']),
            models.Index(fields=['is_deleted', 'is_operational']),
        ]

    def __str__(self):
        return self.structure_name or f'Запись №{self.pk}'
    
    #-----Вычисляемое-----

    @property
    def is_expired(self):
        if not self.valid_until:
            return False
        return self.valid_until < date.today()
    
    @property
    def days_left(self):
        """Дней до истечения срока. Отрицательное значит, что срок истек"""
        if not self.valid_until:
            return None
        return (self.valid_until - date.today()).days
    
    @property
    def status(self):
        """
        Категория для окраски строки.
        Порядок задается приоритетом.
        """
        if self.is_operational is False:
            return ExpertiseStatus.DECOMMISSIONED
        
        if self.is_expired:
            if self.is_expertise_required_after_delay:
                if self.is_action_required_after_delay:
                    return ExpertiseStatus.SUSPENDED_ACTION
                return ExpertiseStatus.SUSPENDED
            return ExpertiseStatus.EXPIRED
        
        if self.days_left is not None and self.days_left <= EXPIRING_SOON_DAYS:
            return ExpertiseStatus.EXPIRING_SOON
        
        return ExpertiseStatus.ACTIVE
    
    @property
    def status_display(self):
        return ExpertiseStatus(self.status).label
    
    @property
    def is_contradictory(self):
        """Признак того, что про запись забыли и ее стоит перепроверить"""
        if self.is_operational is not True or not self.valid_until:
            return False
        return self.valid_until < date.today() - timedelta(days=365 * 3) 
