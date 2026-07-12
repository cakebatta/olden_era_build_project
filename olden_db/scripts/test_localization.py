from __future__ import annotations

from olden_db.localization import parse_localization_file
from olden_db.paths import require_english_cities_localization_file


REPRESENTATIVE_KEYS = {
    "human_name": "Temple",
    "undead_name": "Necropolis",
    "nature_name": "Grove",
    "demon_name": "Hive",
    "unfrozen_name": "Schism",
    "dungeon_name": "Dungeon",
    "Undead_Build_Tier_4_name_level_1": "Bone Exchange",
    "Undead_Build_Tier_4_name_level_2": "Bone Exchange II",
    "Human_Build_Market_name": "Marketplace",
}


def main() -> None:
    localization_file = require_english_cities_localization_file()

    print(f"Loading English city localization from:\n  {localization_file}\n")

    catalog = parse_localization_file(
        localization_file,
        language="english",
    )

    print("=" * 80)
    print("Localization summary")
    print("=" * 80)
    print(f"Language: {catalog.language}")
    print(f"Tokens loaded: {len(catalog.tokens)}")
    print()

    print("Representative localization checks")

    for sid, expected_text in REPRESENTATIVE_KEYS.items():
        actual_text = catalog.get(sid)
        print(f"  {sid}")
        print(f"    {actual_text}")

        if actual_text != expected_text:
            raise RuntimeError(
                f"Unexpected text for {sid!r}: "
                f"{actual_text!r} != {expected_text!r}"
            )

    print()

    missing_sid = "definitely_missing_localization_sid"
    if catalog.resolve(missing_sid) != missing_sid:
        raise RuntimeError("Missing SID fallback did not preserve the SID")

    if catalog.resolve(None, fallback="Unknown") != "Unknown":
        raise RuntimeError("None fallback did not return the supplied value")

    print("Localization test completed successfully.")
    print("English city and building localization tokens resolve correctly.")


if __name__ == "__main__":
    main()
