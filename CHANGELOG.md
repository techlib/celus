# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.0]

### Added

#### Frontend

- tags were introduced (this feature needs to be explicitly enabled in settings to activate it)
  - the ability to tag titles, platforms and organizations was added
  - the possibility to tag titles loaded from a CSV file was added
  - full support for tag based filtering and summarization was added to reporting
- it is now possible to upload data for multiple organizations from one CSV file
- a simple page listing all organizations was added to consortial installations
- filtering by whole years was added to reporting
- simple chart output was added to reporting
- reporting - show the number of accessible organizations to make it obvious that a filter may be
  necessary
- show accessible stored reports from reporting on the platform list page
- "data coverage" chart series was added to all reports except interest (this feature needs to be
  explicitly enabled in settings to activate it)
- data coverage tab was added to the platform detail page (this feature needs to be explicitly
  enabled in settings to activate it)
- show a link to the source file in the list of manually uploaded data
- help widget (sidebar) was added to the dashboard and tag list pages
- reporting - users can now manually delete exports
- reporting - exports are now automatically deleted after 7 days
- charts which do not have a metric on one of the axes now display a metric selector to choose
  which metric will be used (previously all interest defining metrics were used)
- changelog view was added to the UI (linked from the version number in the footer)
- a list of releases with their main changes was added together with alerts for new releases
- the manual upload of data was reworked to
  - separate import of COUNTER and non-COUNTER reports
  - new experimental feature to import data non-COUNTER data from a raw format obtained from the
    publisher was added
- the ability to import non-COUNTER data for multiple organizations from one CSV file was added
- it is now possible to create system-wide platforms using the UI (for consortial managers only)
- 'Select all' button was added to the SUSHI credentials overview dialog to allow selecting of all
  available slots at once


#### Backend

- a script was added for finding and removing import batches without data and for resolving
  conflicting import batches
- CLI script for tagging titles using the (publicly available) Scopus title list was added
- information about supported report types was added to the platform information from the
  knowledgebase



### Changes

#### Frontend

- the "Extra attributes" section in SUSHI credentials dialog was reworked to better handle specifics
  of individual COUNTER versions
- most forms were modified to support submitting with the Enter key
- reporting - when no data were found, display an explicit message instead of an empty table
- reporting - the default report type was changed to COUNTER 5 TR instead of interest
- "Ad hoc report" menu entry was renamed to "Create report"
- tooltips are disabled in the platform overlap widget when the table is too large to avoid
  performance issues
- images used in the `FirstSushiHelpWidget` were updated to match the current UI

#### Backend

- COUNTER 5 report processing was made stricter to avoid errors on publisher side
- the `nigiri` library was moved to a separate repository
- if no report view is defined for a report type, a proxy view is returned to allow for some data
  display
- charts can be marked as `default`. Such charts will be shown for proxy report views (see above)
- a field listing duplicates of a platform record was added to enable storage of this information
- a much faster algorithm for computing platform overlap was introduced
- the CLI script for importing of SUSHI credentials was extended to allow for using SUSHI URL from
  the knowledgebase rather than from the file itself
- missing leading zeros are automatically added to ISSNs given as plain number
- performance of the `raw-data` API endpoint was optimized
- allow syncing of report type dimensions with the knowledgebase if the report type is not yet
  used in any usage data
- unique_together database constraints were added to the `ReportInterestMetric` model


### Fixed

#### Frontend

- handle `unknown` state in the data presence information in harvesting dialog
- prevent the "Basic tour" to be activated on pages where the necessary elements are not present
- it is no longer possible to have no organization selected in the top menu bar
- null values are remapped to "- empty -" in charts to prevent them from being omited
- the header of the introductory "wizard" (shown where no data are yet present for the current user)
  was prevented from overflowing to the text on small screens
- sorting was disabled for columns which do not have natural sorting order (actions, etc.) in
  several tables (annotation, manual data uploads, interest overview, etc.)
- incorrect display of "success" icon instead of "empty data" icon for some downloads was fixed
- SUSHI credentials verification is checked immediately after the test dialog is closed to avoid
  the need to reload the page
- double loading of data for the Dashboard top-titles widgets was fixed

#### Backend

- the number of queries in the impersonation API was optimized
- detection of CSV encoding and dialect (used delimiter, etc.) was improved



## [4.7.0]

### Added

#### Backend

- add missing reader for IR_M1 reports in table form
- update CLI script `check_report_type_dimensions` to also create missing COUNTER reports


### Changes

#### Backend

- allow deleting of user accounts from Django admin by allowing deleting of impersonation logs
- use constant memory mode when creating Excel exports in reporting


### Fixed

#### Frontend

- do not try to translate '-- blank --' id into title name
- show import errors in dashboard SUSHI overview widget
- fix sorting by title attributes (such as ISSN, ISBN, etc.) in reporting
- fix locking of SUSHI credentials by adding the missing `can_lock` attribute to the API endpoint
- fix situation where it was not possible to leave impersonation of a user without an assigned
  organization
- fix regression in sorting by explicit dimensions in reporting
- reset pagination when report is changed in reporting

#### Backend

- fix celery task name for cleaning obsolete platform-title links
- fix incorrect behavior of harvest planing after credentials are verified
- fix computation of data-presence by using ImportBatch presence rather than FetchAttempt status
- properly store owner attributes when saving a new report
- skip custom platforms from other organizations when importing SUSHI credentials using CLI


## [4.6.2]

### Fixed

#### Frontend

- fix regression which caused automatic harvesting of new SUSHI credentials to be off by default
- fix styling inconsistencies of platform and title detail pages if user got there directly without
  visiting a different page before

#### Backend

- fix planning of new intentions for last month not respecting already harvested data
- when reporting SUSHI status from the API, prefer fetch intentions with import_batch over newer
  ones without it.
- the code for merging titles was sped up to avoid "timeouts" in celery jobs


## [4.6.1]

### Fixed

#### Frontend

- visiting a page of a title with ISBN caused the user to be logged out due to an error when
  fetching cover image data from Google. The cover image functionality was removed to fix the issue.



## [4.6.0]

### Added

#### Frontend

- SUSHI credentials are newly marked as verified on first successful use. Automatic harvesting is
  only enabled for verified credentials.
- user role "consortial user" was added - it has the same access level as normal user but can see
  data for all consortium members without them being explicitly assigned
- possibility to delete all platform usage data from the platform detail page was added
- a new tab 'Data management' was added to the platform detail page
- more options were added to the data range selection widget

#### Backend

- support was added for retrieving report type information from knowledgebase
- a CLI script was added to move credentials with all the associated data into a new custom platform


### Changes

#### Frontend

- raw data export functionality was moved to the 'Data management' tab
- SUSHI credentials export now respects the selected organization and platform
- the SUSHI related dashboard widgets are no longer shown to non-admin user
- the default displayed data period was changed from 'all' to 'current + last two whole years'

#### Backend

- retries of failed SUSHI harvesting were modified:
  - only automatically created harvest are retried
  - retries are done only for credentials which were verified (successfully used for harvesting)
  - retries are done for all non-breaking fetch attempt states
- partial data downloads are marked as containing no data until imported at the end of the retry
  period
- validity of invitations and password reset tokens was extended from 3 to 10 days
- the user detail API endpoint was extended to include the `is_staff` attribute
- automatically created harvests are planned a few days before month start, not whole month

### Fixed

#### Frontend

- the platform detail page of a platform not connected to the current organization no longer
  displays error messages and contains more information about the platform
- fix missing metric (and potentially other objects) names in exports from the reporting module
- all import batches are shown in the delete confirmation dialog, not just the first 10

#### Backend

- user preferred language is always explicitly selected on the backend to ensure correct data
  localization
- marking SUSHI credentials as broken no longer lead to duplication of stored extra parameters
- access rights to the SUSHI credentials API endpoint was fixed to only include admin users
- the django admin list interface for import batches now shows `date` instead of `user`


## [4.5.0]

### Added

#### Frontend

- possibility to impersonate another user was added to the consortium administrator users

#### Backend

- periodic housekeeping jobs were added to remove obsolete platform-title links, merge matching
  titles and synchronize platforms with knowledgebase.

### Changes

#### Frontend

- the v-charts library was replaced by vue-echarts (the former was not maintained anymore)
- information about interest definition was moved to the `Content` section of the menu
- when displaying raw harvested data, additional records (such as interest or materialized data) are
  not shown anymore

#### Backend

- empty data in SUSHI response without a corresponding exception are treated as having exception 3030
- Celus newly tries to re-harvest data from failed attempts (regardless of the error) if the
  credentials were successfully used to harvest some data lately
- reporting speed was optimized in case when non-zero rows are not requested, most significantly
  those with titles in rows
- cli commands for reimport and subsequent analysis were extended and improved

### Fixed

#### Backend

- an error in title merging caused by incorrect order of update and delete was fixed

## [4.4.5]

### Changes

#### Backend

- lowercase 'x' as last character of ISSN is replaced by upper case 'X'
- `hcube` was update to speed up deleting of data from Clickhouse in newer versions

### Fixed

#### Backend

- synchronization with knowledgebase unassignes `counter_registry_id` from platforms which no longer
  use it

## [4.4.4]

### Added

#### Backend

- Celus newly stores checksums of files from SUSHI or manually uploaded and checks them on import
  to prevent against potential data corruption or attacks

### Fixed

#### Backend

- merging of titles was fixed not to merge titles with the same name but without any common ID
- a cli script for merging title out-of-band was added

## [4.4.3]

### Fixed

#### Frontend

- reporting - export of reports split by year and month was fixed
- users logging in by EduID are no longer warned about missing email validation

#### Backend

- data import was sped up by factor of about 5 with about 2x memory reduction

## [4.4.2]

### Added

#### Frontend

- the SUSHI credentials edit dialog autofills the URL based on existing credentials for other
  organizations

#### Backend

- cli command for assigning reports to platforms was added
- cli command for comparison of the current database with an older version was added to help in
  finding differences after data reimport

### Changes

#### Frontend

- more detailed fields in SUSHI credentials edit dialog are disabled until the platform is selected

#### Backend

- cleaner method for recaching aggregate queries in AccessLog table was implemented
- detection of last interest change was optimized by remembering the last change time
- django admin was extended to support reimport of manual data uploads
- email about preflight errors is sent to admins asynchronously
- the `reimport_data` cli command was improved

### Fixed

#### Frontend

- placeholder text for data upload was made more generic to reflect really supported formats
- when showing status of harvest, full data are preferred over partial data
- all fetch intentions are now shown when the mode is set to 'All', not just latest ones
- when validating the SUSHI URL, check `/reports/` not `/report/`

#### Backend

- Gitlab CI config for coverage was fixed

## [4.4.1]

### Added

#### Frontend

- pagination was added to the platform page to show the number of platforms present

#### Backend

- ISSN without hyphen (just digits) support added

### Fixed

#### Frontend

- filtering of titles by eISSN was fixed

#### Backend

- regression of pycounter not being properly updated in 4.4.0 was fixed
- superfluous import batches created for attempts with 3030 error code when migrating from very
  old Celus versions were removed

## [4.4.0]

### Added

#### Frontend

- progressbar was added to the manual data upload page

### Changes

#### Frontend

- top menubar now hides organization and date range selectors on pages where it is not used

#### Backend

- SUSHI exceptions 3050, 3060, 3061 and 3062 do not cause import error if data is also present in the response
- import of multi-month files was sped up considerably
- reimport script was improved with more verbose output and other changes
- obsolete code related to `Dimension.type` was removed
- several unused fields were removed from `ReportTypeSerializer`
- API for manual data uploads was optimized for speed and data size
- API for finding existing data for new harvests was sped up
- SUSHI APIKey maximum size was increased to 400 to support some strange platforms

### Fixed

#### Frontend

- filtering of titles by eISSN was fixed

#### Backend

- several small fixes and optimizations in Django admin
- pycounter was updated to fix error in date handling in specific situations
  (when the date range in header differs from the actual data)

## [4.3.3]

### Added

#### Frontend

- export function was added to the SUSHI management page

## [4.3.2]

### Fixed

#### Backend

- merging of titles between incoming data and database was fixed for cases where
  only name and proprietary IDs are available. Lowercasing of İ was tweaked.

## [4.3.1]

### Added

#### Frontend

- preflight data were extended to include:
  - information if a metric was previously used for the selected report type
  - comparison of imported data with average of previous year and the same month in previous year

#### Backend

- Django admin for Report Types was extended to include the list of interest defining metrics as an
  inline

### Changes

#### Frontend

- reporting improvements:
  - make visibility level tooltip part of the selector
  - when starting new report, select something by default to make it 'runnable' immediately
  - add list of organizations to metadata if organization is not in rows, columns, split_by or
    filtered

#### Backend

- Celus ignores the `Severity` attribute in C5 SUSHI (marked as obsolete in CoP 5.0.2)

### Fixed

#### Frontend

- SUSHI status dashboard and monthly overview were fixed to correctly display waiting harvests
  (COUNTER exception 3031)
- regression in formatting of log data in expander of list of attempts was fixed

#### Backend

- error in harvesting when dealing with in-memory files was fixed
- ignoring `Severity` (see above) fixes errors when importing data with exception 1011 which had
  incorrect severity

## [4.3.0]

### Added

#### Frontend

- new view of Interest definition was added (available under Administration/Interests)
- progress bar was added to reporting when list of individual parts is loaded
- manual data uploading was improved
  - it is now possible to return to data upload from the 'preflight' step
  - error reporting was improved to handle some specific cases better
  - progress indicator was improved

### Changes

#### Frontend

- report types are now alphabetically sorted in reporting and use the autocomplete widget

### Fixed

#### Frontend

- *SUSHI harvesting dashboard widget* and *SUSHI status page* were fixed not to include incorrect
  `Waiting` entries for reports successfully harvested

#### Backend

- when downloading large files, make sure they are really flushed to the disk before trying to parse
  them
- race condition in locking of manual uploads was fixed - fixes manual data sometimes not being
  imported and getting stuck as `importing`.

## [4.2.0]

### Added

#### Frontend

- reporting was extended to include
  - splitting reports by a specified attribute into several files/sheets
  - export to Excel format
  - metadata about the export in a separate file/sheet
  - export now has name taken from the report which created it
- show data extracted from SUSHI header (organization name and 'Created-By') together with each download
- harvest list UI was improved with a platform filter, info about currently processed downloads, etc.
- when uploading data manually more heuristics about used metrics are presented
- processing of manually uploaded files was optimized for speed

#### Backend

- titles newly store proprietary IDs and URIs extracted from COUNTER data
- the Platform dimension is newly extracted from COUNTER reports and stored in the database
- extract data from SUSHI header and store them with harvested data (data reimport is required to
  fully take advantage)
- Celus version was added to the prometheus exporter
- cli script was to check if report type dimensions match reader classes

### Changes

#### Frontend

- manual uploads are by default sorted by date

#### Backend

- processing of manually uploaded data was moved to the backend process. This fixes timeout issues
  when processing large files
- it is now possible to disable automatic creation of metrics on a per-installation basis
- it is now possible to limit the set of metrics allowed for a report
- the way how incoming titles are compared with the database has been changed to merge titles which
  only differ in some identifiers being empty (data reimport is required to fully take advantage)
- normalization is newly applied to ISBNs
- normalization and cleanup was added for ISSNs and ISBNs which ensures length restrictions
- the django-error-report module was removed

### Fixed

#### Frontend

- deleting of data for one month for specific credentials deletes all related downloads - not only
  the last successful one.

#### Backend

- synchronization with knowledgebase was fixed to prevent creation of duplicated records
- flush file to disk after it was downloaded - may fix situation when a large file is downloaded
  by the sushi celery worker and it appears as incomplete in the import worker

## [4.1.1]

### Added

#### Frontend

- The annotations list table now shows the dates and text of the annotations in an expansion panel

### Changes

#### Frontend

- Manual data uploads are sorted by the upload date by default (not randomly ordered)

### Fixed

#### Frontend

- It is now possible to reharvest data for months where the data was empty
- Very slow parsing of some manual data uploads caused by slow date parser was fixed

## [4.1.0]

### Added

#### Frontend

- a new page for management of annotations was added
- it is now possible to delete manually uploaded data from the "SUSHI overview" view
- deleting of data was improved to show more details about deleted data
- when manually uploading data, conflicting existing data are detected and presented to the user
  with the option of deleting them

#### Backend

- encoding of manually uploaded files is automatically detected
- new model `FetchIntentionQueue` was introduced to bind together follow-up `FetchIntentions`
  created after SUSHI error 3031 or 3030

### Changes

#### Frontend

- the SUSHI management page now uses the whole page even on large screens
- the "Save" button in SUSHI editing dialog is disabled when save is in progress to prevent
  double-clicking related issues
- the SUSHI overview dialog always shows one more year than there are existing data for

#### Backend

- intervals of re-checking not-yet-available recent data by SUSHI (exception 3031) were changed
  from 1,2,4,8,16,32 days to 1,2,4,8,8,8,8 days (for 3030 the intervals remain at 1,2,4,8,16,32 days)
- automatic harvesting ending in SUSHI error 3040 (partial data) newly leads to retries similar to
  3031
- several required Python packages were updated - most notably Celery
- feature: added brin index to ImportBatch.date
- performance of the API endpoint for retrieving report-views was improved
- a `timestamp` field was added to the FetchIntention model
- a `date` field was added to the ImportBatch model
- unused `system_created` field from ImportBatch was removed
- detection of "broken credentials" was extended to cover more SUSHI statuses
- the `create_organization_api_keys` CLI management command was improved
- an empty ImportBatch object is now created after the last attempt in a queue of attempts with
  the 3030 or 3040 SUSHI errors
- manual uploads model was modify to use several ImportBatches - one for each month of data
- when the connected knowledgebase source no longer exports a platform, its knowledgebase related
  data are cleared up
- SUSHI exceptions of type `Info` are now correctly processed and stored

### Fixed

#### Frontend

- no longer relevant ongoing requests to the backend are cancelled on the Harvest and SUSHI
  overview pages
- duplicated FetchIntentions are now properly handled on the SUSHI overview page (no more cases
  where successful attempts are also marked as scheduled for future harvesting)
- the "Top 10" widgets on the dashboard now properly react to change of the displayed time range
- menu is automatically expanded when the user navigates to a child page without using the menu
  (for example to the SUSHI management page from the dashboard widget)
- Overlap of text and widget in the test harvesting dialog was fixed

#### Backend

- data migration fixing several problematic ImportBatch states was added
- code to determine when interest should be recalculated when interest definition changes was
  optimized
- skip index for `import_batch_id` was added to Clickhouse to improve deletion speed
- fix cases where celery did not properly close open sushi-attempt related files
- gracefully handle situations when `Item_ID` is null in SUSHI C5 reports

## [4.0.1]

### Added

#### Frontend

- IP addresses of Celus harvesters are no longer hardcoded in the code, but rather configured in
  Django settings.

#### Backend

- a slower but more memory efficient method of synchronization between Django database and
  Clickhouse was added
- more information (username, etc.) was added to the error message sent to admins when an error
  occurs during manual data upload

### Fixed

#### Frontend

- activation and deactivation of shown interest types on platform page was fixed (regression
  introduced in 4.0.0)
- active reports are properly synchronized when credentials are edited after being selected for
  harvesting
- fixed - manual upload of incorrect data always ended up displaying message about UTF-8 encoding
  (regression introduced in 4.0.0)

## [4.0.0]

### Added

#### Frontend

- when harvesting data using SUSHI, overview of existing data is shown and months with existing
  data are automatically skipped
- it is now possible to delete SUSHI data from the "Overview" dialog in SUSHI management
- months with already planned harvesting are marked with a badge in the "Overview" dialog
- rows with zero usage are removed from advanced reporting output by default, it is possible to
  configure reports to add them
- upload of another file is offered in the last step of manual upload
- outstanding HTTP requests to the backend are cancelled when user switches pages, thus improving
  frontend responsiveness (especially when quickly leaving dashboard page after initial load)

#### Backend

- support for synchronization of log data into Clickhouse was added
- management command was added to remove titles without any associated usage data
- management command was added to remove orphaned files from sushi harvesting
- management command was added for comparing the main database content with Clickhouse

### Changes

#### Frontend

- menu sections for reporting and overlap analysis were renamed based on user feedback
- selection of organization and platforms when adding new SUSHI credentials was optimized for space
- downloads resulting in SUSHI exception 3030 (no usage) are now shown with the "empty data" icon
  rather than the "error" icon
- when switching between tabs on the platform detail page, the chart data get automatically
  reloaded to make sure they are up to date
- more informative error messages are shown when incorrect encoding it used for manually uploaded
  CSV files
- javascript libraries were updated

#### Backend

- older data harvested using SUSHI for a period longer than one month were split to individual
  months for easier management (deleting and re-harvesting)
- CSV "sniffing" size was increased to improve accuracy of format dialect detection
- python libraries were updated

### Fixed

#### Frontend

- when adding new platform, warning of potential clash with existing platforms now works correctly
- remove background request for unused chart data on the dashboard page
- manual upload of data is no longer permitted if all organizations are selected

#### Backend

- rare database constraint error when creating new title records during data import was fixed
- properly handle exceptions coming from the pycounter library when importing C4 data
- check for correct site.domain configuration were added when sending user invitations
- disabling of cachalot in test settings was fixed
- ensure than only enabled languages are available for user selection in Django admin
- export of empty data no longer crashes with "KeyError"

## [3.2.5]

### Fixed

#### Frontend

- different method of filtering fetch-intentions for particular credentials was introduced.
  It fixes cases where more than one set of credentials was used for the same organization and
  platform which resulted in records being mixed together
- a regression in dashboard SUSHI chart was fixed to include waiting harvests (broken in 3.2.4)

#### Backend

- a regression was fixed in API providing fetch-intention data - it had a slow response and data
  were incomplete (broken in 3.2.4)

### Added

#### Backend

- support for using HTTP proxy for SUSHI requests was added to nigiri for C5

## [3.2.4]

### Fixed

#### Frontend

- test for `/report/` as part of SUSHI URL was fixed to prevent false positives like
  `https::/report.foo.bar/`
- platform `short_name` is used if `name` is blank to prevent showing platforms with blank name
- tooltip for icons in SUSHI status was fixed

### Changes

#### Backend

- the API to get status of "fetch attempts" was removed in favor of "fetch intentions" (is related
  to the above fix of tooltips)
- server log messages about user identity were changed from `error` to `debug` importance

## [3.2.3]

### Fixed

#### Backend

- invitation links were fixed after switch to dj-rest-auth broke their functionality
- fix scheduling of FetchIntentions added by migration for older FetchAttempts - fixes overload
  of celery by endless stream of tasks without effect

### Changes

#### Backend

- expiration was added to all celery tasks planned by celerybeat to avoid accumulation of tasks in
  queue if celery does not handle them quickly enough
- harvest API endpoint was optimized for speed

## [3.2.2]

### Fixed

#### Frontend

- clicking on individual downloads on the monthly overview page displayed details for incorrect
  download

## [3.2.1]

### Added

#### Backend

- API keys are now automatically exported to knowledgebase server

### Changes

#### Backend

- Django was upgraded from the 3.1 to the 3.2 branch

## [3.2.0]

### Added

#### Frontend

- all COUNTER reports are offered for manual upload - regardless if they define interest or not

#### Backend

- it is now possible to export SUSHI credentials from the Django admin
- API key based authentication for specific API endpoints was implemented
- API endpoint for access to "raw" data for individual reports was added with API key access

### Changes

#### Backend

- speed up loading of list of manual uploads by identifying import batches with their IDs only
- the API and related code for SUSHI harvesting was cleaned up by removing unused/obsolete code
- internal working of fetch attempt state was changed from several booleans into a progression of
  specific states
- replace django-rest-auth with dj-reset-auth
- manual data upload model was added into Django admin
- do not cache queries with empty result - removes delay between first data is harvested and
  displayed for new users
- list of platforms for an organization was made accessible using API key authentication
- deployment of requirements using requirements files for pip was dropped in favor of poetry

### Fixed

#### Frontend

- the registration link did not properly work on first load

#### Backend

- the celery task for updating approximate number of records for a report type was not correctly
  scheduled
- do not respond by server error when user creates a platform with `short_name` that is already used
- parsing of exceptions from COUNTER 5 table format was made more robust
- code to derive SUSHI exception severity from a response was made more robust

## [3.1.1]

### Changes

#### Frontend

- some less important columns are hidded from the SUSHI management page on smaller screens
- year selection for harvesting of SUSHI data was limited to years after 2010

### Fixed

#### Frontend

- slow loading of SUSHI fetch attempt data was fixed by using server-side pagination

#### Backend

- users with organization admin privileges are no longer denied access when manually importing data
- automatic deduction of title type using ISBN and ISSN was fixed to work in more cases,
  most notably for manually uploaded data
- performance of several API endpoints was fixed by optimizing the number of database queries
- data for SUSHI overview are correctly serialized even if harvested year is lower than 2000
- state of SUSHI fetch attempts marked as crashed because they were already imported was fixed
  (it no longer shows as crashed)

## [3.1.0]

### Added

#### Frontend

- buttons for immediate harvesting and cancellation of harvests planned for later were added
- partial-data status was added to `FetchAttempt` information
- Celus frontend now checks the version of the backend and forces refresh if the versions do not
  match

#### Backend

- support for IR_M1 report was added
- ability to trigger postponed re-imports via celery was added to Django admin

### Changes

#### Frontend

- harvest list view was extended and improved
- the 'Harvest selected' button on 'SUSH management page' was changed for better visibility
- all views were updated to stretch to the whole available space where the UI benefits from it
- empty harvests were hidden from harvest views
- obsolete `Attempt overview` view was removed from the UI
- the name of the organization created by the user after registration is limited to 100 characters
- user-created platforms and report types are marked with a special badge for easy recognition
- if a status filter is active on the sushi monthly overview page, it is automatically disabled
  when month is changed if there are no records with this status for the newly selected month

#### Backend

- Celery task locking was switched from Redis-based locks to database locks where appropriate
- extra whitespace is stripped from string values imported from C5 tabular format
- obsolete backend code related to the `Attempt overview` view was removed
- database unique constrains for `short_name` and `source` were reworked
- a Django setting was added to selectively allow manual upload of COUNTER data only
- speed and number of queries for listing harvest intentions was optimized

### Fixed

#### Frontend

- when changing selected organization, the list of available platforms on the `manual upload` page
  is automatically refreshed
- date related filters were not copied when a report was copied
- 'untried' fetch-intention status was fixed to actually work
- sushi monthly overview no longer prematurely hides the loading progress bar which was confusing

#### Backend

- harvests planning for the current month was fixed

## [3.0.3]

### Fixed

#### Frontend

- fixed regression in SUSHI credentials edit dialog which caused selected report types to
  sometimes appear empty when viewing the first set of credentials
- Interest is not longer missing from the list of report types in the Reporting module
- position of 'Add annotation' and 'Add platform' buttons on the platform list page was adjusted
  for full visibility
- SUSHI harvesting progress dialog newly shows activity even between individual harvests
- integer overflow error was fixed in code determining how long to wait for new data when
  showing harvest progress
- use organization and platform `short_name` if full name is not available in the harvest list view

#### Backend

- memory consumption of importing data from a very large JSON files was optimized by processing
  files in chunks
- translation admin is properly used for all models using database translations
- uniform report type ordering is used in the SUSHI data view


## [3.0.2]

### Fixed

#### Backend

- speed of resolving possible dimension values in report editor was dramatically improved in some
  cases - most notably when creating reports with titles in rows
- new materialized reports will not be immediately used until they are populated with data. This
  prevents intermittent loss of data in charts when new materialized reports are introduced

## [3.0.1]

### Added

#### Backend

- removal of whole harvests in Django admin was implemented

### Changes

#### Backend

- numerical dimensions (only YOP in TR for COUNTER) were migrated to text in order to simplify
  code and database schema

### Fixed

#### Frontend

- ordering reports by primary dimension was fixed
- loading of date filter in report editor was fixed
- filtering by YOP is now possible in reporting due to the above mentioned change of dimension type
- adding filter for organization did not work properly when specific organization was selected
  globally

## [3.0.0]

### Added

#### Frontend

- advanced reporting module - allows creation of custom reports by selecting desired output
  rows and columns with possible filtering.
- per credentials overview of harvested data was added. It shows harvests by years and allows
  quick reharvesting of missing data.
- it is now possible to create and edit platforms in the UI

#### Backend

- support for reading COUNTER 5 reports in table format was added
- management command for detection of conflicting import batches was added
- management command for removal of empty fetch attempts was added
- management command for removal of obsolete platform-title links

### Changes

#### Frontend

- the left sidebar was reworked using collapsible entries to save space
- harvest overview was extended with more information
- it is now possible to only download data for one month using the "Save and test" button in
  the SUSHI credentials edit dialog
- when using the "Harvest selected" button for manual harvesting, the harvest is split into
  separate downloads for individual months
- crashed data imports are now marked as a distinct state with its own icon

#### Backend

- harvest scheduling was switched to the new system by default. This means that future harvests
  are planned automatically in advance and past data have to be explicitly harvested by the user.
- HTTP authentication information was removed from COUNTER 5 SUSHI credentials as it is not used
  there
- better handling of SUSHI exceptions 1030, 2010 and 3060 was added. Errors 1030 and 2010 causes
  credentials to be marked as broken
- scheduler admin was improved

### Fixed

#### Frontend

- fix reporting of used metrics for interest related charts when materialized reports are used
  in the background
- harvest view was optimized for speed
- error when clearing search text on SUSHI management page using the "x" icon was fixed
- error which caused reports types sometimes not appearing when editing SUSHI credentials was fixed

#### Backend

- update Cachalot to a newer version containing our fix for temporary disabling of Cachalot
  - fixes memory problems when exporting large amounts of raw data
- fix for error causing users to be disconnected from their organizations upon login of other user
  when live ERMS sync was used was ported from 1.0.x
- database constraints enforcing uniqueness in combination with `source` were fixed to properly
  handle `source` being null.
- scheduling of harvests for new months was fixed to wait until month end before attempting
  to harvest data for that month
- reevaluation of queries by recache was fixed - it did not occur because of wrong celery config

## [2.8.3]

### Fixed

#### Frontend

- ordering of platforms in several menus was fixed
- SUSHI status dashboard widget size when loading data was fixed (it was too high and thus caused
  "jumping" of the content during data loading)
- empty dates in harvest overview table no longer cause the table to get stuck

#### Backend

- manual data CSV files containing BOM (Byte Order Mark) are properly parsed

## [2.8.2]

### Fixed

#### Backend

- computation of interest in presence of materialized reports has been fixed (it resulted in
  erroneous 3x increase in interest in some cases)

## [2.8.1]

### Fixed

#### Frontend

- harvest detail view stopped refreshing when some download was rescheduled for later
- count of finished downloads in a harvest was inconsistent between the harvest table and the detail
  view.

## [2.8.0]

### Added

#### Frontend

- more transparent form validation was added to the SUSHI edit dialog
- new view for individual harvest progress was added and used for SUSHI testing dialog and harvest
  detail view
- SUSHI server URL is filled in automatically when data is available from knowledge-base
- highlight supported report types when corresponding data is available from knowledge-base
- icons in statistics row on monthly overview page are clickable and allow filtering of table rows

### Changes

#### Frontend

- the SUSHI edit dialog was overhauled for clarity and simplicity

#### Backend

- detection of currently running harvests was optimized for speed (by using explicit attributes
  rather then transaction state)
- Celery was updated to new major version 5.0 (5.0.2)

### Fixed

#### Frontend

- it is now possible to add annotations from platform list and platform detail pages even when
  no existing annotations are present

## [2.7.2]

### Changes

#### Frontend

- favicon was replaced with new logo
- 'Portfolio optimization' tab on 'Platform overlap analysis' page tells user to select at least one publication type if none was selected
- List of platforms was reduced to only those with usage data or SUSHI credentials even when all
  organizations are selected to make it consistent with single-organization view

#### Backend

- Django updated to the 3.1 branch (3.1.3)

### Fixes

#### Frontend

- text on 'Portfolio optimization' tab on 'Platform overlap analysis' page was replaced by the correct one
- fetch intentions with broken credentials are not properly identified and described in harvest detail dialog

#### Backend

- add more robust detection of Exception codes from COUNTER 5 SUSHI data - ignores even more common mistakes providers make.
- broken credentials are properly skipped when processing scheduled harvests

## [2.7.1]

### Fixes

#### Backend

- add more robust detection of Exception codes from COUNTER 4 SUSHI data (ignore namespaces which many providers mess up, etc.)
- fix detection of broken credentials based on error codes extracted from SUSHI headers

## [2.7.0]

### Added

#### Frontend

- two new views for platform overlap analysis were added
  - "portfolio optimization" which finds the platforms most important for covering user interest
  - "cancellation simulation" which allows interactive simulation of the impact of removing a platform or platforms
- new dashboard card with SUSHI overview was added showing the number of credentials and their status
- password change dialog was added to the user page

#### Backend

- new mechanism for planning SUSHI harvesting introduced in 2.6.0 was improved and is used for manual data harvesting. Automatic harvesting will switch to the new code in release 2.8.0
- support for COUNTER 5 IR and COUNTER 4 MR1 reports was added

### Changes

#### Frontend

- changing organization in the toolbar does not lead to reload and redirect to dashboard. The current page updates automatically instead.
- references to CzechELib on the user page were replaced by more generic wording
- broken credentials are now shown separately in the SUSHI status dashboard chart
- new Celus logo was introduced

### Fixed

#### Backend

- reading of PR reports was fixed to use fields specific to the PR report

## [2.6.1]

### Fixes

#### Frontend

- fix wrong sorting of platforms in some browsers on platform overlap page

## [2.6.0]

### Added

#### Frontend

- view for platform overlap with all other platforms was added including interest overlap

#### Backend

- new mechanism for planning SUSHI harvesting was added. It will replace the currently used code
  in release 2.7.0

### Changes

#### Frontend

- manual harvesting uses the new code for SUSHI harvesting
- platform-platform overlap view was polished and improved

#### Backend

- API urls for user registration were completely disabled for installations without user registration
- deleting DataSource no longer deletes objects created from that source

### Fixed

#### Frontend

- logarithmic scale for platform interest chart was fixed

## [2.5.4]

### Changes

#### Backend

- recache re-evaluation is done periodically by a celerybeat task rather than each object planning
  its renewal separately. This should get rid of multiplication of celery tasks as observed
  in some installations.

## [2.5.3]

### Fixed

#### Backend

- error causing data sometimes not being downloaded from platforms with rate limiting was fixed

## [2.5.2]

### Fixed

#### Frontend

- error introduced in **2.5.0** leading to charts not respecting selected date range was fixed

## [2.5.1]

### Changes

#### Backend

- scheduling of recache renewals was changed to get around multiplication of renewal tasks observed
  in production

## [2.5.0]

### Added

#### Frontend

- "broken" credentials are reported to the user using a warning icon in the side menu
- support for identifying and handling "broken" credentials on the SUSHI management page was added
- subtitle was added to charts with date on X-axis to distinguish between normal and year-to-year view
- Platform overlap table was added as an overall view of how many titles are shared amongst platforms

#### Backend

- specific errors during SUSHI harvesting result in credentials being marked as "broken". Such credentials are not
  automatically harvested and have to be fixed by the user.

### Changes

#### Frontend

- legend icons in charts were changed to make it obvious they can be selected and unselected
- manual harvesting dialog title and text was fixed (it referred to testing)

### Fixes

#### Frontend

- SUSHI credentials edit dialog checks for credentials on the same platform with the same name even when editing
  existing credentials
- display of the SUSHI management page on large screens was fixed

#### Backend

- harvesting of COUNTER 4 JR1GOA reports was fixed

## [2.4.1]

### Changes

#### Frontend

- year-to-year comparison chart was reworked to reduce the number of colors and make it more
  readable
- title names are shortened in cards on dashboard page

## [2.4.0]

### Added

#### Frontend

- new dashboard panel with SUSHI status chart for last two month replaces the "Interest histogram" panel
- new menu section "Analytics" was added with the "Overlap analysis" page showing titles available from more than one
  platform

#### Backend

- it is possible to mark report types as default for interest calculation. Such reports are automatically added
  as interest reports to newly created platforms

### Changes

#### Frontend

- platform selector in SUSHI credentials dialog is now filterable

### Fixes

#### Frontend

- SUSHI intro wizard displayed when no SUSHI credentials are defined correctly disappears when credentials are added
  outside of the wizard

#### Backend

- processing of COUNTER 4 BR3, JR1a and JR1GOA reports was fixed

## [2.3.1]

### Added

#### Backend

- preliminary support for centralized source of data for Celus (Celus brain) was added

### Fixes

#### Frontend

- it was not possible to save credentials with title after running the test without changing
  the title

#### Backend

- properly report attempts to fetch SUSHI data that span more than one month in the monthly overview (SUSHI status)

## [2.3.0]

### Added

#### Frontend

- show Celus version number in the side-panel
- add a toggle to show status of credentials that are not automatically harvested in the
  SUSHI status view

### Changes

#### Frontend

- attempts to fetch SUSHI resulting in error 3030 are not longer shown as unsuccessful
- confirmation dialog is shown when deleting SUSHI credentials
- unfinished months are no longer available when selecting months for manual SUSHI harvesting

#### Backend

- SUSHI responses with non-200 no longer automatically lead to a "non-sushi" error code - valid
  SUSHI error codes are extracted even from these replies.

### Fixes

#### Frontend

- error was fixed that caused changes in selected report types not being reflected in an
  immediately started test
- the wizard about SUSHI was updated to reflect the new wording introduced in 2.2.0 in the
  SUSHI credentials edit dialog

#### Backend

- language not active for specific Celus installation cannot become users default language
- when synchronizing users with ERMS, properly disconnect organizations when user is no longer
  associated with them
- recache did not properly check for Django version when looking for cached data

## [2.2.1]

### Fixes

#### Backend

- Error in SUSHI download retrial was fixed

## [2.2.0]

### Added

#### UI

- new month based view of SUSHI fetching success was introduced to help in debugging
- the SUSHI management page was extended with a "Harvest selected" button to allow testing
  and harvesting of data for more than one set of credentials
- the SUSHI downloads page now has a "Cleanup" button that allows deleting old unsuccessful
  attempts

#### Backend

- a caching mechanism with automatic renewal called `recache` was implemented for selected long
  running database queries
- a specialized view for top 10 titles was implemented using `recache`
- charts used on dashboard page use `recache`

### Changes

#### UI

- the way yes-no style icons are presented in the UI was changed to avoid colors
  where the color conveyed incorrect connotations
- available languages are loaded from the backend and selector is only displayed if more than
  one is available
- SUSHI credentials edit dialog was cleaned up and tooltips were added
- Retried attempts to fetch data using SUSHI are only displayed as one record when viewing
  attempts
- SUSHI downloads page is visible only to superusers. Organization admins can use the new
  'SUSHI status' page as more convenient replacement
- View of existing SUSHI fetch attempts was simplified and cleaned up

#### Backend

- SUSHI reports with error 3030 are treated as 3031 (retried later) only in case they are
  for current months. For later dates, they are considered simply empty.
- empty reports with code 3030 are no longer considered an error, but a successful import instead

### Fixes

#### UI

- fix error when assigning second chart to report type in the charts tab on maintenance page
- fix error displaying wrong platform name in sushi edit dialog when editing existing credentials

#### Backend

- case is now ignored when checking if email address is verified which makes it
  consistent with the rest of the login/password reset system
- StopIteration error occurring for empty Counter 4 files was fixed
- error ingesting JR1 GOA report was fixed

## [2.1.2] (2020-08-19)

### Fixes

- fix metric display in charts - remapping should not be shown the same way as in the admin
- fix storing of TSV files instead of raw XML for successful C4 attempts

## [2.1.1] (2020-08-18)

### Fixes

- fix mismatch of version hash between credentials and attempts causing
  incorrect display of attempt status on SUSHI downloads page

## [2.1.0] (2020-08-18)

### Added

#### UI

- it is now possible to manage report-view to chart mappings in the frontend
- UI tour for first time users was added
- add password reset function to the login screen + use it for invitations as well
- when UI is 'booting up', unsuccessful attempts to connect to the backend are
  repeated until success
- Sentry was added to the frontend

#### Backend

- add django admin command to send invitations to new users
- make it possible to specify used languages/locales in .env file
- add management command to create users from a CSV table
- add management command to load organizations from a CSV file
- organization can now have unlimited number of alternative names
- alternative sushi namespace was added to fix problems with some messed up C4 reports
- C4 and C5 responses are always stored in file first and then processed

### Changes

#### UI

- update js dependencies and some vue-cli related packages

#### Backend

- ReportDataViews are ordered by name in Django admin
- if a Metric has different short_name and name (and thus remaps between imported
  and displayed value), show both of them in Django admin

### Fixes

#### UI

- always convert dimension name to string in charts to prevent errors for 'null'
