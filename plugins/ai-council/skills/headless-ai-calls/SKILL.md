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

## Cost: measure one call, then cut the start-up load
- Ask for `--output-format json`. The answer arrives with `result`, `usage` (input, cache creation, cache read, output), `total_cost_usd`, `num_turns` and `is_error`. Record a row per call and a total per job; never estimate usage.
- Measure a call that only replies "OK" from the project folder. If it reads tens of thousands of tokens, that is Claude Code's own start-up text plus the project's CLAUDE.md, memory index and skill list, loaded on every call. On one project this was 50,000 tokens a call, three quarters of every meeting.
- Cut it with `--setting-sources user --disable-slash-commands --tools <only the tools allowed> --system-prompt "<two plain sentences>"`. Measured: about 52,000 down to about 10,000 a step. Check afterwards that a file read still works.
- `--bare` is not the answer on a subscription: it reads no saved sign-in, only an API key.
- A model that uses a tool re-reads everything each step. A co-chair that looked things up read 370,000 tokens in one turn. Give tools only to the calls that need them.
- The dollar figure in the answer is the list price. On a subscription nothing is charged, and it does not convert into a percentage of the plan limit.

## Sign-in and finding the program (rows N9, N10)
- Background calls keep their own sign-in, apart from the desktop app's, and it expires. Provide a self-check that makes one tiny real call without the session's own CLAUDE*/ANTHROPIC* variables and prints READY, SIGN-IN NEEDED, NOT FOUND or USAGE, each with what to do.
- The desktop app moves its program between versions. Find it by pattern, newest first, and when started from inside a Claude session save that session's own program path as a pattern for later starts from an icon.

## Markers and answers (rows N4, N8, N20)
- Before adding a marker to a parsed line, search every reader of that line for separators it would collide with. A question's "IF NO ANSWER:" part collided with the " ANSWER:" that stores the owner's reply.
- A reply that only says the question was not understood ("what???") is not a decision. Do not file it as one.
- Accept the slips a weaker model makes in a format (a slash where a bar belongs), and tell the model which exact line the program copies.
- A network error is not a usage limit. Retry it once or twice before failing the job. Done in the council chair on 18 Nov 2026 (`is_network_error`, two retries after 30 s and 90 s, inside `resuming`); the same day a real ENOTFOUND mid-meeting was retried and the meeting finished. Match Claude's own error phrases (ENOTFOUND, socket hang up, overloaded), never a bare word like "network" that a reply can contain.
- **Shared text goes in the system prompt (18 Nov 2026):** text that every call in a job shares (charter, brief, rules) must lead the request, before anything that differs, or nothing is reused from cache. Put it in `--system-prompt-file` (a file: it is far past a Windows command line's limit) and keep each call's own part in the message. Measured: the second of two calls read 5,944 tokens from cache and cost $0.00019 instead of $0.00132; a real Haiku meeting went from 18% to 38% reused and about 30% cheaper. The cache is per model and per tool set, so calls with the same model and tools share it. Codex has no system prompt: prepend the shared text to its message.
- **Tools per turn (18 Nov 2026, row N28):** a call that judges from the record in its prompt gets no tools: `--tools ""`, no `--allowedTools`, and a system prompt that says "this turn has no tools". Measured: about 700 tokens of start-up instead of about 4,400, and always one step. Give tools only to the turn that must open a file (drafts in the owner's voice, an attached PDF).
- **A rule that drops output passes it on (row N25):** when the chair refuses a line (a question outside the decision turn), hand it to whoever can still use it and give the clerk the chair's own record of what went through, or the minutes will describe what never happened.

## Environment, launch place and echoes (18 Nov 2026, rows N34, N29)
- **Clean the environment of every background call.** A program started from inside a Claude chat inherits about 35 of that session's variables (`CLAUDE*`, `ANTHROPIC*` such as a local base URL, `AI_AGENT*`); its calls then run through the chat's own connection. Pass `env=` with those removed (keep the user's own `ANTHROPIC_API_KEY`) to every `subprocess` call, and make the self-check use exactly the same environment as the real calls.
- **Strip an echoed record heading.** A speaker sometimes repeats its own `## Turn N, NAME` line at the top of its reply; the chair writes that heading itself, so remove a leading one before saving.
- **A cap or early exit must return what the caller unpacks.** A daily cap returning a bare `0` where the caller unpacks three values crashed `main()`; no test had reached it. Test the early exits.

## Effort, and lines lost in a repair turn (18 Nov 2026)
- `claude -p --effort <low|medium|high|xhigh|max>` works headless (checked with one Haiku call). Measured on Haiku: high effort made members write 4 to 6 times more (thinking) and take 12 to 15 s instead of 5. Set it per role, not globally.
- When a later turn restates part of a structured block (a repair restating CONCLUSION and FIRST STEP), lines it leaves out are lost unless the parser falls back to the earlier turn's line. Ask for the full block in every turn that restates it, and parse with a fallback.

## Testing council or prompt variants (19 Nov 2026)
- **Use the program's own prompt builders** (for the council: `opening_prompt` and `call_member`, imported with `COUNCIL_PROJECT` set to a scratch copy), so a test matches real conditions.
- **One trial call first,** then the full run. Run every variant at the same time, each in its own scratch project, so time of day and model load fall on all of them alike.
- **`num_turns` in the JSON result tells you whether a call used tools** (more than 1 means it looked something up); record it with tokens, cost and seconds for every answer.
- **Grade blind and one answer at a time,** against the ground truth, by a strong model that may read the sources; then check two or three of the grader's claims on the page before reporting them.
- **Ask the questions that separate the variants:** a judgement call, a question that needs a specific detail, and a trap on a topic the source is silent on.
