from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from olden_db.models import ResourceCost
from olden_db.scenario_persistence import (
    LocalScenarioRepository,
    ScenarioConflictError,
    ScenarioNotFoundError,
    ScenarioStorageError,
    create_scenario_document,
    serialize_scenario_document_bytes,
)

T0 = datetime(2026, 7, 16, 22, 30, tzinfo=timezone.utc)
T1 = datetime(2026, 7, 16, 22, 31, tzinfo=timezone.utc)
T2 = datetime(2026, 7, 16, 22, 32, tzinfo=timezone.utc)
ID1 = UUID("33333333-3333-4333-8333-333333333333")
ID2 = UUID("44444444-4444-4444-8444-444444444444")
ID3 = UUID("55555555-5555-4555-8555-555555555555")
ID4 = UUID("66666666-6666-4666-8666-666666666666")


def main() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary) / "repository"
        repository = LocalScenarioRepository(root)
        original = create_scenario_document(
            name="Duplicate Name", faction="human", target_sid="Build_Main", target_level=1,
            now=T0, scenario_id_factory=lambda: ID1, starting_resources=ResourceCost(gold=100),
        )
        saved = repository.save_scenario(original, expected_token=None, now=T0)
        expected_path = root / "scenarios" / f"{ID1}.json"
        if not expected_path.exists():
            raise RuntimeError("Repository did not use UUID-owned filename")
        loaded = repository.get_scenario(ID1)
        if loaded.document != saved.document or loaded.conflict_token != saved.conflict_token:
            raise RuntimeError("Saved scenario did not retrieve exactly")

        second = create_scenario_document(
            name="Duplicate Name", faction="human", target_sid="Build_Main", target_level=1,
            now=T0, scenario_id_factory=lambda: ID2,
        )
        repository.save_scenario(second, expected_token=None, now=T0)
        if len(repository.list_scenarios().scenarios) != 2:
            raise RuntimeError("Duplicate display names were not supported")

        edited = replace(loaded.document, name="Renamed")
        updated = repository.save_scenario(edited, expected_token=loaded.conflict_token, now=T1)
        if updated.document.scenario_id != ID1 or updated.document.created_at != T0:
            raise RuntimeError("Update changed identity or creation timestamp")
        if updated.document.modified_at != T1:
            raise RuntimeError("Successful content save did not update modified_at")
        _expect(ScenarioConflictError, lambda: repository.save_scenario(
            replace(loaded.document, notes="stale"), expected_token=loaded.conflict_token, now=T2))

        before_failure = expected_path.read_bytes()
        original_atomic = repository._atomic_write
        repository._atomic_write = lambda path, data: (_ for _ in ()).throw(ScenarioStorageError("simulated write failure"))
        try:
            _expect(ScenarioStorageError, lambda: repository.save_scenario(
                replace(updated.document, notes="will fail"), expected_token=updated.conflict_token, now=T2))
        finally:
            repository._atomic_write = original_atomic
        if expected_path.read_bytes() != before_failure:
            raise RuntimeError("Failed atomic save damaged the prior valid file")

        malformed = root / "scenarios" / f"{ID3}.json"
        malformed.write_text("{broken", encoding="utf-8")
        listing = repository.list_scenarios()
        if len(listing.scenarios) != 2 or len(listing.diagnostics) != 1:
            raise RuntimeError("Malformed entry blocked valid listing or lacked diagnostics")

        export_path = Path(temporary) / "export.json"
        exported = repository.export_scenario(ID1, export_path)
        if exported != updated.document:
            raise RuntimeError("Export did not preserve managed document metadata")
        after_export = repository.get_scenario(ID1)
        if (
            after_export.document != updated.document
            or after_export.conflict_token != updated.conflict_token
        ):
            raise RuntimeError("Export mutated repository state")
        _expect(ScenarioConflictError, lambda: repository.export_scenario(ID1, export_path))
        repository.export_scenario(ID1, export_path, overwrite=True)

        import_source = Path(temporary) / "external-any-name.json"
        import_source.write_bytes(serialize_scenario_document_bytes(updated.document))
        imported = repository.import_scenario(import_source, now=T2, scenario_id_factory=lambda: ID4)
        if imported.document.scenario_id != ID4 or imported.document.created_at != T2 or imported.document.modified_at != T2:
            raise RuntimeError("Import-as-copy did not generate identity and timestamps")
        if imported.document.name != updated.document.name or imported.document.target != updated.document.target:
            raise RuntimeError("Import-as-copy did not preserve user-authored content")
        if not (root / "scenarios" / f"{ID4}.json").exists():
            raise RuntimeError("Imported display/source name affected managed path")

        invalid_source = Path(temporary) / "invalid.json"
        invalid_source.write_text("{broken", encoding="utf-8")
        count_before = len(repository.list_scenarios().scenarios)
        try:
            repository.import_scenario(invalid_source, now=T2)
        except Exception:
            pass
        else:
            raise RuntimeError("Invalid import unexpectedly succeeded")
        if len(repository.list_scenarios().scenarios) != count_before:
            raise RuntimeError("Failed import mutated repository")

        repository.delete_scenario(ID2)
        _expect(ScenarioNotFoundError, lambda: repository.get_scenario(ID2))
        _expect(ScenarioNotFoundError, lambda: repository.delete_scenario(ID2))

        outside = Path(temporary) / "outside.json"
        if outside.exists():
            raise RuntimeError("Unexpected outside file before isolation check")
        for path in root.rglob("*.json"):
            if root not in path.parents:
                raise RuntimeError("Repository wrote outside configured root")

    print("Scenario repository validation completed successfully.")
    print("UUID-owned save, retrieve, update, delete, and duplicate-name behavior succeeded.")
    print("SHA-256 conflict tokens rejected stale saves.")
    print("Simulated atomic-write failure preserved the previous canonical file.")
    print("Malformed entries produced diagnostics without hiding valid scenarios.")
    print("Import-as-copy and non-mutating portable export succeeded.")
    print("Repository writes remained inside the configured root.")


def _expect(error_type, operation):
    try:
        operation()
    except error_type:
        return
    raise RuntimeError(f"Expected {error_type.__name__}")


if __name__ == "__main__":
    main()
