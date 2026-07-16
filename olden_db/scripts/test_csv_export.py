from __future__ import annotations

import csv
import tempfile
from pathlib import PurePosixPath

from olden_db.constants import RESOURCE_NAMES
from olden_db.csv_export import export_validation_csvs
from olden_db.database import PLAYABLE_FACTIONS, load_default_game_data


def main() -> None:
    data = load_default_game_data()

    with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
        first = export_validation_csvs(data, first_directory)
        second = export_validation_csvs(data, second_directory)

        for first_path, second_path in (
            (first.buildings, second.buildings),
            (first.units, second.units),
            (first.dependency_graph, second.dependency_graph),
            (first.representative_plan, second.representative_plan),
        ):
            if first_path.read_bytes() != second_path.read_bytes():
                raise RuntimeError(
                    f"Repeated export was not byte-for-byte identical: {first_path.name}"
                )

        with first.units.open("r", encoding="utf-8", newline="") as file:
            unit_rows = tuple(csv.DictReader(file))
        with first.buildings.open("r", encoding="utf-8", newline="") as file:
            building_reader = csv.DictReader(file)
            building_fields = tuple(building_reader.fieldnames or ())
            building_rows = tuple(building_reader)

    if not unit_rows:
        raise RuntimeError("units.csv did not contain any unit rows")

    for row in unit_rows:
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

    expected_income_fields = tuple(f"income_{name}" for name in RESOURCE_NAMES)
    if not all(field in building_fields for field in expected_income_fields):
        raise RuntimeError("buildings.csv is missing normalized income columns")

    for faction in PLAYABLE_FACTIONS:
        rows = {
            int(row["level"]): row
            for row in building_rows
            if row["faction"] == faction and row["sid"] == "Build_Main"
        }
        for level, expected_gold in ((1, 500), (2, 750), (3, 1000)):
            row = rows.get(level)
            if row is None:
                raise RuntimeError(f"Missing exported income row: {faction}/Build_Main L{level}")
            if int(row["income_gold"]) != expected_gold:
                raise RuntimeError(f"Incorrect exported income for {faction}/Build_Main L{level}")
            for name in RESOURCE_NAMES:
                if name != "gold" and int(row[f"income_{name}"]) != 0:
                    raise RuntimeError("Unrelated income resource was nonzero in CSV")

    print("CSV export validation completed successfully.")
    print(f"Validated {len(unit_rows)} unit source paths.")
    print("Building income was exported in deterministic canonical resource columns.")
    print("Repeated exports were byte-for-byte identical.")
    print("All exported source paths are logical, relative, and use POSIX separators.")


if __name__ == "__main__":
    main()
