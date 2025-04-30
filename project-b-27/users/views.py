from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.models import User
from allauth.socialaccount.providers.google.views import oauth2_login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from .forms import RatingForm
from .models import Collection, Library, CD, Rating, FriendActivity, Profile, CDRequest, CollectionAccessRequest
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.core.exceptions import ValidationError

def index_view(request):
    return render(request, "users/dashboard.html")

def logout_view(request):
    logout(request)
    return redirect("account_login")

def google_login(request):
    if request.method == 'POST':
        account_type = request.POST.get('account_type', 'P')
        request.session['account_type'] = account_type
    return oauth2_login(request)

def dashboard_view(request):
    user = request.user
    is_authenticated = user.is_authenticated
    is_librarian = user.is_authenticated and user.profile.is_librarian

    # Collections
    if is_authenticated:
        # Patrons and librarians see all collection titles (public & private)
        collections = Collection.objects.all()
    else:
        collections = Collection.objects.filter(is_public=True)

    # Unlisted + Public CDs (viewable by everyone)
    public_cds = CD.objects.filter(
        Q(collections__isnull=True) |
        Q(collections__is_public=True)
    ).distinct()

    # Private CDs (only for librarians)
    private_cds = CD.objects.none()
    if is_librarian:
        private_cds = CD.objects.filter(
            collections__is_public=False
        ).distinct()

    return render(request, "users/dashboard.html", {
        "collections": collections,
        "public_cds": public_cds,
        "private_cds": private_cds,
    })

@login_required
def recent_activity_view(request):
    recent_friends = FriendActivity.objects.filter(user=request.user).order_by('-timestamp')[:5]
    recent_collections = Collection.objects.filter(owner=request.user).order_by('-created_at')[:5]
    recent_ratings = Rating.objects.filter(user=request.user).order_by('-created_at')[:5]

    return render(request, "users/recent_activity.html", {
        "recent_friends": recent_friends,
        "recent_collections": recent_collections,
        "recent_ratings": recent_ratings,
    })

@login_required
def ratings_view(request):
    ratings = Rating.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        form = RatingForm(request.POST, user=request.user)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.user = request.user
            rating.save()
            return redirect('ratings')
    else:
        form = RatingForm(user=request.user)

    context = {
        'ratings': ratings,
        'form': form,
    }
    return render(request, 'users/ratings.html', context)


@login_required
def profile_view(request):
    if request.method == 'POST' and 'profile_picture' in request.FILES:
        profile = request.user.profile
        profile.image = request.FILES['profile_picture']
        profile.save()
        messages.success(request, "Profile picture updated.")
        return redirect('profile')
    
    return render(request, "users/profile.html")

@login_required
def edit_profile_info(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')

        if username and email:
            request.user.username = username
            request.user.email = email
            request.user.save()
            messages.success(request, "Profile updated successfully.")
        else:
            messages.error(request, "Username and email are required.")

    return redirect('profile')

@login_required
def settings_view(request):
    return render(request, "users/settings.html")

@login_required
def upgrade_user_to_librarian(request, user_id):
    if request.user.profile.account_type != 'L':
        return HttpResponseForbidden("Only librarians can upgrade user accounts.")
    
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user.profile.account_type != 'P':
        return HttpResponse("Target user is either already a librarian or not eligible for upgrade.", status=400)
    
    if request.method == 'POST':
        target_user.profile.account_type = 'L'
        target_user.profile.save()
        # Add success message and redirect
        messages.success(request, f"Success! Upgraded {target_user.username} to a Librarian!")
        return redirect('librarians')
    else:
        return render(request, 'users/confirm_upgrade.html', {'target_user': target_user})


@login_required
def delete_record_view(request, record_id):
    record = get_object_or_404(CD, id=record_id, user=request.user)
    if request.method == 'POST':
        record.delete()
        return redirect("collection")
    else:
        return redirect("collection")
    
@login_required
def add_friend(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    request.user.profile.friends.add(target_user.profile)
    #log recent friend activity
    FriendActivity.objects.create(user=request.user, friend=target_user)
    return redirect('friends')

@login_required
def remove_friend(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    request.user.profile.friends.remove(target_user.profile)
    return redirect('friends')

@login_required
def friends_view(request):
    all_users = User.objects.exclude(id=request.user.id).exclude(is_superuser=True)
    friends = request.user.profile.friends.all()
    return render(request, "users/friends.html", {
        "friends": friends,
        "all_users": all_users,
    })

@login_required
def librarians_view(request):
    librarians = User.objects.filter(profile__account_type='L')
    context = {
        "librarians": librarians,
    }
    if request.user.profile.is_librarian:
        patrons = User.objects.filter(profile__account_type='P')
        context["patrons"] = patrons
    
    return render(request, "users/librarians_list.html", context)

@login_required
def my_collections_view(request):
    own_collections = Collection.objects.filter(owner=request.user)
    
    other_collections = None
    
    if request.user.profile.is_librarian:
        other_collections = Collection.objects.exclude(owner=request.user)
    
    has_pending_requests = any(
        req.status == "pending"
        for col in own_collections
        for req in col.access_requests.all()
    )
    return render(request, "users/collection.html", {
        "own_collections": own_collections,
        "other_collections": other_collections,
        "is_librarian": request.user.profile.is_librarian,
    })

@login_required
def add_collection_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            is_public = True if request.user.profile.account_type == 'P' else request.POST.get("is_public") == "on"
            Collection.objects.create(owner=request.user, name=name, is_public=is_public)
            col = Collection.objects.get(
                owner=request.user,
                name=name,
                is_public=is_public
            )
            if 'cover_image' in request.FILES:
                col.cover_image = request.FILES['cover_image']
                
            col.save()
            return redirect("collection")
    return render(request, "users/add_collection.html")

@login_required
def collection_detail_view(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    allowed_users = collection.allowed_users.all()
    has_requested = CollectionAccessRequest.objects.filter(
                        collection=collection,
                        requester=request.user,
                        status='pending'
                    ).exists()

    has_access = (collection.is_public or 
                 request.user == collection.owner or 
                 request.user.profile.is_librarian or 
                 request.user in allowed_users)

    if not has_access:
        return render(request, "users/collection_detail_limited.html", {
            "collection": collection, 
            "has_requested": has_requested
        })

    if request.user.profile.is_librarian:
        available_cds = CD.objects.exclude(id__in=collection.cds.values_list('id', flat=True))
    else:
        available_cds = CD.objects.filter(owner=request.user).exclude(id__in=collection.cds.values_list('id', flat=True))

    if request.method == "POST":
        cd_id = request.POST.get("cd_id")
        if cd_id:
            cd = get_object_or_404(CD, id=cd_id)
            try:
                if not collection.is_public:
                    cd.collections.clear()
                collection.cds.add(cd)
                messages.success(
                    request,
                    f"Added '{cd.title}' to collection '{collection.name}'."
                )
                return redirect("collection_detail", collection_id=collection.id)
            except ValidationError:
                messages.error(
                    request,
                    "That item is private and cannot be added to a public collection."
                )
                return redirect("collection")

    query = request.GET.get("q", "").strip()
    cds = collection.cds.all()
    if query:
        cds = cds.filter(
            Q(title__icontains=query) |
            Q(artist__icontains=query) |
            Q(unique_code__icontains=query) |
            Q(genre__icontains=query) |
            Q(release_year__icontains=query)
        )

    cd_with_location = [(cd, cd.get_visibility_label(request.user)) for cd in cds]
    
    all_librarians = User.objects.filter(profile__account_type='L')

    return render(request, "users/collection_detail.html", {
        "collection": collection,
        "has_requested": has_requested,
        "available_cds": available_cds,
        "is_librarian": request.user.profile.is_librarian,
        "cds": cds,
        "cd_with_location": cd_with_location,
        "query": query,
        "all_librarians": all_librarians,
    })

@login_required
def remove_cd_from_collection(request, collection_id, cd_id):
    # allow librarians to remove CDs from any collection
    if request.user.profile.is_librarian:
        collection = get_object_or_404(Collection, id=collection_id)
    else:
        collection = get_object_or_404(Collection, id=collection_id, owner=request.user)
    
    cd = get_object_or_404(CD, id=cd_id)
    if request.method == "POST":
        collection.cds.remove(cd)
    return redirect("collection_detail", collection_id=collection.id)

@login_required
def delete_collection_view(request, collection_id):
    # allow librarians to delete any collection
    if request.user.profile.is_librarian:
        collection = get_object_or_404(Collection, id=collection_id)
    else:
        collection = get_object_or_404(Collection, id=collection_id, owner=request.user)

    if request.method == "POST":
        collection.delete()
        return redirect("collection")

    return render(request, "users/confirm_delete.html", {"collection": collection})

@login_required
def edit_collection(request, collection_id):
    if request.user.profile.is_librarian:
        collection = get_object_or_404(Collection, id=collection_id)
    else:
        collection = get_object_or_404(Collection, id=collection_id, owner=request.user)

    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            collection.name = name
            # Only librarians can change is_public
            if request.user.profile.is_librarian:
                collection.is_public = request.POST.get("is_public") == "on"
            if 'cover_image' in request.FILES:
                collection.cover_image = request.FILES['cover_image']
                
            collection.save()
            return redirect("collection_detail", collection_id=collection.id)

    return redirect("collection_detail", collection_id=collection.id)


@login_required
def toggle_collection_privacy(request, collection_id):
    # allow librarians to toggle privacy for any collection
    if request.user.profile.is_librarian:
        collection = get_object_or_404(Collection, id=collection_id)
    else:
        collection = get_object_or_404(Collection, id=collection_id, owner=request.user)

    if request.method == "POST":
        collection.is_public = not collection.is_public
        collection.save()
    return redirect("collection_detail", collection_id=collection.id)

# LIBRARY VIEWS

@login_required
def library_view(request):
    user = request.user
    is_librarian = user.profile.is_librarian

    # Get all relevant CDs
    if is_librarian:
        cds = CD.objects.all()
    else:
        cds = CD.objects.filter(
            Q(collections__isnull=True) |
            Q(collections__is_public=True) |
            Q(collections__allowed_users=user)
        ).distinct()

    cd_info = []
    for cd in cds:
        if is_librarian:
            collection = cd.collections.first()
            is_owned = cd.owner == user
        else:
            # patrons only add to their own collections
            collection = cd.collections.filter(owner=user).first()
            is_owned = cd.owner == user

        location_data = cd.get_visibility_label(user)
        cd_info.append({
            'cd': cd,
            'collection': collection,
            'is_owned': is_owned,
            'location_data': location_data,
        })

    user_collections = Collection.objects.filter(owner=user)

    # Handle CD creation by librarians only
    if request.method == "POST" and is_librarian:
        title = request.POST.get("title")
        artist = request.POST.get("artist")
        genre = request.POST.get("genre")
        release_year = request.POST.get("release_year")
        description = request.POST.get("description")

        if 'cover_image' not in request.FILES:
            return render(request, "users/library.html", {
                "cd_info": cd_info,
                "error": "Cover image is required",
                "is_librarian": is_librarian,
                "user_collections": user_collections,
                "form_data": {
                    "title": title,
                    "artist": artist,
                    "genre": genre,
                    "release_year": release_year,
                    "description": description,
                }
            })

        if title and artist:
            cd = CD.objects.create(
                title=title,
                artist=artist,
                genre=genre,
                release_year=release_year or None,
                description=description or "",
                owner=user,
                cover_image=request.FILES['cover_image'],
            )
            return redirect("library")

    return render(request, "users/library.html", {
        "cd_info": cd_info,
        "is_librarian": is_librarian,
        "user_collections": user_collections,
    })


@login_required
def add_cd_to_library(request):
    if request.method == "POST":
        title = request.POST.get("title")
        artist = request.POST.get("artist")
        genre = request.POST.get("genre")
        release_year = request.POST.get("release_year")

        if title and artist:
            cd = CD.objects.create(
                title=title,
                artist=artist,
                genre=genre,
                release_year=release_year or None,
                owner=request.user,
            )
            return redirect("library")
    
    return render(request, "users/add_cd.html")

@login_required
def delete_cd(request, cd_id):
    profile = request.user.profile
    if not profile.is_librarian:
        return redirect('library')
    cd = get_object_or_404(CD, id=cd_id, owner=request.user)
    if request.method == "POST":
        cd.delete()
    return redirect("library")

@login_required
def edit_cd(request, cd_id):
    # Only librarians get in
    if not request.user.profile.is_librarian:
        return redirect('library')

    # Librarians can edit any CD
    cd = get_object_or_404(CD, id=cd_id)

    if request.method == "POST":
        title = request.POST.get("title")
        artist = request.POST.get("artist")
        genre = request.POST.get("genre")
        release_year = request.POST.get("release_year")
        description = request.POST.get("description")

        if not cd.cover_image and 'cover_image' not in request.FILES:
            return render(request, "users/edit_cd.html", {
                "cd": cd,
                "error": "Cover image is required",
                "form_data": {
                    "title": title,
                    "artist": artist,
                    "genre": genre,
                    "release_year": release_year,
                    "description": description,
                }
            })

        cd.title = title
        cd.artist = artist
        cd.genre = genre
        cd.release_year = release_year or None
        cd.description = description

        if 'cover_image' in request.FILES:
            cd.cover_image = request.FILES['cover_image']
        cd.save()
        return redirect("library")

    return render(request, "users/edit_cd.html", {"cd": cd})


# had to take out the login required so anon users can see it 
def public_item_view(request, cd_id):
    cd = get_object_or_404(CD, id=cd_id)
    location_data = cd.get_visibility_label(request.user)

    #restrict unlisted items for anonymous users
    if location_data[0] == "Unlisted Item" and not request.user.is_authenticated:
        return HttpResponseForbidden("You must be logged in to view this item.")

    user_rating = None
    user_collections = None
    is_owner = False
    is_librarian = False
    can_add_to_collection = False
    has_pending_request = False

    ratings = cd.ratings.all()
    avg_rating = round(sum(r.rating_value for r in ratings) / ratings.count(), 1) if ratings.exists() else 0

    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(user=request.user, cd=cd)
        except Rating.DoesNotExist:
            pass

        user_collections = Collection.objects.filter(owner=request.user)
        is_owner = cd.owner == request.user
        is_librarian = request.user.profile.is_librarian
        can_add_to_collection = is_librarian or is_owner or (cd.is_public() and request.user.profile.account_type == 'P')

        has_pending_request = CDRequest.objects.filter(
            cd=cd,
            requester=request.user,
            status='pending'
        ).exists()

    is_public = cd.is_public()

    return render(request, "users/public_item.html", {
        "cd": cd,
        "user_rating": user_rating,
        "user_collections": user_collections,
        "is_owner": is_owner,
        "is_librarian": is_librarian,
        "can_add_to_collection": can_add_to_collection,
        "avg_rating": avg_rating,
        "has_pending_request": has_pending_request,
        "is_public": is_public,
        "location_data": location_data,
    })

@login_required
def add_to_collection(request, collection_id, cd_id):
    collection = get_object_or_404(Collection, id=collection_id, owner=request.user)
    cd = get_object_or_404(CD, id=cd_id)
    

    
    if request.method == "POST":
        collection.cds.add(cd)
        messages.success(request, f"Added '{cd.title}' to collection '{collection.name}'.")
    
    return redirect('public_item', cd_id=cd_id)

@login_required
def rate_cd_public(request, cd_id):
    cd = get_object_or_404(CD, id=cd_id)
    
    if request.method == 'POST':
        form_data = {
            'rating_value': request.POST.get('rating_value'),
            'review': request.POST.get('review')
        }
        
        # check for existing rating by this user
        try:
            rating = Rating.objects.get(user=request.user, cd=cd)
            rating.rating_value = form_data['rating_value']
            rating.review = form_data['review']
            rating.save()
            messages.success(request, 'Your rating has been updated.')
        except Rating.DoesNotExist:
            Rating.objects.create(
                user=request.user,
                cd=cd,
                rating_value=form_data['rating_value'],
                review=form_data['review']
            )
            messages.success(request, 'Your rating has been submitted.')
        
    return redirect('public_item', cd_id=cd.id)

@login_required
def delete_rating(request, rating_id):
    rating = get_object_or_404(Rating, id=rating_id, user=request.user)
    
    if request.method == 'POST' or request.method == 'GET':
        cd_id = rating.cd.id
        rating.delete()
        
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
            
        messages.success(request, 'Rating deleted successfully.')
        return redirect('ratings')
        
    return redirect('ratings')

@login_required
def add_cd_to_collection(request, collection_id, cd_id):
    collection = get_object_or_404(Collection, id=collection_id)
    cd = get_object_or_404(CD, id=cd_id)
    if request.method == "POST":
        try:
            if not collection.is_public:
                cd.collections.clear()
            collection.cds.add(cd)
            messages.success(request, f"Added '{cd.title}' to collection '{collection.name}'.")
            return redirect("collection_detail", collection_id=collection.id)
        except ValidationError:
            messages.error(
                request,
                "That item is private and cannot be added to a public collection."
            )
            return redirect("collection")
    return redirect("collection_detail", collection_id=collection.id)

@login_required
def create_collection_with_cd(request, cd_id):
    cd = get_object_or_404(CD, id=cd_id)

    # patrons can only add their own CDs
    if request.user.profile.account_type != 'L' and cd.owner != request.user:
        return HttpResponseForbidden("Patrons can only create collections with their own CDs.")

    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            is_public = True if request.user.profile.account_type == 'P' else request.POST.get("is_public") == "on"
            collection = Collection.objects.create(owner=request.user, name=name, is_public=is_public)
            collection.cds.add(cd)
            messages.success(request, f"Created collection '{collection.name}' and added '{cd.title}'.")
    
    return redirect("library")

@login_required
def delete_profile_picture(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.image = 'profile_pics/default.jpg'
        profile.save()
        messages.success(request, "Profile picture reset to default.")
    return redirect('profile')  # or whatever your profile view name is

def search_results(request):
    query = request.GET.get('q', '').strip()
    user = request.user

    cd_results = []
    collection_results = []

    if query:
        base = Collection.objects.filter(name__icontains=query)
        if user.is_authenticated:
            cd_results = CD.objects.filter(
                Q(title__icontains=query) |
                Q(artist__icontains=query) |
                Q(unique_code__icontains=query) |
                Q(genre__icontains=query) |
                Q(release_year__icontains=query)
            ).filter(
                Q(collections__isnull=True) |
                Q(collections__is_public=True) |
                Q(owner=user)
            ).distinct()

            collection_results = base.filter(
                Q(is_public=True) |
                Q(owner=user) | Q(is_public=False)
            ).distinct()

        else:  # anonymous user
            cd_results = CD.objects.filter(
                (
                    Q(collections__isnull=True) |
                    Q(collections__is_public=True)
                ) & (
                    Q(title__icontains=query) |
                    Q(artist__icontains=query) |
                    Q(unique_code__icontains=query) |
                    Q(genre__icontains=query) |
                    Q(release_year__icontains=query)
                )
            ).distinct()

            collection_results = base.filter(is_public=True).distinct()

    return render(request, 'users/search_results.html', {
        'query': query,
        'cd_results': cd_results,
        'collection_results': collection_results,
    })
# lending views

@login_required
def request_cd(request, cd_id):
    cd = get_object_or_404(CD, id=cd_id)
    
    # Check if CD is available and public
    if cd.status != 'available' or not cd.is_public():
        messages.error(request, "This CD is not available for borrowing.")
        return redirect('public_item', cd_id=cd.id)
    
    # Check if user already has a pending request for this CD
    if CDRequest.objects.filter(cd=cd, requester=request.user, status='pending').exists():
        messages.info(request, "You already have a pending request for this CD.")
        return redirect('public_item', cd_id=cd.id)
    
    if request.method == 'POST':
        requested_days = int(request.POST.get('requested_days', 7))
        
        # Create request
        cd_request = CDRequest.objects.create(
            cd=cd,
            requester=request.user,
            requested_days=requested_days
        )
        
        messages.success(request, f"Request sent for '{cd.title}'")
        return redirect('my_requests')
    
    return render(request, 'users/request_cd.html', {'cd': cd})

@login_required
def my_requests(request):
    # Get requests made by the user
    sent_requests = CDRequest.objects.filter(requester=request.user).order_by('-request_date')
    
    if request.user.profile.is_librarian:
        # librarians see ALL requests in the system
        received_requests = CDRequest.objects.all().order_by('-request_date')
    else:
        received_requests = CDRequest.objects.none()
    
    return render(request, 'users/my_requests.html', {
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'is_librarian': request.user.profile.is_librarian,
    })

@login_required
def respond_to_request(request, request_id):
    if request.user.profile.is_librarian:
        cd_request = get_object_or_404(CDRequest, id=request_id)
    else:
        return HttpResponseForbidden("Only librarians can respond to borrow requests.")
    
    if request.method == 'POST':
        response = request.POST.get('response')
        
        if response == 'approve':
            cd_request.status = 'approved'
            cd_request.response_date = timezone.now()
            
            # Update CD status
            cd = cd_request.cd
            cd.status = 'checked_out'
            cd.checked_out_to = cd_request.requester
            
            # Calculate due date
            due_date = timezone.now().date() + timezone.timedelta(days=cd_request.requested_days)
            cd.due_date = due_date
            
            cd.save()
            cd_request.save()
            
            messages.success(request, f"Request approved. '{cd.title}' is now checked out to {cd_request.requester.username}.")
        
        elif response == 'reject':
            cd_request.status = 'rejected'
            cd_request.response_date = timezone.now()
            cd_request.save()
            messages.info(request, f"Request rejected.")
        
        return redirect('my_requests')
    
    return render(request, 'users/respond_to_request.html', {'cd_request': cd_request})

@login_required
def return_cd(request, request_id):
    profile = request.user.profile
    if profile.is_librarian:
        cd_request = get_object_or_404(
            CDRequest,
            id=request_id,
            status='approved'
        )
    else:
        cd_request = get_object_or_404(
            CDRequest,
            requester=request.user,
            id=request_id,
            status='approved'
        )
    
    if request.method == 'POST':
        cd_request.status = 'returned'
        cd_request.return_date = timezone.now()
        
        # Update CD status
        cd = cd_request.cd
        cd.status = 'available'
        cd.checked_out_to = None
        cd.due_date = None
        
        cd.save()
        cd_request.save()
        
        messages.success(request, f"'{cd.title}' has been marked as returned.")
        return redirect('my_requests')
    
    return render(request, 'users/return_cd.html', {'cd_request': cd_request})


def anon_user_view(request):
    public_cds = CD.objects.filter(
        Q(collections__isnull=True) | Q(collections__is_public=True)
    ).distinct()
    public_collections = Collection.objects.filter(is_public=True).distinct()
    return render(request, 'recordstar/anon_user_welcome.html', {
        'public_cds': public_cds,
        'public_collections': public_collections,
    })

@login_required
@require_POST
def request_access_to_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    
    # Check if user already has access
    if collection.owner == request.user or request.user in collection.allowed_users.all():
        messages.info(request, "You already have access to this collection.")
    else:
        # Check if there's a pending request
        existing_request = CollectionAccessRequest.objects.filter(
            collection=collection,
            requester=request.user
        ).first()
        
        if existing_request:
            if existing_request.status == 'pending':
                messages.info(request, "Your access request is pending approval from a librarian.")
            elif existing_request.status == 'approved':
                messages.info(request, "Your access request has already been approved.")
            else:  # rejected
                # Create a new request if previous one was rejected
                CollectionAccessRequest.objects.create(
                    collection=collection,
                    requester=request.user,
                    status='pending'
                )
                messages.success(request, f"Access request sent for {collection.name}. Waiting for approval.")
        else:
            # Create a new request
            CollectionAccessRequest.objects.create(
                collection=collection,
                requester=request.user,
                status='pending'
            )
            messages.success(request, f"Access request sent for {collection.name}. Waiting for approval.")
    
    # Redirect back to the limited view
    return redirect('collection_detail', collection_id=collection.id)

@login_required
def respond_to_collection_access_request(request, request_id):
    access_request = get_object_or_404(CollectionAccessRequest, id=request_id)

    if not request.user.profile.is_librarian:
        return HttpResponseForbidden("Only librarians can approve or reject access requests.")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            access_request.status = 'approved'
            access_request.collection.allowed_users.add(access_request.requester)
            access_request.save()
            messages.success(request, f"Access granted to {access_request.requester.username}.")

        elif action == 'reject':
            access_request.status = 'rejected'
            access_request.save()
            messages.info(request, f"Access request rejected for {access_request.requester.username}.")

        return redirect('collection')

    return render(request, 'users/respond_to_collection_access_request.html', {'access_request': access_request})