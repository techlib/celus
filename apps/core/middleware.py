from django.conf import settings
from django.contrib import auth
from django.contrib.auth import load_backend
from django.contrib.auth.middleware import RemoteUserMiddleware
import logging

from apps.core.auth import EDUIdAuthenticationBackend


logger = logging.getLogger(__name__)


class EDUIdHeaderMiddleware(RemoteUserMiddleware):

    header = settings.EDUID_IDENTITY_HEADER

    def process_request(self, request):
        logger.warning('Identity: %s', request.META.get(self.header))
        headers = [
            'HTTP_X_USER_ID',
            'HTTP_X_FULL_NAME',
            'HTTP_X_FIRST_NAME',
            'HTTP_X_LAST_NAME',
            'HTTP_X_USER_NAME',
            'HTTP_X_MAIL',
            'HTTP_X_CN',
            'HTTP_X_ROLES',
            'HTTP_X_IDENTITY',
        ]
        out = '; '.join(f'{header}: {request.META.get(header)}' for header in headers)
        logger.warning('Headers: %s', out)
        super().process_request(request)

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
