from django.contrib import admin
from django.contrib.auth.admin import  UserAdmin as BaseUserAdmin

from .forms import UserCreateForm, UserEditForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """"""

    form = UserEditForm
    add_form = UserCreateForm

    # Список
    list_display = ('personnel_number', 'full_name', 'department', 'position', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'groups', 'department')
    search_fields = ('personnel_number', 'full_name', 'department', 'position')
    ordering = ('full_name', 'personnel_number')

    # Форма редактирования
    fieldsets = (
        (None, {
            'fields': ('personnel_number', 'password'),
        }),
        ('Личные данные', {
            'fields': ('full_name', 'position', 'department'),
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Служебное', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    # Форма создания
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('personnel_number', 'password1', 'password2'),
        }),
        ('Личные данные', {
            'fields': ('full_name', 'position', 'department'),
        }),
    )

    readonly_fields = ('last_login', 'date_joined')
    filter_horizontal = ('groups', 'user_permissions')
