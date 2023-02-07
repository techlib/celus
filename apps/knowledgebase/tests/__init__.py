PLATFORM_INPUT_DATA = [
    {
        "name": "AAP - American Academy of Pediatrics",
        "pk": 328,
        "provider": "AAP",
        "providers": [
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "JR1"}
                ],
                "counter_version": 4,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "sushi.highwire.org",
                    "pk": 65,
                    "url": "http://sushi.highwire.org/services/SushiService",
                    "yearly": None,
                },
            },
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "TR"}
                ],
                "counter_version": 5,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "hwdpapi.highwire.org",
                    "pk": 83,
                    "url": "https://hwdpapi.highwire.org/sushi",
                    "yearly": None,
                },
            },
        ],
        "report_types": [],
        "counter_registry_id": None,
        "duplicates": [],
        "short_name": "AAP",
        "url": "https://www.aap.org/",
    },
    {
        "name": "American Association for Cancer Research",
        "pk": 327,
        "provider": "AACR",
        "providers": [
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "JR1"}
                ],
                "counter_version": 4,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "sushi.highwire.org",
                    "pk": 65,
                    "url": "http://sushi.highwire.org/services/SushiService",
                    "yearly": None,
                },
            },
            {
                "assigned_report_types": [
                    {"not_valid_after": None, "not_valid_before": None, "report_type": "TR"}
                ],
                "counter_version": 5,
                "provider": {
                    "extra": {},
                    "monthly": None,
                    "name": "hwdpapi.highwire.org",
                    "pk": 85,
                    "url": "https://hwdpapi.highwire.org/sushi/",
                    "yearly": None,
                },
            },
        ],
        "report_types": [
            {"pk": 15, "short_name": "MY", "name": "MyReport", "definitions": [999, 888]}
        ],
        "counter_registry_id": "11111111-1111-1111-1111-111111111111",
        "duplicates": [],
        "short_name": "AACR",
        "url": "https://www.aacr.org/",
        "platform_filter": "aacr_filter",
    },
    {
        "name": "APS",
        "pk": 339,
        "provider": "APS",
        "providers": [],
        "report_types": [],
        "short_name": "APS",
        "duplicates": [999, 888],
        "counter_registry_id": "00000000-0000-0000-0000-000000000000",
        "url": "https://www.journals.aps.org/",
        "platform_filter": None,
    },
]

PLATFORM_INPUT_DATA2 = [
    {
        "name": "ABC",
        "pk": 340,
        "provider": "ABC",
        "providers": [],
        "report_types": [],
        "short_name": "ABC",
        "counter_registry_id": "11111111-1111-1111-1111-111111111111",
        "url": "https://www.journals.abc.org/",
    }
]


REPORT_TYPE_INPUT_DATA = [
    {"pk": 111, "short_name": "one", "name": "first", "dimensions": [], "metrics": []},
    {
        "pk": 222,
        "short_name": "two",
        "name": "second",
        "dimensions": [
            {"pk": 1, "short_name": "dim1", "aliases": ["dimension1", "DIM1", "d1"]},
            {"pk": 2, "short_name": "dim2", "aliases": ["dimension2", "d2"]},
        ],
        "metrics": [{"pk": 1, "short_name": "metric1", "aliases": ["m1", "met1"]}],
    },
]


REPORT_TYPE_INPUT_DATA2 = [
    {
        "pk": 111,
        "short_name": "one",
        "name": "first",
        "dimensions": [{"pk": 1, "short_name": "dim1", "aliases": ["dimension1", "DIM1", "d1"]}],
        "metrics": [],
    },
    {
        "pk": 222,
        "short_name": "Two",
        "name": "SECOND",
        "dimensions": [
            {"pk": 1, "short_name": "dim1", "aliases": ["dimension1", "DIM1", "d1"]},
            {"pk": 3, "short_name": "dim3", "aliases": ["dimension3"]},
        ],
        "metrics": [
            {"pk": 2, "short_name": "metric2", "aliases": ["m2", "met2"], "interest_group": None}
        ],
    },
    {
        "pk": 333,
        "short_name": "three",
        "name": "third",
        "dimensions": [
            {"pk": 4, "short_name": "dim4", "aliases": ["dim4", "D4"]},
            {"pk": 3, "short_name": "dim3", "aliases": ["dimension3"]},
        ],
        "metrics": [
            {
                "pk": 2,
                "short_name": "metric2",
                "aliases": ["m2", "met2"],
                "interest_group": "search",
            },
            {"pk": 3, "short_name": "metric3", "aliases": ["m3"]},
        ],
    },
]
