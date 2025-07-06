from django.urls import path
from . import views

app_name = 'meal_planning'

urlpatterns = [
    path('', views.meal_calendar, name='calendar'),
    path('add/', views.add_meal_plan, name='add_meal'),
    path('remove/<int:pk>/', views.remove_meal_plan, name='remove_meal'),
    path('generate-shopping-list/', views.generate_shopping_list, name='generate_shopping_list'),
    path('templates/', views.MealPlanTemplateListView.as_view(), name='templates'),
    path('templates/create/', views.MealPlanTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:template_id>/apply/', views.apply_template, name='apply_template'),
]