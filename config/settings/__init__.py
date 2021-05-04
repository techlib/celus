import re

from pathlib import Path


def get_version(base_dir: Path) -> str:
    try:
        with (base_dir / "pyproject.toml").open() as f:
            for line in f.readlines():
                match = re.match(r'^version\s+=\s+"([^"]+)"$', line.strip())
                if match:
                    return match.group(1)

    except Exception as e:
        raise RuntimeError("Failed to read pyproject.toml") from e

    raise RuntimeError("Version not found in pyproject.toml")
