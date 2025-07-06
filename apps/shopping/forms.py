from django import forms
from django.contrib.auth import get_user_model
from .models import ShoppingList, ShoppingListItem, ShoppingListTemplate, ShoppingListCategory
from apps.recipes.models import Ingredient

User = get_user_model()

class ShoppingListForm(forms.ModelForm):
    class Meta:
        model = ShoppingList
        fields = ['name', 'description', 'priority', 'due_date', 'shared_with']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'shared_with': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Exclude the current user from sharing options
            self.fields['shared_with'].queryset = User.objects.exclude(id=user.id).order_by('username')

class ShoppingListItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingListItem
        fields = ['ingredient', 'name', 'quantity', 'unit', 'category', 'notes', 'estimated_cost']
        widgets = {
            'ingredient': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.1, 'min': 0.1}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.01, 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['ingredient'].queryset = Ingredient.objects.all().order_by('name')
        self.fields['ingredient'].required = False
        self.fields['category'].queryset = ShoppingListCategory.objects.all().order_by('sort_order', 'name')
        self.fields['category'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        ingredient = cleaned_data.get('ingredient')
        name = cleaned_data.get('name')
        
        if not ingredient and not name:
            raise forms.ValidationError('Either select an ingredient or enter a custom name.')
        
        if ingredient and not name:
            cleaned_data['name'] = ingredient.name
        
        return cleaned_data

class BulkItemAddForm(forms.Form):
    """Form for adding multiple items at once via text input"""
    items_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Enter items, one per line. Format: quantity unit item_name\nExample:\n2 kg Chicken breast\n1 package Pasta\n500 ml Milk'
        }),
        help_text='Enter items one per line. Use format: quantity unit item_name'
    )
    default_category = forms.ModelChoiceField(
        queryset=ShoppingListCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Default category for all items (optional)'
    )

class ShoppingListTemplateForm(forms.ModelForm):
    class Meta:
        model = ShoppingListTemplate
        fields = ['name', 'description', 'category', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ShoppingListShareForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username to share with'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError('User not found.')
        return username