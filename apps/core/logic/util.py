from hashlib import blake2b


def text_hash(text: str):
    return blake2b(text.encode('utf-8'), digest_size=16).hexdigest()
