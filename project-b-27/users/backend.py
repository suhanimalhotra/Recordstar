from django.contrib.auth.backends import ModelBackend

class NonAdminSiteAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username, password, **kwargs)
        if user and user.is_superuser:
            # only allow request if from /admin/
            if request is None or not request.path.startswith('/admin/'):
                return None
        return user