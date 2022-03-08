class DataStructureError(ValueError):
    """
    Exception signalling that there is something wrong in the data saved to the database
    - might be missing data, conflict with existing data, etc.
    """


class SourceFileMissingError(Exception):
    """
    Used in re-importing code if is finds that the file to read is not there
    """


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
