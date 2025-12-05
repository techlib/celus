"""
Report definitions are stored as YAML files in the reports subdirectory.
Each YAML file defines a single report with its data sources and parts.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Get the reports directory path relative to this file
_REPORTS_DIR = Path(__file__).parent.parent / "reports"


def get_reports() -> list[dict]:
    """
    Load all report definitions from YAML files in the reports directory.
    Returns a list of report dictionaries, sorted by position.
    """
    reports = []

    if not _REPORTS_DIR.exists():
        logger.warning(f"Reports directory not found: {_REPORTS_DIR}")
        return reports

    # Load all YAML files from the reports directory
    for yaml_file in sorted(_REPORTS_DIR.glob("*.yaml")):
        try:
            with yaml_file.open("rt", encoding="utf-8") as f:
                if report := yaml.safe_load(f):
                    reports.append(report)
        except Exception as e:
            logger.error(f"Failed to load report from {yaml_file}: {e}", exc_info=True)

    # Sort by position (default to 999 if position is not specified)
    reports.sort(key=lambda r: r.get("position", 999))

    return reports


def get_report_def_by_name(name: str) -> dict | None:
    """
    Get a report definition by its name.
    Returns the report dictionary if found, None otherwise.
    """
    for report in get_reports():
        if report.get("name") == name:
            return report
    return None
