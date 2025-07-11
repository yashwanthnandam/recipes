from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from apps.recipes.models import Recipe, Category, Ingredient, Unit, RecipeStep
from apps.meal_planning.models import MealPlanTemplate, MealPlanTemplateItem

class Command(BaseCommand):
    help = 'Verify the imported data from TheMealDB with detailed statistics including recipe steps'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📊 IMPORT VERIFICATION REPORT WITH STEPS'))
        self.stdout.write('=' * 60)
        
        # Count recipes
        recipe_count = Recipe.objects.count()
        recipes_with_images = Recipe.objects.exclude(image='').count()
        public_recipes = Recipe.objects.filter(is_public=True).count()
        
        self.stdout.write(f'📄 Total recipes: {recipe_count}')
        self.stdout.write(f'📸 Recipes with images: {recipes_with_images}')
        self.stdout.write(f'🌍 Public recipes: {public_recipes}')
        
        # Count recipe steps
        total_steps = RecipeStep.objects.count()
        steps_with_images = RecipeStep.objects.exclude(image='').count()
        avg_steps_per_recipe = RecipeStep.objects.values('recipe').annotate(
            step_count=Count('id')
        ).aggregate(avg_steps=Avg('step_count'))['avg_steps'] or 0
        
        self.stdout.write(f'\n👣 Recipe Steps Statistics:')
        self.stdout.write(f'  📝 Total steps: {total_steps}')
        self.stdout.write(f'  📸 Steps with images: {steps_with_images}')
        self.stdout.write(f'  📊 Average steps per recipe: {avg_steps_per_recipe:.1f}')
        
        if total_steps > 0:
            step_image_rate = (steps_with_images / total_steps) * 100
            self.stdout.write(f'  📈 Step image success rate: {step_image_rate:.1f}%')
        
        # Count by category
        self.stdout.write('\n📂 Recipes by category:')
        categories_with_counts = Category.objects.annotate(
            recipe_count=Count('recipe')
        ).order_by('-recipe_count')
        
        for category in categories_with_counts:
            if category.recipe_count > 0:
                self.stdout.write(f'  {category.icon} {category.name}: {category.recipe_count}')
        
        # Count ingredients and units
        ingredient_count = Ingredient.objects.count()
        unit_count = Unit.objects.count()
        self.stdout.write(f'\n🥕 Ingredients: {ingredient_count}')
        self.stdout.write(f'📏 Units: {unit_count}')
        
        # Count meal plan templates
        template_count = MealPlanTemplate.objects.count()
        public_templates = MealPlanTemplate.objects.filter(is_public=True).count()
        self.stdout.write(f'\n📅 Meal plan templates: {template_count}')
        self.stdout.write(f'🌍 Public templates: {public_templates}')
        
        for template in MealPlanTemplate.objects.all():
            item_count = MealPlanTemplateItem.objects.filter(template=template).count()
            self.stdout.write(f'  📋 {template.name}: {item_count} meals')
        
        # Show detailed recipe information
        self.stdout.write('\n🍽️  Sample recipes with steps:')
        sample_recipes = Recipe.objects.filter(is_public=True).prefetch_related('steps')[:5]
        for recipe in sample_recipes:
            category_name = recipe.category.name if recipe.category else "No category"
            image_status = "📸" if recipe.image else "❌"
            step_count = recipe.steps.count()
            steps_with_img = recipe.steps.exclude(image='').count()
            self.stdout.write(f'  {image_status} {recipe.title} ({category_name})')
            self.stdout.write(f'    👣 {step_count} steps, {steps_with_img} with images')
        
        # Show step time statistics
        steps_with_time = RecipeStep.objects.exclude(time_required__isnull=True)
        if steps_with_time.exists():
            avg_time = steps_with_time.aggregate(avg_time=Avg('time_required'))['avg_time']
            self.stdout.write(f'\n⏱️  Average step time: {avg_time:.1f} minutes')
        
        # Image statistics
        if recipes_with_images > 0:
            recipe_image_rate = (recipes_with_images/recipe_count)*100
            self.stdout.write(f'\n📊 Recipe image success rate: {recipe_image_rate:.1f}%')
        
        # File system check
        import os
        from django.conf import settings
        
        recipe_media_path = os.path.join(settings.MEDIA_ROOT, 'recipes')
        step_media_path = os.path.join(settings.MEDIA_ROOT, 'recipe_steps')
        
        if os.path.exists(recipe_media_path):
            recipe_files = len([f for f in os.listdir(recipe_media_path) if f.endswith('.jpg')])
            self.stdout.write(f'📁 Recipe image files on disk: {recipe_files}')
        
        if os.path.exists(step_media_path):
            step_files = len([f for f in os.listdir(step_media_path) if f.endswith('.jpg')])
            self.stdout.write(f'📁 Step image files on disk: {step_files}')
        
        self.stdout.write('\n✅ Verification completed!')