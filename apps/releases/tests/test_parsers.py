import pytest
from releases.parsers import parse_changelog

changelog_temp = """
        # Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

{before_changelog}

## [5.2.0] - 2023-01-18

### Added

#### Frontend

- Added a new feature to the frontend


## [5.1.1] - 2023-01-05

### Fixed

#### Frontend

- Fixed a bug in the frontend


## [5.1.0] - 2022-12-19

### Added

#### Frontend

- Added a new feature to the frontend
- Added another new feature to the frontend

### Changes

#### Frontend

- Changed the frontend to use a new API
        """


class TestChangelogParsing:
    def test_without_unreleased(self):
        changelog = changelog_temp.format(before_changelog="")
        releases = parse_changelog(changelog)
        assert len(releases) == 3
        assert releases[0]["version"] == "5.2.0"
        assert releases[0]["date"] == "2023-01-18"
        assert releases[2]["version"] == "5.1.0"
        assert releases[2]["date"] == "2022-12-19"

    def test_with_unreleased(self):
        changelog = changelog_temp.format(
            before_changelog="## [Unreleased]\n\n### Added\n\n- Added a new feature\n"
        )
        releases = parse_changelog(changelog)
        assert len(releases) == 4
        assert releases[0]["version"] == "Unreleased"
        assert releases[0]["date"] is None
        assert releases[1]["version"] == "5.2.0"
        assert releases[1]["date"] == "2023-01-18"
        assert releases[3]["version"] == "5.1.0"
        assert releases[3]["date"] == "2022-12-19"

    def test_incorrect_format_1(self):
        """
        Only `Unreleased` is allowed if it is not a numbered version.
        """
        changelog = changelog_temp.format(
            before_changelog="## [Not yet released]\n\n### Added\n\n- Added a new feature\n"
        )
        with pytest.raises(ValueError):
            parse_changelog(changelog)

    @pytest.mark.parametrize(
        'text',
        [
            "## [Foo]\n\n### Added",
            "## [6.3.3] - Jan 20, 2022\n\n### Added",
            "## [6.3.3] - not released\n\n### Added",
        ],
    )
    def test_incorrect_formats(self, text):
        """
        Test some more incorrect formats.
        For example the date must be correct or missing completely.
        """
        with pytest.raises(ValueError):
            parse_changelog(text)
