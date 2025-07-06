from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'cooking_skill_level', 'is_staff', 'date_joined', 'avatar_preview')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'cooking_skill_level', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': ('avatar', 'bio', 'location', 'birth_date', 'dietary_preferences', 'cooking_skill_level')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile Information', {
            'fields': ('first_name', 'last_name', 'email', 'cooking_skill_level')
        }),
    )
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;">',
                obj.avatar.url
            )
        return "No Avatar"
    avatar_preview.short_description = "Avatar"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()