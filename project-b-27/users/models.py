from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
def get_default_profile_image():
    return 'default.jpg'

class Profile(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('P', 'Patron'),
        ('L', 'Librarian'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_type = models.CharField(max_length=1, choices=ACCOUNT_TYPE_CHOICES, default='P')
    image = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics/')
    created_at = models.DateTimeField(auto_now_add=True)
    friends = models.ManyToManyField("self", symmetrical=True, blank=True)
    is_collection_public = models.BooleanField(default=True)
    birthday = models.DateField(null=True, blank=True)
    profile_completed = models.BooleanField(default=False)

    @property
    def is_librarian(self):
        return self.account_type == 'L'
    
    def __str__(self):
        return f"{self.user.username} ({self.get_account_type_display()})"
    
class FriendActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_activities")
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="added_by")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} added {self.friend.username}"

class CD(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('checked_out', 'Checked Out'),
        ('reserved', 'Reserved'),
    ]

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=100)
    release_year = models.IntegerField(null=True, blank=True)
    genre = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='cd_covers/', null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cds')
    date_added = models.DateTimeField(auto_now_add=True)
    unique_code = models.CharField(max_length=12, unique=True, editable=False, blank=True)
    
    # fields for lending functionality
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    checked_out_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='borrowed_cds')
    due_date = models.DateField(null=True, blank=True)

    # Rating fields
    user_rating = models.IntegerField(null=True, blank=True)
    review = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.unique_code:
            self.unique_code = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} by {self.artist}"
    
    def is_public(self):
        if not self.collections.exists():
            return True
        return self.collections.filter(is_public=True).exists()
    
    def get_visibility_label(self, user):
        if self.collections.filter(is_public=True).exists():
            return ("Public Item", "success")
        elif user.is_authenticated and (
            self.collections.filter(owner=user).exists() or
            self.collections.filter(allowed_users=user).exists()
        ):
            return ("Private Item", "warning")
        else:
            return ("Unlisted Item", "secondary")


class CDRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned'),
    ]
    
    cd = models.ForeignKey(CD, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cd_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_date = models.DateTimeField(auto_now_add=True)
    requested_days = models.IntegerField(default=14)  # default loan period
    response_date = models.DateTimeField(null=True, blank=True)
    return_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.requester.username} requests {self.cd.title}"
    
class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cd = models.ForeignKey(CD, on_delete=models.CASCADE, related_name='ratings')
    rating_value = models.IntegerField()  # e.g., 1-10 scale
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} rated {self.cd.title} ({self.rating_value})"
    
class Collection(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="collections")
    name = models.CharField(max_length=100)
    is_public = models.BooleanField(default=True)
    cover_image = models.ImageField(
        upload_to='collection_covers/',
        null=True,
        blank=True,
        default='collection_covers/default.jpg'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    cds = models.ManyToManyField(CD, blank=True, related_name="collections")
    allowed_users = models.ManyToManyField(User, blank=True, related_name="allowed_collections")

    def __str__(self):
        return f"{self.name} ({'Public' if self.is_public else 'Private'})"
    
class Library(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="library")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Library"

class CollectionAccessRequest(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='access_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.requester.username} requests access to {self.collection.name}"