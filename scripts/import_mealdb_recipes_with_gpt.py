#!/usr/bin/env python
"""
Import recipes with cost-optimized GPT analysis
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print("🤖 Starting Smart GPT-Enhanced Recipe Import")
    print("💰 Cost-optimized with caching and intelligent processing")
    print("⚡ Processing in batches to minimize API calls")
    
    # Check if OpenAI API key is set
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    print(f"✅ API key configured")
    
    # Run the import with GPT enhancement
    call_command(
        'import_meal_db_recipes_with_gpt',
        '--recipes-count=50',  # Start with smaller batch
        '--create-admin',
        '--admin-username=nandamyashwanth',
        '--use-gpt',  # Enable GPT features
        '--gpt-batch-size=5',  # Process 5 at a time
        '--skip-step-images'  # Skip step images to reduce processing time
    )
    
    print("\n💰 Cost Monitoring:")
    print("Run: python scripts/monitor_gpt_costs.py")
    print("\n🎯 Features enabled:")
    print("- ✅ Intelligent step parsing")
    print("- ✅ Smart time estimation") 
    print("- ✅ Auto-categorization")
    print("- ✅ Cost optimization with caching")
    print("- ✅ Fallback to rule-based parsing")