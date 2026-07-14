from __future__ import annotations

from olden_db.desktop.formatting import format_faction_status
from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState


class StubQueryService:
    def list_factions(self) -> tuple[str, ...]:
        return ("demon", "nature")


class StubView:
    pass


def main() -> None:
    state = PlannerState()
    statuses: list[str] = []

    presenter = PlannerPresenter(
        service=StubQueryService(),  # type: ignore[arg-type]
        state=state,
        view=StubView(),
        set_status=statuses.append,
    )
    presenter.initialize()

    if statuses != ["Ready — 2 factions available."]:
        raise RuntimeError(f"Unexpected initial desktop status: {statuses!r}")

    if format_faction_status(1) != "Ready — 1 faction available.":
        raise RuntimeError("Singular faction status formatting was incorrect")

    if state != PlannerState():
        raise RuntimeError("Desktop initialization unexpectedly changed selection state")

    print("Desktop skeleton validation completed successfully.")
    print("Presenter initialized through Query Layer discovery.")
    print("Initial planner selection state remained empty.")


if __name__ == "__main__":
    main()
