from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import IntegrityError
from datetime import date, timedelta, datetime
import calendar
import json

from .models import MealPlan, MealPlanTemplate, WeeklyMealPlan
from .forms import MealPlanForm, MealPlanTemplateForm
from apps.recipes.models import Recipe

@login_required
def meal_calendar(request):
    """Display meal planning calendar view"""
    # Get the current week or requested week
    today = date.today()
    week_offset = int(request.GET.get('week', 0))
    
    # Calculate week start (Monday)
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    # Get meal plans for the week
    meal_plans = MealPlan.objects.filter(
        user=request.user,
        date__range=[week_start, week_end]
    ).select_related('recipe').order_by('date', 'meal_type')
    
    # Organize meals by day and meal type
    week_data = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_meals = {
            'date': day_date,
            'day_name': calendar.day_name[day_date.weekday()],
            'is_today': day_date == today,
            'meals': {
                'breakfast': [],
                'lunch': [],
                'dinner': [],
                'snack': [],
            }
        }
        
        # Group meals by type for this day
        for meal in meal_plans:
            if meal.date == day_date:
                day_meals['meals'][meal.meal_type].append(meal)
        
        week_data.append(day_meals)
    
    # Get recent recipes for quick adding
    recent_recipes = Recipe.objects.filter(
        author=request.user
    ).order_by('-created_at')[:10]
    
    # Get meal plan templates
    templates = MealPlanTemplate.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'week_data': week_data,
        'week_start': week_start,
        'week_end': week_end,
        'week_offset': week_offset,
        'prev_week': week_offset - 1,
        'next_week': week_offset + 1,
        'recent_recipes': recent_recipes,
        'templates': templates,
        'meal_types': MealPlan.MEAL_TYPES,
    }
    
    return render(request, 'meal_planning/calendar.html', context)

@login_required
def add_meal_plan(request):
    """Add a meal plan via AJAX"""
    if request.method == 'POST':
        try:
            form = MealPlanForm(request.POST)
            if form.is_valid():
                meal_plan = form.save(commit=False)
                meal_plan.user = request.user
                
                # Check if this exact meal plan already exists
                existing_meal = MealPlan.objects.filter(
                    user=request.user,
                    recipe=meal_plan.recipe,
                    date=meal_plan.date,
                    meal_type=meal_plan.meal_type
                ).first()
                
                if existing_meal:
                    # Update the existing meal plan instead of creating a new one
                    existing_meal.servings = meal_plan.servings
                    existing_meal.notes = meal_plan.notes
                    existing_meal.save()
                    meal_plan = existing_meal
                    message = 'Meal plan updated successfully!'
                else:
                    meal_plan.save()
                    message = 'Meal plan added successfully!'
                
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'meal_plan': {
                        'id': meal_plan.id,
                        'recipe_title': meal_plan.recipe.title,
                        'recipe_url': meal_plan.recipe.get_absolute_url(),
                        'meal_type': meal_plan.meal_type,
                        'servings': meal_plan.servings,
                        'date': meal_plan.date.isoformat(),
                    }
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'errors': form.errors,
                    'message': 'Please check the form data.'
                })
                
        except IntegrityError:
            return JsonResponse({
                'success': False,
                'message': 'This meal is already planned for this date and meal type.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def remove_meal_plan(request, pk):
    """Remove a meal plan via AJAX"""
    meal_plan = get_object_or_404(MealPlan, pk=pk, user=request.user)
    
    if request.method == 'POST':
        meal_plan.delete()
        return JsonResponse({
            'success': True,
            'message': 'Meal plan removed successfully!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def generate_shopping_list(request):
    """Generate shopping list from meal plans for a specific week"""
    if request.method == 'POST':
        week_start = datetime.strptime(request.POST.get('week_start'), '%Y-%m-%d').date()
        week_end = week_start + timedelta(days=6)
        
        # Get all meal plans for the week
        meal_plans = MealPlan.objects.filter(
            user=request.user,
            date__range=[week_start, week_end]
        ).select_related('recipe')
        
        if not meal_plans.exists():
            messages.warning(request, 'No meal plans found for the selected week.')
            return redirect('meal_planning:calendar')
        
        # Import here to avoid circular imports
        from apps.shopping.models import ShoppingList, ShoppingListItem
        from apps.shopping.utils import generate_shopping_list_from_meals
        
        # Generate the shopping list
        shopping_list = generate_shopping_list_from_meals(request.user, meal_plans, week_start)
        
        messages.success(request, f'Shopping list "{shopping_list.name}" created successfully!')
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    return redirect('meal_planning:calendar')

class MealPlanTemplateListView(LoginRequiredMixin, ListView):
    model = MealPlanTemplate
    template_name = 'meal_planning/template_list.html'
    context_object_name = 'templates'
    paginate_by = 12
    
    def get_queryset(self):
        return MealPlanTemplate.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

class MealPlanTemplateCreateView(LoginRequiredMixin, CreateView):
    model = MealPlanTemplate
    form_class = MealPlanTemplateForm
    template_name = 'meal_planning/template_form.html'
    success_url = reverse_lazy('meal_planning:templates')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Meal plan template created successfully!')
        return super().form_valid(form)

@login_required
def apply_template(request, template_id):
    """Apply a meal plan template to a specific week"""
    template = get_object_or_404(MealPlanTemplate, id=template_id, user=request.user)
    
    if request.method == 'POST':
        week_start = datetime.strptime(request.POST.get('week_start'), '%Y-%m-%d').date()
        
        # Clear existing meal plans for the week if requested
        if request.POST.get('clear_existing'):
            week_end = week_start + timedelta(days=6)
            MealPlan.objects.filter(
                user=request.user,
                date__range=[week_start, week_end]
            ).delete()
        
        # Apply template items
        for item in template.items.all():
            meal_date = week_start + timedelta(days=item.day_of_week)
            
            MealPlan.objects.get_or_create(
                user=request.user,
                recipe=item.recipe,
                date=meal_date,
                meal_type=item.meal_type,
                defaults={'servings': item.servings}
            )
        
        messages.success(request, f'Template "{template.name}" applied successfully!')
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})