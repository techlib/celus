import json
from base64 import b64encode, b64decode
from typing import Union


def b64json(data):
    return b64encode(json.dumps(data).encode('utf-8')).decode('ascii')


def parse_b64json(data: str) -> Union[dict, list]:
    return json.loads(b64decode(data))
