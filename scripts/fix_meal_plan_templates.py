#!/usr/bin/env python
"""
Fix common issues in meal plan templates
"""

import os
import sys
import django
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.meal_planning.models import MealPlanTemplate, MealPlanTemplateItem
from apps.recipes.models import Recipe
from collections import defaultdict

User = get_user_model()

def fix_incomplete_templates():
    """Fix templates that are missing meals"""
    user = User.objects.get(username='nandamyashwanth')
    templates = MealPlanTemplate.objects.filter(user=user)
    
    print("🔧 Fixing incomplete meal plan templates")
    print("=" * 50)
    
    all_recipes = list(Recipe.objects.filter(author=user, is_public=True).select_related('category'))
    breakfast_recipes = [r for r in all_recipes if r.category and r.category.name == 'Breakfast']
    
    for template in templates:
        print(f"\n📋 Checking {template.name}")
        
        # Get existing items
        existing = defaultdict(lambda: defaultdict(list))
        for item in template.items.all():
            existing[item.day_of_week][item.meal_type].append(item)
        
        fixed_count = 0
        
        # Check each day and meal type
        for day in range(7):
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                if meal_type not in existing[day]:
                    # Missing meal - add one
                    if meal_type == 'breakfast' and breakfast_recipes:
                        recipe = random.choice(breakfast_recipes)
                    else:
                        # Get appropriate recipe for meal type
                        suitable_recipes = []
                        if meal_type == 'lunch':
                            suitable_recipes = [r for r in all_recipes if r.category and r.category.name in ['Chicken', 'Seafood', 'Vegetarian', 'Pasta']]
                        elif meal_type == 'dinner':
                            suitable_recipes = [r for r in all_recipes if r.category and r.category.name in ['Beef', 'Chicken', 'Lamb', 'Seafood']]
                        
                        if not suitable_recipes:
                            suitable_recipes = all_recipes
                        
                        recipe = random.choice(suitable_recipes)
                    
                    MealPlanTemplateItem.objects.create(
                        template=template,
                        recipe=recipe,
                        day_of_week=day,
                        meal_type=meal_type,
                        servings=4
                    )
                    
                    fixed_count += 1
        
        if fixed_count > 0:
            print(f"   ✅ Added {fixed_count} missing meals")
        else:
            print(f"   ✓ Template is complete")
    
    print(f"\n🎉 Template fixing completed!")

if __name__ == '__main__':
    fix_incomplete_templates()