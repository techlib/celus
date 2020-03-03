import logging

from django.conf import settings

from core.logic.sync import UserSyncer, IdentitySyncer
from core.models import Identity, User, DataSource
from erms.api import ERMS

logger = logging.getLogger(__name__)


def sync_user_with_erms(user_id):
    erms = ERMS(settings.ERMS_API_URL)
    identities = erms.fetch_endpoint(ERMS.EP_IDENTITY, identity=user_id)
    if identities:
        identity = identities[0]
        persons = erms.fetch_objects(ERMS.CLS_PERSON, object_id=identity['person'])
        if persons:
            data_source, _created = DataSource.objects.get_or_create(short_name='ERMS',
                                                                     type=DataSource.TYPE_API)
            u_syncer = UserSyncer(data_source)
            stats = u_syncer.sync_data(persons)
            logger.debug('User sync on login: %s', stats)
            i_syncer = IdentitySyncer(data_source)
            stats = i_syncer.sync_data(identities)
            logger.debug('Identity sync on login: %s', stats)


class EDUIdAuthenticationBackend:
    """
    Custom authentication backend that uses the data provided in HTTP header (extracted
    in the middleware in .middleware) and checks it against the identity database
    stored locally or accessed remotely using API.
    """

    def authenticate(self, request, remote_user=None):
        if not remote_user:
            return None
        if settings.LIVE_ERMS_AUTHENTICATION:
            try:
                sync_user_with_erms(remote_user)
            except Exception as e:
                logger.error('ERMS sync error: %s', e)
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
