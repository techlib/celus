from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    def get_usable_name(self):
        if self.first_name or self.last_name:
            return "{0} {1}".format(self.first_name, self.last_name)
        return self.email
