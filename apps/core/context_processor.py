from django.conf import settings

def site_context(request):
    """Add site-wide context variables"""
    return {
        'site_name': 'Recipe Manager',
        'site_description': 'Organize your recipes, plan your meals, and simplify your cooking.',
    }