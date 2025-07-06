from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.RecipeListView.as_view(), name='list'),
    path('create/', views.RecipeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.RecipeDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.RecipeUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.RecipeDeleteView.as_view(), name='delete'),
    path('my-recipes/', views.my_recipes, name='my_recipes'),
]