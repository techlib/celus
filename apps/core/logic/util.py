from hashlib import blake2b

from django.conf import settings


def text_hash(text: str):
    return blake2b(text.encode('utf-8'), digest_size=16).hexdigest()


def this_celus_domain():
    return settings.ALLOWED_HOSTS[0]
