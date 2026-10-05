from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Создание пользователей"""

    use_in_migrations = True

    def _create_user(self, personnel_number, password, **extra_fields):
        """Общая логика создания пользователей"""
        if not personnel_number:
            raise ValueError('Табельный номер обязателен')
        
        user = self.model(personnel_number=personnel_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, personnel_number, password=None, **extra_fields):
        """Создание обычного пользователя - без прав суперпользователя и доступа к админке"""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(personnel_number, password, **extra_fields)
    
    def create_superuser(self, personnel_number, password=None, **extra_fields):
        """Создание суперпользователя"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True')
        
        return self._create_user(personnel_number, password, **extra_fields)
