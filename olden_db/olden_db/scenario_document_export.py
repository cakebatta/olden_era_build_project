from __future__ import annotations
import os, tempfile
from pathlib import Path
from .scenario_persistence import ScenarioConflictError, ScenarioDocument, ScenarioStorageError, serialize_scenario_document_bytes

def export_scenario_document(document: ScenarioDocument, destination: str | Path, *, overwrite: bool=False) -> ScenarioDocument:
    path=Path(destination)
    if path.exists() and not overwrite:
        raise ScenarioConflictError(f"Export destination already exists: {path.name}")
    if path.exists() and path.is_symlink():
        raise ScenarioStorageError("Refusing to overwrite a symlink export destination")
    data=serialize_scenario_document_bytes(document)
    temp_name=None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as temp:
            temp_name=temp.name
            temp.write(data); temp.flush(); os.fsync(temp.fileno())
        os.replace(temp_name, path); temp_name=None
    except OSError as exc:
        raise ScenarioStorageError(f"Unable to export scenario to {path.name}") from exc
    finally:
        if temp_name:
            try: Path(temp_name).unlink(missing_ok=True)
            except OSError: pass
    return document
