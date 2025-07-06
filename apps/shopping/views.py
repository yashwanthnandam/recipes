from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import models
from django.db.models import Sum, Count

from .models import ShoppingList, ShoppingListItem, ShoppingListCategory, ShoppingListTemplate
from .forms import ShoppingListForm, ShoppingListItemForm, ShoppingListTemplateForm
from .utils import generate_shopping_list_from_meals

class ShoppingListListView(LoginRequiredMixin, ListView):
    model = ShoppingList
    template_name = 'shopping/list.html'
    context_object_name = 'shopping_lists'
    paginate_by = 12
    
    def get_queryset(self):
        return ShoppingList.objects.filter(
            user=self.request.user
        ).annotate(
            item_count=Count('items'),
            completed_count=Count('items', filter=models.Q(items__completed=True))
        ).order_by('-created_at')

class ShoppingListDetailView(LoginRequiredMixin, DetailView):
    model = ShoppingList
    template_name = 'shopping/detail.html'
    context_object_name = 'shopping_list'
    
    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shopping_list = self.get_object()
        
        # Group items by category
        categories = ShoppingListCategory.objects.all().order_by('sort_order')
        categorized_items = {}
        uncategorized_items = []
        
        for category in categories:
            category_items = shopping_list.items.filter(category=category).order_by('completed', 'name')
            if category_items.exists():
                categorized_items[category] = category_items
        
        # Items without category
        uncategorized_items = shopping_list.items.filter(category__isnull=True).order_by('completed', 'name')
        
        context.update({
            'categorized_items': categorized_items,
            'uncategorized_items': uncategorized_items,
            'categories': categories,
            'item_form': ShoppingListItemForm(),
        })
        
        return context

class ShoppingListCreateView(LoginRequiredMixin, CreateView):
    model = ShoppingList
    form_class = ShoppingListForm
    template_name = 'shopping/form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Shopping list created successfully!')
        return super().form_valid(form)

class ShoppingListUpdateView(LoginRequiredMixin, UpdateView):
    model = ShoppingList
    form_class = ShoppingListForm
    template_name = 'shopping/form.html'
    
    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Shopping list updated successfully!')
        return super().form_valid(form)

class ShoppingListDeleteView(LoginRequiredMixin, DeleteView):
    model = ShoppingList
    template_name = 'shopping/confirm_delete.html'
    success_url = reverse_lazy('shopping:lists')
    
    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Shopping list deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_item(request, list_id):
    """Add item to shopping list via AJAX"""
    shopping_list = get_object_or_404(ShoppingList, id=list_id, user=request.user)
    
    if request.method == 'POST':
        form = ShoppingListItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.shopping_list = shopping_list
            item.save()
            
            return JsonResponse({
                'success': True,
                'item': {
                    'id': item.id,
                    'name': item.name,
                    'quantity': float(item.quantity),
                    'unit': item.unit,
                    'category': item.category.name if item.category else None,
                    'completed': item.completed,
                }
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'success': False})

@login_required
def toggle_item(request, item_id):
    """Toggle item completion status via AJAX"""
    item = get_object_or_404(ShoppingListItem, id=item_id, shopping_list__user=request.user)
    
    if request.method == 'POST':
        item.completed = not item.completed
        if item.completed:
            item.completed_at = timezone.now()
        else:
            item.completed_at = None
        item.save()
        
        return JsonResponse({
            'success': True,
            'completed': item.completed,
            'completion_percentage': item.shopping_list.completion_percentage
        })
    
    return JsonResponse({'success': False})

@login_required
def delete_item(request, item_id):
    """Delete shopping list item via AJAX"""
    item = get_object_or_404(ShoppingListItem, id=item_id, shopping_list__user=request.user)
    
    if request.method == 'POST':
        item.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
def share_list(request, list_id):
    """Share shopping list with other users"""
    shopping_list = get_object_or_404(ShoppingList, id=list_id, user=request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_to_share = User.objects.get(username=username)
            shopping_list.shared_with.add(user_to_share)
            messages.success(request, f'Shopping list shared with {username}!')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    
    return redirect('shopping:detail', pk=list_id)

@login_required
def shopping_lists(request):
    """Placeholder for shopping lists"""
    return render(request, 'shopping/lists.html', {
        'title': 'Shopping Lists'
    })