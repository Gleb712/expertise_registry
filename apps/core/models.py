from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Отметки о времени создания и последнего изменения"""

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Изменено', auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """Методы доступные в любом месте цепочки запроса"""
    
    def alive(self):
        return self.filter(is_deleted=False)
    
    def dead(self):
        return self.filter(is_deleted=True)
    
    def delete(self):
        """Групповое мягкое удаление. Перекрывает стандартный delete, который физически удаляет записи"""
        return self.update(is_deleted=True, deleted_at=timezone.now())
    
    def hard_delete(self):
        """Полное удаление - стандартный delete"""
        return super.delete()
    
    def restore(self):
        return self.update(is_deleted=False, deleted_at=None)
    

class AliveManager(models.Manager):
    """Менеджер, показывающий только неудаленные записи"""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)
    

class SoftDeleteModel(models.Model):
    """Мягкое удаление - запись помечается удаленной, но остается в бд"""

    is_deleted = models.BooleanField('Удалено', default=False, db_index=True)
    deleted_at = models.DateTimeField('Дата удаления', null=True, blank=True)

    # Первый менеджер становится менеджером по умолчанию
    objects = AliveManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents= False):
        """Мягкое удаление одного объекта"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """Обе способности сразу - от этого класса будут наследоваться модели"""

    class Meta:
        abstract = True


class SystemPermission(models.Model):
    """Держатель прав для доступа пользователей к разному функционалу сервиса"""

    class Meta:
        managed = False
        default_permissions = ()
        verbose_name = 'Права системы'
        verbose_name_plural = 'Права системы'

        permissions = [
            # Меню
            ('view_registry_menu', 'Меню: Реестр'),
            ('view_reports_menu', 'Меню: Отчеты'),
            ('view_opo_catalog_menu', 'Меню: Справочник ОПО'),
            ('view_objects_catalog_menu', 'Меню: Справочник объектов'),
            ('view_users_menu', 'Меню: Пользователи'),
            ('view_import_menu', 'Меню: Загрузка из файла'),

            # Отчеты
            ('view_suspend_column', 'Отчеты: Дополнительный столбец приостановленных'),
            ('view_user_journal', 'Отчеты: Журнал пользователей'),

            # Поля карточек
            ('change_structure_name', 'Карточка: Менять наименование объекта'),
            ('change_division', 'Карточка: Менять цех'),
            ('change_commissioning_year', 'Карточка: Менять год ввода в эксплуатацию'),
        ]
