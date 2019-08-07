from core.models import Identity, User


class EDUIdAuthenticationBackend:
    """
    Custom authentication backend that uses the data provided in HTTP header (extracted
    in the middleware in .middleware) and checks it against the identity database
    stored locally or accessed remotely using API.
    """

    def authenticate(self, request, remote_user=None):
        if not remote_user:
            return None
        try:
            identity = Identity.objects.select_related('user').get(identity=remote_user)
        except Identity.DoesNotExist:
            return None
        return identity.user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def clean_username(self, username):
        """
        This is used by the middleware to compare currently logged in user and the
        one that is being provided by the backend. We need to resolve the identity->user
        mapping here
        """
        try:
            identity = Identity.objects.select_related('user').get(identity=username)
        except Identity.DoesNotExist:
            return username
        return identity.user.get_username()
