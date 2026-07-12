from olden_db.parser import parse_city_directory
from olden_db.paths import require_city_directory


def main() -> None:
    city_dir = require_city_directory()

    print(f"Loading city files from:\n  {city_dir}\n")

    db = parse_city_directory(city_dir)

    print(f"Loaded {len(db.cities)} factions.\n")

    for faction in sorted(db.cities):
        city = db.city(faction)

        print("=" * 70)
        print(f"Faction: {city.faction}")
        print(f"City ID: {city.city_id}")
        print(f"Building levels parsed: {len(city.buildings)}")
        print()

        for building in sorted(city.buildings.values(), key=lambda b: (b.key.sid, b.key.level)):
            print(f"{building.key.sid} (Level {building.key.level})")
            print(f"  Category: {building.category}")
            print(f"  Cost: {building.cost.as_dict()}")

            if building.prerequisites:
                print("  Immediate prerequisites:")
                for prereq in building.prerequisites:
                    print(f"    - {prereq.sid} (Level {prereq.level})")
            else:
                print("  Immediate prerequisites: None")

            if building.unit_family:
                uf = building.unit_family
                print("  Unit family:")
                print(f"    Base: {uf.base_sid}")
                print(f"    Upgrade A: {uf.upgrade_option_1_sid}")
                print(f"    Upgrade B: {uf.upgrade_option_2_sid}")
                print(f"    Weekly growth: {uf.weekly_growth}")

            print()

    print("Parser test completed successfully.")


if __name__ == "__main__":
    main()
