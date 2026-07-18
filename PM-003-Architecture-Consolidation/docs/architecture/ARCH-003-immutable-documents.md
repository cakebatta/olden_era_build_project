# ARCH-003 – Immutable Documents

Status: Approved

ScenarioDocument and other persisted documents are immutable.
Controllers construct candidate documents; views never mutate persisted state directly.
