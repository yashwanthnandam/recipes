from django.contrib import admin
from .models import (
    Category, Tag, Unit, Ingredient, Recipe,
    RecipeIngredient, RecipeRating, RecipeStep
)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'icon', 'color')
    search_fields = ('name', 'description')
    ordering = ('name',)

class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)
    ordering = ('name',)

class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'unit_type')
    search_fields = ('name', 'abbreviation')
    list_filter = ('unit_type',)
    ordering = ('name',)

class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'default_unit', 'calories_per_100g')
    search_fields = ('name', 'description')
    list_filter = ('default_unit',)
    ordering = ('name',)

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1

class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 1

class RecipeRatingInline(admin.TabularInline):
    model = RecipeRating
    extra = 0
    readonly_fields = ('user', 'score', 'comment', 'created_at')
    can_delete = False

class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'category', 'difficulty', 
        'servings', 'is_public', 'featured', 'created_at'
    )
    list_filter = ('category', 'difficulty', 'is_public', 'featured', 'tags')
    search_fields = ('title', 'description', 'instructions')
    ordering = ('-created_at',)
    filter_horizontal = ('tags',)
    inlines = [RecipeIngredientInline, RecipeStepInline, RecipeRatingInline]
    readonly_fields = ('created_at', 'updated_at', 'average_rating', 'total_time')

class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'quantity', 'unit', 'notes')
    search_fields = ('recipe__title', 'ingredient__name', 'notes')
    list_filter = ('unit',)

class RecipeRatingAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'score', 'comment', 'created_at')
    search_fields = ('recipe__title', 'user__username', 'comment')
    list_filter = ('score', 'created_at')
    readonly_fields = ('created_at',)

class RecipeStepAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'step_number', 'instruction', 'time_required')
    search_fields = ('recipe__title', 'instruction')
    list_filter = ('recipe',)
    ordering = ('recipe', 'step_number')

admin.site.register(Category, CategoryAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
admin.site.register(RecipeRating, RecipeRatingAdmin)
admin.site.register(RecipeStep, RecipeStepAdmin)