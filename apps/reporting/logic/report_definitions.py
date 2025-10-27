"""
Here we store the dictionary descriptions of individual reports. In the future, we may
move this to a database or find some other way of storing this information. For now it is
good enough.
"""

REBIUN_REPORT = {
    "name": "Rebiun report",
    "description": "Standardized report used in Spain to report usage of electronic resources.",
    "dataSources": [
        {
            "id": "TR_JOURNAL",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Data_Type": "Journal",
                "Access_Type": "Controlled",
            },
        },
        {"reportType": "JR1", "metric": "FT Article Requests", "fallbackFor": "TR_JOURNAL"},
        {
            "id": "JR1GOA_SUB",
            "reportType": "JR1GOA",
            "metric": "FT Article Requests",
            "fallbackFor": "TR_JOURNAL",
        },
        {
            "id": "TR_JOA",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Data_Type": "Journal",
                "Access_Type": "OA_Gold",
            },
        },
        {"reportType": "JR1GOA", "metric": "FT Article Requests", "fallbackFor": "TR_JOA"},
        {
            "reportType": "PR",
            "metric": "Searches_Platform",
            "filters": {"Access_Method": "Regular"},
        },
        {"reportType": "DB1", "metric": "Regular Searches", "fallbackFor": "PR"},
        {
            "id": "TR_BOOKS",
            "reportType": "TR",
            "metric": "Unique_Title_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Data_Type": "Book",
                "Access_Type": "Controlled",
            },
        },
        {"reportType": "BR1", "metric": "Book Title Requests", "fallbackFor": "TR_BOOKS"},
        {
            "id": "TR_BOOKS_OA",
            "reportType": "TR",
            "metric": "Unique_Title_Requests",
            "filters": {"Access_Method": "Regular", "Data_Type": "Book", "Access_Type": "OA_Gold"},
        },
        {
            "id": "TR_OTHER",
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
                    "Platform",
                    "Other",
                    "Report",
                    "Standards",
                    # we keep the versions with spaces for compatibility with some strange reports
                    # which incorrectly use spaces instead of underscores
                    "Newspaper or Newsletter",
                    "Newspaper_or_Newsletter",
                    "Repository Item",
                    "Repository_Item",
                    "Thesis or Dissertation",
                    "Thesis_or_Dissertation",
                ]
            },
        },
        {"reportType": "MR1", "metric": None, "fallbackFor": "TR_OTHER"},
    ],
    "parts": [
        {
            "name": "NCONSULRECPAGOCOUNT",
            "description": "6.5.1.1.Búsquedas en recursos electrónicos de pago o con licencia a "
            "lo largo del año:datos Counter.",
            "explanation": "COUNTER 5 PR report is used to get information about searches. If "
            "it is not available, COUNTER 4 DB1 report is used instead.",
            "stages": [{"name": "NCONSULRECPAGOCOUNT", "formula": "PR | DB1"}],
        },
        {
            "name": "NVISDESREVCOUNTPAG",
            "description": "6.5.2.1.1.1. Vistas y descargas del texto completo de artículos "
            "de revistas de pago: datos Counter",
            "explanation": "COUNTER 5 TR report is used to get information about journal "
            "usage without open access. If it is not available, COUNTER 4 JR1 report is "
            "used with data from the COUNTER 4 JR1GOA report subtracted from it to remove "
            "open access usage.",
            "stages": [
                # the following would show complete genesis of the data, but creates too many tabs
                # {"id": "tr_journal", "name": "TR", "formula": "TR_JOURNAL"},
                # {"id": "jr1x", "name": "JR1", "formula": "JR1"},
                # {"id": "jr1goa_sub", "name": "JR1GOA", "formula": "JR1GOA_SUB"},
                # {"id": "jr1final", "name": "JR1 - JR1GOA", "formula": "jr1x - jr1goa_sub"},
                # {"name": "TR & JR1-JR1GOA", "formula": "tr_journal | (jr1x - jr1goa_sub)"},
                {"name": "NVISDESREVCOUNTPAG", "formula": "TR_JOURNAL | (JR1 - JR1GOA_SUB)"}
            ],
        },
        {
            "name": "NVISDESREVCOUNTOP",
            "description": "6.5.2.1.1.2. Vistas y descargas del texto completo de artículos de "
            "revistas de open access: datos Counter",
            "explanation": "COUNTER 5 TR report is used to get information about journal "
            "open-access usage. If it is not available, COUNTER 4 JR1GOA is used instead.",
            "stages": [{"name": "NVISDESREVCOUNTOP", "formula": "TR_JOA | JR1GOA"}],
        },
        {
            "name": "NVISDESLIBRCOUNTPAG",
            "description": "6.5.2.1.2.1. Vistas y descargas del texto completo de libros de "
            + "pago: datos Counter",
            "explanation": "COUNTER 5 TR report is used to get information about book usage. "
            "If it is not available, COUNTER 4 BR1 report is used instead.",
            "stages": [{"name": "NVISDESLIBRCOUNTPAG", "formula": "TR_BOOKS | BR1"}],
        },
        {
            "name": "NVISDESLIBRCOUNTOP",
            "description": "6.5.2.1.2.2. Vistas y descargas del texto completo de libros open "
            + "access: datos Counter",
            "explanation": "COUNTER 5 TR report is used to get information about open-access book "
            "usage.",
            "stages": [{"name": "NVISDESLIBRCOUNTOP", "formula": "TR_BOOKS_OA"}],
        },
        {
            "name": "NVISDESDISTCOUNT",
            "description": "6.5.2.1.3. Vistas y descargas del texto completo de tipologías de "
            "datos (Data type) distintas de libros y revistas: datos Counter",
            "explanation": "COUNTER 5 TR report is used to get information about usage of specified"
            " data types excluding journal and books. If it is TR report is not "
            "available, COUNTER 4 MR1 report is used instead.",
            "stages": [{"name": "NVISDESDISTCOUNT", "formula": "TR_OTHER | MR1"}],
        },
    ],
}

ARL_REPORT = {
    "name": "ARL Statistics survey",
    "description": "A standardized report used in the US",
    "dataSources": [
        {
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {  # TR_J3 or TR_J1 + OpenAccess
                "Access_Method": "Regular",
                "Data_Type": "Journal",
            },
        },
        {
            "reportType": "DR",
            "metric": "Searches_Regular",
            "filters": {"Access_Method": "Regular"},  # DR_D1
        },
        {
            "reportType": "PR",
            "metric": "Searches_Platform",
            "filters": {"Access_Method": "Regular"},  # PR_P1
            "fallbackFor": "DR",
        },
        {
            "id": "dr_federated",
            "reportType": "DR",
            "metric": "Searches_Federated",
            "filters": {"Access_Method": "Regular"},  # DR_D1
        },
    ],
    "parts": [
        {
            "name": "Question 18",
            "description": "Number of successful full-text article requests (journals)",
            "explanation": "COUNTER 5 TR report is used to get information about journal usage - "
            "regardless of licensing.",
            "stages": [{"id": "tr_stage", "name": "TR", "formula": "TR"}],
        },
        {
            "name": "Question 19",
            "description": "Number of regular searches (databases)",
            "explanation": "COUNTER 5 DR report is used to get information about searches. "
            "If it is not available, COUNTER 4 PR report is used instead.",
            "stages": [
                {"id": "dr", "name": "DR", "formula": "DR"},
                {"id": "pr", "name": "PR", "formula": "PR"},
                {"name": "DR & PR", "formula": "dr | pr"},
            ],
        },
        {
            "name": "Question 20",
            "description": "Number of federated searches (databases)",
            "explanation": "COUNTER 5 DR report is used to get information about federated "
            "searches.",
            "implementationNote": 'The specification states that "Metric options include '
            "“Searches_Federated”, “Total_Item_Requests for full text databases”, "
            'and “Total_Item_Investigations for non-full text databases”." '
            "CELUS cannot automatically assign the database type to decide which metric to use, "
            'so only "Searches_Federated" is reported.',
            "stages": [{"id": "dr_stage", "name": "DR", "formula": "dr_federated"}],
        },
    ],
}

IPEDS_REPORT_2022 = {
    "name": "ACRL IPEDS 2022",
    "description": "ACRL IPEDS report - used in the US - 2022 version",
    "dataSources": [
        {
            "id": "tr_b1",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {"Access_Method": "Regular", "Data_Type": "Book"},
        },
        {"id": "ir_m1", "reportType": "IR_M1", "metric": "Total_Item_Requests"},
        {"id": "br1", "reportType": "BR1", "metric": "Book Title Requests", "fallbackFor": "tr_b1"},
        {"id": "br2", "reportType": "BR2", "metric": "Book Section Requests", "fallbackFor": "br1"},
        {
            "id": "mr1",
            "reportType": "MR1",
            "metric": "Multimedia Downloads",
            "fallbackFor": "ir_m1",
        },
        {"id": "mr2", "reportType": "MR2", "metric": "Multimedia Downloads", "fallbackFor": "mr1"},
        {
            "id": "tr_j",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": ["Controlled", "OA_Gold"],
                "Data_Type": "Journal",
            },
        },
        {
            "id": "jr1",
            "reportType": "JR1",
            "metric": "Full Text Article Requests",
            "fallbackFor": "tr_j",
        },
    ],
    "parts": [
        {
            "name": "60B",
            "description": "Total Digital/Electronic Circulation or Usage",
            "explanation": "Information about book usage from COUNTER 5 TR report is summed up "
            "together with information about multimedia usage from COUNTER 5 IR_M1 report.",
            "stages": [
                {"id": "TR_B1", "name": "TR", "formula": "tr_b1"},
                {"name": "IR_M1", "formula": "ir_m1"},
                {"name": "TR + IR_M1", "formula": "TR_B1 + IR_M1"},
            ],
        },
        {
            "name": "61B",
            "description": "COUNTER Release 4 Circulation or Usage",
            "explanation": "For platforms which do not support COUNTER 5 in part 60B, information "
            "about book usage from COUNTER 4 BR1 report is summed up together with "
            "information about multimedia usage from COUNTER 4 MR1 report.",
            "stages": [
                {"name": "BR1", "formula": "br1"},
                {"name": "MR1", "formula": "mr1"},
                {"name": "BR1 + MR1", "formula": "BR1 + MR1"},
            ],
        },
        {
            "name": "62B",
            "description": "COUNTER Release 4 Circulation or Usage - fallback",
            "explanation": "For platforms which support neither COUNTER 5 in part 60B, nor the "
            "COUNTER 4 reports used in part 61B, this entry combines information about book usage "
            "from COUNTER 4 BR2 report with information about multimedia usage from COUNTER 4 MR2 "
            "report.",
            "stages": [
                {"name": "BR2", "formula": "br2"},
                {"name": "MR2", "formula": "mr2"},
                {"name": "BR2 + MR2", "formula": "BR2 + MR2"},
            ],
        },
        {
            "name": "63B",
            "description": "E-serials Usage (COUNTER 5, COUNTER 4, or other if needed)",
            "explanation": "COUNTER 5 TR report is used to get information about journal usage. "
            "If it is not available, COUNTER 4 JR1 report is used instead.",
            "stages": [
                {"id": "TR_J", "name": "TR", "formula": "tr_j"},
                {"name": "JR1", "formula": "jr1"},
                {"name": "TR & JR1", "formula": "TR_J | JR1"},
            ],
        },
    ],
}

IPEDS_REPORT_2023 = {
    "name": "ACRL IPEDS 2023",
    "description": "ACRL IPEDS report - used in the US - 2023 version",
    "dataSources": [
        {
            "id": "tr_b1",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {"Access_Method": "Regular", "Data_Type": "Book"},
        },
        {"id": "ir_m1", "reportType": "IR_M1", "metric": "Total_Item_Requests"},
        {
            "id": "tr_j",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": ["Controlled", "OA_Gold"],
                "Data_Type": "Journal",
            },
        },
    ],
    "parts": [
        {
            "name": "61A",
            "description": "Total E-book & E-media Usage",
            "explanation": "Information about book usage from COUNTER 5 TR_B1 report is summed up "
            "together with information about multimedia usage from COUNTER 5 IR_M1 report.",
            "stages": [
                {"id": "TR_B1", "name": "TR", "formula": "tr_b1"},
                {"name": "IR_M1", "formula": "ir_m1"},
                {"name": "TR + IR_M1", "formula": "TR_B1 + IR_M1"},
            ],
        },
        {
            "name": "61B",
            "description": "E-serials Usage",
            "explanation": "COUNTER 5 TR report is used to get information about journal usage. "
            "Both Controlled and Open Access usage is reported.",
            "stages": [{"name": "TR", "formula": "tr_j"}],
        },
    ],
}

IPEDS_REPORT_2024 = {
    "name": "ACRL IPEDS 2024",
    "description": "ACRL IPEDS report - used in the US - 2024 version",
    "dataSources": [
        {
            "id": "tr51_b1",
            "reportType": "TR51",
            "metric": "Unique_Item_Requests",
            "filters": {"Access_Method": "Regular", "Data_Type": "Book"},
        },
        {
            "id": "tr_b1",
            "fallbackFor": "tr51_b1",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {"Access_Method": "Regular", "Data_Type": "Book"},
        },
        {
            "id": "ir51",
            "reportType": "IR51",
            "metric": "Total_Item_Requests",
            "filters": {
                "Data_Type": [
                    "Multimedia",
                    "Audiovisual",
                    "Image",
                    "Interactive_Resource",
                    "Sound",
                ],
                "Access_Method": "Regular",
            },
        },
        {
            "id": "ir_m1",
            "reportType": "IR_M1",
            "metric": "Total_Item_Requests",
            "fallbackFor": "ir51",
        },
        {
            "id": "tr51_j",
            "reportType": "TR51",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": ["Controlled", "Open"],
                "Data_Type": "Journal",
            },
        },
        {
            "id": "tr_j",
            "fallbackFor": "tr51_j",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": ["Controlled", "OA_Gold"],
                "Data_Type": "Journal",
            },
        },
    ],
    "parts": [
        {
            "name": "61A",
            "description": "Total E-book & E-media Usage",
            "explanation": "Information about book usage from COUNTER 5.1 TR_B1 report is summed "
            "up together with information about multimedia usage from COUNTER 5.1 IR report. We "
            "assume that COUNTER 5 reports may be used as a fallback because 5.1 was not available "
            "in 2024.",
            "implementationNote": "The standard specifies that COUNTER 5.1 reports should be used, "
            "but as COUNTER 5.1 was not available in 2024, we use COUNTER 5 reports as fallback. "
            "For those we use the same configuration as in 2023.",
            "stages": [
                {"id": "TR_B1", "name": "TR", "formula": "tr51_b1 | tr_b1"},
                {"name": "IR_M1", "formula": "ir51 | ir_m1"},
                {"name": "TR + IR_M1", "formula": "TR_B1 + IR_M1"},
            ],
        },
        {
            "name": "61B",
            "description": "E-serials Usage",
            "explanation": "COUNTER 5.1 TR report is used to get information about journal usage. "
            "Both Controlled and Open Access usage is reported. We assume that COUNTER 5 reports "
            "may be used as a fallback because 5.1 was not available in 2024.",
            "implementationNote": "The standard specifies that COUNTER 5.1 reports should be used, "
            "but as COUNTER 5.1 was not available in 2024, we use COUNTER 5 reports as fallback. "
            "For those we use the same configuration as in 2023.",
            "stages": [{"name": "TR", "formula": "tr51_j | tr_j"}],
        },
    ],
}

CAUL_REPORT_2024 = {
    "name": "CAUL (Council of Australian University Librarians) report",
    "description": "Standardized report used in Australia to report usage of electronic resources.",
    "dataSources": [
        {"id": "br2", "reportType": "BR2", "metric": "Book Section Requests"},
        {
            "id": "tr_b3",
            "reportType": "TR",
            "metric": "Total_Item_Requests",
            "filters": {"Access_Method": "Regular", "Data_Type": "Book"},
        },
        {"id": "jr1", "reportType": "JR1", "metric": "FT Article Requests"},
        {
            "id": "tr_j3",
            "reportType": "TR",
            "metric": "Total_Item_Requests",
            "filters": {"Data_Type": "Journal", "Access_Method": "Regular"},
        },
    ],
    "parts": [
        # not using full names from source because they are too long for Excel tabs
        {
            # Books (Digital) COUNTER Release 4
            "name": "COUNTER 4 Books",
            "description": "This is the COUNTER Release 4 BR2 total representing all eBook section "
            "usage across all publisher and aggregator platforms. A single total "
            "R4 BR2 figure for all eBook section usage during the year.",
            "stages": [{"name": "BR2", "formula": "br2"}],
        },
        {
            # Books (Digital) COUNTER Release 5 (2019 - )
            "name": "COUNTER 5 Books",  # used for Excel sheet tabs
            "description": "This is the COUNTER Release 5 TR_B3 total representing all eBook "
            "section usage across all publisher and aggregator platforms including GOA "
            "(usage of gold open access titles).",
            "explanation": "Report equivalent to TR_B3 is generated from the full Title Report (TR)"
            " by applying the corresponding filters (Access_Method=Regular, Data_Type=Book).",
            "stages": [{"name": "TR_B3", "formula": "tr_b3"}],
        },
        {
            # Journals (Digital) COUNTER Release 4
            "name": "COUNTER 4 Journals",  # used for Excel sheet tabs
            "description": " This is the COUNTER Release 4 JR1 total representing all eJournal "
            "usage across all publisher and aggregator platforms. A single total COUNTER R4 JR1 "
            "figure for all eJournal usage during the year. The R4 JR1 total includes JR1a "
            "(usage of backfile/archive titles) as well as JR1 GOA (usage of gold open access "
            "titles).",
            "explanation": "It includes only usage recorded via R4 JR1 reports for eJournals "
            "across all publisher and aggregator platforms. Usage of any title that is not "
            "recorded via a R4 JR1 report is excluded.",
            "stages": [{"name": "JR1", "formula": "jr1"}],
        },
        {
            # Journals (Digital) COUNTER Release 5 (2019 - )
            "name": "COUNTER 5 Journals",  # used for Excel sheet tabs
            "description": "This is the COUNTER Release 5 TR_J3 total representing all eJournal "
            "usage across all publisher and aggregator platforms including GOA "
            "(usage of gold open access titles).",
            "explanation": "Report equivalent to TR_J3 is generated from the full Title Report (TR)"
            " by applying the corresponding filters (Access_Method=Regular, Data_Type=Journal).",
            "stages": [{"name": "TR_J3", "formula": "tr_j3"}],
        },
    ],
}

CEL_REPORT = {
    "name": "CzechELib report",
    "preview": True,
    "description": {
        "en": "Demo report for the CzechELib consortium - inspired by interest calculations",
        "cs": "Demo report pro CzechELib - inspirovaný výpočtem zájmu",
    },
    "dataSources": [
        {
            "id": "tr51_b1",
            "reportType": "TR51",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": "Controlled",
                "Data_Type": "Book",
            },
        },
        {
            "id": "tr_b1",
            "fallbackFor": "tr51_b1",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": "Controlled",
                "Data_Type": "Book",
            },
        },
        {
            "id": "tr51_j",
            "reportType": "TR51",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": "Controlled",
                "Data_Type": "Journal",
            },
        },
        {
            "id": "tr_j",
            "fallbackFor": "tr51_j",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": "Controlled",
                "Data_Type": "Journal",
            },
        },
        {
            "id": "ir51",
            "reportType": "IR51",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Data_Type": [
                    "Multimedia",
                    "Audiovisual",
                    "Image",
                    "Interactive_Resource",
                    "Sound",
                ],
                "Access_Method": "Regular",
                "Access_Type": "Controlled",
            },
        },
        {
            "id": "ir_m1",
            "reportType": "IR_M1",
            "metric": "Unique_Item_Requests",
            "fallbackFor": "ir51",
        },
        {
            "id": "dr51",
            "reportType": "DR51",
            "metric": "Searches_Regular",
            "filters": {"Access_Method": "Regular"},
        },
        {
            "id": "dr",
            "reportType": "DR",
            "metric": "Searches_Regular",
            "filters": {"Access_Method": "Regular"},
            "fallbackFor": "dr51",
        },
    ],
    "parts": [
        {
            "name": {"en": "Full text interest", "cs": "Plný text"},
            "description": {
                "en": "Total interest for full-text split to Books and Journals",
                "cs": "Celkový zájem o plný text rozdělený na knihy a časopisy",
            },
            "explanation": {
                "en": "Information about journal and book usage from COUNTER 5.1 TR report. "
                "When not available, the TR report from COUNTER 5 is used as a fallback.",
                "cs": "Informace o používání časopisů a knih z COUNTER 5.1 TR reportu. "
                "Pokud není dostupný, použije se TR report z COUNTER 5 jako záložní.",
            },
            "stages": [
                {
                    "id": "TR_B1",
                    "name": {"en": "Books", "cs": "Knihy"},
                    "formula": "tr51_b1 | tr_b1",
                },
                {
                    "id": "TR_J1",
                    "name": {"en": "Journals", "cs": "Časopisy"},
                    "formula": "tr51_j | tr_j",
                },
                {
                    "name": {"en": "Books + Journals", "cs": "Knihy + Časopisy"},
                    "formula": "TR_B1 + TR_J1",
                },
            ],
        },
        {
            "name": {"en": "Search", "cs": "Hledání"},
            "description": {
                "en": "Total interest for searches from COUNTER 5.1 and COUNTER 5 DR reports",
                "cs": "Celkový zájem o vyhledávání z DR reportů pro COUNTER 5.1 a COUNTER 5",
            },
            "explanation": {
                "en": "Information about search usage from COUNTER 5.1 DR report. "
                "When not available, the DR report from COUNTER 5 is used as a fallback.",
                "cs": "Informace o využití vyhledávání z reportu COUNTER 5.1 DR. "
                "Pokud není dostupný, použije se DR report z COUNTER 5 jako záložní.",
            },
            "stages": [{"id": "DR", "name": {"en": "DR", "cs": "DR"}, "formula": "dr51 | dr"}],
        },
        {
            "name": {"en": "Multimedia", "cs": "Multimédia"},
            "description": {
                "en": "Total interest for multimedia from COUNTER 5.1 IR and COUNTER 5 IR_M1 "
                "reports",
                "cs": "Celkový zájem o multimédia z reportů COUNTER 5.1 IR a COUNTER 5 IR_M1",
            },
            "explanation": {
                "en": "Information about multimedia usage from COUNTER 5.1 IR report. "
                "When not available, the IR_M1 report from COUNTER 5 is used as a fallback.",
                "cs": "Informace o využití multimédií z reportu COUNTER 5.1 IR. "
                "Pokud není dostupný, použije se IR_M1 report z COUNTER 5 jako záložní.",
            },
            "stages": [{"id": "IR", "name": {"en": "IR", "cs": "IR"}, "formula": "ir51 | ir_m1"}],
        },
    ],
}

REPORTS = [
    # preview reports
    CEL_REPORT,
    # standard reports
    IPEDS_REPORT_2024,
    IPEDS_REPORT_2023,
    IPEDS_REPORT_2022,
    ARL_REPORT,
    CAUL_REPORT_2024,
    REBIUN_REPORT,
]


def get_report_def_by_name(name):
    for report in REPORTS:
        if report["name"] == name:
            return report
    return None
