from django import forms
from .models import MealPlan, MealPlanTemplate
from apps.recipes.models import Recipe

class MealPlanForm(forms.ModelForm):
    class Meta:
        model = MealPlan
        fields = ['recipe', 'date', 'meal_type', 'servings', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'meal_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'recipe': forms.Select(attrs={
                'class': 'form-select'
            }),
            'servings': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional notes...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Show user's recipes only
            self.fields['recipe'].queryset = Recipe.objects.filter(
                author=user
            ).order_by('title')

class MealPlanTemplateForm(forms.ModelForm):
    class Meta:
        model = MealPlanTemplate
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Template name...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description...'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }