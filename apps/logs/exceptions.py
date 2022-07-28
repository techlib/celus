class DataStructureError(ValueError):
    """
    Exception signalling that there is something wrong in the data saved to the database
    - might be missing data, conflict with existing data, etc.
    """


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
