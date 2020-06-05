import json


def load_secret_settings_json_file(filename: str) -> dict:
    """
    Is used for loading of settings from a json file
    """
    result = {}
    try:
        with open(filename, 'r') as secretf:
            secret_settings = json.load(secretf)
    except FileNotFoundError:
        raise ValueError("The settings file '{0}' is missing!".format(filename))
    for name in ("SECRET_KEY", "DB_PASSWORD"):
        value = secret_settings.get(name, None)
        if value is None:
            raise ValueError(
                "Required secret setting {0} missing from file {1}".format(name, filename)
            )
        result[name] = value
    # the following loads all the not required settings silently and passes them to the caller
    for key, value in secret_settings.items():
        if key not in result:
            result[key] = value
    return result
