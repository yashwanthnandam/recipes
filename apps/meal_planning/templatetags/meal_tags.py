from django import template

register = template.Library()

@register.filter
def get_meals_for_type(meals, meal_type):
    return [meal for meal in meals if getattr(meal, 'meal_type', None) == meal_type]