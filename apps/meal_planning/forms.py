from django import forms
from django.contrib.auth import get_user_model
from .models import MealPlan, MealPlanTemplate, MealPlanTemplateItem
from apps.recipes.models import Recipe

User = get_user_model()

class MealPlanForm(forms.ModelForm):
    class Meta:
        model = MealPlan
        fields = ['recipe', 'date', 'meal_type', 'servings', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'meal_type': forms.Select(attrs={'class': 'form-control'}),
            'servings': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filter recipes to user's own recipes and public recipes
            self.fields['recipe'].queryset = Recipe.objects.filter(
                models.Q(author=user) | models.Q(is_public=True)
            ).select_related('category').order_by('title')
        
        self.fields['recipe'].widget.attrs.update({'class': 'form-control'})
        self.fields['recipe'].empty_label = "Select a recipe..."

class MealPlanTemplateForm(forms.ModelForm):
    class Meta:
        model = MealPlanTemplate
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter template name...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your meal plan template...'
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MealPlanTemplateItemForm(forms.ModelForm):
    class Meta:
        model = MealPlanTemplateItem
        fields = ['recipe', 'day_of_week', 'meal_type', 'servings']
        widgets = {
            'recipe': forms.Select(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'meal_type': forms.Select(attrs={'class': 'form-control'}),
            'servings': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['recipe'].queryset = Recipe.objects.filter(
                models.Q(author=user) | models.Q(is_public=True)
            ).select_related('category').order_by('title')

class QuickMealPlanForm(forms.Form):
    """Form for quickly adding meal plans"""
    recipe = forms.ModelChoiceField(
        queryset=Recipe.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    meal_type = forms.ChoiceField(
        choices=MealPlan.MEAL_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    servings = forms.IntegerField(
        min_value=1,
        max_value=12,
        initial=4,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            from django.db import models
            self.fields['recipe'].queryset = Recipe.objects.filter(
                models.Q(author=user) | models.Q(is_public=True)
            ).select_related('category').order_by('title')