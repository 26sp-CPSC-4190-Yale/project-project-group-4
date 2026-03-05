from django.urls import path
from . import views

urlpatterns = [
    path('api/artwork/', views.single_artwork, name='single_artwork'),
]