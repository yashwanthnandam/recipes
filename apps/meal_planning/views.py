from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from datetime import date, timedelta, datetime
import calendar
import json
import sys
import os
from django.http import JsonResponse, HttpResponse
from .utils.pdf_export import export_week_to_pdf
import json
from .models import MealPlan, MealPlanTemplate, MealPlanTemplateItem, WeeklyMealPlan
from .forms import MealPlanForm, MealPlanTemplateForm
from apps.recipes.models import Recipe, Category
from django.conf import settings


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
    ).select_related('recipe', 'recipe__category').order_by('date', 'meal_type')
    
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
        Q(author=request.user) | Q(is_public=True)
    ).select_related('category').order_by('-created_at')[:10]
    
    # Get meal plan templates
    templates = MealPlanTemplate.objects.filter(
        Q(user=request.user) | Q(is_public=True)
    ).prefetch_related('items__recipe').order_by('-created_at')[:5]
    
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

class MealPlanTemplateListView(LoginRequiredMixin, ListView):
    model = MealPlanTemplate
    template_name = 'meal_planning/template_list.html'
    context_object_name = 'templates'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = MealPlanTemplate.objects.filter(
            Q(user=self.request.user) | Q(is_public=True)
        ).select_related('user').prefetch_related('items__recipe__category').annotate(
            meal_count=Count('items')
        ).order_by('-created_at')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by category
        category_filter = self.request.GET.get('category')
        if category_filter:
            if category_filter == 'mine':
                queryset = queryset.filter(user=self.request.user)
            elif category_filter == 'public':
                queryset = queryset.filter(is_public=True).exclude(user=self.request.user)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        return context

class MealPlanTemplateDetailView(LoginRequiredMixin, DetailView):
    model = MealPlanTemplate
    template_name = 'meal_planning/template_detail.html'
    context_object_name = 'template'
    
    def get_queryset(self):
        return MealPlanTemplate.objects.filter(
            Q(user=self.request.user) | Q(is_public=True)
        ).select_related('user').prefetch_related(
            'items__recipe__category',
            'items__recipe__author'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Organize template items by day and meal type
        template_items = self.object.items.all().order_by('day_of_week', 'meal_type')
        
        week_data = []
        for day in range(7):
            day_data = {
                'day_name': calendar.day_name[day],
                'day_number': day,
                'meals': {
                    'breakfast': [],
                    'lunch': [],
                    'dinner': [],
                    'snack': [],
                }
            }
            
            for item in template_items:
                if item.day_of_week == day:
                    day_data['meals'][item.meal_type].append(item)
            
            week_data.append(day_data)
        
        context['week_data'] = week_data
        return context

class MealPlanTemplateCreateView(LoginRequiredMixin, CreateView):
    model = MealPlanTemplate
    template_name = 'meal_planning/template_form.html'
    fields = ['name', 'description', 'is_public']
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Meal plan template "{form.instance.name}" created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('meal_planning:template_edit', kwargs={'pk': self.object.pk})

class MealPlanTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = MealPlanTemplate
    template_name = 'meal_planning/template_form.html'
    fields = ['name', 'description', 'is_public']
    
    def get_queryset(self):
        return MealPlanTemplate.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, f'Meal plan template "{form.instance.name}" updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('meal_planning:template_detail', kwargs={'pk': self.object.pk})

class MealPlanTemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = MealPlanTemplate
    template_name = 'meal_planning/template_confirm_delete.html'
    success_url = reverse_lazy('meal_planning:templates')
    
    def get_queryset(self):
        return MealPlanTemplate.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        template_name = self.get_object().name
        messages.success(request, f'Meal plan template "{template_name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def template_edit_meals(request, pk):
    """Edit meals in a meal plan template"""
    template = get_object_or_404(MealPlanTemplate, pk=pk, user=request.user)
    
    # Get all available recipes
    recipes = Recipe.objects.filter(
        Q(author=request.user) | Q(is_public=True)
    ).select_related('category').order_by('title')
    
    # Get template items organized by day and meal type
    template_items = template.items.all().select_related('recipe__category')
    
    # Organize items by day and meal type
    week_data = []
    for day in range(7):
        day_data = {
            'day_name': calendar.day_name[day],
            'day_number': day,
            'meals': {
                'breakfast': None,
                'lunch': None,
                'dinner': None,
                'snack': None,
            }
        }
        
        for item in template_items:
            if item.day_of_week == day:
                day_data['meals'][item.meal_type] = item
        
        week_data.append(day_data)
    
    if request.method == 'POST':
        try:
            # Clear existing items
            template.items.all().delete()
            
            # Process form data
            for day in range(7):
                for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
                    recipe_id = request.POST.get(f'day_{day}_{meal_type}_recipe')
                    servings = request.POST.get(f'day_{day}_{meal_type}_servings')
                    
                    if recipe_id and servings:
                        try:
                            recipe = Recipe.objects.get(id=recipe_id)
                            # Check if user has access to this recipe
                            if recipe.author == request.user or recipe.is_public:
                                MealPlanTemplateItem.objects.create(
                                    template=template,
                                    recipe=recipe,
                                    day_of_week=day,
                                    meal_type=meal_type,
                                    servings=int(servings)
                                )
                        except (Recipe.DoesNotExist, ValueError):
                            continue
            
            messages.success(request, f'Meal plan template "{template.name}" updated successfully!')
            return redirect('meal_planning:template_detail', pk=template.pk)
            
        except Exception as e:
            messages.error(request, f'Error updating template: {str(e)}')
    
    context = {
        'template': template,
        'recipes': recipes,
        'week_data': week_data,
        'meal_types': MealPlan.MEAL_TYPES,
    }
    
    return render(request, 'meal_planning/template_edit_meals.html', context)

@login_required
def recipe_search_ajax(request):
    """AJAX endpoint for recipe search"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    
    recipes = Recipe.objects.filter(
        Q(author=request.user) | Q(is_public=True)
    ).select_related('category')
    
    if query:
        recipes = recipes.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )
    
    if category_id:
        recipes = recipes.filter(category_id=category_id)
    
    recipes = recipes.order_by('title')[:20]  # Limit results
    
    results = []
    for recipe in recipes:
        results.append({
            'id': recipe.id,
            'title': recipe.title,
            'category': recipe.category.name if recipe.category else '',
            'author': recipe.author.username,
            'is_public': recipe.is_public,
            'image_url': recipe.image.url if recipe.image else None,
            'prep_time': recipe.prep_time,
            'cook_time': recipe.cook_time,
            'servings': recipe.servings,
        })
    
    return JsonResponse({'recipes': results})

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
def apply_template(request, template_id):
    """Apply a meal plan template to a specific week"""
    template = get_object_or_404(MealPlanTemplate, id=template_id)
    
    # Check if user has access to this template
    if not (template.user == request.user or template.is_public):
        return JsonResponse({'success': False, 'message': 'Access denied.'})
    
    if request.method == 'POST':
        try:
            week_start_str = request.POST.get('week_start')
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            
            # Clear existing meal plans for the week if requested
            if request.POST.get('clear_existing'):
                week_end = week_start + timedelta(days=6)
                MealPlan.objects.filter(
                    user=request.user,
                    date__range=[week_start, week_end]
                ).delete()
            
            # Apply template items
            applied_count = 0
            for item in template.items.all():
                meal_date = week_start + timedelta(days=item.day_of_week)
                
                meal_plan, created = MealPlan.objects.get_or_create(
                    user=request.user,
                    recipe=item.recipe,
                    date=meal_date,
                    meal_type=item.meal_type,
                    defaults={
                        'servings': item.servings,
                        'notes': f'Applied from template: {template.name}'
                    }
                )
                
                if created:
                    applied_count += 1
            
            messages.success(request, f'Template "{template.name}" applied successfully! {applied_count} meals added.')
            return JsonResponse({'success': True, 'applied_count': applied_count})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def generate_shopping_list(request):
    """Generate shopping list from meal plans for a specific week"""
    if request.method == 'POST':
        try:
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
            
        except Exception as e:
            messages.error(request, f'Error generating shopping list: {str(e)}')
    
    return redirect('meal_planning:calendar')

@login_required
def copy_template(request, template_id):
    """Copy a public template to user's own templates"""
    template = get_object_or_404(MealPlanTemplate, id=template_id, is_public=True)
    
    if request.method == 'POST':
        try:
            # Create a copy of the template
            new_template = MealPlanTemplate.objects.create(
                name=f"{template.name} (Copy)",
                description=template.description,
                user=request.user,
                is_public=False
            )
            
            # Copy all template items
            for item in template.items.all():
                MealPlanTemplateItem.objects.create(
                    template=new_template,
                    recipe=item.recipe,
                    day_of_week=item.day_of_week,
                    meal_type=item.meal_type,
                    servings=item.servings
                )
            
            messages.success(request, f'Template "{template.name}" copied successfully!')
            return redirect('meal_planning:template_detail', pk=new_template.pk)
            
        except Exception as e:
            messages.error(request, f'Error copying template: {str(e)}')
    
    return redirect('meal_planning:template_detail', pk=template_id)


# Add this new view to your existing views.py
@login_required
def export_meal_plan_pdf(request):
    """Export weekly meal plan as PDF"""
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
    ).select_related('recipe', 'recipe__category').order_by('date', 'meal_type')
    
    # Organize meals by day and meal type (same logic as calendar view)
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
    
    # Generate PDF
    return export_week_to_pdf(week_data, week_start, week_end, request.user)

@login_required 
def export_project_analysis_pdf(request):
    """Export project analysis as PDF"""
    # Run the analysis
    import subprocess
    import json
    
    try:
        # Run the analysis script
        result = subprocess.run([
            sys.executable, 'scripts/analyze_project_size.py'
        ], capture_output=True, text=True, cwd=settings.BASE_DIR)
        
        # Load the JSON data
        analysis_file = os.path.join(settings.BASE_DIR, 'project_analysis.json')
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)
            
            # Create PDF (you'd implement this similar to the meal plan PDF)
            # For now, return JSON response
            return JsonResponse({
                'success': True,
                'data': analysis_data,
                'message': 'Analysis completed successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Analysis file not found'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error running analysis: {str(e)}'
        })