from django.contrib import admin

from .models import ObjectType, Opo, Division


@admin.register(Opo)
class OpoAdmin(admin.ModelAdmin):
    list_display = ('number', 'is_deleted', 'updated_at')
    list_filter = ('is_deleted',)
    search_fields = ('number',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    fieldsets = (
        (None, {'fields': ('number',)}),
        ('Служебное', {
            'fields': ('is_deleted', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ("collapse",),
        }),
    )

    def get_queryset(self, request):
        # Показываем все объекты (в том числе удаленные)
        return self.model.all_objects.all()
    
@admin.register(ObjectType)
class ObjectTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_deleted')
    list_filter = ('is_deleted',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    def get_queryset(self, request):
        return self.model.all_objects.all()
    

@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_deleted')
    list_filter = ('is_deleted',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    def get_queryset(self, request):
        return self.model.all_objects.all()
