
# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


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
