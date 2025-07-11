import os
import requests
import json
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.recipes.models import Recipe, Category, Ingredient, Unit, RecipeIngredient, Tag, RecipeStep
from apps.meal_planning.models import MealPlanTemplate, MealPlanTemplateItem
import time
from PIL import Image
from io import BytesIO
import calendar
import hashlib
import re

User = get_user_model()

class Command(BaseCommand):
    help = 'Import recipes from TheMealDB API with images and recipe steps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recipes-count',
            type=int,
            default=100,
            help='Number of recipes to import (default: 100)'
        )
        parser.add_argument(
            '--admin-username',
            type=str,
            default='nandamyashwanth',
            help='Admin username to assign imported recipes (default: nandamyashwanth)'
        )
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='Create admin user if not exists'
        )
        parser.add_argument(
            '--skip-images',
            action='store_true',
            help='Skip downloading images (faster import)'
        )
        parser.add_argument(
            '--skip-step-images',
            action='store_true',
            help='Skip downloading step images but keep recipe images'
        )

    def handle(self, *args, **options):
        self.recipes_count = options['recipes_count']
        self.admin_username = options['admin_username']
        self.skip_images = options['skip_images']
        self.skip_step_images = options['skip_step_images']
        
        # Get or create admin user
        try:
            self.admin_user = User.objects.get(username=self.admin_username)
            self.stdout.write(
                self.style.SUCCESS(f'Using existing user: {self.admin_username}')
            )
        except User.DoesNotExist:
            if options['create_admin']:
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
                    self.style.ERROR(f'Admin user {self.admin_username} not found. Use --create-admin to create.')
                )
                return

        self.stdout.write('Starting TheMealDB import with images and recipe steps...')
        
        # Initialize default data
        self.create_default_units()
        self.create_default_categories()
        
        # Import recipes
        imported_recipes = self.import_recipes()
        
        # Create meal plan templates
        self.create_meal_plan_templates(imported_recipes)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {len(imported_recipes)} recipes with steps and created meal plans!')
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
            
            # Download image with headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(image_url, timeout=30, headers=headers)
            response.raise_for_status()
            
            # Check if we got actual image data
            if len(response.content) < 1000:  # Too small to be a real image
                self.stdout.write(f'Image too small for {recipe_title}, skipping')
                return None
            
            # Open and process image
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary (handles RGBA, P modes)
            if img.mode in ('RGBA', 'P', 'LA'):
                # Create white background for transparency
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if len(img.split()) == 4 else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize based on image type
            if is_step_image:
                # Smaller size for step images
                img.thumbnail((600, 400), Image.Resampling.LANCZOS)
            else:
                # Larger size for main recipe images
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            # Save to BytesIO with high quality
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=85, optimize=True)
            img_io.seek(0)
            
            # Create unique filename
            safe_title = "".join(c for c in recipe_title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:50]
            
            # Add hash to ensure uniqueness
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
        
        for i in range(1, 21):  # TheMealDB has up to 20 ingredients
            ingredient_key = f'strIngredient{i}'
            measure_key = f'strMeasure{i}'
            
            ingredient_name = meal_data.get(ingredient_key, '').strip()
            measure = meal_data.get(measure_key, '').strip()
            
            if ingredient_name and ingredient_name.lower() not in ['', 'null']:
                ingredients.append({
                    'name': ingredient_name,
                    'measure': measure
                })
        
        return ingredients

    def parse_instructions_into_steps(self, instructions):
        """Parse instruction text into individual steps"""
        if not instructions:
            return []
        
        # Clean up the instructions text
        instructions = instructions.strip()
        
        # Split by common step separators
        # Try different patterns to split instructions
        step_patterns = [
            r'\n\d+\.',  # "1.", "2.", etc. at start of line
            r'\d+\.\s',   # "1. ", "2. ", etc.
            r'STEP \d+',  # "STEP 1", "STEP 2", etc.
            r'Step \d+',  # "Step 1", "Step 2", etc.
            r'\n-\s',     # "- " at start of line
            r'\n\n',      # Double newlines
        ]
        
        steps = []
        
        # Try to split by numbered steps first
        for pattern in step_patterns[:4]:  # Try numbered patterns first
            if re.search(pattern, instructions, re.IGNORECASE):
                # Split by the pattern
                parts = re.split(pattern, instructions, flags=re.IGNORECASE)
                # Remove empty parts and clean up
                steps = [part.strip() for part in parts if part.strip()]
                if len(steps) > 1:
                    # Remove the first part if it's just intro text
                    if len(steps[0]) < 50:  # Likely just title or intro
                        steps = steps[1:]
                    break
        
        # If no numbered steps found, try other patterns
        if len(steps) <= 1:
            for pattern in step_patterns[4:]:
                if re.search(pattern, instructions):
                    parts = re.split(pattern, instructions)
                    steps = [part.strip() for part in parts if part.strip()]
                    if len(steps) > 1:
                        break
        
        # If still no steps, split by sentences as last resort
        if len(steps) <= 1:
            # Split by periods followed by capital letters (likely new sentences)
            sentences = re.split(r'\.\s+(?=[A-Z])', instructions)
            if len(sentences) > 3:  # Only if we get reasonable number of steps
                steps = [s.strip() + '.' for s in sentences if len(s.strip()) > 20]
        
        # If still no luck, create artificial steps
        if len(steps) <= 1:
            # Split by reasonable length chunks
            words = instructions.split()
            chunk_size = 30  # words per step
            steps = []
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                if chunk.strip():
                    steps.append(chunk.strip())
        
        # Clean up steps and ensure they're reasonable
        cleaned_steps = []
        for i, step in enumerate(steps):
            # Remove step numbers if present
            step = re.sub(r'^\d+\.?\s*', '', step).strip()
            step = re.sub(r'^STEP\s*\d+:?\s*', '', step, flags=re.IGNORECASE).strip()
            step = re.sub(r'^Step\s*\d+:?\s*', '', step, flags=re.IGNORECASE).strip()
            
            # Ensure step is not too short or too long
            if 10 <= len(step) <= 500:
                cleaned_steps.append(step)
        
        # If we don't have any good steps, create one from the whole instruction
        if not cleaned_steps:
            cleaned_steps = [instructions[:500] + '...' if len(instructions) > 500 else instructions]
        
        return cleaned_steps

    def estimate_step_time(self, step_text, step_number, total_steps):
        """Estimate time required for a cooking step"""
        step_text_lower = step_text.lower()
        
        # Time indicators in the text
        time_patterns = {
            r'(\d+)\s*hours?': lambda m: int(m.group(1)) * 60,
            r'(\d+)\s*minutes?': lambda m: int(m.group(1)),
            r'(\d+)\s*mins?': lambda m: int(m.group(1)),
            r'(\d+)\s*hrs?': lambda m: int(m.group(1)) * 60,
        }
        
        # Check for explicit time mentions
        for pattern, converter in time_patterns.items():
            match = re.search(pattern, step_text_lower)
            if match:
                return converter(match)
        
        # Estimate based on cooking action keywords
        if any(word in step_text_lower for word in ['bake', 'roast', 'cook', 'simmer', 'boil']):
            return 20  # Longer cooking processes
        elif any(word in step_text_lower for word in ['fry', 'saute', 'brown', 'sear']):
            return 8   # Medium cooking time
        elif any(word in step_text_lower for word in ['mix', 'stir', 'combine', 'whisk', 'beat']):
            return 3   # Quick mixing
        elif any(word in step_text_lower for word in ['chop', 'dice', 'slice', 'cut', 'prepare']):
            return 5   # Prep time
        elif any(word in step_text_lower for word in ['chill', 'cool', 'rest', 'sit']):
            return 15  # Waiting time
        else:
            # Default time based on step position
            if step_number == 1:
                return 10  # First step usually prep
            elif step_number == total_steps:
                return 5   # Last step usually finishing
            else:
                return 7   # Middle steps
    
    def get_step_images_from_youtube(self, recipe_title):
        """Generate placeholder step images or try to find related images"""
        # For now, we'll use the main recipe image for some steps
        # In a real implementation, you might want to:
        # 1. Search for cooking videos on YouTube
        # 2. Extract frames from cooking videos
        # 3. Use AI to generate step images
        # 4. Use stock photo APIs
        
        # For this demo, we'll return None and let some steps have no images
        return None

    def parse_measure(self, measure_str):
        """Parse measure string to extract quantity and unit"""
        if not measure_str:
            return 1, 'piece'
        
        measure_str = measure_str.strip().lower()
        
        # Common unit mappings
        unit_mappings = {
            'cups': 'cup',
            'cup': 'cup',
            'tablespoons': 'tablespoon',
            'tablespoon': 'tablespoon',
            'tbsp': 'tablespoon',
            'teaspoons': 'teaspoon',
            'teaspoon': 'teaspoon',
            'tsp': 'teaspoon',
            'pounds': 'pound',
            'pound': 'pound',
            'lb': 'pound',
            'lbs': 'pound',
            'ounces': 'ounce',
            'ounce': 'ounce',
            'oz': 'ounce',
            'grams': 'gram',
            'gram': 'gram',
            'g': 'gram',
            'kg': 'kilogram',
            'ml': 'milliliter',
            'l': 'liter',
            'cloves': 'clove',
            'clove': 'clove',
            'pinch': 'pinch',
            'pinches': 'pinch',
            'slices': 'slice',
            'slice': 'slice',
            'can': 'can',
            'cans': 'can',
            'bottle': 'bottle',
            'bottles': 'bottle',
            'jar': 'jar',
            'jars': 'jar',
            'package': 'package',
            'packages': 'package',
            'bunch': 'bunch',
            'bunches': 'bunch',
            'sprig': 'sprig',
            'sprigs': 'sprig',
            'dash': 'dash',
            'dashes': 'dash',
        }
        
        # Try to extract quantity and unit
        parts = measure_str.split()
        quantity = 1
        unit = 'piece'
        
        if parts:
            # Try to parse first part as quantity
            try:
                if '/' in parts[0]:
                    # Handle fractions like 1/2
                    if ' ' in parts[0]:
                        # Handle mixed numbers like "1 1/2"
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
                
                # Look for unit in remaining parts
                for part in parts[1:]:
                    clean_part = part.strip('.,()').lower()
                    if clean_part in unit_mappings:
                        unit = unit_mappings[clean_part]
                        break
                        
            except ValueError:
                # If first part isn't a number, look for unit in all parts
                for part in parts:
                    clean_part = part.strip('.,()').lower()
                    if clean_part in unit_mappings:
                        unit = unit_mappings[clean_part]
                        break
        
        return quantity, unit

    # ...[imports and previous code]...
# ...[imports and previous code]...

    def create_recipe_from_meal_data(self, meal_data):
        """Create a Recipe object from TheMealDB data"""
        try:
            with transaction.atomic():
                # Get or create category
                category_name = meal_data.get('strCategory', 'Miscellaneous')
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={
                        'description': f'{category_name} dishes',
                        'color': '#6c757d'
                    }
                )
                
                # Create recipe
                recipe = Recipe.objects.create(
                    title=meal_data['strMeal'],
                    description=f"Delicious {meal_data['strMeal']} recipe from {meal_data.get('strArea', 'International')} cuisine.",
                    instructions=meal_data.get('strInstructions', ''),
                    prep_time=15,  # Default prep time
                    cook_time=30,  # Default cook time
                    servings=4,    # Default servings
                    difficulty='medium',
                    author=self.admin_user,
                    category=category,
                    is_public=True,
                    featured=False
                )
                
                # Download and set main recipe image
                if meal_data.get('strMealThumb') and not self.skip_images:
                    image_file = self.download_image(meal_data['strMealThumb'], recipe.title, is_step_image=False)
                    if image_file:
                        recipe.image.save(image_file.name, image_file, save=True)
                        self.stdout.write(f'✓ Main image saved for: {recipe.title}')
                    else:
                        self.stdout.write(f'⚠ No main image saved for: {recipe.title}')
                
                # Create recipe steps from instructions
                if meal_data.get('strInstructions'):
                    steps = self.parse_instructions_into_steps(meal_data['strInstructions'])
                    self.stdout.write(f'Creating {len(steps)} steps for: {recipe.title}')
                    
                    for i, step_text in enumerate(steps, 1):
                        # Estimate time for this step
                        estimated_time = self.estimate_step_time(step_text, i, len(steps))
                        
                        # Create the recipe step
                        recipe_step = RecipeStep.objects.create(
                            recipe=recipe,
                            step_number=i,
                            instruction=step_text,
                            time_required=estimated_time
                        )
                        # REMOVED: No step images created or attached

                # Create ingredients
                ingredients_data = self.parse_ingredients(meal_data)
                for ing_data in ingredients_data:
                    ingredient, _ = Ingredient.objects.get_or_create(
                        name=ing_data['name'],
                        defaults={'description': f'{ing_data["name"]} ingredient'}
                    )
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
                # Add tags
                if meal_data.get('strArea'):
                    area_tag, _ = Tag.objects.get_or_create(
                        name=meal_data['strArea'],
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

# ...[rest of code unchanged]...


    def import_recipes(self):
        """Import recipes from TheMealDB"""
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
                
                # Check if recipe already exists
                if Recipe.objects.filter(title=meal['strMeal']).exists():
                    self.stdout.write(f'Recipe "{meal["strMeal"]}" already exists, skipping...')
                    continue
                
                # Get detailed recipe data
                meal_details = self.get_recipe_details(meal_id)
                if meal_details:
                    recipe = self.create_recipe_from_meal_data(meal_details)
                    if recipe:
                        imported_recipes.append(recipe)
                        count += 1
                        step_count = recipe.steps.count()
                        self.stdout.write(f'✓ Imported: {recipe.title} ({step_count} steps)')
                
                # Be nice to the API
                time.sleep(0.8)  # Slightly longer delay due to step images
                
                if len(imported_recipes) >= self.recipes_count:
                    break
            
            if len(imported_recipes) >= self.recipes_count:
                break
        
        return imported_recipes

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
                    0: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Seafood'},  # Monday
                    1: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Beef'},  # Tuesday
                    2: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},   # Wednesday
                    3: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Pork'},    # Thursday
                    4: {'breakfast': 'Breakfast', 'lunch': 'Vegan', 'dinner': 'Lamb'},      # Friday
                    5: {'breakfast': 'Breakfast', 'lunch': 'Side', 'dinner': 'Pasta'},      # Saturday
                    6: {'breakfast': 'Breakfast', 'lunch': 'Starter', 'dinner': 'Chicken'}, # Sunday
                }
            },
            {
                'name': 'Vegetarian Delight',
                'description': 'Plant-based meals for the week',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Vegan'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Vegan', 'dinner': 'Vegetarian'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Vegetarian'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Side', 'dinner': 'Vegan'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Pasta'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Vegan', 'dinner': 'Vegetarian'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Vegan'},
                }
            },
            {
                'name': 'Meat Lovers',
                'description': 'Hearty meat dishes throughout the week',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Chicken'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Lamb'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Beef'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Pork'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Chicken'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Lamb'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Beef'},
                }
            },
            {
                'name': 'Seafood Week',
                'description': 'Fresh seafood meals',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Seafood'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Seafood'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Pasta'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Seafood'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Chicken'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Seafood'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Beef'},
                }
            },
            {
                'name': 'Quick & Easy',
                'description': 'Simple meals for busy weeks',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Chicken'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Vegetarian'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Chicken'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Vegetarian'},
                }
            },
            {
                'name': 'Family Favorites',
                'description': 'Kid-friendly meals the whole family will love',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Beef'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Chicken'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Dessert', 'dinner': 'Beef'},
                }
            },
            {
                'name': 'International Cuisine',
                'description': 'Explore flavors from around the world',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Beef'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Lamb'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Chicken'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Seafood'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Pork'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Vegetarian'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Miscellaneous'},
                }
            },
            {
                'name': 'Low Carb Week',
                'description': 'Reduced carbohydrate meals',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Seafood'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Chicken'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Beef'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Lamb'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Seafood'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Chicken'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Pork'},
                }
            },
            {
                'name': 'Comfort Food',
                'description': 'Hearty, comforting meals',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Pasta'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Pork', 'dinner': 'Beef'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Pasta', 'dinner': 'Chicken'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Beef', 'dinner': 'Pork'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Pasta'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Beef'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Dessert', 'dinner': 'Chicken'},
                }
            },
            {
                'name': 'Mediterranean Style',
                'description': 'Fresh Mediterranean-inspired meals',
                'meals': {
                    0: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Vegetarian'},
                    1: {'breakfast': 'Breakfast', 'lunch': 'Chicken', 'dinner': 'Seafood'},
                    2: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Lamb'},
                    3: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Chicken'},
                    4: {'breakfast': 'Breakfast', 'lunch': 'Lamb', 'dinner': 'Seafood'},
                    5: {'breakfast': 'Breakfast', 'lunch': 'Vegetarian', 'dinner': 'Chicken'},
                    6: {'breakfast': 'Breakfast', 'lunch': 'Seafood', 'dinner': 'Vegetarian'},
                }
            },
        ]
        
        for template_data in templates_data:
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
                        # Get a random recipe from the category
                        category_recipes = [r for r in recipes if r.category and r.category.name == category_name]
                        if not category_recipes:
                            # Fallback to any recipe
                            category_recipes = recipes
                        
                        if category_recipes:
                            import random
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