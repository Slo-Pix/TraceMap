# IBM Bob configuration — TraceMap's runtime fix engine

These files ARE the engine. TraceMap does not embed an LLM: `tracemap fix` builds a
CodeMap evidence pack and hands it to IBM Bob 2.0 running in this custom mode.

```
custom_modes.yaml          the `tracemap-fixer` custom mode (slug, role, tool groups)
skills/tracemap-fixer/     the Skill: the 8-step fix contract Bob follows
```

## Install

Bob reads these from the workspace root, so copy them one level above this repo:

```bash
cp bob_config/custom_modes.yaml       ../.bob/custom_modes.yaml
cp -r bob_config/skills/tracemap-fixer ../.bob/skills/
```

## How TraceMap invokes it at runtime

```bash
bobide chat -m tracemap-fixer --add-file .tracemap/pack.md "<instruction>"
```

`engine.py` makes exactly that call. Bob reads the evidence pack, diagnoses the root
cause, applies a minimal patch, and writes a regression test that is red before and
green after — then `verify.py` proves both states independently.
