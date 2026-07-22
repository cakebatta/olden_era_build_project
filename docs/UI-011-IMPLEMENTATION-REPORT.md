# UI-011 Implementation Report

UI-011 establishes the Query Layer as the presentation-facing owner of faction, building, and unit display-name resolution. Canonical identities remain unchanged for planning, persistence, equality, and comparison correlation. Presenters construct immutable display options and starting-building rows; views render supplied strings and translate selector display text back to canonical identities for callbacks.

The default Query Layer loads the complete English localization directory and uses deterministic fallback: localized text, authoritative source identity when available, then canonical SID. Existing Planning Summary, Timeline, and UI-010 comparison building presentation continue through Query Layer resolution.
