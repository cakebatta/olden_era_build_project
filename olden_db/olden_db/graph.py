from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from .models import BuildingKey, FactionCity


class GraphError(ValueError):
    """Base exception for dependency-graph errors."""


class MissingBuildingError(GraphError):
    """Raised when a target or prerequisite is absent from the parsed city."""


class DependencyCycleError(GraphError):
    """Raised when the city data contains a prerequisite cycle."""


class TopologicalOrderLimitError(GraphError):
    """Raised when topological-order generation exceeds an imposed limit."""


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    """
    The constructible prerequisite subgraph for one target building level.

    `nodes` contains only building levels that require construction. Buildings
    available at game start are treated as satisfied boundary nodes and are
    recorded separately in `satisfied_starting_nodes`.

    `prerequisites[node]` contains only prerequisites that also require
    construction. `dependents[node]` contains the reverse edges.
    """

    faction: str
    target: BuildingKey
    nodes: frozenset[BuildingKey]
    prerequisites: dict[BuildingKey, frozenset[BuildingKey]]
    dependents: dict[BuildingKey, frozenset[BuildingKey]]
    satisfied_starting_nodes: frozenset[BuildingKey]

    def __post_init__(self) -> None:
        if self.target.faction != self.faction:
            raise ValueError("target faction does not match graph faction")

        if (
            self.target not in self.nodes
            and self.target not in self.satisfied_starting_nodes
        ):
            raise ValueError(
                "target must be present in the graph or already satisfied"
            )

        if set(self.prerequisites) != set(self.nodes):
            raise ValueError(
                "prerequisites must contain exactly one entry per graph node"
            )

        if set(self.dependents) != set(self.nodes):
            raise ValueError(
                "dependents must contain exactly one entry per graph node"
            )

        for node, required in self.prerequisites.items():
            if not required.issubset(self.nodes):
                raise ValueError(
                    f"Prerequisites for {node} contain nodes outside the graph"
                )

        for node, downstream in self.dependents.items():
            if not downstream.issubset(self.nodes):
                raise ValueError(
                    f"Dependents for {node} contain nodes outside the graph"
                )

    @property
    def build_actions(self) -> int:
        """Number of building actions required to complete the target."""
        return len(self.nodes)

    @property
    def target_is_already_constructed(self) -> bool:
        """Whether the selected target is available at game start."""
        return self.target in self.satisfied_starting_nodes


def build_dependency_graph(
    city: FactionCity,
    target: BuildingKey,
    *,
    starting_buildings: frozenset[BuildingKey] | None = None,
) -> DependencyGraph:
    """
    Build the prerequisite DAG needed for `target`.

    When `starting_buildings` is omitted, canonical `constructed_on_start`
    values define starting availability. When supplied, that explicit set is
    authoritative, including when it is empty.
    """
    if target.faction != city.faction:
        raise GraphError(
            f"Target faction {target.faction!r} does not match city faction "
            f"{city.faction!r}"
        )

    if target not in city.buildings:
        raise MissingBuildingError(f"Unknown target building node: {target}")

    if starting_buildings is None:
        effective_starting = frozenset(
            key
            for key, building in city.buildings.items()
            if building.constructed_on_start
        )
    else:
        effective_starting = frozenset(starting_buildings)
        for key in effective_starting:
            if key.faction != city.faction:
                raise GraphError(
                    f"Starting building faction {key.faction!r} does not match "
                    f"city faction {city.faction!r}: {key}"
                )
            if key not in city.buildings:
                raise MissingBuildingError(
                    f"Unknown starting building node: {key}"
                )

    required_nodes: set[BuildingKey] = set()
    satisfied_starting: set[BuildingKey] = set()
    visiting: list[BuildingKey] = []
    visited: set[BuildingKey] = set()

    def visit(node: BuildingKey) -> None:
        if node in visited:
            return

        if node not in city.buildings:
            parent = visiting[-1] if visiting else target
            raise MissingBuildingError(
                f"Missing prerequisite node {node} referenced by {parent}"
            )

        if node in visiting:
            cycle_start = visiting.index(node)
            cycle = visiting[cycle_start:] + [node]
            cycle_text = " -> ".join(
                f"{item.sid} L{item.level}" for item in cycle
            )
            raise DependencyCycleError(
                f"Dependency cycle detected: {cycle_text}"
            )

        if node in effective_starting:
            satisfied_starting.add(node)
            visited.add(node)
            return

        building = city.buildings[node]
        visiting.append(node)

        for prerequisite in building.prerequisites:
            visit(prerequisite)

        visiting.pop()
        visited.add(node)
        required_nodes.add(node)

    visit(target)

    prerequisites: dict[BuildingKey, frozenset[BuildingKey]] = {}
    dependents_mutable: dict[BuildingKey, set[BuildingKey]] = {
        node: set() for node in required_nodes
    }

    for node in required_nodes:
        direct_required = frozenset(
            prerequisite
            for prerequisite in city.buildings[node].prerequisites
            if prerequisite in required_nodes
        )
        prerequisites[node] = direct_required

        for prerequisite in direct_required:
            dependents_mutable[prerequisite].add(node)

    dependents = {
        node: frozenset(children)
        for node, children in dependents_mutable.items()
    }

    return DependencyGraph(
        faction=city.faction,
        target=target,
        nodes=frozenset(required_nodes),
        prerequisites=prerequisites,
        dependents=dependents,
        satisfied_starting_nodes=frozenset(satisfied_starting),
    )


def iter_topological_orders(
    graph: DependencyGraph,
    *,
    max_orders: int | None = None,
) -> Iterator[tuple[BuildingKey, ...]]:
    """Yield every valid topological build order for `graph`."""
    if max_orders is not None and max_orders < 1:
        raise ValueError("max_orders must be at least 1 or None")

    if not graph.nodes:
        yield ()
        return

    indegree = {
        node: len(graph.prerequisites[node])
        for node in graph.nodes
    }
    available = {
        node for node, count in indegree.items() if count == 0
    }

    yielded = 0
    order: list[BuildingKey] = []

    def backtrack(
        current_available: set[BuildingKey],
    ) -> Iterator[tuple[BuildingKey, ...]]:
        nonlocal yielded

        if len(order) == len(graph.nodes):
            if max_orders is not None and yielded >= max_orders:
                raise TopologicalOrderLimitError(
                    f"More than {max_orders} topological orders exist for "
                    f"{graph.target}"
                )
            yielded += 1
            yield tuple(order)
            return

        if not current_available:
            raise DependencyCycleError(
                "No buildable node remains before all graph nodes were ordered"
            )

        for node in sorted(
            current_available,
            key=lambda item: (item.sid, item.level),
        ):
            order.append(node)

            next_available = set(current_available)
            next_available.remove(node)

            for dependent in graph.dependents[node]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    next_available.add(dependent)

            yield from backtrack(next_available)

            for dependent in graph.dependents[node]:
                indegree[dependent] += 1

            order.pop()

    yield from backtrack(available)


def all_topological_orders(
    graph: DependencyGraph,
    *,
    max_orders: int | None = None,
) -> tuple[tuple[BuildingKey, ...], ...]:
    """Materialize every valid topological order as an immutable tuple."""
    return tuple(iter_topological_orders(graph, max_orders=max_orders))


def is_valid_topological_order(
    graph: DependencyGraph,
    order: tuple[BuildingKey, ...] | list[BuildingKey],
) -> bool:
    """Return whether `order` contains every graph node exactly once and legally."""
    if len(order) != len(graph.nodes):
        return False

    if set(order) != set(graph.nodes):
        return False

    completed: set[BuildingKey] = set()

    for node in order:
        if not graph.prerequisites[node].issubset(completed):
            return False
        completed.add(node)

    return True
