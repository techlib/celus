===================
Analytical database
===================

.. warning::
    This feature is currently in beta and is subject to change. If you would like to test it,
    please contact us at ask@celus.net.

For users who want to analyze the data stored in CELUS themselves, CELUS offers an export into
a dedicated analytical database.

The export is updated weekly and contains all usage data from CELUS. Other data, such as information
about harvesting success, configured credentials, etc. is not included.

Technology
==========

The analytical database is built on top of `ClickHouse <https://clickhouse.com/>`_ - a powerful
column-oriented analytical database. This database is run and maintained by CELUS on its own
infrastructure.

Clickhouse is compatible with Microsoft Power BI, Apache Superset, Metabase and many other
analytical tools.

Database structure
==================

Report tables
-------------

Each report from your CELUS instance is stored in a separate table in the database. For example,
if you are harvesting TR, DR and PR reports, you will have three tables in the database with the
names ``TR``, ``DR`` and ``PR``. COUNTER 5.1 reports have their own tables with the ``51`` suffix,
e.g. ``TR51``. Non-COUNTER reports are exported as well.

Each table has the same basic structure, with some report-specific columns. The common columns are
(please note the double underscore in some of the column names):

- ``organization_id`` (``integer``) - internal CELUS id of the organization that the report belongs to
- ``organization__name`` (``string``) - the name of the organization that the report belongs to
- ``platform_id`` (``integer``) - internal CELUS id of the platform that the report belongs to
- ``platform__name`` (``string``) - the name of the platform that the report belongs to
- ``date`` (``date``) - the date of the usage
- ``metric_id`` (``integer``) - internal CELUS id of the metric that the report belongs to
- ``metric__short_name`` (``string``) - the short name of the metric, for COUNTER matches the COUNTER metric name
- ``import_batch_id`` (``integer``) - internal CELUS id of the import batch - this groups together data from one
    import (harvest, manual upload, etc.). One import batch always covers one month. This column is intended
    mainly for internal use.
- ``value`` (``integer``) - the value of the metric - the usage count

If the report type uses titles, the following columns are added for titles (for example the Platform Report
does not use titles, but the Title Report does):

- ``title_id`` (``integer``) - internal CELUS id of the title that the report belongs to
- ``title__name`` (``string``) - the name of the title
- ``title__pub_type`` (``string``) - the publication type of the title
- ``title__isbn`` (``string``) - the ISBN of the title
- ``title__issn`` (``string``) - the ISSN of the title
- ``title__eissn`` (``string``) - the e-ISSN of the title
- ``title__doi`` (``string``) - the DOI of the title


If the report type uses items, the following columns are added for items:
- ``item_id`` (``integer``) - internal CELUS id of the item that the report belongs to
- ``item__name`` (``string``) - the name of the item
- ``item__isbn`` (``string``) - the ISBN of the item
- ``item__issn`` (``string``) - the ISSN of the item
- ``item__eissn`` (``string``) - the e-ISSN of the item
- ``item__doi`` (``string``) - the DOI of the item
- ``item__publication_date`` (``date``) - the publication date of the item

The extra columns/dimensions correspond to the COUNTER specification of that report. For example,
COUNTER 5.1 TR report (stored in ``TR51`` table) has the following extra columns:

- ``data_type`` (``string``) - the data type of the title
- ``access_method`` (``string``) - the access method
- ``platform_in_counter_data`` (``string``) - the platform name as it is found in the COUNTER data (the ``Platform`` column in the COUNTER data)
- ``access_type`` (``string``) - the access type
- ``publisher`` (``string``) - the publisher of the title
- ``yop`` (``string``) - the year of publication


Tag tables
----------

The database also contains tag tables for titles, organizations and platforms.
These tables are used to store the tags for the titles, organizations and platforms and can
be joined with the main report tables to enable filtering, grouping and other analytics
based on tags.

The tables are:

- ``title_tags``
- ``organization_tags``
- ``platform_tags``

The structure of the tag tables is as follows:

- ``{TARGET_ID}`` (``integer``) - internal CELUS id of the tagged target, where `TARGET` is one of (`title`, `organization`, `platform`).
- ``tag_id`` (``integer``) - internal CELUS id of the tag
- ``tag__name`` (``string``) - the name of the tag
- ``tag_class_id`` (``integer``) - internal CELUS id of the tag class that the tag belongs to
- ``tag_class__name`` (``string``) - the name of the tag class

The first column differs by table. In the `title_tags` table, it is ``title_id``,
in the `organization_tags` table, it is ``organization_id``,
and in the `platform_tags` table, it is ``platform_id``.

Example query:

.. code-block:: sql

    SELECT
        tag__name AS Topic,
        SUM(value) AS Unique_Item_Requests
    FROM TR
    INNER JOIN title_tags AS tt ON tt.title_id = TR.title_id
    WHERE (tt.tag_class__name = 'Scopus #2') AND (metric__short_name = 'Unique_Item_Requests')
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 10

The above query uses the internal CELUS tags class `Scopus #2` to assign topics to titles and then
sums up the usage by topic. It prints the top 10 topics by usage defined by the `Unique_Item_Requests`
metric.

The output may look like this:

.. code-block:: text

       ┌─Topic────────────────────────────────────────┬─Unique_Item_Requests─┐
    1. │ Medicine                                     │              4435267 │
    2. │ Social Sciences                              │              3788952 │
    3. │ Biochemistry, Genetics and Molecular Biology │              2205736 │
    4. │ Arts and Humanities                          │              1775827 │
    5. │ Engineering                                  │              1543425 │
    6. │ Environmental Science                        │              1516750 │
    7. │ Agricultural and Biological Sciences         │              1487613 │
    8. │ Chemistry                                    │              1250674 │
    9. │ Business, Management and Accounting          │              1236660 │
    10.│ Psychology                                   │              1082768 │
       └──────────────────────────────────────────────┴──────────────────────┘
