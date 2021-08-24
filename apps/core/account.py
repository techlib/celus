from django.contrib.auth.forms import PasswordResetForm
from django.urls import resolve
from allauth.account.adapter import DefaultAccountAdapter
from allauth.utils import build_absolute_uri
from urllib.parse import urlparse


class CelusAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        url = f'/verify-email/?key={emailconfirmation.key}'
        return build_absolute_uri(request, url)

    def send_invitation_email(self, request, user):
        form = PasswordResetForm(data={"email": user.email})
        form.is_valid()  # don't care about retval this should be always valid...
        form.save(
            subject_template_name='registration/invitation_subject.txt',
            email_template_name='registration/invitation_email.html',
            request=request,
            extra_email_context={'user': user},  # overrides user in the template
        )

    def send_mail(self, template_prefix, email, context):
        # override reset password template
        if template_prefix == "account/email/password_reset_key":
            # get user_id and token from url
            orig_url = urlparse(context["password_reset_url"])
            kwargs = resolve(orig_url.path).kwargs
            context[
                "reset_url"
            ] = f"{orig_url.scheme}://{orig_url.netloc}/reset-password/?uid={kwargs.get('uidb64')}&token={kwargs.get('token')}"
            context["site_name"] = orig_url.netloc

            msg = self.render_mail("registration/password_reset", email, context)
            msg.send()
        else:
            super().send_mail(template_prefix, email, context)
