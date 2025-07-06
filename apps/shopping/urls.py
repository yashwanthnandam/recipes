from django.urls import path
from . import views

app_name = 'shopping'

urlpatterns = [
    path('', views.ShoppingListListView.as_view(), name='lists'),
    path('<int:pk>/', views.ShoppingListDetailView.as_view(), name='detail'),
    path('create/', views.ShoppingListCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.ShoppingListUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ShoppingListDeleteView.as_view(), name='delete'),
    path('<int:list_id>/add-item/', views.add_item, name='add_item'),
    path('item/<int:item_id>/toggle/', views.toggle_item, name='toggle_item'),
    path('item/<int:item_id>/delete/', views.delete_item, name='delete_item'),
    path('<int:list_id>/share/', views.share_list, name='share_list'),
]