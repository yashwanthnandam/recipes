from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q

from .models import Recipe, Category
from .forms import RecipeForm

class RecipeListView(ListView):
    model = Recipe
    template_name = 'recipes/list.html'
    context_object_name = 'recipes'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Recipe.objects.filter(is_public=True).select_related('author', 'category').prefetch_related('tags', 'ingredients', 'steps')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(instructions__icontains=search_query)
            )
        
        # Category filter
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context

class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/detail.html'
    context_object_name = 'recipe'
    
    def get_queryset(self):
        queryset = Recipe.objects.select_related('author', 'category').prefetch_related(
            'ingredients__ingredient',
            'ingredients__unit', 
            'steps',
            'tags',
            'ratings__user'
        )
        
        if self.request.user.is_authenticated:
            # Show user's own recipes even if private
            return queryset.filter(
                Q(is_public=True) | Q(author=self.request.user)
            )
        return queryset.filter(is_public=True)
from django.forms import inlineformset_factory
from .models import RecipeStep
from .forms import RecipeStepForm

RecipeStepFormSet = inlineformset_factory(
    Recipe, RecipeStep,
    form=RecipeStepForm,
    fields=['step_number', 'instruction', 'time_required'],
    extra=1,
    can_delete=True
)

class RecipeCreateView(LoginRequiredMixin, CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['step_formset'] = RecipeStepFormSet(self.request.POST, self.request.FILES)
        else:
            context['step_formset'] = RecipeStepFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        step_formset = context['step_formset']
        form.instance.author = self.request.user
        self.object = form.save()
        if step_formset.is_valid():
            step_formset.instance = self.object
            step_formset.save()
        else:
            return self.form_invalid(form)
        messages.success(self.request, 'Recipe created successfully!')
        return super().form_valid(form)

class RecipeUpdateView(LoginRequiredMixin, UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'
    
    def get_queryset(self):
        return Recipe.objects.filter(author=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Recipe updated successfully!')
        return super().form_valid(form)

class RecipeDeleteView(LoginRequiredMixin, DeleteView):
    model = Recipe
    template_name = 'recipes/recipe_confirm_delete.html'
    success_url = reverse_lazy('recipes:list')
    
    def get_queryset(self):
        return Recipe.objects.filter(author=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Recipe deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def my_recipes(request):
    """View user's own recipes with enhanced data"""
    recipes = Recipe.objects.filter(author=request.user).select_related('category').prefetch_related(
        'ingredients__ingredient',
        'steps',
        'tags'
    ).order_by('-created_at')
    
    search_query = request.GET.get('search')
    if search_query:
        recipes = recipes.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(instructions__icontains=search_query)
        )
    
    context = {
        'recipes': recipes,
        'search_query': search_query,
    }
    return render(request, 'recipes/my_recipes.html', context)

# Function-based views for compatibility
def recipe_list(request):
    view = RecipeListView.as_view()
    return view(request)

def recipe_detail(request, pk):
    view = RecipeDetailView.as_view()
    return view(request, pk=pk)

@login_required
def calendar_view(request):
    """Placeholder for meal planning calendar"""
    return render(request, 'meal_planning/calendar.html', {
        'title': 'Meal Planning Calendar'
    })