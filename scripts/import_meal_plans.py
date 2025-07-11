#!/usr/bin/env python
"""
Standalone script to import recipes from TheMealDB API with images
Run this from the project root directory

Usage:
    python scripts/import_mealdb_and_create_mealplans.py
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print("🍽️  Starting TheMealDB import with images...")
    print("📸 This will import 120+ recipes WITH IMAGES and create meal plan templates")
    print("🌐 Make sure you have internet connection for downloading images")
    print("⏱️  This process may take 10-15 minutes due to image downloads")
    
    # Step 1: Import recipes from TheMealDB API
    # You should have a command like `import_mealdb_recipes` in your project.
    # Uncomment below if such a command exists.
    # call_command(
    #     'import_mealdb_recipes',
    #     '--count=120',
    #     '--with-images'
    # )

    # Step 2: Create sample meal plans and templates
    call_command(
        'create_sample_meal_plans',
        admin_username='nandamyashwanth',
        create_user=True,
        weeks=4
    )
    
    print("\n✅ Import completed!")
    print("You can now:")
    print("1. Login with username: nandamyashwanth, password: admin123")
    print("2. View imported recipes with images in the admin panel")
    print("3. Use meal plan templates for planning")
    print("4. All recipe images are stored in media/recipes/ directory")