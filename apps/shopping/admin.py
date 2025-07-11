from django.contrib import admin
from .models import (
    ShoppingList,
    ShoppingListCategory,
    ShoppingListItem,
    ShoppingListTemplate,
    ShoppingListTemplateItem,
)

class ShoppingListItemInline(admin.TabularInline):
    model = ShoppingListItem
    extra = 1

class ShoppingListAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'user', 'priority', 'due_date', 'completed', 'auto_generated', 
        'meal_plan_week', 'created_at', 'updated_at', 'total_items', 'completed_items', 'completion_percentage', 'estimated_total_cost'
    )
    list_filter = ('priority', 'completed', 'auto_generated', 'due_date', 'meal_plan_week', 'user',)
    search_fields = ('name', 'description', 'user__username')
    ordering = ('-created_at',)
    filter_horizontal = ('shared_with',)
    readonly_fields = ('created_at', 'updated_at', 'total_items', 'completed_items', 'completion_percentage', 'estimated_total_cost')
    inlines = [ShoppingListItemInline]

class ShoppingListCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color', 'sort_order')
    ordering = ('sort_order', 'name')
    search_fields = ('name',)
    
class ShoppingListTemplateItemInline(admin.TabularInline):
    model = ShoppingListTemplateItem
    extra = 1

class ShoppingListTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_public', 'category', 'created_at')
    list_filter = ('is_public', 'category', 'user')
    search_fields = ('name', 'description', 'category', 'user__username')
    ordering = ('-created_at',)
    inlines = [ShoppingListTemplateItemInline]
    readonly_fields = ('created_at',)

class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = (
        'shopping_list', 'name', 'quantity', 'unit', 'category', 'estimated_cost', 
        'actual_cost', 'completed', 'priority', 'from_recipe', 'created_at'
    )
    list_filter = ('completed', 'unit', 'category', 'shopping_list')
    search_fields = ('name', 'notes', 'ingredient__name', 'shopping_list__name')
    ordering = ('completed', 'category__sort_order', 'priority', 'name')

class ShoppingListTemplateItemAdmin(admin.ModelAdmin):
    list_display = (
        'template', 'name', 'quantity', 'unit', 'category', 'estimated_cost'
    )
    list_filter = ('template', 'unit', 'category')
    search_fields = ('name', 'ingredient__name', 'template__name')
    ordering = ('template', 'category', 'name')

admin.site.register(ShoppingList, ShoppingListAdmin)
admin.site.register(ShoppingListCategory, ShoppingListCategoryAdmin)
admin.site.register(ShoppingListItem, ShoppingListItemAdmin)
admin.site.register(ShoppingListTemplate, ShoppingListTemplateAdmin)
admin.site.register(ShoppingListTemplateItem, ShoppingListTemplateItemAdmin)