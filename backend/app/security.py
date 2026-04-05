from pathlib import Path


def safe_filename(name: str) -> str:
    return Path(name).name
