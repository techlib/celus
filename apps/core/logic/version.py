import pathlib
import toml


def celus_version() -> str:
    """ Returns current celus version """
    path = pathlib.Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    with path.open() as f:
        data = toml.load(f)
        return data["tool"]["poetry"]["version"]
