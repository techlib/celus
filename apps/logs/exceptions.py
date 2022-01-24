class DataStructureError(ValueError):
    """
    Exception signalling that there is something wrong in the data saved to the database
    - might be missing data, conflict with existing data, etc.
    """

    ...
