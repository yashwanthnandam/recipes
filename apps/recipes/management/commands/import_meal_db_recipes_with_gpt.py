import os
import requests
import json
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.recipes.models import Recipe, Category, Ingredient, Unit, RecipeIngredient, Tag, RecipeStep
from apps.meal_planning.models import MealPlanTemplate, MealPlanTemplateItem
from apps.recipes.services.gpt_service import recipe_analyzer
import time
from PIL import Image
from io import BytesIO
import calendar
import hashlib
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Import recipes from TheMealDB API with GPT-enhanced step analysis'

    def add_arguments(self, parser):
        parser.add_argument('--recipes-count', type=int, default=100)
        parser.add_argument('--admin-username', type=str, default='nandamyashwanth')
        parser.add_argument('--create-admin', action='store_true')
        parser.add_argument('--skip-images', action='store_true')
        parser.add_argument('--skip-step-images', action='store_true')
        parser.add_argument('--use-gpt', action='store_true', help='Use GPT for intelligent step parsing')
        parser.add_argument('--gpt-batch-size', type=int, default=10, help='Process recipes in batches for GPT')

    def handle(self, *args, **options):
        self.recipes_count = options['recipes_count']
        self.admin_username = options['admin_username']
        self.skip_images = options['skip_images']
        self.skip_step_images = options['skip_step_images']
        self.use_gpt = options['use_gpt']
        self.gpt_batch_size = options['gpt_batch_size']
        
        # Get or create admin user
        try:
            self.admin_user = User.objects.get(username=self.admin_username)
            self.stdout.write(self.style.SUCCESS(f'Using existing user: {self.admin_username}'))
        except User.DoesNotExist:
            if options['create_admin']:
                self.admin_user = User.objects.create_user(
                    username=self.admin_username,
                    email=f'{self.admin_username}@example.com',
                    password='admin123',
                    is_staff=True,
                    is_superuser=True
                )
                self.stdout.write(self.style.SUCCESS(f'Created admin user: {self.admin_username}'))
            else:
                self.stdout.write(self.style.ERROR(f'Admin user {self.admin_username} not found.'))
                return

        if self.use_gpt:
            if not recipe_analyzer.enabled:
                self.stdout.write(self.style.WARNING('GPT is not configured. Falling back to rule-based parsing.'))
                self.use_gpt = False
            else:
                self.stdout.write(self.style.SUCCESS('GPT-enhanced step analysis enabled.'))

        self.stdout.write('Starting TheMealDB import with intelligent step parsing...')
        
        # Initialize default data
        self.create_default_units()
        self.create_default_categories()
        
        # Import recipes
        imported_recipes = self.import_recipes()
        
        # Create meal plan templates
        self.create_meal_plan_templates(imported_recipes)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {len(imported_recipes)} recipes!')
        )

    def create_default_units(self):
        """Create default units for measurements"""
        units_data = [
            ('cup', 'cup', 'volume'),
            ('tablespoon', 'tbsp', 'volume'),
            ('teaspoon', 'tsp', 'volume'),
            ('pound', 'lb', 'weight'),
            ('ounce', 'oz', 'weight'),
            ('gram', 'g', 'weight'),
            ('kilogram', 'kg', 'weight'),
            ('liter', 'l', 'volume'),
            ('milliliter', 'ml', 'volume'),
            ('piece', 'pc', 'count'),
            ('clove', 'clove', 'count'),
            ('pinch', 'pinch', 'count'),
            ('slice', 'slice', 'count'),
            ('can', 'can', 'count'),
            ('package', 'pkg', 'count'),
            ('bottle', 'bottle', 'count'),
            ('jar', 'jar', 'count'),
            ('bunch', 'bunch', 'count'),
            ('sprig', 'sprig', 'count'),
            ('dash', 'dash', 'count'),
        ]
        for name, abbrev, unit_type in units_data:
            Unit.objects.get_or_create(
                name=name,
                defaults={'abbreviation': abbrev, 'unit_type': unit_type}
            )
        self.stdout.write('Created default units')

    def create_default_categories(self):
        """Create default recipe categories"""
        categories_data = [
            ('Beef', 'Main dishes with beef', '🥩', '#dc3545'),
            ('Chicken', 'Chicken-based dishes', '🐔', '#28a745'),
            ('Dessert', 'Sweet treats and desserts', '🍰', '#ffc107'),
            ('Lamb', 'Lamb and mutton dishes', '🐑', '#6f42c1'),
            ('Miscellaneous', 'Various other dishes', '🍽️', '#6c757d'),
            ('Pasta', 'Pasta dishes', '🍝', '#fd7e14'),
            ('Pork', 'Pork-based dishes', '🐷', '#e83e8c'),
            ('Seafood', 'Fish and seafood', '🐟', '#20c997'),
            ('Side', 'Side dishes', '🥗', '#17a2b8'),
            ('Starter', 'Appetizers and starters', '🥙', '#007bff'),
            ('Vegan', 'Plant-based dishes', '🌱', '#28a745'),
            ('Vegetarian', 'Vegetarian dishes', '🥕', '#ffc107'),
            ('Breakfast', 'Morning meals', '🍳', '#fd7e14'),
            ('Goat', 'Goat meat dishes', '🐐', '#6f42c1'),
        ]
        for name, desc, icon, color in categories_data:
            Category.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'icon': icon,
                    'color': color
                }
            )
        self.stdout.write('Created default categories')

    def get_recipes_by_category(self, category):
        """Get recipes from TheMealDB by category"""
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('meals', [])
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error fetching recipes for category {category}: {e}')
            )
            return []

    def get_recipe_details(self, meal_id):
        """Get detailed recipe information"""
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            meals = data.get('meals', [])
            return meals[0] if meals else None
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error fetching recipe details for ID {meal_id}: {e}')
            )
            return None

    def download_image(self, image_url, recipe_title, is_step_image=False):
        """Download and save recipe image with enhanced processing"""
        if self.skip_images or (is_step_image and self.skip_step_images):
            return None
            
        try:
            img_type = "step image" if is_step_image else "main image"
            self.stdout.write(f'Downloading {img_type} for: {recipe_title}')
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(image_url, timeout=30, headers=headers)
            response.raise_for_status()
            if len(response.content) < 1000:
                self.stdout.write(f'Image too small for {recipe_title}, skipping')
                return None
            img = Image.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P', 'LA'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if len(img.split()) == 4 else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            if is_step_image:
                img.thumbnail((600, 400), Image.Resampling.LANCZOS)
            else:
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=85, optimize=True)
            img_io.seek(0)
            safe_title = "".join(c for c in recipe_title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:50]
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            prefix = "step_" if is_step_image else ""
            filename = f"{prefix}{safe_title}_{url_hash}.jpg"
            content_file = ContentFile(img_io.read(), name=filename)
            self.stdout.write(f'✓ Downloaded and processed {img_type}: {filename}')
            return content_file
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.WARNING(f'Network error downloading {img_type} for {recipe_title}: {e}')
            )
            return None
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error processing {img_type} for {recipe_title}: {e}')
            )
            return None

    def parse_ingredients(self, meal_data):
        """Parse ingredients from TheMealDB format"""
        ingredients = []
        for i in range(1, 21):
            ingredient_key = f'strIngredient{i}'
            measure_key = f'strMeasure{i}'
            # Use (value or '') to avoid NoneType errors
            ingredient_name = (meal_data.get(ingredient_key) or '').strip()
            measure = (meal_data.get(measure_key) or '').strip()
            if ingredient_name and ingredient_name.lower() not in ['', 'null']:
                ingredients.append({
                    'name': ingredient_name,
                    'measure': measure
                })
        return ingredients

    def parse_measure(self, measure_str):
        """Parse measure string to extract quantity and unit"""
        if not measure_str:
            return 1, 'piece'
        measure_str = measure_str.strip().lower()
        unit_mappings = {
            'cups': 'cup', 'cup': 'cup',
            'tablespoons': 'tablespoon', 'tablespoon': 'tablespoon', 'tbsp': 'tablespoon',
            'teaspoons': 'teaspoon', 'teaspoon': 'teaspoon', 'tsp': 'teaspoon',
            'pounds': 'pound', 'pound': 'pound', 'lb': 'pound', 'lbs': 'pound',
            'ounces': 'ounce', 'ounce': 'ounce', 'oz': 'ounce',
            'grams': 'gram', 'gram': 'gram', 'g': 'gram', 'kg': 'kilogram',
            'ml': 'milliliter', 'l': 'liter',
            'cloves': 'clove', 'clove': 'clove',
            'pinch': 'pinch', 'pinches': 'pinch',
            'slices': 'slice', 'slice': 'slice',
            'can': 'can', 'cans': 'can',
            'bottle': 'bottle', 'bottles': 'bottle',
            'jar': 'jar', 'jars': 'jar',
            'package': 'package', 'packages': 'package',
            'bunch': 'bunch', 'bunches': 'bunch',
            'sprig': 'sprig', 'sprigs': 'sprig',
            'dash': 'dash', 'dashes': 'dash',
        }
        parts = measure_str.split()
        quantity = 1
        unit = 'piece'
        if parts:
            try:
                if '/' in parts[0]:
                    if ' ' in parts[0]:
                        whole_and_frac = parts[0].split(' ')
                        if len(whole_and_frac) == 2:
                            whole = float(whole_and_frac[0])
                            num, den = whole_and_frac[1].split('/')
                            quantity = whole + (float(num) / float(den))
                    else:
                        num, den = parts[0].split('/')
                        quantity = float(num) / float(den)
                else:
                    quantity = float(parts[0])
                for part in parts[1:]:
                    clean_part = part.strip('.,()').lower()
                    if clean_part in unit_mappings:
                        unit = unit_mappings[clean_part]
                        break
            except ValueError:
                for part in parts:
                    clean_part = part.strip('.,()').lower()
                    if clean_part in unit_mappings:
                        unit = unit_mappings[clean_part]
                        break
        return quantity, unit

    def import_recipes(self):
        """Import recipes from TheMealDB using GPT (if enabled) for step and time analysis"""
        categories = [
            'Beef', 'Chicken', 'Dessert', 'Lamb', 'Miscellaneous',
            'Pasta', 'Pork', 'Seafood', 'Side', 'Starter',
            'Vegan', 'Vegetarian', 'Breakfast', 'Goat'
        ]
        imported_recipes = []
        recipes_per_category = max(1, self.recipes_count // len(categories))
        for category in categories:
            self.stdout.write(f'Importing recipes from category: {category}')
            meals = self.get_recipes_by_category(category)
            count = 0
            for meal in meals:
                if count >= recipes_per_category:
                    break
                meal_id = meal['idMeal']
                if Recipe.objects.filter(title=meal['strMeal']).exists():
                    self.stdout.write(f'Recipe "{meal["strMeal"]}" already exists, skipping...')
                    continue
                meal_details = self.get_recipe_details(meal_id)
                if meal_details:
                    recipe = self.create_recipe_from_meal_data_gpt(meal_details)
                    if recipe:
                        imported_recipes.append(recipe)
                        count += 1
                        step_count = recipe.steps.count()
                        self.stdout.write(f'✓ Imported: {recipe.title} ({step_count} steps)')
                time.sleep(0.8)
                if len(imported_recipes) >= self.recipes_count:
                    break
            if len(imported_recipes) >= self.recipes_count:
                break
        return imported_recipes

    def create_recipe_from_meal_data_gpt(self, meal_data):
        """Create a Recipe object with GPT-enhanced analysis"""
        try:
            with transaction.atomic():
                recipe_data = {
                    'title': meal_data['strMeal'],
                    'category': meal_data.get('strCategory', ''),
                    'instructions': meal_data.get('strInstructions', ''),
                    'area': meal_data.get('strArea', ''),
                    'ingredients': self.parse_ingredients(meal_data)
                }
                # GPT for category determination
                if self.use_gpt and (not recipe_data['category'] or recipe_data['category'] == 'Miscellaneous'):
                    smart_category = recipe_analyzer.categorize_recipe(recipe_data)
                    recipe_data['category'] = smart_category
                category, _ = Category.objects.get_or_create(
                    name=recipe_data['category'],
                    defaults={
                        'description': f'{recipe_data["category"]} dishes',
                        'color': '#6c757d'
                    }
                )

                prep_time, cook_time = recipe_analyzer.estimate_cooking_times(recipe_data)

                # TODO: Use GPT for servings and difficulty if available
                servings = 4
                difficulty = 'medium'
                recipe = Recipe.objects.create(
                    title=recipe_data['title'],
                    description=f"Delicious {recipe_data['title']} recipe from {recipe_data['area']} cuisine.",
                    instructions=recipe_data['instructions'],
                    prep_time=prep_time,
                    cook_time=cook_time,
                    servings=servings,
                    difficulty=difficulty,
                    author=self.admin_user,
                    category=category,
                    is_public=True,
                    featured=False
                )
                if meal_data.get('strMealThumb') and not self.skip_images:
                    image_file = self.download_image(meal_data['strMealThumb'], recipe.title)
                    if image_file:
                        recipe.image.save(image_file.name, image_file, save=True)
                        self.stdout.write(f'✓ Main image saved for: {recipe.title}')
                # Create recipe steps with GPT or fallback
                if recipe_data['instructions']:
                    if self.use_gpt and hasattr(recipe_analyzer, 'analyze_recipe_steps'):
                        steps_data = recipe_analyzer.analyze_recipe_steps(
                            recipe_data['instructions'],
                            recipe_data['title']
                        )
                        self.stdout.write(f'GPT parsed {len(steps_data)} steps for: {recipe.title}')
                    else:
                        steps_data = self.parse_instructions_into_steps_simple(recipe_data['instructions'])
                        self.stdout.write(f'Rule-based parsed {len(steps_data)} steps for: {recipe.title}')
                    for step_data in steps_data:
                        recipe_step = RecipeStep.objects.create(
                            recipe=recipe,
                            step_number=step_data['number'],
                            instruction=step_data['text'],
                            time_required=step_data['time_minutes']
                        )
                        # No step images
                # --- MIN CHANGE: Deduplicate RecipeIngredient for (recipe, ingredient) ---
                used_ingredient_ids = set()
                for ing_data in recipe_data['ingredients']:
                    ingredient, _ = Ingredient.objects.get_or_create(
                        name=ing_data['name'],
                        defaults={'description': f'{ing_data["name"]} ingredient'}
                    )
                    if ingredient.id in used_ingredient_ids:
                        continue  # Skip duplicate ingredient for this recipe
                    used_ingredient_ids.add(ingredient.id)
                    quantity, unit_name = self.parse_measure(ing_data['measure'])
                    unit, _ = Unit.objects.get_or_create(
                        name=unit_name,
                        defaults={'abbreviation': unit_name[:10], 'unit_type': 'count'}
                    )
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,
                        quantity=quantity,
                        unit=unit,
                        notes=ing_data['measure']
                    )
                if recipe_data['area']:
                    area_tag, _ = Tag.objects.get_or_create(
                        name=recipe_data['area'],
                        defaults={'color': '#17a2b8'}
                    )
                    recipe.tags.add(area_tag)
                if meal_data.get('strTags'):
                    tags = [tag.strip() for tag in meal_data['strTags'].split(',')]
                    for tag_name in tags:
                        if tag_name:
                            tag, _ = Tag.objects.get_or_create(
                                name=tag_name,
                                defaults={'color': '#28a745'}
                            )
                            recipe.tags.add(tag)
                return recipe
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating recipe {meal_data.get("strMeal", "Unknown")}: {e}')
            )
            return None
        
    def parse_instructions_into_steps_simple(self, instructions):
        """Improved: Keep all steps, no trimming or step count limits"""
        if not instructions:
            return []
        import re
        steps = []
        patterns = [r'\n\d+\.', r'\d+\.\s', r'STEP \d+', r'Step \d+']
        parts = []
        for pattern in patterns:
            if re.search(pattern, instructions, re.IGNORECASE):
                parts = re.split(pattern, instructions, flags=re.IGNORECASE)
                parts = [part.strip() for part in parts if part.strip()]
                if len(parts) > 1:
                    if len(parts[0]) < 50:
                        parts = parts[1:]
                    break
        if not parts:
            parts = [p.strip() for p in instructions.split('\n\n') if p.strip()]
        if not parts:
            parts = [instructions]
        for i, part in enumerate(parts):
            if len(part.strip()) == 0:
                continue
            time_estimate = 5
            part_lower = part.lower()
            if any(word in part_lower for word in ['bake', 'roast', 'cook', 'simmer']):
                time_estimate = 20
            elif any(word in part_lower for word in ['mix', 'stir', 'combine']):
                time_estimate = 3
            steps.append({
                'number': i + 1,
                'text': part.strip(),
                'time_minutes': time_estimate,
                'type': 'prep'
            })
        return steps

    def create_meal_plan_templates(self, recipes):
        """Create default meal plan templates"""
        if not recipes:
            self.stdout.write(self.style.WARNING('No recipes available for meal plan templates'))
            return
        templates_data = [
            {
                'name': 'Healthy Week',
                'description': 'A balanced week of healthy meals',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Seafood'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Beef'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Pork'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Vegan', 'dinner': 'Lamb'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Side', 'dinner': 'Pasta'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Starter', 'dinner': 'Chicken'},
                }
            },
            # ... (other templates as in your original code)
        ]
        for template_data in templates_data:
            try:
                if MealPlanTemplate.objects.filter(name=template_data['name'], user=self.admin_user).exists():
                    self.stdout.write(f'Template "{template_data["name"]}" already exists, skipping...')
                    continue
                template = MealPlanTemplate.objects.create(
                    name=template_data['name'],
                    description=template_data['description'],
                    user=self.admin_user,
                    is_public=True
                )
                for day_of_week, meals in template_data['meals'].items():
                    for meal_type, category_name in meals.items():
                        category_recipes = [r for r in recipes if r.category and r.category.name == category_name]
                        if not category_recipes:
                            category_recipes = recipes
                        if category_recipes:
                            recipe = random.choice(category_recipes)
                            MealPlanTemplateItem.objects.create(
                                template=template,
                                recipe=recipe,
                                day_of_week=day_of_week,
                                meal_type=meal_type,
                                servings=4
                            )
                self.stdout.write(f'✓ Created meal plan template: {template.name}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating template {template_data["name"]}: {e}')
                )