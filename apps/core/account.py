from django.contrib.auth.forms import PasswordResetForm
from allauth.account.adapter import DefaultAccountAdapter
from allauth.utils import build_absolute_uri


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
