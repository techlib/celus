
# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.4]

### Fixed

#### Frontend

* test for `/report/` as part of SUSHI URL was fixed to prevent false positives like
  `https::/report.foo.bar/`
* platform `short_name` is used if `name` is blank to prevent showing platforms with blank name
* tooltip for icons in SUSHI status was fixed

### Changes

#### Backend

* the API to get status of "fetch attempts" was removed in favor of "fetch intentions" (is related
  to the above fix of tooltips)
* server log messages about user identity were changed from `error` to `debug` importance


## [3.2.3]

### Fixed

#### Backend

* invitation links were fixed after switch to dj-rest-auth broke their functionality
* fix scheduling of FetchIntentions added by migration for older FetchAttempts - fixes overload
  of celery by endless stream of tasks without effect

### Changes

#### Backend

* expiration was added to all celery tasks planned by celerybeat to avoid accumulation of tasks in
  queue if celery does not handle them quickly enough
* harvest API endpoint was optimized for speed



## [3.2.2]

### Fixed

#### Frontend

* clicking on individual downloads on the monthly overview page displayed details for incorrect
  download


## [3.2.1]

### Added

#### Backend

* API keys are now automatically exported to knowledgebase server

### Changes

#### Backend

* Django was upgraded from the 3.1 to the 3.2 branch


## [3.2.0]

### Added

#### Frontend

* all COUNTER reports are offered for manual upload - regardless if they define interest or not

#### Backend

* it is now possible to export SUSHI credentials from the Django admin
* API key based authentication for specific API endpoints was implemented
* API endpoint for access to "raw" data for individual reports was added with API key access

### Changes

#### Backend

* speed up loading of list of manual uploads by identifying import batches with their IDs only
* the API and related code for SUSHI harvesting was cleaned up by removing unused/obsolete code
* internal working of fetch attempt state was changed from several booleans into a progression of
  specific states
* replace django-rest-auth with dj-reset-auth
* manual data upload model was added into Django admin
* do not cache queries with empty result - removes delay between first data is harvested and
  displayed for new users
* list of platforms for an organization was made accessible using API key authentication
* deployment of requirements using requirements files for pip was dropped in favor of poetry


### Fixed

#### Frontend

* the registration link did not properly work on first load

#### Backend

* the celery task for updating approximate number of records for a report type was not correctly
  scheduled
* do not respond by server error when user creates a platform with `short_name` that is already used
* parsing of exceptions from COUNTER 5 table format was made more robust
* code to derive SUSHI exception severity from a response was made more robust


## [3.1.1]


### Changes

#### Frontend

* some less important columns are hidded from the SUSHI management page on smaller screens
* year selection for harvesting of SUSHI data was limited to years after 2010

### Fixed

#### Frontend

* slow loading of SUSHI fetch attempt data was fixed by using server-side pagination

#### Backend

* users with organization admin privileges are no longer denied access when manually importing data
* automatic deduction of title type using ISBN and ISSN was fixed to work in more cases,
  most notably for manually uploaded data
* performance of several API endpoints was fixed by optimizing the number of database queries
* data for SUSHI overview are correctly serialized even if harvested year is lower than 2000
* state of SUSHI fetch attempts marked as crashed because they were already imported was fixed
  (it no longer shows as crashed)


## [3.1.0]

### Added

#### Frontend

* buttons for immediate harvesting and cancellation of harvests planned for later were added
* partial-data status was added to `FetchAttempt` information
* Celus frontend now checks the version of the backend and forces refresh if the versions do not
  match

#### Backend

* support for IR_M1 report was added
* ability to trigger postponed re-imports via celery was added to Django admin

### Changes

#### Frontend

* harvest list view was extended and improved
* the 'Harvest selected' button on 'SUSH management page' was changed for better visibility
* all views were updated to stretch to the whole available space where the UI benefits from it
* empty harvests were hidden from harvest views
* obsolete `Attempt overview` view was removed from the UI
* the name of the organization created by the user after registration is limited to 100 characters
* user-created platforms and report types are marked with a special badge for easy recognition
* if a status filter is active on the sushi monthly overview page, it is automatically disabled
  when month is changed if there are no records with this status for the newly selected month

#### Backend

* Celery task locking was switched from Redis-based locks to database locks where appropriate
* extra whitespace is stripped from string values imported from C5 tabular format
* obsolete backend code related to the `Attempt overview` view was removed
* database unique constrains for `short_name` and `source` were reworked
* a Django setting was added to selectively allow manual upload of COUNTER data only
* speed and number of queries for listing harvest intentions was optimized

### Fixed

#### Frontend

* when changing selected organization, the list of available platforms on the `manual upload` page
  is automatically refreshed
* date related filters were not copied when a report was copied
* 'untried' fetch-intention status was fixed to actually work
* sushi monthly overview no longer prematurely hides the loading progress bar which was confusing

#### Backend

* harvests planning for the current month was fixed


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

* advanced reporting module - allows creation of custom reports by selecting desired output
  rows and columns with possible filtering.
* per credentials overview of harvested data was added. It shows harvests by years and allows
  quick reharvesting of missing data.
* it is now possible to create and edit platforms in the UI

#### Backend

* support for reading COUNTER 5 reports in table format was added
* management command for detection of conflicting import batches was added
* management command for removal of empty fetch attempts was added
* management command for removal of obsolete platform-title links

### Changes

#### Frontend

* the left sidebar was reworked using collapsible entries to save space
* harvest overview was extended with more information
* it is now possible to only download data for one month using the "Save and test" button in
  the SUSHI credentials edit dialog
* when using the "Harvest selected" button for manual harvesting, the harvest is split into
  separate downloads for individual months
* crashed data imports are now marked as a distinct state with its own icon

#### Backend

* harvest scheduling was switched to the new system by default. This means that future harvests
  are planned automatically in advance and past data have to be explicitly harvested by the user.
* HTTP authentication information was removed from COUNTER 5 SUSHI credentials as it is not used
  there
* better handling of SUSHI exceptions 1030, 2010 and 3060 was added. Errors 1030 and 2010 causes
  credentials to be marked as broken
* scheduler admin was improved

### Fixed

#### Frontend

* fix reporting of used metrics for interest related charts when materialized reports are used
  in the background
* harvest view was optimized for speed
* error when clearing search text on SUSHI management page using the "x" icon was fixed
* error which caused reports types sometimes not appearing when editing SUSHI credentials was fixed

#### Backend

* update Cachalot to a newer version containing our fix for temporary disabling of Cachalot
  - fixes memory problems when exporting large amounts of raw data
* fix for error causing users to be disconnected from their organizations upon login of other user
  when live ERMS sync was used was ported from 1.0.x
* database constraints enforcing uniqueness in combination with `source` were fixed to properly
  handle `source` being null.
* scheduling of harvests for new months was fixed to wait until month end before attempting
  to harvest data for that month
* reevaluation of queries by recache was fixed - it did not occur because of wrong celery config



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
