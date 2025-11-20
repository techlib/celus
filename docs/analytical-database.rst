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

The extra columns/dimensions correspond to the COUNTER specification of that report. For example,
COUNTER 5.1 TR report (stored in ``TR51`` table) has the following extra columns:

- ``data_type`` (``string``) - the data type of the title
- ``access_method`` (``string``) - the access method of the title
- ``platform_in_counter_data`` (``string``) - whether the platform is in the COUNTER data
- ``access_type`` (``string``) - the access type of the title
- ``publisher`` (``string``) - the publisher of the title
- ``yop`` (``string``) - the year of publication of the title
