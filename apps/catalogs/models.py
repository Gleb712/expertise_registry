from django.db import models

from apps.core.models import BaseModel


class Opo(BaseModel):
    """Опасный производственный объект"""

    number = models.CharField(
        'Регистрационный номер',
        max_length=64,
        unique=True,
    )
    
    legacy_id = models.IntegerField(
        'ID в старой БД',
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text='Заполняется при переносе'
    )

    class Meta:
        verbose_name = 'ОПО'
        verbose_name_plural = 'ОПО'
        ordering = ['number']

    def __str__(self):
        return self.number
    
    def save(self, *args, **kwargs):
        """Обрезка случайных пробелов по краям"""
        if self.number:
            self.number = self.number.strip()
        super().save(*args, **kwargs)


class ObjectType(BaseModel):
    """Тип объекта экспертизы: Здание, Сооружение, Техническое устройство, Не зарегистрировано"""

    name = models.CharField('Наименование', max_length=255, unique=True)

    legacy_id = models.IntegerField(
        'ID в старой БД',
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text='Заполняется при переносе'
    )


    class Meta:
        verbose_name = 'Тип объекта'
        verbose_name_plural = 'Типы объектов'
        ordering = ['name']

    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

        
class Division(BaseModel):
    """Цех"""

    name = models.CharField('Наименование', max_length=255, unique=True)

    legacy_id = models.IntegerField(
        'ID в старой БД',
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text='Заполняется при переносе'
    )

    class Meta:
        verbose_name = 'Цех'
        verbose_name_plural = 'Цеха'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)
