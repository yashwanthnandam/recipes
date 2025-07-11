from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.meal_planning.models import MealPlan, MealPlanTemplate, MealPlanTemplateItem
from apps.recipes.models import Recipe, Category
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample meal plans for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            type=str,
            default='nandamyashwanth',
            help='Admin username to create meal plans for (default: nandamyashwanth)'
        )
        parser.add_argument(
            '--create-user',
            action='store_true',
            help='Create user if not exists'
        )
        parser.add_argument(
            '--weeks',
            type=int,
            default=4,
            help='Number of weeks to create meal plans for (default: 4)'
        )

    def handle(self, *args, **options):
        self.admin_username = options['admin_username']
        self.weeks = options['weeks']
        
        # Get or create admin user
        try:
            self.admin_user = User.objects.get(username=self.admin_username)
            self.stdout.write(
                self.style.SUCCESS(f'Using existing user: {self.admin_username}')
            )
        except User.DoesNotExist:
            if options['create_user']:
                self.admin_user = User.objects.create_user(
                    username=self.admin_username,
                    email=f'{self.admin_username}@example.com',
                    password='admin123',
                    is_staff=True,
                    is_superuser=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created admin user: {self.admin_username}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Admin user {self.admin_username} not found. Use --create-user to create.')
                )
                return

        # Check if we have recipes
        recipes = Recipe.objects.filter(is_public=True)
        if not recipes.exists():
            self.stdout.write(
                self.style.ERROR('No public recipes found. Please run the recipe import first.')
            )
            return

        self.stdout.write('Creating sample meal plans...')
        
        # Create advanced meal plan templates
        self.create_advanced_meal_plan_templates()
        
        # Create actual meal plans for the next few weeks
        self.create_weekly_meal_plans()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample meal plans!')
        )

    def create_advanced_meal_plan_templates(self):
        """Create more diverse and interesting meal plan templates"""
        
        # Get recipes by category for better assignment
        recipes_by_category = {}
        for category in Category.objects.all():
            recipes_by_category[category.name] = list(
                Recipe.objects.filter(category=category, is_public=True)
            )
        
        # Fallback to all recipes if category is empty
        all_recipes = list(Recipe.objects.filter(is_public=True))
        
        advanced_templates = [
            {
                'name': 'Keto Lifestyle',
                'description': 'Low-carb, high-fat meal plan perfect for ketogenic diet',
                'category': 'Diet',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Beef', 'snack': 'Starter'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pork', 'snack': 'Side'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Seafood', 'snack': 'Starter'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Chicken', 'snack': 'Side'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Lamb', 'snack': 'Starter'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Beef', 'snack': 'Side'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pork', 'snack': 'Dessert'},
                }
            },
            {
                'name': 'Mediterranean Magic',
                'description': 'Fresh, healthy Mediterranean-inspired meals rich in olive oil, fish, and vegetables',
                'category': 'Healthy',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Vegetarian', 'snack': 'Starter'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Seafood', 'snack': 'Side'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Lamb', 'snack': 'Starter'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Chicken', 'snack': 'Side'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Seafood', 'snack': 'Starter'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Chicken', 'snack': 'Side'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Vegetarian', 'snack': 'Dessert'},
                }
            },
            {
                'name': 'Busy Professional',
                'description': 'Quick and easy meals for busy schedules - all under 30 minutes',
                'category': 'Quick',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Chicken'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Seafood'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Chicken'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Dessert'},
                }
            },
            {
                'name': 'Budget Friendly',
                'description': 'Economical meals that don\'t compromise on taste or nutrition',
                'category': 'Budget',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Pasta'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Vegetarian'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Pasta'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Vegetarian'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                }
            },
            {
                'name': 'Athlete\'s Performance',
                'description': 'High-protein, energy-rich meals designed for active lifestyles',
                'category': 'Fitness',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Beef', 'snack': 'Starter'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Seafood', 'snack': 'Side'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Chicken', 'snack': 'Starter'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Lamb', 'snack': 'Side'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Beef', 'snack': 'Starter'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Seafood', 'snack': 'Side'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Lamb', 'snack': 'Dessert'},
                }
            },
            {
                'name': 'Plant-Based Power',
                'description': 'Completely plant-based meals packed with nutrition and flavor',
                'category': 'Vegan',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Vegan'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Vegan', 'dinner': 'Vegetarian'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Vegan'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Vegan', 'dinner': 'Vegetarian'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Vegan'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Vegan', 'dinner': 'Vegetarian'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Vegan'},
                }
            },
            {
                'name': 'Comfort Food Classics',
                'description': 'Hearty, soul-warming meals that bring comfort and satisfaction',
                'category': 'Comfort',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Pasta'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Beef'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pork'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Pasta'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Chicken'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Dessert'},
                }
            },
            {
                'name': 'World Cuisine Explorer',
                'description': 'A culinary journey around the world with diverse international flavors',
                'category': 'International',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Seafood'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Pasta'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Lamb'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Chicken'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Beef'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Seafood'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Miscellaneous', 'dinner': 'Dessert'},
                }
            },
        ]
        
        for template_data in advanced_templates:
            try:
                # Check if template already exists
                if MealPlanTemplate.objects.filter(name=template_data['name'], user=self.admin_user).exists():
                    self.stdout.write(f'Template "{template_data["name"]}" already exists, skipping...')
                    continue
                
                template = MealPlanTemplate.objects.create(
                    name=template_data['name'],
                    description=template_data['description'],
                    user=self.admin_user,
                    is_public=True
                )
                
                # Add meals to template
                for day_of_week, meals in template_data['meals'].items():
                    for meal_type, category_name in meals.items():
                        # Get recipes from the specified category
                        category_recipes = recipes_by_category.get(category_name, [])
                        if not category_recipes:
                            category_recipes = all_recipes
                        
                        if category_recipes:
                            recipe = random.choice(category_recipes)
                            
                            MealPlanTemplateItem.objects.create(
                                template=template,
                                recipe=recipe,
                                day_of_week=day_of_week,
                                meal_type=meal_type,
                                servings=random.choice([2, 3, 4, 6])  # Vary serving sizes
                            )
                
                self.stdout.write(f'✓ Created meal plan template: {template.name}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating template {template_data["name"]}: {e}')
                )

    def create_weekly_meal_plans(self):
        """Create actual meal plans for the next few weeks"""
        
        # Get all public recipes
        all_recipes = list(Recipe.objects.filter(is_public=True))
        if not all_recipes:
            self.stdout.write(self.style.WARNING('No public recipes found'))
            return
        
        # Create meal plans for the next few weeks
        start_date = date.today()
        
        for week in range(self.weeks):
            week_start = start_date + timedelta(weeks=week)
            
            # Create 3-5 random meal plans per week
            meals_per_week = random.randint(8, 15)
            
            for _ in range(meals_per_week):
                # Random date within the week
                day_offset = random.randint(0, 6)
                meal_date = week_start + timedelta(days=day_offset)
                
                # Random meal type
                meal_type = random.choice(['breakfast', 'lunch', 'dinner', 'snack'])
                
                # Random recipe
                recipe = random.choice(all_recipes)
                
                # Random servings
                servings = random.choice([1, 2, 3, 4, 6])
                
                # Check if this meal plan already exists
                if not MealPlan.objects.filter(
                    user=self.admin_user,
                    recipe=recipe,
                    date=meal_date,
                    meal_type=meal_type
                ).exists():
                    
                    # Create meal plan
                    MealPlan.objects.create(
                        user=self.admin_user,
                        recipe=recipe,
                        date=meal_date,
                        meal_type=meal_type,
                        servings=servings,
                        notes=f'Auto-generated meal plan for {meal_date}',
                        completed=random.choice([True, False]) if meal_date < date.today() else False
                    )
            
            self.stdout.write(f'✓ Created meal plans for week starting {week_start}')