from django.contrib import admin
from .models import FacebookGroup


@admin.register(FacebookGroup)
class FacebookGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'group_type', 'members', 'quality', 'is_active']
    search_fields = ['name', 'owner_name']
    list_filter = ['group_type', 'quality', 'is_active']
