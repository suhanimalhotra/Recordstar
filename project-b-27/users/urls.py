from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import dashboard_view
from .views import (
    profile_view, settings_view, dashboard_view
)

urlpatterns = [
    path("", views.index_view, name="index"),
    path("logout", views.logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("cd/<int:cd_id>/", views.public_item_view, name="public_item"),
    path('add-to-collection/<int:collection_id>/<int:cd_id>/', views.add_to_collection, name='add_to_collection'),
    path('rate-cd/<int:cd_id>/', views.rate_cd_public, name='rate_cd'),
    path("recent-activity/", views.recent_activity_view, name="recent_activity"),
    path("ratings/", views.ratings_view, name="ratings"),
    path('ratings/delete/<int:rating_id>/', views.delete_rating, name='delete_rating'),
    path("profile/", profile_view, name="profile"),
    path("settings/", settings_view, name="settings"),
    path("upgrade_user/<int:user_id>/", views.upgrade_user_to_librarian, name="upgrade_user"),
    path('add-friend/<int:user_id>/', views.add_friend, name='add_friend'),
    path('remove-friend/<int:user_id>/', views.remove_friend, name='remove_friend'),
    path('friends/', views.friends_view, name='friends'),
    path('librarians/', views.librarians_view, name='librarians'),
    path("collection/", views.my_collections_view, name="collection"),
    path("collection/add/", views.add_collection_view, name="add_collection"),
    path("collection/<int:collection_id>/", views.collection_detail_view, name="collection_detail"),
    path("collection/<int:collection_id>/remove/<int:cd_id>/", views.remove_cd_from_collection, name="remove_cd_from_collection"),
    path("collection/<int:collection_id>/delete/", views.delete_collection_view, name="delete_collection"),
    path('collection/<int:collection_id>/edit/', views.edit_collection, name='edit_collection'),
    path("collection/<int:collection_id>/toggle-privacy/", views.toggle_collection_privacy, name="toggle_collection_privacy"),
    path('library/', views.library_view, name='library'),
    path('library/add/', views.add_cd_to_library, name='add_cd_to_library'),
    path('library/edit/<int:cd_id>/', views.edit_cd, name='edit_cd'),
    path('library/delete/<int:cd_id>/', views.delete_cd, name='delete_cd'),
    path('cds/<int:cd_id>/add-to-collection/', views.add_cd_to_collection, name='add_cd_to_collection'),
    path('cds/<int:cd_id>/create-collection/', views.create_collection_with_cd, name='create_collection_with_cd'),
    path('profile/delete-picture/', views.delete_profile_picture, name='delete_profile_picture'),
    path('dashboard/search/', views.search_results, name='search_results'),
    path('request-cd/<int:cd_id>/', views.request_cd, name='request_cd'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('respond-to-request/<int:request_id>/', views.respond_to_request, name='respond_to_request'),
    path('return-cd/<int:request_id>/', views.return_cd, name='return_cd'),
    path('edit-profile-info/', views.edit_profile_info, name='edit_profile_info'),
    path("anon-user/", views.anon_user_view, name="anon_user"),
    path('collection/<int:collection_id>/request-access/', views.request_access_to_collection, name='request_access_to_collection'),
    path('collection-access-request/<int:request_id>/respond/', views.respond_to_collection_access_request, name='respond_to_collection_access_request'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)