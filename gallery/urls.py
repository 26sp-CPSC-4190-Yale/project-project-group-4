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

    # Get current user's liked artworks (requires auth)
    path('api/liked/', views.liked_artworks, name='liked_artworks'),

    # Taste profile (requires auth)
    path('api/taste/me/', views.my_taste, name='my_taste'),

    # Matches & messaging
    path('api/matches/', views.match_list, name='match_list'),
    path('api/matches/<int:user_id>/action/', views.match_action, name='match_action'),
    path('api/matches/<int:user_id>/facets/', views.match_facets, name='match_facets'),
    path('api/matches/<int:user_id>/', views.unmatch, name='unmatch'),
    path('api/messages/<int:user_id>/', views.conversation, name='conversation'),
    path('api/notifications/', views.notifications, name='notifications'),

    # Get current user's interaction stats (requires auth)
    path('api/profile/stats/', views.profile_stats, name='profile_stats'),
]