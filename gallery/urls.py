from django.urls import path
from . import views

urlpatterns = [
    # MVP Gallery View - fetch single artwork for display
    path('api/artwork/', views.single_artwork, name='single_artwork'),
    
    # Fetch specific artwork by ID with interaction data
    path('api/artwork/<int:artwork_id>/', views.artwork_detail, name='artwork_detail'),
    
    # Fetch all artworks (with pagination support)
    path('api/artworks/', views.artwork_list, name='artwork_list'),
]