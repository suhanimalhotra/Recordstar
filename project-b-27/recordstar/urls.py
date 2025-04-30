from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import dashboard_view
from .views import anon_user_welcome


urlpatterns = [
    # Example URL pattern:
    # path('example/', views.example_view, name='example'),
    path("", views.IndexView.as_view(), name="index"),
    path('dashboard/', dashboard_view, name='dashboard'),
    path("first_time_setup/", views.first_time_setup, name='first_time_setup'),
    path('anon-user/', anon_user_welcome, name='anon_user_welcome'),
    path("", include("users.urls")),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)