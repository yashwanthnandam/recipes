from datetime import timedelta
from collections import defaultdict
from decimal import Decimal

from .models import ShoppingList, ShoppingListItem, ShoppingListCategory
from apps.recipes.models import RecipeIngredient

def generate_shopping_list_from_meals(user, meal_plans, week_start):
    """Generate a shopping list from meal plans"""
    week_end = week_start + timedelta(days=6)
    
    # Create shopping list
    shopping_list = ShoppingList.objects.create(
        user=user,
        name=f"Week of {week_start.strftime('%B %d, %Y')}",
        description=f"Auto-generated from meal plans for {week_start} to {week_end}",
        auto_generated=True,
        meal_plan_week=week_start,
    )
    
    # Aggregate ingredients from all recipes
    ingredient_totals = defaultdict(lambda: {'quantity': Decimal('0'), 'unit': None, 'recipes': []})
    
    for meal_plan in meal_plans:
        recipe = meal_plan.recipe
        servings_multiplier = Decimal(str(meal_plan.servings)) / Decimal(str(recipe.servings))
        
        for recipe_ingredient in recipe.ingredients.all():
            ingredient = recipe_ingredient.ingredient
            key = f"{ingredient.id}_{recipe_ingredient.unit.id}"
            
            adjusted_quantity = Decimal(str(recipe_ingredient.quantity)) * servings_multiplier
            ingredient_totals[key]['quantity'] += adjusted_quantity
            ingredient_totals[key]['unit'] = recipe_ingredient.unit
            ingredient_totals[key]['ingredient'] = ingredient
            ingredient_totals[key]['recipes'].append(recipe.title)
    
    # Create shopping list items
    for key, data in ingredient_totals.items():
        ingredient = data['ingredient']
        unit = data['unit']
        quantity = data['quantity']
        recipes = list(set(data['recipes']))  # Remove duplicates
        
        # Try to categorize the ingredient
        category = get_ingredient_category(ingredient)
        
        ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            ingredient=ingredient,
            name=ingredient.name,
            quantity=quantity,
            unit=unit.abbreviation,
            category=category,
            notes=f"For: {', '.join(recipes[:3])}{'...' if len(recipes) > 3 else ''}",
        )
    
    return shopping_list

def get_ingredient_category(ingredient):
    """Determine the shopping category for an ingredient"""
    # This is a simple categorization - you could make this more sophisticated
    category_mapping = {
        'meat': ['chicken', 'beef', 'pork', 'lamb', 'turkey', 'fish', 'salmon', 'tuna'],
        'dairy': ['milk', 'cheese', 'butter', 'yogurt', 'cream', 'eggs'],
        'produce': ['apple', 'banana', 'carrot', 'onion', 'tomato', 'lettuce', 'potato'],
        'pantry': ['flour', 'sugar', 'salt', 'pepper', 'oil', 'vinegar', 'pasta', 'rice'],
        'frozen': ['frozen', 'ice cream'],
        'bakery': ['bread', 'rolls', 'bagels'],
    }
    
    ingredient_name = ingredient.name.lower()
    
    for category_name, keywords in category_mapping.items():
        for keyword in keywords:
            if keyword in ingredient_name:
                try:
                    return ShoppingListCategory.objects.get(name__iexact=category_name)
                except ShoppingListCategory.DoesNotExist:
                    continue
    
    return None

def consolidate_shopping_items(shopping_list):
    """Consolidate duplicate items in a shopping list"""
    items_by_ingredient = defaultdict(list)
    
    for item in shopping_list.items.all():
        key = f"{item.ingredient.id if item.ingredient else item.name}_{item.unit}"
        items_by_ingredient[key].append(item)
    
    # Merge duplicate items
    for items in items_by_ingredient.values():
        if len(items) > 1:
            # Keep the first item and consolidate others into it
            main_item = items[0]
            total_quantity = sum(Decimal(str(item.quantity)) for item in items)
            
            # Combine notes
            notes = [item.notes for item in items if item.notes]
            combined_notes = '; '.join(notes)
            
            # Update main item
            main_item.quantity = total_quantity
            main_item.notes = combined_notes
            main_item.save()
            
            # Delete other items
            for item in items[1:]:
                item.delete()
