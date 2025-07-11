#!/usr/bin/env python
"""
Verify meal plan template population results
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.meal_planning.models import MealPlanTemplate, MealPlanTemplateItem
from collections import defaultdict
import calendar

User = get_user_model()

def verify_templates():
    """Verify all meal plan templates have appropriate content"""
    user = User.objects.get(username='nandamyashwanth')
    templates = MealPlanTemplate.objects.filter(user=user).prefetch_related('items__recipe__category')
    
    print("📊 Meal Plan Template Verification Report")
    print("=" * 60)
    
    total_items = 0
    
    for template in templates:
        items = template.items.all()
        total_items += len(items)
        
        print(f"\n📋 {template.name}")
        print(f"   📅 Created: {template.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   🍽️  Total meals: {len(items)}")
        
        # Organize by day and meal type
        by_day = defaultdict(lambda: defaultdict(list))
        category_count = defaultdict(int)
        
        for item in items:
            by_day[item.day_of_week][item.meal_type].append(item)
            if item.recipe.category:
                category_count[item.recipe.category.name] += 1
        
        # Show category distribution
        if category_count:
            print(f"   📂 Categories: {dict(category_count)}")
        
        # Check completeness
        missing_meals = []
        for day in range(7):
            day_name = calendar.day_name[day]
            day_meals = by_day[day]
            
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                if meal_type not in day_meals:
                    missing_meals.append(f"{day_name} {meal_type}")
        
        if missing_meals:
            print(f"   ⚠️  Missing: {', '.join(missing_meals[:5])}")
            if len(missing_meals) > 5:
                print(f"       ... and {len(missing_meals) - 5} more")
        else:
            print(f"   ✅ Complete weekly plan")
        
        # Show sample meals
        print(f"   📝 Sample meals:")
        for day in range(min(2, 7)):  # Show first 2 days
            day_name = calendar.day_name[day]
            day_meals = by_day[day]
            
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                if meal_type in day_meals and day_meals[meal_type]:
                    item = day_meals[meal_type][0]
                    category = item.recipe.category.name if item.recipe.category else 'No category'
                    print(f"     {day_name} {meal_type}: {item.recipe.title} ({category})")
    
    print(f"\n📈 Overall Summary:")
    print(f"   📋 Templates: {templates.count()}")
    print(f"   🍽️  Total meal items: {total_items}")
    print(f"   📊 Average per template: {total_items / templates.count():.1f}")
    
    # Check for template variety
    all_recipes_used = set()
    for template in templates:
        for item in template.items.all():
            all_recipes_used.add(item.recipe.id)
    
    from apps.recipes.models import Recipe
    total_available = Recipe.objects.filter(author=user, is_public=True).count()
    
    print(f"   🎯 Recipe utilization: {len(all_recipes_used)}/{total_available} ({len(all_recipes_used)/total_available*100:.1f}%)")

if __name__ == '__main__':
    verify_templates()