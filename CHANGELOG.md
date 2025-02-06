# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [8.0.1]  - 2025-02-07

### Changes

#### Frontend

* credentials upgradable to 5.1 were split into two groups depending on the presence of C5.1
  record in the knowledgebase
* the cloning dialog was extended to contain more information and also discourage users from blindly
  cloning all the credentials regardless of the knowledgebase record
* cloning of broken credentials was disallowed


#### Backend

* when harvesting using full dates (2025-01-01) fails with 3020, CELUS will try short version
  (2025-01) as a backup before giving up
* heuristics was added to replace /r5 with /r51 when cloning credentials without a knowledgebase
  record


### Fixed

#### Frontend

* bug preventing newly cloned credentials from being harvested when a credentials filter is applied
  was fixed


#### Backend

* synchronization of harvest data with the knowledgebase was fixed to properly aggregate data before
  uploading it to the knowledgebase
* generation of OTP tokens was fixed for cases where impersonation is used by a user with 2FA
  disabled


## [8.0.0]  - 2025-01-31


### Added

#### Frontend

* support for COUNTER 5.1 was added
* a button to easily clone existing COUNTER 5 credentials to COUNTER 5.1 was added
* reporting was extended to allow comparison of two report types side by side
* a new specialized report for CAUL (Council of Australian University Librarians) was added

#### Backend

* several command line scripts were added to help with COUNTER 5.1 migration


### Changes

#### Frontend

* the "problematic only" filter was replaced by a "potential issues" dropdown to show credentials
  needing attention for different types of reasons
* the "Save & Verify" button was removed from the SUSHI credentials dialog - the functionality
  is now part of the "Save" function
* report selection in charts was split to two separate dropdowns - one for type of report and one
  for the report itself
* reporting was extended to allow filtering and grouping by explicit dimensions when two reports
  are used - provided the dimensions are the same in both reports and map to the same db column
* data coverage percentage is rounded to the lower integer (floor) to prevent misleading
  information about the completeness of the data (100% coverage is now only shown when all data is
  present)
* when tag names longer than 200 characters are submitted in a title list, the user is warned
  about the limit and the tagging fails

#### Backend

* BOM (Byte Order Mark) is newly added to COUNTER export according to COUNTER recommendation
* interest synchronization when new superseding reports are added was optimized to prevent
  unnecessary recalculations
* case-insensitive matching of proprietary IDs is used when matching titles during data import


### Fixed

#### Frontend

* pagination is correctly reset to 1 when filters are changed in the event list
* missing "delete" button was added to the list of manually uploaded reports
* properly handle cases when a background error occurs during title list processing - the task
  should no longer appear as "running" indefinitely

#### Backend

* command line script to clean up orphaned data files was fixed to clean files from directories
  without any existing attempts
* query used in reporting when titles are viewed in trend mode was optimized with a 10x speedup
* specialized report export was fixed to properly show end date of the data range
  (last instead of first day of the month)
* ISBNs in COUNTER export are now correctly hyphenated
* the `find_split_accesslogs_with_the_same_title_task` celery task was fixed to correctly send
  emails when intervention is needed
* OOM (Out Of Memory) errors in Postgres during title merging on large installations were
  circumvented by performing updates batches
* when consortium admin is performing download of SUSHI credentials template file for one
  organization, do not include private platforms from other organizations



## [7.0.1]  - 2024-12-18

### Added

#### Frontend

* consortium admins can newly mark several SUSHI credentials at once as fixed
* new users without any data are newly directed to the SUSHI management page from the title and
  platform lists


### Changes

#### Frontend

* the capitalization of the name `CELUS` was unified throughout the application
* `Platform filter` was renamed to `Platform` in the SUSHI management page
* cleanup was performed in the frontend code (e.g. empty `class` and `color` attributes were
  removed, html fragments were removed from translation strings)
* unique user email addresses are now enforced regardless of the case of the email address and the
  verification status of the email address

#### Backend

* user created platforms are not included when computing the generic SUSHI data arrival statistics
  (which is used for platforms without enough data to compute the statistics from the past)


### Fixed

#### Frontend

* a more useful error message is shown when an admin tries to add a user with an email address
  already in use
* error handling for uploading non-COUNTER data was improved to show a more useful error messages

#### Backend

* potential conflicts when doing platform-title cleanup are now ignored to prevent bogus errors
* uploading non-COUNTER data with Japanese (SHIFT_JIS) encoding was fixed



## [7.0.0]  - 2024-10-16

### Added

#### Frontend

* SUSHI management page now shows statistics about the day of month when the data typically becomes
  available
* the platform selector widget was improved to allow for searching by both short and long names
* links to individual titles added to annotated CSV files are newly split to individual columns
  to allow the links to render correctly in Excel
* an option to only allow consortial managers to manage users was added
* make it possible to create a custom platform from the dropdown when uploading data manually
* more information was added to the list of stored reports in reporting (author, etc.)
* tag class was added to the detailed information for title lists used tagging by tag names from
  the uploaded file
* warning is newly shown when the same credentials are used for multiple platforms, or by multiple
  organizations (in consortial installations)


#### Backend

* support for storing items and related usage was added - it is considered beta and is not yet
  exposed in the UI


### Changes

#### Frontend

* overlap analysis was reworked to only use types of interest which imply title availability
  on a platform - not denials.
* the 'Add platform' button was removed from the platform list page (it confused people into
  thinking it added platform to the displayed list)
* links to knowledgebase on non-COUNTER list page were redesigned to be more visible
* server-side pagination is used when listing manual data uploads to speed up the page load
* SUSHI yearly overview dialog was reworked to show 2 years by default and allow up to 5 years
  to be displayed on a single page
* in reporting, the maximum number of displayed parts was limited to 1000 to prevent performance
  issues
* the SUSHI management page was reworked for new users to include an introductory video
* the 'SUSHI status' dashboard panel was reworked to show a hungry CELUS logo when no SUSHI is
  set up yet


#### Backend

* data harvest planning was reworked to use statistics of past harvests to better predict when
  the data will be available
* when a SUSHI URL of a platform is updated automatically from the knowledgebase, the last two
  months are automatically harvested if the data is missing


### Fixed

#### Frontend

* platform selector on the SUSHI month overview page did not work correctly
* date range selector is hidden when displaying the cost tab on the platform page
* use lowercase report names in debug SUSHI URLs in the SUSHI credentials dialog

#### Backend

* the number of queries run by the `update_for_month` harvest planning function was reduced
  significantly
* fix false warning about 'Dropping inconsistent order by "_total"'
* more resilient parsing of /etc/os-releases was implemented
* use django's standard smtp email backend for error handling when mailgun is not used
* error was fixed when tagging titles from a file containing explicit tag names and using a tag
  class owned by an organization
* 'too many open files' error was fixed in reporting when exporting report with many parts into
  Excel format
* platform short-name uniqueness is newly enforced even when updating existing platforms




## [6.1.2]  - 2024-08-08

### Added

#### Frontend

* in reporting, it is now possible to order the rows by the row totals
* in reporting, when "merge rows by tag" is active, it is now possible to order the results by the
  tag name


### Changes

#### Frontend

* when "merge rows by tag" is active, tags from classes which have been marked as hidden by the user
  are no longer shown in the report - unless the class was explicitly selected by the user
* after email verification, the user is automatically redirected to the dashboard without needing to
  click on a button
* the "Introductory tour" feature was removed (it was buggy anyway)
* when removing users from the UI, the account is actually deleted when removed from the last
  organization
* clashing import batches (usually in situations where the same data is requested while a download
  is in progress) are not shown by default in the list of downloads

#### Backend

* a one-second delay was added between downloads from the same SUSHI URL to ease the load on fast
  SUSHI servers (thanks to ScholarlyIQ for reporting this issue)


### Fixed

#### Frontend

* an error in reporting causing unresponsive "Run report" button when report type was changed
  under specific conditions was fixed

#### Backend

* a bug causing CELUS not to respect the 1020 (too many requests) SUSHI exception was fixed
  (thanks to ScholarlyIQ for reporting this issue)


## [6.1.1]  - 2024-06-28

### Added

#### Backend

* a CLI script was added to export and import fetch attempts to aid with accidental data deletion
  recovery
* support for user invitations when external SSO is enabled was added


### Changes

#### Backend

* various dash types (n-dash, m-dash, minus) are now normalized to a single character during
  ISSN and eISSN normalization
* deleting data from Clickhouse was optimized to delete more than one import batch at once


### Fixed

#### Frontend

* export to COUNTER format was made visible to non-admin users
* endless loop in websocket reauthentication when the user session expires was fixed
* bug causing errors when saved report with platforms in rows was modified to merge rows by tags
  was fixed (result ordering is invalidated when row merging is toggled)
* a typo in the documentation leading to incorrect API endpoint URL was fixed
* COUNTER registry domain name was updated to the new one (fixes CORS issues)

#### Backend

* loading of Excel files with credentials which do not include row number information
  (as produced by Google Sheets) was fixed
* extra safety features were added to the necronomicon app for deleting data (remove unfinished
  batches after one day, re-check stats before delete, etc.)



## [6.1.0]  - 2024-05-23

### Added

#### Frontend

* make it possible to apply filters from standard reports to full reports in reporting with one click
* warn users against possible metric summation in reporting
* make it possible to use proprietary IDs for matching titles in title tagging and title overlap

#### Backend

* statistics of events was added to the exported prometheus metrics
* make it possible for a superadmin to disable second factor authentication for a user
* improve Django admin for events
* API endpoint for getting output of a stored report was added
* send notifications about regular reprocessing of internal title lists to superusers

### Changes

#### Frontend

* change display of report type selection in charts, etc.
  * show full reports first
  * call full reports "full reports" (not customizable reports)
  * only add real standard views to the standard views section
* prefer full reports when showing charts for individual import batches or manual data uploads
* better error message was added when uploading an incompatible XLS file

#### Backend

* metadata from SUSHI responses are extracted during download rather than during import
* cleanup in SUSHI harvesting code was performed and some unused code was removed
* use skip-magic-trailing-comma for ruff format
* the `django-prometheus` library was removed from the project

### Fixed

#### Frontend

* on title page, make sure the title is loaded before trying to show proprietary IDs
* missing values in chart tooltips under specific conditions were fixed
* fix pagination of the events list with a large number of events
* second factor authentication display was fixed for superusers without verified email

#### Backend

* deterministic selection of titles during data import when several candidates with equal score are
  present was introduced
* do not use ContentFile when storing C4 reports
* do not create events about title list reprocessing if the list is not owned by a user (e.g. for
  internal title lists)
* make sure that a valid email OTP device exists for each user after login
* get around a race-condition in locking the next tagging batch to reprocess
* unused OTP plugins were removed reducing the number of queries to the database per request


## [6.0.0]  - 2024-04-24

### Added

#### Frontend

* system of "events" for in-app notifications was introduced
* possibility to export data in COUNTER format was added to the platform page (under Data management)
* it is now possible to mark unsuccessful harvests as empty data under "SUSHI management"/"Overview"
* fiscal year based data ranges were added to the data range selector with the possibility to
  select the start month of a fiscal year
* data coverage information was added to exports from the reporting module
* email-based two-factor authentication was added to all accounts
* more details about SUSHI exceptions is now shown for individual harvests
* when uploading reports for multiple organizations, information about organizations with clashing
  data is now shown
* list of proprietary IDs was added to the title detail page
* tags can be now created directly from the title list creation dialog


#### Backend

* CLI script was added for creating internal tagging batches from a CSV file
* a welcome event is created when a user account is created
* an introductory event for existing users was added


### Changes

#### Frontend

* unless manually changed, the SUSHI server URL will be taken from the platform metadata and
  automatically updated when the platform is updated
* search was enabled in the platform filter selector on the SUSHI status page
* import of "CELUS format" was removed from the import format options (unless turned on in the settings)

#### Backend

* clickhouse integration has been modified in several ways
  * plain MergeTree engine with lightweight deletes is used in favor of CollapsingMergeTree
  * synchronization between the main database and Clickhouse was optimized and fixed for cases
    where titles were merged together
  * dictionaries were added to make mapping of integer IDs to strings possible
* it is now possible to get the knowledgebase API key from settings instead of storing it in the
  database
* add extra info into the request logs about use of API key authentication and content of error
  responses
* more SUSHI exceptions are newly considered as partial data
* username and organization name were added to the subjects of emails about new registrations
* some obsolete settings were removed
* specialized code to add Scopus title list tags was removed - standard tagging may be used instead


### Fixed

#### Frontend

* a bug in reporting leading to incorrect number of possible values being shown after a text search
  was used was fixed
* do not show the user edit dialog unless ALLOW_USER_MANAGEMENT=True - edit attempts would cause
  errors otherwise
* the date selector widget is properly hidden on pages where it is not needed
* translations for the account management page were fixed
* display of data from one harvest/manual upload no longer displays the whole selected date range,
  but rather the range of the data itself
* debug links to the SUSHI server are now shown only for COUNTER 5 (and higher) credentials
* bug preventing change of tag class visibility under certain conditions was fixed
* coverage display on platform page with non-COUNTER data no longer causes errors

#### Backend

* extra check for existing data is done before a planned attempt to harvest data is made - fixes
  creation of clashing import batches for newly verified credentials
* normalize emails before checking them using the Octopus protocol
* fix email verification for installations where both password and shibboleth authentication are
  enabled
* only consider user's main email address when checking email verification status


## [5.10.0]  - 2024-02-28

### Added

#### Frontend

* support for the 2023 version of the ACRL IPEDS report was added to the list of specialized reports
* a built-in OA (Open Access) tag class was added with two tags (DOAJ and DOAB) marking titles as
  listed in the respective directories

### Fixed

#### Frontend

* algorithm for detection of the last covered year was fixed to match previous year in February
  (not March)
* when uploading a source file in an unsupported format, a more helpful error message is now shown
* error display in the ReportViewSelector was fixed

#### Backend

* reporting module export was fixed to only include tags visible to the user
* Clickhouse version used in Gitlab CI was fixed to get around a bug in the latest version


## [5.9.1]  - 2024-01-23

### Changes

#### Frontend

* the frontend code was updated to compile using node 18; support for version 16 was dropped

#### Backend

* the overlap computation was optimized to use less memory and be faster
* a more effective method is used to list all tags visible to a user resulting in slight performance
  improvement
* the API for external access was extended to allow COUNTER registry IDs for platform identification
* a more compact method of passing list of object IDs is used to request list of tags associated
  with them. This fixes a problem with some URL strings being too long for the server on large CELUS
  installations


### Fixed

#### Frontend

* error when too large a file is uploaded to the title list page is now handled more gracefully
* error when uploading table data in a file with an unrecognized encoding is now handled
  more gracefully
* the coverage widget was fixed not to offer harvesting of missing data to read-only users
* when manually uploading data for a platform which is private to one organization, the
  organization is now automatically selected and cannot be changed
* alignment of icons in the application top bar was fixed

#### Backend

* problem with the platform overlap computation over-reporting the number of titles under specific
  conditions when viewed for the whole consortium was fixed
* the language preference API endpoint was fixed after Django upgrade
* access of read-only users to harvesting data and harvest processing was reviewed and fixed where
  necessary
* several minor inconsistencies in the platform-title support table were fixed
* inconsistencies between the main database and clickhouse caused by title merging were fixed
* potential race condition in creating organization-platform links was fixed


## [5.9.0]  - 2023-12-05

### Added

#### Frontend

* interface for managing organization users was added to organization admins
* reharvesting of data is now possible directly from the harvest dialog
* report selection was added to the harvest dialog to allow for limiting the harvest to a subset
  of reports
* values of filters are now shown on the report and export list pages - no need to open the report detail
* filtering of reports by row dimension and visibility was added to the report list page
* when running a report directly from the report list, the current report is newly highlighted
* two new states were added to the montly SUSHI status overview to indicate broken and past last
  harvestable month credentials

#### Backend

* NTFY integration was added for admin notifications


### Changes

#### Frontend

* menu entry `non-COUNTER platforms` was renamed to `non-SUSHI platforms` to better reflect the
  nature of the platforms listed there
* autocomplete is now used for selecting platforms when uploading data manually
* during an ongoing harvest, progress checks with the backend are done progressively less often
  to reduce the load on the server
* default logo was changed from "CELUS Plus" to "CELUS"
* logic for displaying platforms in the list of non-COUNTER platforms was changed to use info about
  presence of support web article
* Excel files incorrectly detected as 'application/CDFV2' are now accepted as XLSX files


#### Backend

* the `pycounter` library was replaced by our internal fork (`celus-pycounter`)
* all internal git based dependencies were replaced by pip based dependencies
* ratelimitting was added to admin emails
* a separate list of customer care admins was added for specific notifications (e.g. user registration)


### Fixed

#### Frontend

* handling of errors connecting to the CDN in presence of security proxies was fixed
* more graceful handling of situations where uploaded file contains more than one report was added



## [5.8.1]  - 2023-11-07

### Fixed

#### Backend

- error importing COUNTER 5 reports with missing `Performance` key was fixed
- error importing some COUNTER 5 reports when Python 3.8 was used was fixed


## [5.8.0]  - 2023-11-03

### Added

#### Frontend

- filtering by tag class (not only by individual tags) was added to reporting
- "last harvestable month" was introduced for SUSHI credentials - CELUS will not try to harvest
  data for months after this date. It is automatically extracted from failed reports and may be
  set/overridden by the user.
- tagging titles from a title list newly supports getting tag names from the uploaded file, rather
  than being selected manually
- tagging titles from a title list newly supports automatic periodic re-tagging of new titles
- report type selection is no longer necessary when uploading COUNTER data - CELUS will detect it
  automatically
- confirmation step was added to the manual data upload process to let user know what report type
  was detected
- page title was added to all pages - makes history, bookmarks and browser tabs more useful
- link to knowledgebase articles was added to several pages
- file size information was added to the list of harvest attempts

#### Backend

- support for importing data from XLS (older Excel format) files was added


### Changes

#### Frontend

- tag management was improved to allow for easier creation of new tags
- users newly see not only the title lists they uploaded, but also those related to tags and
  tag classes they can assign
- tags are newly applied to titles immediately after they are selected - no confirmation is needed
- the templates for SUSHI credentials batch upload were polished for more consistent formatting
- more user-friendly error messages were added to the manual data upload process

#### Backend

- code cleanup + typo fixing was performed in the backend code
- lazy imports were added to the nibbler library to speed up startup of CELUS
- API key based authentication was sped up by using a newer version of the corresponding library
- CSV processing throughout CELUS was unified to use the same library


### Fixed

#### Frontend

- tags for platforms occasionally not loading was fixed
- when tag roll up is switched off, computation of remainder is automatically switched off as well

#### Backend

- creation of organization-platform link records was fixed to work more reliably
- processing of title lists containing the BOM character was fixed


## [5.7.1]  - 2023-09-07

### Fixed

#### Frontend

- expanding a row in the list of stored reports no longer messes up the formatting of the table
- displaying of errors on the platform list page was fixed

#### Backend

- an occasional database deadlock when deleting SUSHI credentials together with all the data was
  fixed
- the command line script `export_analytical` no longer crashes when output file is not explicitly
  specified



## [5.7.0]  - 2023-08-28

### Added

#### Frontend

- in tag management, it is now possible to hide some tag classes from being listed together with
  the tagged items (e.g. in reporting output, "All titles", etc.)
- in reporting, it is now possible to expand the resulting table to whole screen for easier
  reading
- the coverage widget in reporting newly contains a tooltip and links to the coverage overview
  page
- consortium admins now can see debug links to the configured SUSHI server in SUSHI credentials
  dialog

#### Backend

- user django admin now contains number of associated organizations and limits data sources in
  filter to the used ones
- cli script for computing statistics about saved reports was added


### Changes

#### Frontend

- title lists without any matched titles are now displayed differently to make them more obvious
- when an open-ended time range is selected, default date range for reporting will end at the last
  "covered" month (the one before the last finished month)
- colors of some of the buttons and other elements was reviewed after the recent UI changes

#### Backend

- the nibbler library was updated to version 9.0.1 fixing some bugs and adding support for
  multi-organization TR reports and per-organization stats in preflight
- export of reports with titles in rows was optimized to use much less memory and be much faster
  for smaller reports
- a database constraint permitting only one import batch for one organization-platform-report-month
  combination was added
- per api-key throttling was added to the external API to prevent spikes in usage
- title list parsing was significantly sped up by adding a database index (about 40x speedup for
  large databases and title lists)
- interest and materialized reports are calculated during the data import step to prevent
  temporary inconsistencies in the user interface

### Fixed

#### Frontend

- tags which are not "assignable" by the user are no longer offered when title list is being
  processed
- locales were fixed in several places

#### Backend

- CSV files with BOM are now properly parsed when uploading title lists
- fix reporting coverage error when date range has open end and no data are available



## [5.6.0]  - 2023-08-03

### Added

#### Frontend

- "trend mode" allowing comparison of usage data between two periods was added to the reporting
  interface
- data coverage widget was added to the reporting interface
- interface for superusers to run CLI commands from the UI was added
- row and column totals were added to CSV exports from reporting

#### Backend

- import of SUSHI credentials from a XLSX file was implemented as a CLI script
- a CLI script for exporting all usage data into a CSV file for ingestion into an analytical
  database was added


### Changes

#### Frontend

- the UI was slightly reworked - some unused elements were removed, menu icons were made smaller,
  the color scheme was changed and many small improvements were made
- when a COUNTER report is uploaded using the non-COUNTER upload interface, the proper report
  is auto-detected and the method switched to COUNTER
- the setting for including totals into reporting output newly influences the exports, not only the
  UI
- on small screens a pointer is shown to navigate user to the details on the coverage overview
  page
- do not allow the user to do anything in the UI until he has verified his email address
- it is now possible to change the organization during a preflight of manually importing data
- naming of stored reports was moved into a dialog to make it more obvious


#### Backend

- handling of the 3040 SUSHI exception was changed - data get ingested immediately and re-harvest
  is scheduled for the future (previously CELUS made several retries before accepting the data)
- SUSHI exception 3060 no longer causes the whole credentials to be marked as broken - only the
  problematic report is disabled
- Clickhouse support was added to the external API `PlatformReportView` endpoint
- performance of the `clean_obsolete_platform_title_links` celery task was improved


### Fixed

#### Frontend

- error causing charts of manually uploaded data for the TR report being empty was fixed
- validation of SUSHI URL in the credentials magement dialog was relaxed to allow `/report/`
  in the path as long as it is not the last part of the URL

#### Backend

- error in the external API endpoint `api_platform_report_data` when attempt had no intention object
  associated was fixed
- a crash in Django admin for `SushiFetchAttempts` when credentials link was missing was fixed
- a fix for deadlock occurring during deleting of data in Celery was introduced
- several random failures in the test suite were fixed
- a crash was fixed in the preflight process of importing multi-organization non-COUNTER reports
- cachalot caching was disabled during exports from reporting to prevent large memory consumption
- memory consumption of reporting exports was reduced


## [5.5.2]  - 2023-06-12

### Added

#### Frontend

- a hint that titles are filtered by tags was added to the reporting page
- the login dialog newly accepts the email address passed as a query parameter

#### Backend

- a CLI script was added to export credentials for which the SUSHI URL does not match the
  knowledgebase URL
- simple API for secure testing of user account existence was added

### Changes

#### Backend

- the `source` field was removed from the Dimension model
- organization and platform names are now sanitized before being used as part of file names


### Fixed

#### Backend

- parsing of COUNTER 4 reports with incomplete headers was fixed
- the missing `Unique_Item_Requests` metric was added to the COUNTER 5 TR_J1 report
- reporting sometimes incorrectly used materialized report which was missing the queried dimension
  when generating list of possible dimension values


## [5.5.1]  - 2023-05-25

### Added

#### Frontend

- the `Titles on multiple platforms` page newly adds span of YOP from the TR report to each
  platform for a title.

#### Backend

- a command line script for looking up a title in all related JSON report files was added

### Fixed

#### Frontend

- when viewing a list of titles, the page newly resets to the first page when the user changes
  the filters - this prevents the user from being stuck on a page with no results


## [5.5.0]  - 2023-05-16

### Added

#### Frontend

- dedicated page for overview of data coverage throughout the whole system was added + it allows
  automatic harvesting of missing data
- a dashboard widget with overall data coverage was added
- download of a template for importing of SUSHI credentials was added to the SUSHI management page
- row and column totals were added to Excel exports from reporting + row totals are now
  displayed in the frontend
- in reporting it is now possible to export data in Excel format without charts
- interface for adding alternative names (alt-names) to organizations was added
- platform filter was added to the SUSHI management page
- the `Title overlap` feature newly adds information about the first and last month of available
  data for each title
- when deleting SUSHI credentials, it is now possible to delete the related usage data as well

#### Backend

- prometheus metrics were extended to include database object counts for common models


### Changes

#### Frontend

- export of SUSHI credentials was improved and now uses .xlsx format
- 'Include rows with zero usage' option is newly only enabled for some types of rows. It is disabled
  where CELUS does not have a correct source of list of possible values (e.g. for all titles
  available on a platform)
- explicit information was added to the harvest dialog that it is safe to close it without
  interrupting the harvest
- unicode errors are now handled more gracefully when parsing uploaded title lists

#### Backend

- manual harvests resulting in no data with the 3030 exception are now marked as finished instead
  of failed
- automatic harvesting scheduled for the future will overwrite empty data if the harvest is
  successful (previously the harvesting would be canceled as duplicated)
- performance of the `sync_materialized_reports_task` celery task was improved significantly
  thus reducing the delay before data is harvested and visible in the frontend

### Fixed

#### Frontend

- error preventing change of access level for stored reports from 'consortium' to 'organization'
  was fixed
- fix issue with creating tag classes with visibility set to 'organization'
- it is not possible to create an organization alt-name with the same value as the organization
  short name or full name anymore
- display of Y-axis values with a high number of digits in charts was fixed by dynamically
  calculating the space required for the values
- fix error which prevented stored reports using tags for organization filtering from being edited
- fix error preventing title details from being displayed when the title has no usage data
- prevent frontend from (under specific conditions) re-requesting data for harvests which are
  already finished
- organization admins are now able to see details of automatic harvests related to their
  organization
- missing last month in the coverage chart was fixed
- file format validation for XLSX files was fixed for cases where the mime-type was detected as
  application/octet-stream

#### Backend

- metrics synced from the knowledgebase no longer create duplicate entries when their equivalent
  already exists in the database
- several random false test failures were fixed in the test suite
- email verification for installations where user registration is not permitted no longer returns
  a 404 response
- database constraint was added to prevent creation of duplicate connections between user and
  organization
- production deployment no longer uses the browseable API view


## [5.4.0]  - 2023-04-12

### Added

#### Frontend

- support for the ACRL IPEDS report was added to the `Specialized reports` section
- interest type `Multimedia` was added
- it is now possible to import empty table reports (reports with no data) into CELUS and thus
  create correct coverage records for the platform and dates at hand (only when nibbler library
  is used for parsing)
- when deleting platform data, it is now possible to delete the related SUSHI credentials as well
- when manually uploading non-COUNTER data, a link to the knowledgebase may be now shown to get
  users to more information about the format
- the title overlap function newly adds info about first and last month of available data for
  each title

#### Backend

- logging of celery tasks into an external database was added


### Changes

#### Frontend

- only one set of SUSHI credentials is now allowed per organization, platform and COUNTER version
- existing conflicting SUSHI credentials can no longer be edited unless the conflict is resolved
- the `Specialized reports` section was reworked to allow for more reports to be added in the
  future and to improve the export functionality
- link to the tags documentation was changed to point to the knowledgebase


#### Backend

- comparison of imported data with past data during manual data upload was optimized for better
  performance
- the recache module was optimized to skip caching of fast queries and to remove unused cache
  entries earlier
- CLI scripts for interest recomputation and materialized report recalculations were improved to
  support report type filters
- CLI script for loading SUSHI credentials from a file was improved to include the title column
  and use case-insensitive matching of platform names
- scheduling of new harvests was improved to reduce the number of database queries and run faster


### Fixed

#### Frontend

- when checking a newly created custom platform name against existing platform names, other custom
  platforms were not taken into account
- when creating tag class with permissions depending on the organization, the organization was not
  properly sent to the backend resulting in a permission error


#### Backend

- comparison of imported data with past data during manual data upload was fixed to work correctly
  when working with multi-organization imports
- synchronization of ParserDefinitions with report types was fixed to work correctly when several
  interest groups are present
- the `nibbler` library was updated to be more lenient toward common misspellings when parsing
  COUNTER 5 reports
- reporting export into Excel format no longer creates a `tags` series for the chart
- data files of manual data uploads are explicitly closed to prevent errors related to too many
  open files
- don't crash in admin when short_name of a new organization already exists
- deleting of all platform data is now allowed independent of the `ALLOW_USER_CREATED_PLATFORMS`
  setting
- the `clean_obsolete_platform_title_links` task was optimized for speed and prints progress
  information to prevent the task from seeming to hang
- incorrect sheet reference format in formulas in Excel exports of specialized export was fixed
- error in specialized reports caused by multiple metrics with the same name was fixed (fixes
  problems with the Rebiun report on run.celus.one)


## [5.3.0] - 2023-03-08

### Added

#### Frontend

- a new function was added to overlap analysis section - `Title list overlap`. It allows users
  to compare titles present in CELUS against an uploaded title list.
- the reporting section was expanded with `Specialized reports` page. It contains synthetic reports
  for specific use cases which go beyond the normal reporting capabilities. At present, it contains
  the `Rebiun report` used in Spain and the `ARL report` used in the USA.
- it is now possible to delete a user-created platform together with all its data
- release dates were added to the changelog and releases pages


### Changes

#### Frontend

- pages not requiring an organization to be selected are now visible even when no organization
  is selected
- the old version of the `Rebiun report` was removed from platforms list page

#### Backend

- when the `nibbler` library is used to parse COUNTER data, CELUS now does more check on the report
  header to prevent user errors in selecting the correct report


### Fixed

#### Frontend

- infinite loading of content of an empty harvest was fixed
- error in reporting causing occasional errors when reloading data after report change was fixed
- error which prevented some users from leaving impersonification mode was fixed



## [5.2.2] - 2023-02-17

### Added

#### Frontend

- CELUS can autofill the appropriate value when a platform requires the `platform` SUSHI parameter

#### Backend

- COUNTER 4 table reports may now optionally be parsed by the `nibbler` package rather than the
  `pycounter` library (can be influenced by `ENABLE_NIBBLER_FOR_COUNTER_FORMAT`)

#### Documentation

- new section about external access to CELUS was added


### Changes

#### Frontend

- optimization: periodic retreival of progress of a harvest newly only transports info about the
  changes, thus saving a lot of bandwidth and computation resources for large harvests

#### Backend

- SUSHI exceptions are properly extracted from SUSHI responses even if they arrive with an HTTP
  status code >= 500
- optimization: saving SUSHI credentials was sped up significantly
- optimization: the SUSHI monthly overview was sped up significantly
- optimization: accesslog list API for manual data uploads and import batches now uses pagination
  and has optimized performance
- the way Clickhouse tables are created was changed to use a separate CLI script
- unused `primary_dimension` attribute was removed from the `ReportDataView` model


### Fixes

#### Frontend

- error when trying to edit a custom platform was fixed

#### Backend

- periodic synchronization with the knowledgebase was fixed to include all synchronized models
- allow `null` in `interest_group` when downloading report types from knowledgebase API
- deleting of past celery task results was blocked by a foreign_key which was removed


## [5.2.1] - 2023-02-02

### Added

#### Frontend

- release dates were added to the changelog

#### Backend

- platform interest definition is now configured from the knowledgebase for platforms with support
  for raw non-COUNTER data import
- a simple CLI command was added to assign COUNTER registry IDs to platforms from a CSV file
- optional logging of diagnostic information from web API requests to a clickhouse database was added

### Changes

#### Frontend

- sorting of titles by tags was disabled - it was not useful and caused performance issues

#### Backend

- optimization: the number of database queries used when creating a harvest with many months was
  significantly reduced
- the speed of the harvest API endpoint was improved dramatically for cases where platform filter
  was used

### Fixed

#### Backend

- scheduler crashes when processing canceled fetch intentions were fixed
- missing `counter_registry_id` field was added to the platforms API endpoint
- synchronization with the knowledge base was made more robust


## [5.2.0] - 2023-01-18

### Added

#### Frontend

- the [COUNTER registry](https://registry.projectcounter.org/) was integrated into the SUSHI
  credentials edit dialog giving extra information about the credentials for platforms in the registry
- a basic "Troubleshooting" page for SUSHI was added containing the IP addresses of the
  CELUS server to be used when IP authentication is required
- a list of non-COUNTER platform for which raw data import is supported was added as a separate
  page
- remember the page size of the SUSHI credentials table between visits

#### Backend

- a periodic task was added to sync report types and parser definitions with the knowledgebase


### Changes

#### Frontend

- the so-called "Spanish report" was renamed to Rebiun report and added to the list of
  available views on platform list page

#### Backend

- only store the parser definitions for raw non-COUNTER data which are compatible with the
  current version of the `nibbler` library
- use a nicer format for displaying the `nibbler` parser definitions in admin
- ensure that all related report types are visible in charts - regardless if they have an explicit
  report view associated or not.

### Fixed

#### Frontend

- display of coverage when the 'All available' date range was selected was fixed

#### Backend

- the number of queries in the `month-overview` API endpoint was reduced


## [5.1.1] - 2023-01-05

### Fixed

#### Frontend

- SUSHI credentials edit dialog only showed one platform if more of them shared the same name
- warn users when the date range is not limited for the "Spanish report"
- optimization: make sure the platform list only loads tags once
- optimize the loading time of platform page by using smarter approach to stored reports


#### Backend

- optimization: reduce the memory footprint of the CLI script for removing unused titles
- optimization: reduce the number of queries in PlatformViewSet to improve performance
- optimization: optimize speed of the annotations endpoint
- fix bug in the `delete_batches_targets` celery task


## [5.1.0] - 2022-12-19

### Added

#### Frontend

- all charts now show the whole selected date range even if there is no data for some months
  (if the end of the range is open, the chart will end with the last calendar month)
- the data coverage tab on title page was extended to split the coverage by platform
- more information about the report (rows, split-by) was added to the exports list
- a check for the file type of the uploaded file was added to the title list page
- several pages listing items (titles, organization, platforms, harvests) now store their settings
  (sorting column, sorting order, page size) in the URL, making it possible to share the link
  and get the same view and to use the browser's back button to return to the previous view
- a test version of an overview page for Spanish libraries was added under the `/spanish-report` URL

#### Backend

- parsing of the internal CELUS format for non-COUNTER data has been reimplemented in the nibbler
  library. It is now possible to activate this new parser by setting the
  `ENABLE_NIBBLER_FOR_CELUS_FORMAT` environment variable to `true`.
- added `is_admin` and `is_consortial_admin` filters to User model in django admin
- it is now possible to enable import of raw non-COUNTER reports on a per-organization basis
- `export` action was added to the `User` model in django admin
- Clickhouse support was added to the `possible-values` endpoint in the reporting API
- support for asynchronous deleting of platforms and organizations was added to the django admin
- the backend now sends email notification to admins when a new organization is created by a user


### Changes

#### Frontend

- When a new report is created in the reporting module, it inherits the filters for currently
  selected organization and date range
- All organizations are now selected by default in the first session of consortium admin (instead of
  the first organization in the list)


### Fixed

#### Frontend

- sorting of titles, harvests and fetch-intentions in corresponding tables was fixed for cases
  where the sorting column values were not unique. This caused issues when switching between pages -
  some rows may have been missing or duplicated.
- action icons on the sushi fetch attempt list were optimized to take less space
- data coverage display on title level without a platform selected was fixed to include only the
  relevant platforms
- the SUSHI credentials edit dialog was refactored to remove the possibility of previously entered
  data passing into the next instance of the dialog

#### Backend

- when SUSHI harvesting returns 3031 (data not available for the requested date range) even after
  1.5 months, the download is now marked as failed instead of being closed as "empty data".
- when SUSHI credentials are edited, the corresponding chains of retries (for 3031, 3030, etc.)
  are no longer broken leading to incorrect counting of previous attempts
- header data are extracted from COUNTER reports even for failed downloads (e.g. 3031, 3030, etc.)
- sorting is now working for organizations in the django admin
- automatically created organization-specific sources were fixed to contain a unique name
  (fixes a bug where it was not possible to create new custom platforms for some organizations)
- when creating custom platforms, the source is properly set to the organization-specific source,
  not the source used for the organization itself.


## [5.0.1] - 2022-11-29

### Fixed

#### Frontend

- empty `platform` attribute is no longer stored when SUSHI credentials are saved
- display of the list of harvests was fixed for cases where sorting was switched off
- changelog for the oldest versions was fixed and the changelog API endpoint was fixed
  for platforms where UTF-8 is not the default encoding

#### Backend

- deleting from Clickhouse was fixed to avoid slow performance for some queries



## [5.0.0] - 2022-11-22

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
- documentation was updated with parts about tags and tagging


#### Backend

- a script was added for finding and removing import batches without data and for resolving
  conflicting import batches
- CLI script for tagging titles using the (publicly available) Scopus title list was added
- information about supported report types was added to the platform information from the
  knowledgebase
- automatic resolving of differences between database and clickhouse was added to the CLI script
- celery task for periodic checking of sync between database and clickhouse was added


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
- in reporting the default visibility was fixed not to include values not available for the
  current user
- possible crash in reporting XLSX export was fixed when a report was empty


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
- a corner case where stale data could be displayed in reporting when ordering of data was changed
  during data loading was fixed
- the title 'Harvesting credentials' was changed to 'Harvesting data' in the harvesting dialog

#### Backend

- the number of queries in the impersonation API was optimized
- detection of CSV encoding and dialect (used delimiter, etc.) was improved
- automatic resync with clickhouse after a previous sync failed was fixed
- detection of differences between the database and clickhouse was fixed to cover all cases


## [4.7.1] - 2022-11-21

### Added

#### Backend

- celery task for periodic checking of database-clickhouse synchronization was added
- automatic resolving of differences between database and clickhouse was added into the CLI command


### Fixed

#### Frontend

- 'unknown' state in data presence view in harvesting dialog was fixed

#### Backend

- incorrect state when doing resync in clickhouse after error was fixed
- some missed cases where detection of database-clickhouse difference did not work correctly were
  fixed


## [4.7.0] - 2022-10-24

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


## [4.6.2] - 2022-07-28

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


## [4.6.1] - 2022-07-21

### Fixed

#### Frontend

- visiting a page of a title with ISBN caused the user to be logged out due to an error when
  fetching cover image data from Google. The cover image functionality was removed to fix the issue.



## [4.6.0] - 2022-07-18

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


## [4.5.0] - 2022-06-20

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
- CELUS newly tries to re-harvest data from failed attempts (regardless of the error) if the
  credentials were successfully used to harvest some data lately
- reporting speed was optimized in case when non-zero rows are not requested, most significantly
  those with titles in rows
- cli commands for reimport and subsequent analysis were extended and improved

### Fixed

#### Backend

- an error in title merging caused by incorrect order of update and delete was fixed

## [4.4.5] - 2022-06-07

### Changes

#### Backend

- lowercase 'x' as last character of ISSN is replaced by upper case 'X'
- `hcube` was update to speed up deleting of data from Clickhouse in newer versions

### Fixed

#### Backend

- synchronization with knowledgebase unassignes `counter_registry_id` from platforms which no longer
  use it

## [4.4.4] - 2022-06-03

### Added

#### Backend

- CELUS newly stores checksums of files from SUSHI or manually uploaded and checks them on import
  to prevent against potential data corruption or attacks

### Fixed

#### Backend

- merging of titles was fixed not to merge titles with the same name but without any common ID
- a cli script for merging title out-of-band was added

## [4.4.3] - 2022-05-27

### Fixed

#### Frontend

- reporting - export of reports split by year and month was fixed
- users logging in by EduID are no longer warned about missing email validation

#### Backend

- data import was sped up by factor of about 5 with about 2x memory reduction

## [4.4.2] - 2022-05-19

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

## [4.4.1] - 2022-05-04

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
  old CELUS versions were removed

## [4.4.0] - 2022-04-29

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

## [4.3.3] - 2022-04-06

### Added

#### Frontend

- export function was added to the SUSHI management page

## [4.3.2] - 2022-04-05

### Fixed

#### Backend

- merging of titles between incoming data and database was fixed for cases where
  only name and proprietary IDs are available. Lowercasing of İ was tweaked.

## [4.3.1] - 2022-04-05

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

- CELUS ignores the `Severity` attribute in C5 SUSHI (marked as obsolete in CoP 5.0.2)

### Fixed

#### Frontend

- SUSHI status dashboard and monthly overview were fixed to correctly display waiting harvests
  (COUNTER exception 3031)
- regression in formatting of log data in expander of list of attempts was fixed

#### Backend

- error in harvesting when dealing with in-memory files was fixed
- ignoring `Severity` (see above) fixes errors when importing data with exception 1011 which had
  incorrect severity

## [4.3.0] - 2022-04-01

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

## [4.2.0] - 2022-03-28

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
- CELUS version was added to the prometheus exporter
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

## [4.1.1] - 2022-03-01

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

## [4.1.0] - 2022-02-25

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

## [4.0.1] - 2022-01-17

### Added

#### Frontend

- IP addresses of CELUS harvesters are no longer hardcoded in the code, but rather configured in
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

## [4.0.0] - 2022-01-07

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

## [3.2.5] - 2021-10-26

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

## [3.2.4] - 2021-10-20

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

## [3.2.3] - 2021-09-30

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

## [3.2.2] - 2021-09-22

### Fixed

#### Frontend

- clicking on individual downloads on the monthly overview page displayed details for incorrect
  download

## [3.2.1] - 2021-09-17

### Added

#### Backend

- API keys are now automatically exported to knowledgebase server

### Changes

#### Backend

- Django was upgraded from the 3.1 to the 3.2 branch

## [3.2.0] - 2021-09-08

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

## [3.1.1] - 2021-06-16

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

## [3.1.0] - 2021-06-08

### Added

#### Frontend

- buttons for immediate harvesting and cancellation of harvests planned for later were added
- partial-data status was added to `FetchAttempt` information
- CELUS frontend now checks the version of the backend and forces refresh if the versions do not
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

## [3.0.3] - 2021-05-14

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


## [3.0.2] - 2021-04-26

### Fixed

#### Backend

- speed of resolving possible dimension values in report editor was dramatically improved in some
  cases - most notably when creating reports with titles in rows
- new materialized reports will not be immediately used until they are populated with data. This
  prevents intermittent loss of data in charts when new materialized reports are introduced

## [3.0.1] - 2021-04-23

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

## [3.0.0] - 2021-04-21

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

## [2.8.3] - 2021-02-01

### Fixed

#### Frontend

- ordering of platforms in several menus was fixed
- SUSHI status dashboard widget size when loading data was fixed (it was too high and thus caused
  "jumping" of the content during data loading)
- empty dates in harvest overview table no longer cause the table to get stuck

#### Backend

- manual data CSV files containing BOM (Byte Order Mark) are properly parsed

## [2.8.2] - 2021-01-26

### Fixed

#### Backend

- computation of interest in presence of materialized reports has been fixed (it resulted in
  erroneous 3x increase in interest in some cases)

## [2.8.1] - 2020-12-04

### Fixed

#### Frontend

- harvest detail view stopped refreshing when some download was rescheduled for later
- count of finished downloads in a harvest was inconsistent between the harvest table and the detail
  view.

## [2.8.0] - 2020-12-02

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

## [2.7.2] - 2020-11-26

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

## [2.7.1] - 2020-11-20

### Fixes

#### Backend

- add more robust detection of Exception codes from COUNTER 4 SUSHI data (ignore namespaces which many providers mess up, etc.)
- fix detection of broken credentials based on error codes extracted from SUSHI headers

## [2.7.0] - 2020-11-19

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
- new CELUS logo was introduced

### Fixed

#### Backend

- reading of PR reports was fixed to use fields specific to the PR report

## [2.6.1] - 2020-11-03

### Fixes

#### Frontend

- fix wrong sorting of platforms in some browsers on platform overlap page

## [2.6.0] - 2020-11-03

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

## [2.5.4] - 2020-11-02

### Changes

#### Backend

- recache re-evaluation is done periodically by a celerybeat task rather than each object planning
  its renewal separately. This should get rid of multiplication of celery tasks as observed
  in some installations.

## [2.5.3] - 2020-10-26

### Fixed

#### Backend

- error causing data sometimes not being downloaded from platforms with rate limiting was fixed

## [2.5.2] - 2020-10-22

### Fixed

#### Frontend

- error introduced in **2.5.0** leading to charts not respecting selected date range was fixed

## [2.5.1] - 2020-10-21

### Changes

#### Backend

- scheduling of recache renewals was changed to get around multiplication of renewal tasks observed
  in production

## [2.5.0] - 2020-10-15

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

## [2.4.1] - 2020-10-09

### Changes

#### Frontend

- year-to-year comparison chart was reworked to reduce the number of colors and make it more
  readable
- title names are shortened in cards on dashboard page

## [2.4.0] - 2020-10-06

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

## [2.3.1] - 2020-09-24

### Added

#### Backend

- preliminary support for centralized source of data for CELUS (CELUS brain) was added

### Fixes

#### Frontend

- it was not possible to save credentials with title after running the test without changing
  the title

#### Backend

- properly report attempts to fetch SUSHI data that span more than one month in the monthly overview (SUSHI status)

## [2.3.0] - 2020-09-18

### Added

#### Frontend

- show CELUS version number in the side-panel
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

- language not active for specific CELUS installation cannot become users default language
- when synchronizing users with ERMS, properly disconnect organizations when user is no longer
  associated with them
- recache did not properly check for Django version when looking for cached data

## [2.2.1] - 2020-09-07

### Fixes

#### Backend

- Error in SUSHI download retrial was fixed

## [2.2.0] - 2020-09-03

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

## [2.1.2] - 2020-08-20

### Fixes

- fix metric display in charts - remapping should not be shown the same way as in the admin
- fix storing of TSV files instead of raw XML for successful C4 attempts

## [2.1.1] - 2020-08-19

### Fixes

- fix mismatch of version hash between credentials and attempts causing
  incorrect display of attempt status on SUSHI downloads page

## [2.1.0] - 2020-08-18

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
