from __future__ import annotations


def format_faction_status(faction_count: int) -> str:
    """Return the initial status message after faction discovery."""

    noun = "faction" if faction_count == 1 else "factions"
    return f"Ready — {faction_count} {noun} available."
