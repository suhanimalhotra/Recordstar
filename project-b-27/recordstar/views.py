from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, authenticate, login
from users.models import CD
from django.contrib import messages

# SHERRIFF: very basic index page created
from users.models import Profile


class IndexView(generic.TemplateView):
    template_name = "recordstar/upload_picture.html"
# Create your views here.

@login_required
def first_time_setup(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.image = request.FILES['profile_picture']
            profile.save()
            return redirect('first_time_setup')  # ✅ stay on the setup page

        # Handle profile info form
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        birthday = request.POST.get('birthday')

        # Only save if all fields are filled
        if first_name and last_name and username and birthday:
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            profile.birthday = birthday
            profile.profile_completed = True  # ✅ now mark profile as completed

            user.save()
            profile.save()

            login(request, user)
            return redirect('first_time_setup')  # ✅ stay on setup page after info submit too

    return render(request, "recordstar/first_time_setup.html")


@login_required
def dashboard_view(request):
    if not request.user.profile.profile_completed:
        return redirect('first_time_setup')  #force back to setup if incomplete

    return render(request, 'dashboard.html')

def anon_user_welcome(request):
    return render(request, 'recordstar/anon_user_welcome.html')

