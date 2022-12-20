from urllib.parse import urlparse

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.forms import default_token_generator
from allauth.account.utils import user_pk_to_url_str as uid_encoder
from allauth.utils import build_absolute_uri
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.urls import resolve


class CelusAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        url = f'/verify-email/?key={emailconfirmation.key}'
        return build_absolute_uri(request, url)

    def send_invitation_email(self, request, user):
        # In this code, we use the token generator and uid encoder from allauth because we
        # are using dj-rest-auth to later process the token and uid and it expects it to be in
        # allauth format when allauth is in INSTALLED_APPS.
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
        # rudimentary checks that the domain is properly set - nothing fancy, we just need
        # to catch wildcards and strange names
        if '.' not in domain or '*' in domain:
            raise ValueError(f'Invalid site.domain: {domain}')
        elif domain not in settings.ALLOWED_HOSTS:
            raise ValueError(
                f'site.domain ({domain}) is not present in ALLOWED_HOSTS, probably a '
                'misconfiguration'
            )
        context = {
            'email': user.email,
            'domain': domain,
            'site_name': site_name,
            'uid': uid_encoder(user),
            'user': user,
            'token': default_token_generator.make_token(user),
            'protocol': request.scheme,
        }
        subject = loader.render_to_string('registration/invitation_subject.txt', context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string('registration/invitation_email.html', context)
        email_message = EmailMultiAlternatives(subject, body, to=[user.email])
        email_message.send()

    def send_mail(self, template_prefix, email, context):
        # override reset password template
        if template_prefix == "account/email/password_reset_key":
            # get user_id and token from url
            orig_url = urlparse(context["password_reset_url"])
            kwargs = resolve(orig_url.path).kwargs
            uid = kwargs.get('uidb64')
            token = kwargs.get('token')
            context[
                "reset_url"
            ] = f"{orig_url.scheme}://{orig_url.netloc}/reset-password/?uid={uid}&token={token}"
            context["site_name"] = orig_url.netloc

            msg = self.render_mail("registration/password_reset", email, context)
            msg.send()
        else:
            super().send_mail(template_prefix, email, context)
