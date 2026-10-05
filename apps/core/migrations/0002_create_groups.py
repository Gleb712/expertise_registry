from django.db import migrations

# Описание групп: название -> список прав в формате 'приложение.имя'
GROUPS = {
    # Администратор — весь функционал
    'Администратор': '__all__',

    # Группа 1
    'Инженер ПБ': [
        'core.view_registry_menu',
        'core.view_reports_menu',
        'core.view_opo_catalog_menu',
        'core.change_structure_name',
        'core.change_division',
        'core.change_commissioning_year',
        'registry.view_expertise',
        'registry.add_expertise',
        'registry.change_expertise',
        'registry.delete_expertise',
        'catalogs.view_opo',
        'catalogs.add_opo',
        'catalogs.change_opo',
        'catalogs.view_division',
        'catalogs.view_objecttype',
        'documents.view_document',
        'documents.add_document',
    ],

    # Группа 1 (журнал + аудит)
    'Инженер ПБ + журнал': [
        'core.view_registry_menu',
        'core.view_reports_menu',
        'core.view_opo_catalog_menu',
        'core.view_user_journal',
        'core.change_structure_name',
        'core.change_division',
        'core.change_commissioning_year',
        'registry.view_expertise',
        'registry.add_expertise',
        'registry.change_expertise',
        'registry.delete_expertise',
        'catalogs.view_opo',
        'catalogs.add_opo',
        'catalogs.change_opo',
        'catalogs.view_division',
        'catalogs.view_objecttype',
        'documents.view_document',
        'documents.add_document',
    ],

    # Группа 2 — карточка без наименования, цеха и года ввода
    'Специалист подразделения': [
        'core.view_registry_menu',
        'core.view_reports_menu',
        'registry.view_expertise',
        'registry.change_expertise',
        'catalogs.view_opo',
        'catalogs.view_division',
        'catalogs.view_objecttype',
        'documents.view_document',
        'documents.add_document',
    ],

    # Группа 3 (только просмотр реестра ЭПБ)
    'Наблюдатель': [
        'core.view_registry_menu',
        'core.view_reports_menu',
        'registry.view_expertise',
        'catalogs.view_opo',
        'catalogs.view_division',
        'catalogs.view_objecttype',
        'documents.view_document',
    ],

    # Статистика
    'Аналитик': [
        'core.view_reports_menu',
        'core.view_user_journal',
        'registry.view_expertise',
        'catalogs.view_opo',
        'catalogs.view_division',
        'catalogs.view_objecttype',
    ],

    # Начальник управления 73 — карточку только смотрит
    'Начальник управления 73': [
        'core.view_registry_menu',
        'core.view_reports_menu',
        'core.view_suspended_column',
        'core.view_user_journal',
        'registry.view_expertise',
        'catalogs.view_opo',
        'catalogs.view_division',
        'catalogs.view_objecttype',
        'documents.view_document',
    ],
}


def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    # Словарь всех прав: 'приложение.кодовое_имя' -> объект
    all_perms = {
        f'{p.content_type.app_label}.{p.codename}': p
        for p in Permission.objects.select_related('content_type').all()
    }

    for group_name, codenames in GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)

        if codenames == '__all__':
            perms = list(all_perms.values())
        else:
            perms = []
            for code in codenames:
                perm = all_perms.get(code)
                if perm:
                    perms.append(perm)
                else:
                    print(f'  ВНИМАНИЕ: право {code} не найдено')

        group.permissions.set(perms)


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=GROUPS.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('registry', '0001_initial'),
        ('catalogs', '0001_initial'),
        ('documents', '0001_initial'),
        ('users', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
