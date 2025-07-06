from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import CustomUserCreationForm, UserProfileForm, CustomAuthenticationForm
from .models import User

class CustomLoginView(auth_views.LoginView):
    template_name = 'users/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('core:dashboard')

class CustomLogoutView(auth_views.LogoutView):
    next_page = 'core:home'
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)

class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('core:dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, f'Welcome to Recipe Manager, {self.object.first_name}!')
        return response
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully!')
        return super().form_valid(form)

@login_required
def profile_detail(request):
    """Display user profile details"""
    user = request.user
    
    # Get user's recipe statistics
    total_recipes = user.recipes.count()
    public_recipes = user.recipes.filter(is_public=True).count()
    recent_recipes = user.recipes.order_by('-created_at')[:5]
    
    # Get meal planning statistics
    from apps.meal_planning.models import MealPlan
    total_meal_plans = MealPlan.objects.filter(user=user).count()
    
    # Get shopping list statistics
    from apps.shopping.models import ShoppingList
    active_shopping_lists = ShoppingList.objects.filter(user=user, completed=False).count()
    
    context = {
        'user': user,
        'total_recipes': total_recipes,
        'public_recipes': public_recipes,
        'recent_recipes': recent_recipes,
        'total_meal_plans': total_meal_plans,
        'active_shopping_lists': active_shopping_lists,
    }
    
    return render(request, 'users/profile_detail.html', context)

class PasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('users:profile')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully!')
        return super().form_valid(form)

class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')

class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'

class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')

class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'