#!/usr/bin/env python
"""
Populate meal plan templates with appropriate recipes using intelligent assignment
"""

import os
import sys
import django
import random
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.recipes.models import Recipe, Category
from apps.meal_planning.models import MealPlanTemplate, MealPlanTemplateItem
from apps.recipes.services.gpt_service import recipe_analyzer
import calendar

User = get_user_model()

class MealPlanPopulator:
    def __init__(self):
        self.user = User.objects.get(username='nandamyashwanth')
        self.recipes_by_category = self._organize_recipes_by_category()
        self.use_gpt = recipe_analyzer.enabled
        
        # Define meal type preferences for better assignment
        self.meal_preferences = {
            'breakfast': {
                'categories': ['Breakfast', 'Dessert'],
                'keywords': ['pancake', 'egg', 'toast', 'omelette', 'breakfast', 'mandazi'],
                'avoid_keywords': ['soup', 'stew', 'heavy']
            },
            'lunch': {
                'categories': ['Chicken', 'Seafood', 'Vegetarian', 'Pasta', 'Starter'],
                'keywords': ['salad', 'sandwich', 'light', 'soup', 'pasta'],
                'avoid_keywords': ['dessert', 'cake', 'heavy']
            },
            'dinner': {
                'categories': ['Beef', 'Chicken', 'Lamb', 'Pork', 'Seafood', 'Pasta'],
                'keywords': ['stew', 'roast', 'main', 'hearty'],
                'avoid_keywords': ['dessert', 'cake', 'breakfast']
            },
            'snack': {
                'categories': ['Dessert', 'Side', 'Starter'],
                'keywords': ['light', 'quick', 'small', 'tart', 'cake'],
                'avoid_keywords': ['heavy', 'main', 'stew']
            }
        }
        
        # Template-specific preferences
        self.template_preferences = {
            'Keto Lifestyle': {
                'prefer_categories': ['Beef', 'Chicken', 'Seafood', 'Lamb', 'Pork'],
                'avoid_categories': ['Dessert', 'Pasta'],
                'keywords': ['protein', 'meat', 'fish'],
                'avoid_keywords': ['pasta', 'bread', 'sugar', 'cake']
            },
            'Mediterranean Magic': {
                'prefer_categories': ['Seafood', 'Chicken', 'Vegetarian', 'Lamb'],
                'keywords': ['olive', 'mediterranean', 'fish', 'fresh'],
                'avoid_keywords': ['heavy', 'fried']
            },
            'Plant-Based Power': {
                'prefer_categories': ['Vegetarian', 'Vegan'],
                'avoid_categories': ['Beef', 'Chicken', 'Lamb', 'Pork', 'Seafood'],
                'keywords': ['vegetarian', 'vegan', 'plant'],
                'avoid_keywords': ['meat', 'fish', 'chicken', 'beef']
            },
            'Athlete\'s Performance': {
                'prefer_categories': ['Chicken', 'Beef', 'Seafood', 'Lamb'],
                'keywords': ['protein', 'energy', 'performance'],
                'avoid_keywords': ['light', 'small']
            },
            'Budget Friendly': {
                'prefer_categories': ['Chicken', 'Vegetarian', 'Pasta'],
                'keywords': ['simple', 'basic', 'easy'],
                'avoid_keywords': ['expensive', 'exotic']
            },
            'Busy Professional': {
                'prefer_categories': ['Chicken', 'Pasta', 'Vegetarian'],
                'keywords': ['quick', 'easy', 'simple', '15-minute'],
                'avoid_keywords': ['complex', 'long', 'slow']
            },
            'Seafood Week': {
                'prefer_categories': ['Seafood'],
                'keywords': ['fish', 'seafood', 'salmon', 'tuna'],
                'avoid_categories': ['Beef', 'Chicken', 'Lamb', 'Pork']
            },
            'Meat Lovers': {
                'prefer_categories': ['Beef', 'Lamb', 'Pork'],
                'keywords': ['meat', 'steak', 'beef', 'lamb'],
                'avoid_categories': ['Vegetarian', 'Vegan', 'Seafood']
            },
            'Vegetarian Delight': {
                'prefer_categories': ['Vegetarian', 'Vegan'],
                'avoid_categories': ['Beef', 'Chicken', 'Lamb', 'Pork', 'Seafood'],
                'keywords': ['vegetarian', 'vegan']
            },
            'Family Favorites': {
                'prefer_categories': ['Chicken', 'Pasta', 'Beef'],
                'keywords': ['family', 'kid', 'simple', 'favorite'],
                'avoid_keywords': ['spicy', 'exotic', 'complex']
            },
            'World Cuisine Explorer': {
                'keywords': ['international', 'exotic', 'world'],
                'prefer_variety': True
            },
            'Comfort Food Classics': {
                'prefer_categories': ['Beef', 'Chicken', 'Pasta'],
                'keywords': ['comfort', 'classic', 'hearty', 'traditional'],
                'avoid_keywords': ['light', 'diet']
            }
        }

    def _organize_recipes_by_category(self):
        """Organize recipes by their categories"""
        recipes_by_category = defaultdict(list)
        
        for recipe in Recipe.objects.filter(author=self.user, is_public=True).select_related('category'):
            if recipe.category:
                recipes_by_category[recipe.category.name].append(recipe)
            else:
                recipes_by_category['Miscellaneous'].append(recipe)
        
        return recipes_by_category

    def _score_recipe_for_template_and_meal(self, recipe, template_name, meal_type):
        """Score how well a recipe fits a template and meal type"""
        score = 0
        recipe_title_lower = recipe.title.lower()
        recipe_category = recipe.category.name if recipe.category else 'Miscellaneous'
        
        # Base score for meal type preferences
        meal_prefs = self.meal_preferences.get(meal_type, {})
        
        # Category preference for meal type
        if recipe_category in meal_prefs.get('categories', []):
            score += 30
        
        # Keyword matching for meal type
        for keyword in meal_prefs.get('keywords', []):
            if keyword in recipe_title_lower:
                score += 20
        
        # Avoid keywords for meal type
        for avoid_keyword in meal_prefs.get('avoid_keywords', []):
            if avoid_keyword in recipe_title_lower:
                score -= 25
        
        # Template-specific preferences
        template_prefs = self.template_preferences.get(template_name, {})
        
        # Preferred categories for template
        if recipe_category in template_prefs.get('prefer_categories', []):
            score += 25
        
        # Avoided categories for template
        if recipe_category in template_prefs.get('avoid_categories', []):
            score -= 40
        
        # Template keyword matching
        for keyword in template_prefs.get('keywords', []):
            if keyword in recipe_title_lower:
                score += 15
        
        # Template avoid keywords
        for avoid_keyword in template_prefs.get('avoid_keywords', []):
            if avoid_keyword in recipe_title_lower:
                score -= 20
        
        # Special handling for variety preference
        if template_prefs.get('prefer_variety'):
            # Give bonus for less common categories
            if recipe_category in ['Goat', 'Miscellaneous']:
                score += 20
        
        return max(0, score)  # Ensure non-negative score

    def _get_best_recipes_for_slot(self, template_name, meal_type, exclude_recipes=None):
        """Get the best recipes for a specific template and meal type slot"""
        if exclude_recipes is None:
            exclude_recipes = set()
        
        all_recipes = []
        for category_recipes in self.recipes_by_category.values():
            all_recipes.extend(category_recipes)
        
        # Filter out already used recipes
        available_recipes = [r for r in all_recipes if r.id not in exclude_recipes]
        
        if not available_recipes:
            return []
        
        # Score all available recipes
        scored_recipes = []
        for recipe in available_recipes:
            score = self._score_recipe_for_template_and_meal(recipe, template_name, meal_type)
            scored_recipes.append((recipe, score))
        
        # Sort by score (highest first)
        scored_recipes.sort(key=lambda x: x[1], reverse=True)
        
        # Return top candidates (with some randomness for variety)
        top_candidates = [r for r, s in scored_recipes[:10] if s > 0]
        
        if not top_candidates:
            # Fallback to any available recipes
            return available_recipes[:5]
        
        return top_candidates

    def populate_template(self, template):
        """Populate a single meal plan template with appropriate recipes"""
        print(f"\n📋 Populating template: {template.name}")
        
        # Clear existing items
        template.items.all().delete()
        
        used_recipes = set()
        created_items = 0
        
        # Define meals for each day
        meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        
        for day in range(7):  # 7 days of the week
            day_name = calendar.day_name[day]
            print(f"  📅 {day_name}:")
            
            for meal_type in meal_types:
                # Get best recipes for this slot
                candidates = self._get_best_recipes_for_slot(
                    template.name, meal_type, used_recipes
                )
                
                if candidates:
                    # Select recipe (with some randomness for variety)
                    if len(candidates) > 1:
                        # Weight selection towards higher-scored recipes
                        weights = [max(1, len(candidates) - i) for i in range(len(candidates))]
                        selected_recipe = random.choices(candidates, weights=weights)[0]
                    else:
                        selected_recipe = candidates[0]
                    
                    # Determine appropriate servings based on meal type
                    if meal_type == 'snack':
                        servings = random.choice([2, 3])
                    elif meal_type == 'breakfast':
                        servings = random.choice([3, 4])
                    else:
                        servings = random.choice([4, 6])
                    
                    # Create the meal plan item
                    MealPlanTemplateItem.objects.create(
                        template=template,
                        recipe=selected_recipe,
                        day_of_week=day,
                        meal_type=meal_type,
                        servings=servings
                    )
                    
                    used_recipes.add(selected_recipe.id)
                    created_items += 1
                    
                    print(f"    🍽️  {meal_type.capitalize()}: {selected_recipe.title} ({selected_recipe.category.name if selected_recipe.category else 'No category'})")
                else:
                    print(f"    ❌ No suitable recipe found for {meal_type}")
        
        print(f"  ✅ Created {created_items} meal items for {template.name}")
        return created_items

    def populate_all_templates(self):
        """Populate all meal plan templates"""
        templates = MealPlanTemplate.objects.filter(user=self.user).order_by('name')
        
        print(f"🚀 Starting to populate {templates.count()} meal plan templates")
        print(f"📊 Available recipes by category:")
        
        for category, recipes in self.recipes_by_category.items():
            print(f"  {category}: {len(recipes)} recipes")
        
        total_items = 0
        
        for template in templates:
            try:
                items_created = self.populate_template(template)
                total_items += items_created
            except Exception as e:
                print(f"❌ Error populating {template.name}: {e}")
        
        print(f"\n🎉 Completed! Created {total_items} total meal plan items across {templates.count()} templates")
        return total_items

def main():
    """Main function to run the meal plan population"""
    print("🍽️  Meal Plan Template Populator")
    print("=" * 50)
    
    populator = MealPlanPopulator()
    
    # Check if we have enough recipes
    total_recipes = sum(len(recipes) for recipes in populator.recipes_by_category.values())
    
    if total_recipes < 20:
        print(f"⚠️  Warning: Only {total_recipes} recipes available. Consider importing more recipes first.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    print(f"✅ Found {total_recipes} recipes across {len(populator.recipes_by_category)} categories")
    
    if populator.use_gpt:
        print("🤖 GPT service is available for enhanced categorization")
    else:
        print("🔧 Using rule-based recipe assignment")
    
    # Run the population
    total_items = populator.populate_all_templates()
    
    print(f"\n📈 Summary:")
    print(f"  • Templates populated: {MealPlanTemplate.objects.filter(user=populator.user).count()}")
    print(f"  • Total meal items created: {total_items}")
    print(f"  • Average items per template: {total_items / MealPlanTemplate.objects.filter(user=populator.user).count():.1f}")
    
    print(f"\n🎯 Next steps:")
    print(f"  1. Visit http://localhost:8000/meal-planning/templates/ to view templates")
    print(f"  2. Apply templates to your weekly meal plans")
    print(f"  3. Generate shopping lists from meal plans")

if __name__ == '__main__':
    main()