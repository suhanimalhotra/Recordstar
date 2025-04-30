from django.contrib import admin
from .models import Profile, Rating, Collection, FriendActivity, Library, CD, CollectionAccessRequest

# Register your models here.
admin.site.register(Profile)
admin.site.register(Rating)
admin.site.register(CD)
admin.site.register(Collection)
admin.site.register(FriendActivity)
admin.site.register(Library)
admin.site.register(CollectionAccessRequest)
