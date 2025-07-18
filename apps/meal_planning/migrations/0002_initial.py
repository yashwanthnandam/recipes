# Generated by Django 4.2.7 on 2025-07-06 13:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('meal_planning', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recipes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklymealplan',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_plans', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mealplantemplateitem',
            name='recipe',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.recipe'),
        ),
        migrations.AddField(
            model_name='mealplantemplateitem',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='meal_planning.mealplantemplate'),
        ),
        migrations.AddField(
            model_name='mealplantemplate',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meal_templates', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='recipe',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meal_plans', to='recipes.recipe'),
        ),
        migrations.AddField(
            model_name='mealplan',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meal_plans', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='weeklymealplan',
            unique_together={('user', 'week_start_date')},
        ),
        migrations.AlterUniqueTogether(
            name='mealplantemplateitem',
            unique_together={('template', 'day_of_week', 'meal_type')},
        ),
        migrations.AlterUniqueTogether(
            name='mealplan',
            unique_together={('user', 'recipe', 'date', 'meal_type')},
        ),
    ]
