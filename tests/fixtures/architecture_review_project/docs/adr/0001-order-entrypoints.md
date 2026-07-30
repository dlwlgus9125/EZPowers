# ADR-0001: Preserve Order entry points

HTTP checkout and batch checkout are public compatibility entry points.
Their internal policy may converge, but callers must not migrate in one
breaking change.
