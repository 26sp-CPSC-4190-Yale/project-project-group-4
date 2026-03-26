from django.urls import path
from . import views

urlpatterns = [
    # Auth endpoints
    path('api/auth/register/', views.register, name='register'),
    path('api/auth/login/', views.login, name='login'),
    path('api/auth/logout/', views.logout, name='logout'),

    # MVP Gallery View - fetch single artwork for display
    path('api/artwork/', views.single_artwork, name='single_artwork'),

    # Fetch specific artwork by ID with interaction data
    path('api/artwork/<int:artwork_id>/', views.artwork_detail, name='artwork_detail'),

    # Fetch all artworks (with pagination support)
    path('api/artworks/', views.artwork_list, name='artwork_list'),

    # Record a like/pass interaction (requires auth)
    path('api/interactions/', views.record_interaction, name='record_interaction'),
]