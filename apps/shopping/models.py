from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

User = get_user_model()

class ShoppingList(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_lists')
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    shared_with = models.ManyToManyField(User, blank=True, related_name='shared_shopping_lists')
    auto_generated = models.BooleanField(default=False)  # True if generated from meal plans
    meal_plan_week = models.DateField(null=True, blank=True)  # Week start date if auto-generated
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('shopping:detail', kwargs={'pk': self.pk})
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def completed_items(self):
        return self.items.filter(completed=True).count()
    
    @property
    def completion_percentage(self):
        if self.total_items == 0:
            return 0
        return round((self.completed_items / self.total_items) * 100)
    
    @property
    def estimated_total_cost(self):
        return sum(item.estimated_cost or 0 for item in self.items.all())

class ShoppingListCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#6c757d')
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Shopping List Categories'
    
    def __str__(self):
        return self.name

class ShoppingListItem(models.Model):
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('lb', 'Pound'),
        ('oz', 'Ounce'),
        ('l', 'Liter'),
        ('ml', 'Milliliter'),
        ('cup', 'Cup'),
        ('tbsp', 'Tablespoon'),
        ('tsp', 'Teaspoon'),
        ('package', 'Package'),
        ('bottle', 'Bottle'),
        ('can', 'Can'),
        ('box', 'Box'),
    ]
    
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey('recipes.Ingredient', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)  # Custom name if no ingredient
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    category = models.ForeignKey(ShoppingListCategory, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    estimated_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(default=1)  # For custom ordering
    from_recipe = models.ForeignKey('recipes.Recipe', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['completed', 'category__sort_order', 'priority', 'name']
    
    def __str__(self):
        return f"{self.quantity} {self.unit} {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.name and self.ingredient:
            self.name = self.ingredient.name
        super().save(*args, **kwargs)

class ShoppingListTemplate(models.Model):
    """Pre-defined shopping list templates for common shopping needs"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_templates')
    is_public = models.BooleanField(default=False)
    category = models.CharField(max_length=100, blank=True)  # e.g., "Weekly Groceries", "Party Supplies"
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class ShoppingListTemplateItem(models.Model):
    template = models.ForeignKey(ShoppingListTemplate, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey('recipes.Ingredient', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, choices=ShoppingListItem.UNIT_CHOICES, default='piece')
    category = models.ForeignKey(ShoppingListCategory, on_delete=models.SET_NULL, null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.quantity} {self.unit} {self.name}"
