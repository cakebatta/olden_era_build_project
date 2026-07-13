from __future__ import annotations

from olden_db.csv_export import export_validation_csvs
from olden_db.database import load_default_game_data
from olden_db.paths import require_output_directory


def main() -> None:
    output_directory = require_output_directory() / "validation_csv"
    paths = export_validation_csvs(load_default_game_data(), output_directory)

    print("Validation CSV export completed:")
    print(f"  Buildings:        {paths.buildings}")
    print(f"  Units:            {paths.units}")
    print(f"  Dependency graph: {paths.dependency_graph}")
    print(f"  Planner output:   {paths.representative_plan}")


if __name__ == "__main__":
    main()
