from django.conf import settings

def site_context(request):
    """Add site-wide context variables"""
    return {
        'site_name': 'Recipe Manager',
        'site_description': 'Organize your recipes, plan your meals, and simplify your cooking.',
    }


def get_meals_for_type(meals, meal_type):
    return [meal for meal in meals if meal.meal_type == meal_type]