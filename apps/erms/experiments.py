import urllib.parse
from pprint import pprint
from collections import Counter

import requests


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
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    @classmethod
    def _construct_query_string(cls, value):
        if type(value) in (list, tuple, set):
            return 'in.({})'.format(','.join(str(_id) for _id in value))
        return f'eq.{value}'

    def construct_object_url(self, cls=None, object_id=None):
        params = {}
        if cls:
            params['class'] = self._construct_query_string(cls)
        if object_id:
            params['id'] = self._construct_query_string(object_id)
        query = urllib.parse.urlencode(params)
        return f'{self.base_url}/{self.EP_OBJECT}?{query}'

    def fetch_url(self, url):
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        raise ERMSError(response)

    def fetch_objects(self, cls=None, object_id=None):
        url = self.construct_object_url(cls=cls, object_id=object_id)
        data = self.fetch_url(url)
        return data

    def fetch_endpoint(self, endpoint, object_id=None, **kwargs):
        url = f'{self.base_url}/{endpoint}'
        params = {}
        if object_id:
            params['id'] = self._construct_query_string(object_id)
        for key, value in kwargs.items():
            params[key] = self._construct_query_string(value)
        if params:
            url += '?{}'.format(urllib.parse.urlencode(params))
        return self.fetch_url(url)


if __name__ == '__main__':
    import json
    with open('../../config/settings/secret_settings.json', 'r') as infile:
        settings = json.load(infile)
    erms = ERMS(settings['ERMS_API_URL'])
    pprint(erms.fetch_objects(object_id=(574, 575, 603)))
    # for idt in erms.fetch_endpoint(erms.EP_IDENTITY):
    #     pprint(idt)
    # ref_keys = Counter()
    # for per in erms.fetch_objects(erms.CLS_PERSON):
    #     for key in per['refs'].keys():
    #         ref_keys[key] += 1
    #     pprint(per)
    # print(ref_keys)
    # for org in erms.fetch_objects(erms.CLS_ORGANIZATION):
    #     for key, val in org.get('vals', {}).items():
    #         if len(val) > 1:
    #             print(key, val)
    # pprint(erms.fetch_objects(cls=erms.CLS_PLATFORM))
    # pprint(erms.fetch_endpoint(erms.EP_CONSORTIUM))
    # pprint(erms.fetch_endpoint(erms.EP_CONSORTIUM_MEMBER))
    # pprint(erms.fetch_endpoint(erms.EP_ACQUISITION))
    # pprint(erms.fetch_objects(object_id=(670, 665)))
    if False:
        offers = Counter()
        for rec in erms.fetch_endpoint(erms.EP_PROCUREMENT):
            offer_id = rec['offer']
            offers[offer_id] += 1
            if offer_id:
                offer = erms.fetch_endpoint(erms.EP_OFFER, object_id=offer_id)[0]
                splits = erms.fetch_endpoint(erms.EP_OFFER_SPLIT, offer=offer_id)
                for ppy in offer['price_per_year']:
                    year_splits = [split for split in splits if split['year'] == ppy['year']]
                    print("Year: {}, Price offer: {} {}; Price splits: {}+{} ({})+({})".format(
                        ppy['year'],
                        ppy['amount'],
                        ppy['currency'],
                        sum(ys['participation']['amount'] for ys in year_splits
                            if ys['participation']['amount']),
                        sum(ys['subsidy']['amount'] for ys in year_splits
                            if 'subsidy' in ys and ys['subsidy'] and ys['subsidy']['amount']),
                        ', '.join(str(ys['participation']['amount']) for ys in year_splits),
                        ', '.join(str(ys['subsidy']['amount']) for ys in year_splits
                                  if 'subsidy' in ys and ys['subsidy']),
                    ))

        print(offers)
