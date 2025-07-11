from django import forms
from .models import Recipe, Category, RecipeStep

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            'title', 'description', 'instructions', 'prep_time', 
            'cook_time', 'servings', 'difficulty', 'category', 
            'image', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter recipe title...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of your recipe...'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Step-by-step cooking instructions...'
            }),
            'prep_time': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': '15'
            }),
            'cook_time': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': '30'
            }),
            'servings': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': '4'
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-select'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make category optional
        self.fields['category'].empty_label = "Select a category (optional)"
        self.fields['category'].required = False
        
        # Add custom help text
        self.fields['prep_time'].help_text = "Time needed to prepare ingredients"
        self.fields['cook_time'].help_text = "Time needed to cook the recipe"
        self.fields['servings'].help_text = "Number of people this recipe serves"

class RecipeStepForm(forms.ModelForm):
    class Meta:
        model = RecipeStep
        fields = ['step_number', 'instruction', 'time_required']
        widgets = {
            'step_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'instruction': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'time_required': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }