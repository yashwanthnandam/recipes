from django.contrib import admin
from .models import MealPlan, MealPlanTemplate, MealPlanTemplateItem, WeeklyMealPlan

class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'date', 'meal_type', 'servings', 'completed', 'created_at')
    list_filter = ('meal_type', 'completed', 'date', 'user')
    search_fields = ('user__username', 'recipe__title', 'notes')
    ordering = ('-date', 'meal_type')
    readonly_fields = ('created_at',)
    
class MealPlanTemplateItemInline(admin.TabularInline):
    model = MealPlanTemplateItem
    extra = 1

class MealPlanTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_public', 'created_at')
    list_filter = ('is_public', 'user')
    search_fields = ('name', 'description', 'user__username')
    ordering = ('-created_at',)
    inlines = [MealPlanTemplateItemInline]
    readonly_fields = ('created_at',)

class WeeklyMealPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'week_start_date', 'name', 'created_at')
    list_filter = ('user', 'week_start_date')
    search_fields = ('user__username', 'name', 'notes')
    ordering = ('-week_start_date',)
    readonly_fields = ('created_at',)

class MealPlanTemplateItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'recipe', 'day_of_week', 'meal_type', 'servings')
    list_filter = ('day_of_week', 'meal_type', 'template')
    search_fields = ('template__name', 'recipe__title')
    ordering = ('template', 'day_of_week', 'meal_type')

admin.site.register(MealPlan, MealPlanAdmin)
admin.site.register(MealPlanTemplate, MealPlanTemplateAdmin)
admin.site.register(MealPlanTemplateItem, MealPlanTemplateItemAdmin)
admin.site.register(WeeklyMealPlan, WeeklyMealPlanAdmin)