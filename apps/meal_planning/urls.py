from django.urls import path
from . import views

app_name = 'meal_planning'

urlpatterns = [
    # Calendar view
    path('', views.meal_calendar, name='calendar'),
    path('calendar/', views.meal_calendar, name='calendar'),
    
    # Meal Plan CRUD
    path('plans/add/', views.add_meal_plan, name='plan_create'),
    path('plans/<int:pk>/remove/', views.remove_meal_plan, name='plan_delete'),
    path('plans/generate-shopping-list/', views.generate_shopping_list, name='generate_shopping_list'),
    
    # Templates
    path('templates/', views.MealPlanTemplateListView.as_view(), name='templates'),
    path('templates/create/', views.MealPlanTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/', views.MealPlanTemplateDetailView.as_view(), name='template_detail'),
    path('templates/<int:pk>/edit/', views.MealPlanTemplateUpdateView.as_view(), name='template_edit'),
    path('templates/<int:pk>/edit-meals/', views.template_edit_meals, name='template_edit_meals'),
    path('templates/<int:pk>/delete/', views.MealPlanTemplateDeleteView.as_view(), name='template_delete'),
    path('templates/<int:template_id>/apply/', views.apply_template, name='template_apply'),
    path('templates/<int:template_id>/copy/', views.copy_template, name='template_copy'),
    path('export/pdf/', views.export_meal_plan_pdf, name='export_pdf'),
    path('analysis/export/', views.export_project_analysis_pdf, name='analysis_export'),
    
    # AJAX endpoints
    path('recipe-search/', views.recipe_search_ajax, name='recipe_search'),
]