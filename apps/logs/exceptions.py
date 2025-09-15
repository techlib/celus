class DataStructureError(ValueError):
    """
    Exception signalling that there is something wrong in the data saved to the database
    - might be missing data, conflict with existing data, etc.
    """


class DataAlreadyPresent(DataStructureError):
    """
    Exception signalling that the data is already present in the database from some other source
    """

    def __init__(self, import_batch, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.import_batch = import_batch


class SourceFileMissingError(Exception):
    """
    Used in re-importing code if is finds that the file to read is not there
    """

    def __init__(self, filename, size, checksum, *args: object) -> None:
        super().__init__(*args)
        self.filename = filename
        self.size = size
        self.checksum = checksum


class WrongState(RuntimeError):
    """
    Exception which occurs when model is in state not suitable to perform request action
    e.g. transition from state to state
    """


class UnknownMetric(Exception):
    """
    Raised during import when unexisting metric is found.
    used only when AUTOMATICALLY_CREATE_METRICS=False
    """


class UnsupportedMetric(Exception):
    """
    Raised when unsupported metric for report type is found during import.
    """


class ImportNotPossible(Exception):
    """
    Raised when an import is request for ManualDataUpload which can't be imported
    """


class OrganizationNotFound(Exception):
    """
    Raised when organization is not found during the import
    """

    def __init__(self, organization):
        super().__init__(organization)
        self.organization = organization


class OrganizationNotAllowedToImportRawData(Exception):
    """
    Raised when organization not allowed to import raw data
    """

    def __init__(self, organization):
        super().__init__(organization)
        self.organization = organization


class MultipleOrganizationsFound(Exception):
    """
    Raised when there are multiple organizations matching the short_name during the import
    """

    def __init__(self, organization):
        super().__init__(organization)
        self.organization = organization


class WrongOrganizations(Exception):
    """
    Unable to resolve organizations from a file
    """

    def __init__(self, organizations):
        self.organizations = organizations
        super().__init__(organizations)


class OrganizationHasToBeSelected(Exception):
    """
    Organization has to be selected for raw imports
    """


class PreflightFailed(Exception):
    """
    Exception which occurs during the preflight phase
    """


class UnknownReportTypeInPreflight(PreflightFailed):
    """
    ReportType from nibbler is not known in this CELUS
    """


class MultipleReportTypes(PreflightFailed):
    """
    ReportType from nibbler matches multiple reportype in this CELUS
    """

    def __init__(self, report_types):
        super().__init__("Multiple ReportTypes found in the data")
        self.report_types = report_types


class UnsupportedReportType(PreflightFailed):
    def __init__(self, report_type_names):
        super().__init__(f"Can't resolve {''.join(report_type_names)} to ReportType")
        self.report_type_names = report_type_names


class NibblerErrors(Exception):
    """
    Nibbler error wrapper
    It may occur during the preflight or during data import phase of processing MDU
    """

    def __init__(self, errors):
        super().__init__(errors)
        self.errors = errors


class ReportDataValidityError(Exception):
    """
    Data inside a report are not valid (not conforming to the CoP) to such an extent that the report
    cannot be ingested and the report type should be marked as broken.
    """


class WhitelistingError(Exception):
    """
    Exception raised when a report type requires whitelisting but is not whitelisted
    for the platform in the knowledgebase.
    """
