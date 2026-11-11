# Demo: «verified by the model» is not «correct»

`demo.py` replays a **real** answer of qwen2.5-coder:7b from `results/C.jsonl` (task `009-config-sed`, condition C) and actually executes it in the sandbox:

1. the model's solution runs;
2. the model's **own test** passes → the agent would report "verified";
3. the **hidden check** in a clean container fails — the model appended a duplicate `max_connections=200` and left the original line in place.

```bash
.venv/bin/asciinema play demo/demo.cast   # recorded terminal session (asciinema v2 format)
cat demo/demo.txt                           # same session as plain text
.venv/bin/python demo/demo.py               # re-run it (needs Docker + verify-agent-base image)
.venv/bin/python demo/demo.py --live        # ask the model again instead of replaying
```

No GIF: converting `.cast` to GIF needs `agg` (a separate binary), which was not installed to avoid system-wide installs.
