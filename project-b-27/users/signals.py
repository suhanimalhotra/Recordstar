from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import Profile
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.signals import pre_social_login
from .models import Profile, Collection, CD
from django.core.exceptions import ValidationError

@receiver(user_signed_up)
def create_profile(sender, request, user, **kwargs):
    if user.is_superuser:
        return
    # create Profile for each new user, default is patron
    account_type = request.session.pop("account_type", "P")
    
    # get_or_create returns a tuple: (object, created)
    profile, created = Profile.objects.get_or_create(user=user, defaults={'account_type': account_type})
    
    if not created:
        # Optionally update fields if needed
        profile.account_type = account_type
        profile.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(pre_social_login)
def detect_social_login(sender, request, sociallogin, **kwargs):
    # Check if this user already exists
    if sociallogin.is_existing:
        # Existing user
        pass
    else:
        # This is a new social account
        if sociallogin.user:
            # Mark the user for our adapter to detect
            sociallogin.user.socialaccount_newly_created = True

@receiver(m2m_changed, sender=Collection.cds.through)
def enforce_private_collection(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Ensure a CD in a private collection isn’t in any other collection,
    and prevent adding a CD from a private collection into a public one.
    """
    if action == 'pre_add' and not reverse:
        collection = instance
        for cd in model.objects.filter(pk__in=pk_set):
            if not collection.is_public:
                # Clear all existing collections to ensure exclusivity
                cd.collections.clear()
            else:
                # Prevent adding to public if the CD is in any private collection
                if cd.collections.filter(is_public=False).exists():
                    raise ValidationError(
                        f"Item '{cd.title}' cannot be added to public collection '{collection.name}' because it belongs to a private collection."
                    )
