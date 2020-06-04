from pprint import pprint

from api import ERMS


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
                    print(
                        "Year: {}, Price offer: {} {}; Price splits: {}+{} ({})+({})".format(
                            ppy['year'],
                            ppy['amount'],
                            ppy['currency'],
                            sum(
                                ys['participation']['amount']
                                for ys in year_splits
                                if ys['participation']['amount']
                            ),
                            sum(
                                ys['subsidy']['amount']
                                for ys in year_splits
                                if 'subsidy' in ys and ys['subsidy'] and ys['subsidy']['amount']
                            ),
                            ', '.join(str(ys['participation']['amount']) for ys in year_splits),
                            ', '.join(
                                str(ys['subsidy']['amount'])
                                for ys in year_splits
                                if 'subsidy' in ys and ys['subsidy']
                            ),
                        )
                    )

        print(offers)
