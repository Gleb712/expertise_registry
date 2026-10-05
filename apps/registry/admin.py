from django.contrib import admin
from django.utils.html import format_html

from .models import Expertise, ExpertiseStatus


# Цвета для подсветки статуса
STATUS_COLORS = {
    ExpertiseStatus.DECOMMISSIONED: '#6c757d',
    ExpertiseStatus.SUSPENDED_ACTION: '#b02a37',
    ExpertiseStatus.SUSPENDED: '#d63384',
    ExpertiseStatus.EXPIRED: '#dc3545',
    ExpertiseStatus.EXPIRING_SOON: '#fd7e14',
    ExpertiseStatus.ACTIVE: '#198754',
}


class ExpiryFilter(admin.SimpleListFilter):
    """Фильтр по сроку эксплуатации. Использует методы QuerySet"""

    title = 'Срок эксплуатации'
    parameter_name = 'expiry'

    def lookups(self, request, model_admin):
        return [
            ('expired', 'Истек'),
            ('soon', 'Заканчивается в течение 3 месяцев'),
            ('valid', 'Действующие'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'expired':
            return queryset.expired()
        if self.value() == 'soon':
            return queryset.expiring_soon()
        if self.value() == 'valid':
            return queryset.valid()
        return queryset


class ContradictoryFilter(admin.SimpleListFilter):
    """Записи, которые нужно перепроверить вручную"""

    title = "Противоречивые данные"
    parameter_name = 'contradictory'

    def lookups(self, request, model_admin):
        return [('yes', 'Только противоречивые')]
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.contradictory()
        return queryset
    

@admin.register(Expertise)
class ExpertiseAdmin(admin.ModelAdmin):

    #-----Список-----
    list_display = (
        'structure_name',
        'divisions_column',
        'object_type',
        'valid_until',
        'days_left_column',
        'status_column',
        'is_deleted',
    )
    list_filter = (
        ExpiryFilter,
        ContradictoryFilter,
        'divisions',
        'is_operational',
        'conclusion',
        'object_type',
        'is_deleted',
    )
    search_fields = (
        'structure_name',
        'divisions__name',
        'registration_number',
        'opo_raw',
        'note',
    )
    list_per_page = 50
    date_hierarchy = 'valid_until'

    #-----Форма-----
    filter_horizontal = ('opo', 'divisions')
    readonly_fields = (
        'legacy_id',
        'opo_raw',
        'division_raw',
        'conclusion_raw',
        'created_at',
        'updated_at',
        'deleted_at',
        'status_column',
        'days_left_column',
    )

    fieldsets = (
        ('Объект', {
            'fields': ('structure_name', 'divisions', 'object_type', 'opo', 'is_in_opo_register'),
        }),
        ('Сроки', {
            'fields': ('commissioning_year', 'service_life_years', 'valid_until', 'days_left_column', 'status_column'),
        }),
        ('Заключение', {
            'fields': ('registration_number', 'date_entry_register', 'conclusion'),
        }),
        ('Состояние', {
            'fields': ('is_operational', 'is_expertise_required_after_delay', 'is_action_required_after_delay'),
        }),
        ('Примечание', {
            'fields': ('note',),
        }),
        ('Служебное', {
            'fields': ('legacy_id', 'opo_raw', 'division_raw', 'conclusion_raw', 'is_deleted', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    #-----Выборка-----

    def get_queryset(self, request):
        """Полный набор, включая удаленные"""
        return (self.model.all_objects.select_related('object_type').prefetch_related('opo', 'divisions'))
    
    #-----Вычисляемые колонки-----

    @admin.display(description='Статус', ordering='valid_until')
    def status_column(self, obj):
        color = STATUS_COLORS.get(obj.status, '#212529')
        return format_html(
            '<span style="color: {}; font-weight: 500;">{}</span>',
            color,
            obj.status_display,
        )
    
    @admin.display(description='Осталось дней', ordering='valid_until')
    def days_left_column(self, obj):
        days = obj.days_left
        if days is None:
            return '-'
        if days < 0:
            return format_html(
                '<span style="color: #dc3545;">просрочено на {}</span>', -days
            )
        return days

    @admin.display(description='Цеха')
    def divisions_column(self, obj):
        names = [d.name for d in obj.divisions.all()]
        return ', '.join(names) if names else '-'
