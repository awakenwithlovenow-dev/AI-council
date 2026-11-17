---
name: headless-ai-calls
description: Use whenever writing or changing code that runs an AI in the background (`claude -p`, `codex exec`, an agent-bridge call, a council chair, a hub chat, a test harness that stubs model calls), or when the user finds stray chats, threads or sessions appearing in Claude or Codex. Covers the flags that keep calls invisible, read-only tools, usage limits and auto-resume, parallel calls, prompt formats that a parser reads, stub tests, and the one real cheap run every prompt change needs.
---

# Headless AI calls

Every rule here was learned from a real failure.

## Leave no trace in the user's apps
- **Claude:** every `claude -p` call gets `--no-session-persistence`. Without it each call is saved as a session, and Codex Desktop imports saved Claude sessions as threads: 74 one-prompt threads appeared in the user's Codex list from one day of council turns. If a feature "needs" `--resume`, send the whole conversation in the prompt instead.
- **Codex:** every `codex exec` call gets `--ephemeral`. Add `--ignore-user-config` when the user's MCP servers are not needed, or switch servers off with `-c mcp_servers.<name>.enabled=false` (bare TOML keys; a quoted key broke config.toml once).
- **Prove it once per machine:** make one tiny call from a scratch folder, then confirm no new file appeared under `~/.claude/projects/<slug>/` (Claude) or `~/.codex/sessions/<date>/` (Codex). A flag in the code is not proof.
- **Grep every call site** after adding a flag: copies of the same chair in a skill folder, a shareable kit, and a bridge all need it.
- If stray threads already exist, archive them; never delete. Look at the thread files first: `external_agent_tool_call` records mean an import of Claude sessions, not Codex calls.

## Read-only by default
- Claude: `--strict-mcp-config`, an explicit `--allowedTools` list, and `--disallowedTools Edit Write NotebookEdit Bash PowerShell Agent Task`. Codex: `-s read-only`.
- The only way a headless member creates something is a fenced block the calling program saves. The program, not the model, writes files.

## Prompts and parsers share one definition
- Every line format the program parses (`FOR OWNER:`, `STATUS:`, `CALL:`, `DEFECT: ... | REPAIR: ...`, `CHECK: ... | WATCH: ...`) is defined once and used both in the prompt text and in the regex. A council chair once dropped every owner question because the charter told members to write the owner's name (`FOR <NAME>`) and the regex wanted `FOR OWNER`.
- Accept the usual model variations: bold markers (`**STATUS:**`), trailing parentheses, "NONE" values (`DEFECT: none` is not a defect).
- Run each new regex against a real transcript before trusting it.
- Escape anything owner- or model-supplied that could forge a record heading (a leading `#` in a note).

## Errors, limits and auto-resume
- Treat as failure: a non-zero exit, empty output, or a short reply (under about 600 characters) containing a stop phrase (not logged in, usage limit, rate limit, quota, credit balance, resets at).
- **Auto-resume** a usage limit: wait (for example 15 minutes), retry the same call, give up after a cap (8 hours). Keep any lock fresh while waiting, show "waiting for usage" in the UI, and let a pause or stop end the wait.
- Run a tiny preflight (Haiku, "Reply with the single word OK.") before a long job, so a logged-out account never costs the first real turn.
- Never substitute a fake answer for a failed call. Stop visibly.

## Parallel calls
- Calls with **no web tools** can run side by side (four at a time ran seven council views in about 20 seconds). Calls that browse run one at a time on this laptop.
- Build every prompt before starting the parallel batch, write results in the main thread as they land, and treat one lost call as a note, not a crash, unless more than half are lost.

## Testing
- **Stub tests:** replace the call function and key the stub on the task's unique header (`=== YOUR TASK (OPENING ROUND) ===`), never on a phrase that other prompts also contain. A stub once matched "OPENING ROUND" inside a later prompt and reported a false failure.
- Script the rare paths (a defect and its repair, a late change, a lost call, the owner pressing pause, the owner stepping away) and assert each outcome.
- Run against a scratch copy of the project (an env var such as `COUNCIL_PROJECT`), never the owner's real records.
- **After any prompt change, make one real run on the cheapest model in the scratch copy.** Dry runs cannot show model behaviour: only a real Haiku meeting showed that an uncapped sign-off check made every close find new defects, so the meeting could never close.
- Say which results came from stubs and which from real calls.
