import logging
import urllib.parse
import typing

import requests


logger = logging.getLogger(__file__)


class ERMSError(Exception):

    pass


class ERMS(object):

    """
    Possible queries:

    /object?id=eq.574
    /object?id=in.(574,575)
    """

    # endpoints
    EP_OBJECT = 'object'
    EP_IDENTITY = 'identity'
    EP_CONSORTIUM = 'consortium'
    EP_CONSORTIUM_MEMBER = 'consortium_member'
    EP_ACQUISITION = 'acquisition'
    EP_PROCUREMENT = 'procurement'
    EP_OFFER = 'offer'
    EP_OFFER_SPLIT = 'offer_split'

    # object classes
    CLS_PERSON = 'Person'
    CLS_ORGANIZATION = 'Organization'
    CLS_PLATFORM = 'Platform'

    def __init__(self, base_url="https://erms.czechelib.cz/api/"):
        ERMS.check_url(base_url)
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    @staticmethod
    def check_url(url):
        """ Check whether the url is in a propper format
            otherwise it raises ERMSError exception
        """
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            raise ERMSError(f"Incorrect ERMS url {url}") from e

        # Need at least 'https://example.com/'
        if not parsed.netloc or not parsed.scheme:
            raise ERMSError(f"Incorrect ERMS url {url}")

    @classmethod
    def _construct_query_string(cls, value):
        if type(value) in (list, tuple, set):
            return 'in.({})'.format(','.join(str(_id) for _id in value))
        return f'eq.{value}'

    def construct_object_url(self, cls=None, object_id=None) -> str:
        params = {}
        if cls:
            params['class'] = self._construct_query_string(cls)
        if object_id:
            params['id'] = self._construct_query_string(object_id)
        else:
            params['order'] = 'id'
        query = urllib.parse.urlencode(params)
        return f'{self.base_url}/{self.EP_OBJECT}?{query}'

    def fetch_url(self, url):
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        raise ERMSError(response)

    def fetch_objects(self, cls=None, object_id=None) -> list:
        url = self.construct_object_url(cls=cls, object_id=object_id)
        ERMS.check_url(url)

        data = self.fetch_url(url)
        return data

    def fetch_endpoint(self, endpoint, object_id=None, **kwargs) -> list:
        url = f'{self.base_url}/{endpoint}'

        params = {}
        if object_id:
            params['id'] = self._construct_query_string(object_id)
        for key, value in kwargs.items():
            params[key] = self._construct_query_string(value)
        if params:
            url += '?{}'.format(urllib.parse.urlencode(params))

        ERMS.check_url(url)
        return self.fetch_url(url)
