---
name: ai-council
description: Use whenever someone wants an AI "council", board of advisors, or panel of persona members built from their existing chats, projects or documents. Also covers AIs that deliberate, strategise and draft autonomously and continuously without the user; building, reviewing, testing, launching, steering, pausing or reading a council; and a council that learns from the owner's rulings. Works with one AI (Claude, with a Claude "challenger" as the second chair) by default, and optionally adds a second AI such as Codex. Includes a numbered super-prompt pack (intake, extraction, member design, independent review, testing, launch), templates, a one-command setup script, and the chair program.
---

# AI council: build, test, run, learn

A council is **a folder of plain files plus a small program, the chair,** that makes AI sessions debate as those files describe.
- **Members** are profile files: expertise, a conviction, questions, veto rules. They come alive only when the chair runs a meeting. They do not live in the chat.
- **Co-chairs:** the lead (Claude) and a **CHALLENGER**, which is Claude on a different model, told to test the lead hardest. With `"two_ai": true` and Codex installed, Codex takes the second chair instead. **One AI is the default; a second AI is optional.**
- **The chair** (`scripts/council.py`) has no opinions. It passes the floor, writes everything to disk, enforces the rules, and runs once on demand or on a timer.
- **It works only on paper.** It debates and drafts on its own, on the owner's agenda, and never publishes, sends, buys, contacts anyone or edits project files.
- **It learns.** `memory/` holds the owner's rulings (which outrank everything), a log of decisions, and per-member lessons.

## Quick start
In the project folder: `python <skill>/scripts/new_council.py`. It creates `outputs/council/` from the templates, copies the chair, runs a dry run, and prints the steps. Then work through the prompt pack.

## The prompt pack (one per step; each works in any AI chat)

| Step | File | Produces |
|---|---|---|
| 00 Intake | `prompts/00-INTAKE.md` | BRIEF, AGENDA, seeded RULINGS, charter rules 4 and 10 |
| 01 Extract | `references/extraction-prompt.md` (pasted into each project) | One DOSSIER (plus optional KEEP) per project |
| 02 Design | `prompts/02-DESIGN-MEMBERS.md` | Seats, member profiles, conflict register, precedent register |
| 03 Review | `prompts/03-CROSS-REVIEW.md` | An independent reviewer's CONCEDE/HOLD/AMEND and SIGN/OBJECT, until all SIGN |
| 04 Test | `prompts/04-TEST.md` | A blind scenario test, member errors found, fixes applied |
| 05 Launch | `prompts/05-LAUNCH-AND-LEARN.md` | Green-light install, one hand-run session, ongoing learning |

Supporting references: `references/member-design.md` (13 rules plus a template), `references/charter-template.md` (the meeting rules, the live floor, memory), `references/deliberation-and-testing.md`. Templates are in `templates/`: BRIEF, AGENDA, SEATS, config.json.

## Rules that make it work (each learned from a real failure)
- **Save every supplied file byte-identical before reading.** If more than one reviewer is involved, record who has which files; different inputs change conclusions.
- **Members need convictions** (labelled hypotheses), earned qualities, real calibration events, the roster, and their reference lists. Without them they copy the chairs, invent seats, or claim empty lists. Include **one creative seat** that proposes the boldest true version first. A seat without its own project is **provisional** (no veto).
- **Review independently.** Use a fresh session on a different model with an adversarial role. Expect about 20 corrections of overstatement. Keep corrections visible. Nothing installs until the reviewer SIGNs **and the owner says go**.
- **Test blind before going live, then run one live session by hand.** A blind test measures each seat alone; only a live floor tests the debate.
- **The live floor:** frame (with a LEAD) → the lead's most ambitious version → open floor (CALL: hand-offs, every member speaks, each red line stated once with WOULD APPROVE IF) → the lead's synthesis with drafts → both chairs close. No consensus close without drafts or `NO DELIVERABLE NEEDED:`.
- **File every owner ruling** in `memory/RULINGS.md`. The owner can also answer in the FOR file: `- [x] question ANSWER: ...`.
- **Never copy one owner's private details** into another council, this skill, or a shared kit.
- **Headless login:** run `claude`, then `/login`, once. The install path changes when the app updates, so look it up fresh. Create `PAUSE` if a timer exists before the owner's green light.

## Lessons from running a real council (Oct 2026)
When an owner's council has been extended with these, its README is the best reference for that project. Never copy one owner's private content into a kit or another council.
- **Leave no trace:** headless calls use `--no-session-persistence` (Claude) and `--ephemeral` (Codex). See the headless-ai-calls skill.
- **Own views first.** Before the open floor, every seat writes a short view (position, why, risk, what would change its mind) without seeing the others. These calls have no web tools, so they can run side by side.
- **Independent is not diverse.** Five of seven independent views still converged on the brief's most prominent asset. For an open topic, the frame names two or three genuinely different directions, and each view says which it backs.
- **A sign-off check, bounded.** Each co-chair names real defects (`DEFECT: ... | REPAIR: ...`): an objection dropped, a claim with no source, an untested assumption. Quick agreement is not a defect. The lead gets one repair round. The second close judges only whether those defects were repaired, and new points become `OPEN:`. Uncapped, every close found new defects and nothing closed.
- **Approval is tied to the version** (a fingerprint of the drafts). A draft changed after a co-chair accepted it means both close again, once.
- **The minutes keep evidence apart from agreement:** evidence strength, who agreed and who dissented, the best minority argument, what it depends on, what would overturn it, and what the meeting changed against the lead chair's own first view.
- **A track record:** decisions reality can test get a number to watch and a date. The owner marks each confirmed, revised, reversed or inconclusive, and every later meeting reads the record.
- **Owner attendance:** collect the questions and ask once before the decision; stop at once only on BLOCKED; offer Step away; Pause holds a running meeting between turns. Asking every turn wore the owner out.
- **Revised drafts** never overwrite. Superseded versions are renamed "(replaced at turn N)", so exactly one version has the plain name.
- **A reset with undo**, and dedupe ledgers kept outside what a reset clears.
- **After any prompt change, run one real meeting on the cheapest model in a scratch copy.**

## Owner controls
- **Steer:** `AGENDA.md`.
- **Pause:** the file `PAUSE`.
- **Pace and models:** `config.json` (`two_ai`, `claude_model`, `second_chair_model`, `council_turns`, `max_sessions_per_day`).
- **Read:** `LATEST-MINUTES.md`, the FOR file, `drafts/`, `memory/`.
- **Commands:**
  - `council.py` runs one session.
  - `--marathon` runs until the agenda is done.
  - `--dry-run` tests the plumbing.
  - `--install-schedule --every-hours N` sets up automatic runs (Task Scheduler on Windows; prints a cron line on Mac/Linux).

## Explaining it to the owner
Answer plainly:
- **The council** lives in files in their project.
- **The skill** is the recipe.
- **The login** is for the program's own background AI sessions.
- **It works on its own,** but only on their agenda and only on paper. Every real decision is theirs.

## Lessons from the owner's own meetings (17 Nov 2026)
- **Judge a meeting as the owner.** Can they act on the first screen? Can they answer each question in one press? A lively debate with checked references is not a result if the owner cannot follow it.
- **Conclusion first.** The lead writes `CONCLUSION:` (three plain sentences, nothing the owner must answer first) and `FIRST STEP:`. The chair copies both to the top of the minutes itself.
- **Assume and mark.** A missing fact is assumed in an `ASSUMED:` line. It never becomes a blank for the owner.
- **Few questions.** Only the lead asks, at most two a meeting, one thing each, as `FOR OWNER: question | OPTIONS: a / b | IF SKIPPED: what happens`. A reply that says the question was not understood is not a ruling.
- **Follow-ups keep the earlier conclusion** and change only what the owner's answers change.
- **Members hold expertise and standing rules, never history.** Old prices, offers, events and summaries of old chats in a member file or brief become "facts" the council argues from. History reaches a meeting only through a file the owner attaches or a ruling.
- **A blank slate must be checked, not assumed.** List everything a prompt contains (brief, pulled-in memory, member file, rulings) before calling a meeting blank.
- **Seat by topic.** The opening co-chair names the seats a topic needs; the rest stay out.
- **Quick meetings have no discussion.** Every seat writes alone and the lead decides. Use a full meeting when disagreement matters.
- **Write rule text without he/his for the owner**, and print the rules from the built template: renaming the owner breaks pronouns and capitals.

## Lessons from the first tests of the blank slate (18 Nov 2026)
- **The conclusion's first sentence is the advice.** A doubt or a shortfall comes after it. If the plan misses the owner's aim, say so once and say what would close the gap (a price, a number, one change).
- **Missing information is never a reason to stop something the owner does.** A blank slate has no sales data, and a council will read "no data" as "does not work" unless told not to.
- **Dropped questions go to the lead.** Questions written outside the decision turn are not filed, but the lead sees them at the decision and may carry one over. The clerk is given the list that was actually filed and writes only that in the minutes' questions section (or "Nothing to answer.").
- **Co-chairs judge from the record.** They get no tools except in the decision and repair turns, or Read when an attached file is named by path. The minutes get none.
- **Mapping matters as much as code.** A blank-slate council is only as good as the facts in the topic and attached files. When a meeting needs a fact (what sells, prices, who buys), the owner gives it in the topic or a short attached note.

## The chat way in, members and role models (18 Nov 2026)
- **A Claude chat can be the owner's main way in.** The meeting command runs the chair in the background, then shows the conclusion and first step word for word, at most five decided points, the questions as clickable choices, and then "meet again / chart or slides / done". The hub stays as an optional overview. A first-time owner already knows the chat; a second app window is one more thing to learn.
- **The program reads and writes the council's files, never the model.** `council.py --report latest` gives the result as JSON (conclusion, first step, decided, questions with options); `council.py --answer latest <n> "<text>"` saves an answer in the hub's own line format. A model editing the questions file by hand would sooner or later break the format the hub and the chair parse.
- **Charts and slides come only from the meeting's own minutes and drafts.** Never add a number the council did not write; mark assumed figures as assumed.
- **Background calls use their own sign-in.** A meeting started from a chat inherits that chat's own settings unless the chair removes them; then its calls depend on the chat staying open. The chair now cleans the environment for every call, wherever it was started.
- **What a member file holds:** what the seat knows how to do, its conviction, questions, red lines, voice and boundaries. Never prices, offers, plans, numbers or past events: those go in the brief, with their date and source. Each proposed member is shown to the owner with the reason from their own material ("pricing comes up in most of your emails").
- **Role models** are seats built only from a public figure's own recorded words (the persona-research skill): `Status: provisional` (object, never veto), named in full, speaking as "<name>'s approach", never as the person, and saying "nothing in their interviews" where the person is silent. A role model kept in a pack holds `member-<name>.md`, `dossier.md`, the research and a `roster-line.txt`.
- **A seat missing from the roster is never seated.** The opening co-chair chooses seats from the roster table. In the first real test a role model was left out of a pricing meeting, its own field, because its row was missing; with the row and one sentence in the seating rule ("a role model sits whenever the topic is in its field") the second test seated it, and it caught a real flaw. Test every new seat in one real cheap meeting on a topic in its field.
- **Debate can lower accuracy.** A 2025 study (Wynn, Satija and Hadfield) found agents switching from right answers to wrong ones to agree. Keep independent first views, keep strong models in real meetings, and keep the floor short. An anonymous ranking of the first views (as in Karpathy's LLM Council) is a candidate step, not yet built or tested.
- **Read the whole program end to end before calling it final.** A full read on 18 Nov found two bugs no test had reached (a daily-cap crash, a name used before it was defined) and a hub button that would have started an old agenda built on a strategy the owner had set aside.

## This plugin's extras: the hub and the commands

Installing the plugin adds three commands and a desktop-style app.
- **`/council-build`** builds a council from the owner's own material: their files, notes and meeting transcripts, from local folders or connected tools (Google Drive, Notion, Zoom, Granola, Fireflies, Otter or any other connector the session has). Claude guides the owner one step at a time through connecting their apps, reads all of it in stages, writes the owner's profile and proposes the members; at the end the owner confirms by multiple choice only, with nothing to type, and the council brings the most important decisions and matters to the table as its first agenda. The look and the members' final names are decided afterwards.
- **`/council-meet <question>`** runs a meeting and brings the result back into the chat: the conclusion and first step first, the council's questions as multiple choice (answers recorded with `council.py --answer`), and charts or slides on request, built only from the meeting's own minutes. It reads the result with `council.py --report latest`. This chat is the owner's main way in.
- **`/council-hub`** (optional) opens the hub: Home, the live meeting, the round table, Talk with Claude, Files, Questions, the Library and the track record.

**Role-model members.** Seats built only from a public figure's own recorded words (the **persona-research** skill), kept in `outputs/council/members/role-models/<name>/` with a `dossier.md`, the research, and a `member-<name>.md` that is copied into `members/approved/` when the owner keeps it. A pack can arrive as a zip ending in `-role-model.zip`; unpack it there and ask the owner Keep / Leave out. Role models are always `Status: provisional`, named in full, and speak as the person's recorded approach, never as the person.

`scripts/new_council.py` installs everything into a project: `tools/council/council.py` (the chair), `tools/council/chamber/` (the hub, served on http://127.0.0.1:8790), and `outputs/council/` (the council's files). The owner's name goes in `outputs/council/config.json` as `owner_name`.
