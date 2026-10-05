from django.apps import AppConfig


class MigrationToolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.migration_tool'
    verbose_name = 'Перенос данных'
    