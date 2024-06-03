from hashlib import blake2b

from django.conf import settings


def text_hash(text: str):
    return blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def this_celus_domain():
    return settings.ALLOWED_HOSTS[0]


def checksum_and_size_fileobj(fileobj, digest_size=32) -> (str, int):
    # store original position
    orig_pos = fileobj.tell()

    fileobj.seek(0)
    hasher = blake2b(digest_size=digest_size)
    size = 0
    while chunk := fileobj.read(1024 * 1024):
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        hasher.update(chunk)
        size += len(chunk)

    # rewind to original position
    fileobj.seek(orig_pos)

    return hasher.hexdigest(), size
