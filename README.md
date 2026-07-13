# Heroes of Might & Magic: Olden Era Build Planner

A planning and analysis tool for **Heroes of Might & Magic: Olden Era** focused on pvp (though I guess you could also use this to sweat regular matches against ai).

The project parses the game's data files to build an internal model of cities, buildings, units, dependencies, construction timing, and resource costs. It is designed to answer strategic planning questions such as:

- What is the fastest path to a particular building?
- What are all valid build orders?
- How much does each path cost?
- When can a build be completed?
- How do different build sequences compare?

The application intentionally models deterministic game mechanics only. Random map generation, resource pickups, and other stochastic elements are considered outside the scope of the planning engine.

---

## Project Status

This project is under active development.

The current focus is building a robust backend and data model before developing the desktop user interface.

Major milestones completed include:

- Building parser
- Unit parser
- Dependency graph
- Planning engine
- Localization support
- Integrated game database
- Automated testing infrastructure

---

## Repository Structure

```text
docs/          Project documentation
olden_db/      Python application
```

The Python project contains:

```text
Core/          Extracted game data
olden_db/      Source code
scripts/       Validation and test scripts
output/        Generated outputs
notes/         Temporary research and investigation files
```

---

## Documentation

The repository documentation is maintained in the `docs/` directory.

Recommended reading order:

1. `architecture.md`
2. `roadmap.md`
3. `game_assumptions.md`
4. `coding_standards.md`
5. `terminology.md`

These documents describe the project's long-term architecture, development philosophy, and design decisions.

---

## Development Philosophy

The project emphasizes:

- deterministic behavior
- reusable components
- explicit data models
- maintainable architecture
- comprehensive validation

GitHub is treated as the canonical source of truth for both code and documentation.

---

## License

This repository is currently intended for personal development and research.
