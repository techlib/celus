===================
Admin documentation
===================

This document describes administration of the Celus application. For user documentation
see :doc:`user`.

--------------------
System configuration
--------------------

Defining report types
=====================

Report types are not hard-coded in the Celus codebase, but rather defined in the database.
This allows flexible creation of new report types, especially in case of custom manually uploaded
data. The following steps describe how to create a report type from scratch. You may also use
existing report types as inspiration when creating your own data types.

Creating report type
--------------------

Report types are available in the Django admin interface in the `Logs` > `Report types` section.
To create a new report type, use the `Add report type` button in the upper right corner of the
above mentioned page.

You will be presented with a dialog similar tot he following:

.. image:: images/dja_add_report_type.png

Fill in the basic information about the report type. The `Short name` is used in some drop down
menus in Django admin, etc., so use something short but obvious and easily recognizable. The
`Name` is present in several language versions. You should fill in at least the English version.
The `Name` is used when presenting this report type to the user, so make it clear. The description
can be used to further obviate the meaning and purpose of this report type.

You do not have to fill the `Source`. The `Superseeded by` attribute is used when you have
the same data available from different report types and you want to make sure that only the newest
version is used when computing interest. You would probably leave it empty in most cases, but
it is useful when specifying that `COUNTER 4` reports are superseeded by `COUNTER 5` reports
and interest data should be preferentially calculated from version 5.

When filled in, submit the form by clicking on `Save` in the lower right corner.

.. image:: images/dja_add_report_type_filled.png

Now we have the report type created, but this is only the beginning. We have to tell Celus how
the data for this report should be saved and also presented to the user.


Adding dimensions to the report type
------------------------------------

Depending on the nature of the report type, each data point can have many dimensions, such as
the date, title name, publisher name, name of metric, type of user accessing the e-resource, etc.
In order for Celus to be able to properly import the data from a source file, it has to know about
these dimensions.

Some of the dimensions are implicit and do not have to be specified. These are:

* date
* title
* organization
* platform
* metric

Other dimensions used by that report type, if any, must be added to the report type in the Django
admin.

When adding a new dimension that is not used by any other report type, the dimension has to be
created. You can do so in the Django admin in section `Logs` > `Dimensions` by using the
`Add dimension` button in the upper right corner.

.. image:: images/dja_add_dimension.png

Short name
    the value as it appears in the source files - that is in COUNTER
    report or as column headers in the tables that you upload to Celus.

Name
    localized name of the dimension as it appears to the user.

Type
    ``text`` for most data, but for integer data ``integer`` type is preferential.

Desc
    Description of the dimension. It may be useful for other admins. It is not displayed to the
    user.

You can leave the `Source` field empty.


-----------
Maintenance
-----------

Removing unsuccessful SUSHI downloads
=====================================

Celus tries to be smart about downloading data using the SUSHI protocol. It does not re-fetch
data for platforms and months for which data was already successfully retrieved or for which
there were too many unsuccessful attempts.

This "intelligence" can sometimes become unwanted, for example when a platform releases corrected
data after fixing an error on their side or when access is finally fixed after many unsuccessful
attempts (e.g. when an IP address is finally added to the providers list of allowed addresses).

In these cases the previous downloads (or attempts) block the correct data from being downloaded
and it is necessary to remove them for the system to redownload the data.

This can be accomplished using the Django admin interface.

1. Navigate to the `SUSHI` app and click on the link to `Sushi fetch attempts`. Here all attempts
   to fetch SUSHI data are stored - regardless of their success.

   .. image:: images/dja_sushi_app.png

2. In the list of `Sushi fetch attempts` use the right-side panel to filter the fetch attempts
   to the desired set. The `organization` and `platform` filters are most likely to be useful.

3. Once you have the list of attempts narrowed down to the desired platform and organization
   (and possibly using other criteria), check the checkmark on the left of each of the attempts
   you wish to delete and select the action `Delete selected attempts including related usage data`
   from the dropdown menu at the top of the table. Then press the `Go` button just to the side of
   the dropdown.

   .. image:: images/dja_sushi_attempt_delete.png

Once you have deleted the corresponding SUSHI fetch attempts, the system will automatically
try to re-download the data for the organizations, platforms and dates you have just cleared up.

The download will take place in the next scheduled download window. The specific timing depends
on your system settings.
