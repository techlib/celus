"""
Here we store the dictionary descriptions of individual reports. In the future, we may
move this to a database or find some other way of storing this information. For now it is
good enough.
"""

REBIUN_REPORT = {
    "name": "Rebiun report",
    "description": "Standardized report used in Spain to report usage of electronic resources.",
    "parts": [
        {
            "name": "NCONSULRECPAGOCOUNT",
            "description": "6.5.1.1.Búsquedas en recursos electrónicos de pago o con licencia a "
            "lo largo del año:datos Counter.",
            "mainReportDefinition": {
                "reportType": "PR",
                "metric": "Searches_Platform",
                "filters": {"Access_Method": "Regular"},
            },
            "fallbackReportDefinition": {"reportType": "DB1", "metric": "Regular Searches"},
        },
        {
            "name": "NVISDESREVCOUNTPAG",
            "description": "6.5.2.1.1.1. Vistas y descargas del texto completo de artículos "
            "de revistas de pago: datos Counter",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Item_Requests",
                "filters": {
                    "Access_Method": "Regular",
                    "Data_Type": "Journal",
                    "Access_Type": "Controlled",
                },
            },
            "fallbackReportDefinition": {"reportType": "JR1", "metric": "FT Article Requests"},
            "subtractedFallbackReportDefinition": {
                "reportType": "JR1GOA",
                "metric": "FT Article Requests",
            },
        },
        {
            "name": "NVISDESREVCOUNTOP",
            "description": "6.5.2.1.1.2. Vistas y descargas del texto completo de artículos de "
            "revistas de open access: datos Counter",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Item_Requests",
                "filters": {
                    "Access_Method": "Regular",
                    "Data_Type": "Journal",
                    "Access_Type": "OA_Gold",
                },
            },
            "fallbackReportDefinition": {"reportType": "JR1GOA", "metric": "FT Article Requests"},
        },
        {
            "name": "NVISDESLIBRCOUNTPAG",
            "description": "6.5.2.1.2.1. Vistas y descargas del texto completo de libros de "
            + "pago: datos Counter",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Title_Requests",
                "filters": {
                    "Access_Method": "Regular",
                    "Data_Type": "Book",
                    "Access_Type": "Controlled",
                },
            },
            "fallbackReportDefinition": {"reportType": "BR1", "metric": "Book Title Requests"},
        },
        {
            "name": "NVISDESLIBRCOUNTOP",
            "description": "6.5.2.1.2.2. Vistas y descargas del texto completo de libros open "
            + "access: datos Counter",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Title_Requests",
                "filters": {
                    "Access_Method": "Regular",
                    "Data_Type": "Book",
                    "Access_Type": "OA_Gold",
                },
            },
        },
        {
            "name": "NVISDESDISTCOUNT",
            "description": "6.5.2.1.3. Vistas y descargas del texto completo de tipologías de "
            "datos (Data type) distintas de libros y revistas: datos Counter",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Item_Requests",
                "filters": {
                    "Data_Type": [
                        "Article",
                        "Book Segment",
                        "Conferences",
                        "Database",
                        "Dataset",
                        "Multimedia",
                        "Newspaper or Newsletter",
                        "Platform",
                        "Other",
                        "Repository Item",
                        "Report",
                        "Standards",
                        "Thesis or Dissertation",
                    ]
                },
            },
            "fallbackReportDefinition": {"reportType": "MR1", "metric": None},
        },
    ],
}

# the following report cannot be fully implemented yet, but I put it here for later
# so that I can capture the information
ACRL_IPEDS_REPORT = {
    "name": "ACRL IPEDS survey",
    "description": "ACRL Academic Library Trends and Statistics Survey - "
    "a standardized report used in the US",
    "parts": [
        # TODO: TR_B1 has to be summed up with TR_M1
        {
            "name": "60B",
            "description": "Total Digital/Electronic Circulation or Usage",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Title_Requests",
                "filters": {  # TR_B1
                    "Access_Method": "Regular",
                    "Data_Type": "Book",
                    "Access_Type": "Controlled",
                },
            },
        },
        # TODO: BR1 has to be summed up with MR1
        {
            "name": "61B",
            "description": "COUNTER Release 4 Circulation or Usage",
            "mainReportDefinition": {"reportType": "BR1", "metric": "Book Title Requests"},
        },
        # TODO BR2 has to be summed up with MR2
        {
            "name": "62B",
            "description": "COUNTER Release 4 Circulation or Usage",
            "mainReportDefinition": {"reportType": "BR2", "metric": "Book Title Requests"},
        },
        {
            "name": "63B",
            "description": "E-serials Usage (COUNTER 5, COUNTER 4, or other if needed)",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Item_Requests",
                "filters": {  # TR_J1 + OpenAccess
                    "Access_Method": "Regular",
                    "Data_Type": "Journal",
                    "Access_Type": ["Controlled", "OA_Gold"],
                },
            },
            "fallbackReportDefinition": {"reportType": "JR1", "metric": "FT Article Requests"},
        },
    ],
}


ARL_REPORT = {
    "name": "ARL Statistics survey",
    "description": "A standardized report used in the US",
    "parts": [
        {
            "name": "Question 18",
            "description": "Number of successful full-text article requests (journals)",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Item_Requests",
                "filters": {  # TR_J3 or TR_J1 + OpenAccess
                    "Access_Method": "Regular",
                    "Data_Type": "Journal",
                },
            },
        },
        {
            "name": "Question 19",
            "description": "Number of regular searches (databases)",
            "mainReportDefinition": {
                "reportType": "DR",
                "metric": "Searches_Regular",
                "filters": {"Access_Method": "Regular"},  # DR_D1
            },
            "fallbackReportDefinition": {
                "reportType": "PR",
                "metric": "Searches_Platform",
                "filters": {"Access_Method": "Regular"},  # PR_P1
            },
        },
        {
            "name": "Question 20",
            "description": "Number of federated searches (databases)",
            "implementationNote": 'The specification states that "Metric options include '
            '“Searches_Federated”, “Total_Item_Requests for full text databases”, '
            'and “Total_Item_Investigations for non-full text databases”." '
            'Celus cannot automatically assign the database type to decide which metric to use, '
            'so only "Searches_Federated" is reported.',
            "mainReportDefinition": {
                "reportType": "DR",
                "metric": "Searches_Federated",
                "filters": {"Access_Method": "Regular"},  # DR_D1
            },
        },
    ],
}


REPORTS = [REBIUN_REPORT, ARL_REPORT]  # ACRL_IPEDS_REPORT]


def get_report_def_by_name(name):
    for report in REPORTS:
        if report["name"] == name:
            return report
    return None
