from allauth.account.adapter import DefaultAccountAdapter
from allauth.utils import build_absolute_uri


class CelusAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        url = f'/verify-email?key={emailconfirmation.key}'
        return build_absolute_uri(request, url)
