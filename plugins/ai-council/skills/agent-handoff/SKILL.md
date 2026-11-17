---
name: agent-handoff
description: Use when handing work to or from another agent (Codex, a headless claude -p run, a subagent), writing a prompt or command another tool will run, republishing an artifact another session may have changed, or running long jobs while the user waits. Covers checking settings and capabilities first, review-loop formats and progress reporting.
---

# Agent handoff

Every rule here was learned from a real failure.

## Before giving the user a command or prompt
- Read the settings that command will run under (`.claude/settings.local.json`, `settings.json`) before choosing flags. A flag can downgrade what is already set; for example, `--permission-mode acceptEdits` overrides a project default of `bypassPermissions`.
- Check what the other agent can actually do. Neither Codex nor headless Claude can use a physical phone, see the user's screen or reach the user's logins from a sandbox. A `claude -p` call from another tool's sandbox may be "Not logged in"; tell the user to run `/login` in a normal terminal, and have a fallback.
- Give the receiving agent a fixed reply format (STATUS, VERIFIED, FIXED, FOR <other agent>, FOR <user>, PUBLISHED) and an explicit loop rule (when to stop, when to send again).

## Receiving a handoff
- Verify its claims against the files: replay patches, run its tests, look at its images. Treat its report as claims, not facts.
- Back up its evidence folders before re-running shared suites.
- Respect constraints it records from the user (for example, "publish nothing this round"), even if an older prompt says otherwise.

## Artifacts and publishing
- Read the live artifact before republishing one you have not read in this session. If refused, diff the live copy against your previous build before overwriting.
- Publishing to a live site always needs the user's explicit yes, every time.

## While long jobs run
- Start a monitor that reports each step's start, end and failure, and tell the user what is running and roughly how long it takes.
- Do not go silent for more than a few minutes. Report the results that have landed.
- Background servers die at their time limit. Check the server with `curl` before each test run, and restart it when needed.

## Another agent's work and the owner's data
- When asked to review another agent's app, test it with its own tests and fixtures, and read its README for the owner's standing holds (for example, "no assistant-started live calls") before running anything that spends allowance or creates threads.
- Do not copy the owner's real records to inspect them; use fixtures, or ask.
- A review of another agent's app is advice. Write it to a file and offer a paste-ready prompt for that agent. Do not edit its code unless the owner asks.
- Silence recurred in the council build: the system had to prompt "say what you're doing" several times. Give a one-line status before every wait of more than a minute, and whenever a background job reports.

## Watching long jobs
- A Monitor expires (the default is 5 minutes). For a single "tell me when done" notice, run a background `until grep -q DONE log; do sleep 10; done; summary` instead. For step-by-step progress, set timeout_ms to the maximum and re-arm on expiry.

## Recovering a stalled Codex thread, and measuring its cost (24 Oct 2026)
- A Codex thread that stalled on a disconnect is not lost. Its full transcript is at `~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-<timestamp>-<id>.jsonl`. Find it with `grep -l "<report filename>" ~/.codex/sessions/<yyyy>/<mm>/*/*.jsonl`. Its files written so far are on disk too; check those first, then pull the last reasoning and tool outputs from the log to rebuild what was unfinished. Wait for any thread that comes back online to finish before judging it.
- Token cost per thread is in the same log: the last `"total_token_usage":{...}` line gives input, cached input and output tokens. Fresh input is input minus cached. Sum across every log that mentions the report's filename (the count may include helper threads, so call it an upper bound). Today's four Astra reports: 39 logs, about 300M input of which 287M cached, 13M fresh, 1.3M output.
- Judge a recovered report with the audit-agent-report skill (project skill) before anything enters the register.
