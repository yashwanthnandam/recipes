from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date, timedelta
import calendar

User = get_user_model()

class MealPlan(models.Model):
    MEAL_TYPES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_plans')
    recipe = models.ForeignKey('recipes.Recipe', on_delete=models.CASCADE, related_name='meal_plans')
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES)
    servings = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date', 'meal_type']
        unique_together = ['user', 'recipe', 'date', 'meal_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.recipe.title} - {self.date} ({self.get_meal_type_display()})"
    
    def get_absolute_url(self):
        return reverse('meal_planning:detail', kwargs={'pk': self.pk})

class MealPlanTemplate(models.Model):
    """Pre-defined meal plan templates that users can apply to their calendar"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_templates')
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class MealPlanTemplateItem(models.Model):
    template = models.ForeignKey(MealPlanTemplate, on_delete=models.CASCADE, related_name='items')
    recipe = models.ForeignKey('recipes.Recipe', on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=[(i, calendar.day_name[i]) for i in range(7)])
    meal_type = models.CharField(max_length=10, choices=MealPlan.MEAL_TYPES)
    servings = models.PositiveIntegerField(default=1)
    
    class Meta:
        unique_together = ['template', 'day_of_week', 'meal_type']
    
    def __str__(self):
        return f"{self.template.name} - {calendar.day_name[self.day_of_week]} {self.get_meal_type_display()}"

class WeeklyMealPlan(models.Model):
    """Container for organizing meal plans by week"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_plans')
    week_start_date = models.DateField()  # Monday of the week
    name = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'week_start_date']
        ordering = ['-week_start_date']
    
    def __str__(self):
        return f"{self.user.username} - Week of {self.week_start_date}"
    
    @property
    def week_end_date(self):
        return self.week_start_date + timedelta(days=6)
    
    def get_meals_for_day(self, day_date):
        return MealPlan.objects.filter(
            user=self.user,
            date=day_date
        ).select_related('recipe').order_by('meal_type')
