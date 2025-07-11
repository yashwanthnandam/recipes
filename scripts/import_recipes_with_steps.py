#!/usr/bin/env python
"""
Import recipes with detailed steps and images
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print("🍽️  Starting TheMealDB import with RECIPE STEPS and images...")
    print("📸 This will import 120+ recipes WITH step-by-step instructions and images")
    print("🌐 Make sure you have internet connection for downloading images")
    print("⏱️  This process may take 15-20 minutes due to step processing and images")
    print("👣 Each recipe will be broken down into detailed steps with time estimates")
    
    # Run the import command
    call_command(
        'import_mealdb_recipes',
        '--recipes-count=120',
        '--create-admin',
        '--admin-username=nandamyashwanth'
    )
    
    print("\n✅ Import with steps completed!")
    print("📊 Run verification: python manage.py verify_import")
    print("You now have:")
    print("1. 📄 120+ recipes with detailed steps")
    print("2. 📸 Recipe and step images")
    print("3. ⏱️  Time estimates for each step")
    print("4. 📅 10 meal plan templates")
    print("5. 🔑 Login: nandamyashwanth / admin123")