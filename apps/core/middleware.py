from django.contrib import auth
from django.contrib.auth import load_backend
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware

from apps.core.auth import EDUIdAuthenticationBackend


class EDUIdHeaderMiddleware(RemoteUserMiddleware):

    header = 'HTTP_X_IDENTITY'

    def _remove_invalid_user(self, request):
        """
        Remove the current authenticated user in the request which is invalid
        but only if the user is authenticated via the EDUIdAuthenticationBackend.

        This is a copy-paste based modification of the parent method
        """
        try:
            stored_backend = load_backend(request.session.get(auth.BACKEND_SESSION_KEY, ''))
        except ImportError:
            # backend failed to load
            auth.logout(request)
        else:
            if isinstance(stored_backend, EDUIdAuthenticationBackend):
                auth.logout(request)
