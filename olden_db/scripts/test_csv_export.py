from __future__ import annotations

import csv
import tempfile
from pathlib import PurePosixPath

from olden_db.csv_export import export_validation_csvs
from olden_db.database import load_default_game_data


def main() -> None:
    data = load_default_game_data()

    with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
        first = export_validation_csvs(data, first_directory)
        second = export_validation_csvs(data, second_directory)

        if first.units.read_bytes() != second.units.read_bytes():
            raise RuntimeError("Repeated unit exports were not byte-for-byte identical")

        with first.units.open("r", encoding="utf-8", newline="") as file:
            rows = tuple(csv.DictReader(file))

    if not rows:
        raise RuntimeError("units.csv did not contain any unit rows")

    for row in rows:
        source = row["source"]
        archive_path, _, member_path = source.partition("!")

        if not source:
            raise RuntimeError(f"Unit {row['sid']!r} exported an empty source")
        if "\\" in source:
            raise RuntimeError(f"Unit {row['sid']!r} exported Windows separators: {source!r}")
        if PurePosixPath(archive_path).is_absolute():
            raise RuntimeError(f"Unit {row['sid']!r} exported an absolute source: {source!r}")
        if len(archive_path) >= 2 and archive_path[1] == ":":
            raise RuntimeError(f"Unit {row['sid']!r} exported a drive-qualified source: {source!r}")
        if member_path and PurePosixPath(member_path).is_absolute():
            raise RuntimeError(f"Unit {row['sid']!r} exported an absolute archive member: {source!r}")

    print("CSV export source-path validation completed successfully.")
    print(f"Validated {len(rows)} unit source paths.")
    print("Repeated exports were byte-for-byte identical.")
    print("All exported source paths are logical, relative, and use POSIX separators.")


if __name__ == "__main__":
    main()
