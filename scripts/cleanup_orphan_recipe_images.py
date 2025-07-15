import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from apps.recipes.models import Recipe

MEDIA_RECIPES_DIR = os.path.join(os.path.dirname(__file__), '..', 'media', 'recipes')
MEDIA_RECIPES_DIR = os.path.abspath(MEDIA_RECIPES_DIR)

# Get all image filenames linked to Recipe objects
used_files = set()
for recipe in Recipe.objects.exclude(image=''):
    if recipe.image and hasattr(recipe.image, 'name'):
        # recipe.image.name is like "recipes/filename.jpg"
        image_name = os.path.basename(recipe.image.name)
        used_files.add(image_name)

# List all files in media/recipes/
files_in_dir = set(os.listdir(MEDIA_RECIPES_DIR))

# Find orphan files
orphans = [f for f in files_in_dir if f not in used_files]

print(f"Found {len(orphans)} orphan image(s) in media/recipes/")

for filename in orphans:
    path = os.path.join(MEDIA_RECIPES_DIR, filename)
    print(f"Deleting {filename} ...")
    os.remove(path)

print("Cleanup complete.")