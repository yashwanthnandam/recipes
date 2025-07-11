from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from datetime import date, timedelta

class HomeView(TemplateView):
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Try to import models, but handle gracefully if they don't exist yet
        try:
            from apps.recipes.models import Recipe, Category
            
            # Featured recipes (public recipes)
            featured_recipes = Recipe.objects.filter(
                is_public=True
            ).select_related('author', 'category').order_by('-created_at')[:6]
            
            context['featured_recipes'] = featured_recipes
            context['total_recipes'] = Recipe.objects.filter(is_public=True).count()
            
            # Categories with recipe counts
            categories = Category.objects.annotate(
                recipe_count=Count('recipe', filter=Q(recipe__is_public=True))
            ).filter(recipe_count__gt=0)[:8]
            
            context['categories'] = categories
            
        except ImportError:
            # Models don't exist yet, provide empty data
            context['featured_recipes'] = []
            context['total_recipes'] = 0
            context['categories'] = []
        
        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            from apps.recipes.models import Recipe
            from apps.meal_planning.models import MealPlan
            from apps.shopping.models import ShoppingList
            
            # User's recent recipes
            user_recipes = Recipe.objects.filter(author=user).order_by('-created_at')[:5]
            
            # This week's meal plans
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            this_week_meals = MealPlan.objects.filter(
                user=user,
                date__range=[today, week_end]
            ).select_related('recipe').order_by('date', 'meal_type')[:10]
            
            # Active shopping lists
            active_shopping_lists = ShoppingList.objects.filter(
                user=user,
                completed=False
            ).order_by('-created_at')[:5]
            
            # Quick stats
            stats = {
                'total_recipes': Recipe.objects.filter(author=user).count(),
                'this_week_meals': this_week_meals.count(),
                'active_lists': active_shopping_lists.count(),
                'completed_meals': MealPlan.objects.filter(
                    user=user,
                    date__range=[week_start, week_end],
                    completed=True
                ).count(),
            }
            
            context.update({
                'user_recipes': user_recipes,
                'this_week_meals': this_week_meals,
                'active_shopping_lists': active_shopping_lists,
                'stats': stats,
                'week_start': week_start,
                'week_end': week_end,
            })
            
        except ImportError:
            # Models don't exist yet, provide default data
            context.update({
                'user_recipes': [],
                'this_week_meals': [],
                'active_shopping_lists': [],
                'stats': {
                    'total_recipes': 0,
                    'this_week_meals': 0,
                    'active_lists': 0,
                    'completed_meals': 0,
                },
            })
        
        return context

def dashboard(request):
    """Simple dashboard view function"""
    return render(request, 'core/dashboard.html')