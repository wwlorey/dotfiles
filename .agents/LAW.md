# LAW

Non-negotiable rules for the system. Each entry is a single principle and
holds across every skill, script, hook, and prompt. Add new entries when a
constraint earns "must" status. Soft preferences and guidelines belong
elsewhere.

## Harness portability

Treat the agent harness as swappable. Anthropic's Claude Code is the runtime
today; another vendor is the runtime tomorrow. Skills and scripts MUST
isolate vendor-specific primitives behind a thin layer. The substantive
content of a skill — the pattern, the procedure, the decision tree — stays
runtime-agnostic. When a skill leans on a vendor primitive (a specific tool,
a hook mechanism, a session API), name the tool, state the underlying
capability it provides, and write the surrounding prose so a port to another
harness rewrites only the named line.
