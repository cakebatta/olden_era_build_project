from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORE_DIR = PROJECT_ROOT / "Core"
CORE_ARCHIVE = PROJECT_ROOT / "Core.zip"

CITY_DIR = CORE_DIR / "DB" / "objects_logic" / "cities"

UNIT_LOGIC_DIR = CORE_DIR / "DB" / "units" / "units_logics"
UNIT_LOGIC_ZIP = UNIT_LOGIC_DIR / "unit_logic.zip"

OUTPUT_DIR = PROJECT_ROOT / "output"


def require_city_directory() -> Path:
    """Return CITY_DIR or raise a clear error if it is unavailable."""
    if not CITY_DIR.is_dir():
        raise FileNotFoundError(
            "City data directory was not found. Expected:\n"
            f"  {CITY_DIR}"
        )
    return CITY_DIR


def require_unit_logic_source() -> Path:
    """
    Return the canonical unit-logic source.

    Prefer the ZIP archive when present. Fall back to the extracted directory
    when it contains JSON files.
    """
    if UNIT_LOGIC_ZIP.is_file():
        return UNIT_LOGIC_ZIP

    if UNIT_LOGIC_DIR.is_dir() and any(UNIT_LOGIC_DIR.rglob("*.json")):
        return UNIT_LOGIC_DIR

    raise FileNotFoundError(
        "Unit logic was not found. Expected either:\n"
        f"  ZIP:       {UNIT_LOGIC_ZIP}\n"
        f"  Directory: {UNIT_LOGIC_DIR}"
    )


def require_output_directory(*, create: bool = True) -> Path:
    """Return OUTPUT_DIR, optionally creating it when absent."""
    if create:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    elif not OUTPUT_DIR.is_dir():
        raise FileNotFoundError(
            "Output directory was not found. Expected:\n"
            f"  {OUTPUT_DIR}"
        )
    return OUTPUT_DIR
