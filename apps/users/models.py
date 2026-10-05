from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Пользователь системы. Вход по табельному номеру и паролю"""
    
    personnel_number = models.CharField('Табельный номер', max_length=7, unique=True)
    full_name = models.CharField('ФИО', max_length=255, blank=True)
    position = models.CharField('Должность', max_length=255, blank=True)
    department = models.CharField('Подразделение', max_length=255, blank=True)

    is_active = models.BooleanField('Активен', default=True, help_text='При увольнении сотрудника нужно снять галочку. Удалять запись не нужно')
    is_staff = models.BooleanField('Доступ к панели администратора', default=False)

    date_joined = models.DateTimeField('Дата создания', default=timezone.now)

    object = UserManager()

    USERNAME_FIELD = 'personnel_number'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['full_name', 'personnel_number']

    def __str__(self):
        if self.full_name:
            return f'{self.full_name} ({self.personnel_number})'
        return self.personnel_number
    
    def get_short_name(self):
        """Фамилия и инициалы пользователя: Иванов Иван Иванович -> Иванов И.И."""
        if not self.full_name:
            return self.personnel_number
        
        parts = self.full_name.split()
        if len(parts) < 2:
            return self.full_name
        
        surname = parts[0]
        initials = " ".join(f'{p[0]}.' for p in parts[1:])
        return f'{surname} {initials}'
    