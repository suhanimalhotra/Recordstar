from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from users.models import Profile
from django.utils import timezone
from datetime import timedelta


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_authenticated:
            # Check if this is a new registration
            is_new_account = False
            
            # Check if we have a session flag for new registration
            if request.session.get('account_newly_created', False):
                is_new_account = True
                # Clear the flag so it only affects this login
                request.session.pop('account_newly_created', None)
                
            # If not a new account, redirect straight to dashboard
            if not is_new_account:
                print("[CustomAccountAdapter] 👋 Existing user - straight to dashboard")
                return "/dashboard/"
                
            # Otherwise, handle new accounts as before
            try:
                profile = user.profile
                if profile.image and not profile.image.name.endswith("default.jpg"):
                    print("[CustomAccountAdapter] ✅ Redirecting to dashboard")
                    return "/dashboard/"
                else:
                    print("[CustomAccountAdapter] 🖼️ Needs profile picture")
                    return "/recordstar/first_time_setup/"
            except Profile.DoesNotExist:
                print("[CustomAccountAdapter] ❌ No profile found")
                return "/recordstar/first_time_setup/"
        return super().get_login_redirect_url(request)
    
    # Override this to set a flag when a new account is created
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit)
        request.session['account_newly_created'] = True
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        request.session['social_account_newly_created'] = True
        return user

    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_authenticated:
            is_new = request.session.pop('social_account_newly_created', False)

            if is_new:
                try:
                    profile = user.profile
                    if profile.image and not profile.image.name.endswith("default.jpg"):
                        return "/dashboard/"
                    else:
                        return "/recordstar/first_time_setup/"
                except Profile.DoesNotExist:
                    return "/recordstar/first_time_setup/"

            return "/dashboard/"
        return super().get_login_redirect_url(request)
