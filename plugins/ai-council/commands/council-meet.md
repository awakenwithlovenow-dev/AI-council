---
description: Run a council meeting on a topic
argument-hint: "<topic> [quick] [attend]"
---
Run a meeting of the council in this project. Topic and options from the owner: $ARGUMENTS

- Use `tools/council/council.py --topic "<topic>"` with the project's Python. Add `--quick` for a quick view (own views, the lead's decision, the close) and `--attend` if the owner wants to answer questions live. Files in `outputs/council/files/` can be added with `--files <name>`.
- Start it in the background and report: the session id, when it closes, the decision, the outcome record and what changed. The hub (`/council-hub`) shows it live.
- If no council exists yet, say so and run `/council-build` instead.
