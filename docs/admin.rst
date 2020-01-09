===================
Admin documentation
===================

This document describes administration of the Celus application. For user documentation
see :doc:`user`.

-----------
Maintenance
-----------

Removing unsuccessful SUSHI downloads
=====================================

Celus tries to be smart about downloading data using the SUSHI protocol. It does not re-fetch
data for platforms and months for which data was already successfully retreived or for which
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
