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
In the project folder: `python3 <skill>/scripts/new_council.py` (`python` on Windows). It creates `outputs/council/` from the templates, copies the chair, runs a dry run, and prints the steps. Then work through the prompt pack.

## The prompt pack (one per step; each works in any AI chat)

| Step | File | Produces |
|---|---|---|
| 00 Intake | `prompts/00-INTAKE.md` | BRIEF, AGENDA, seeded RULINGS, charter rules 4 and 10 |
| 01 Extract | `references/extraction-prompt.md` (pasted into each project) | One DOSSIER (plus optional KEEP) per project |
| 02 Design | `prompts/02-DESIGN-MEMBERS.md` | Seats, member profiles, conflict register, precedent register |
| 03 Review | `prompts/03-CROSS-REVIEW.md` | An independent reviewer's CONCEDE/HOLD/AMEND and SIGN/OBJECT, until all SIGN |
| 04 Test | `prompts/04-TEST.md` | A blind scenario test, member errors found, fixes applied |
| 05 Launch | `prompts/05-LAUNCH-AND-LEARN.md` | Green-light install, one hand-run session, ongoing learning |

Supporting references: `references/member-design.md` (14 rules, a template, and how the seats are chosen), `references/charter-template.md` (the meeting rules, the live floor, memory), `references/deliberation-and-testing.md`. Templates are in `templates/`: BRIEF, AGENDA, SEATS, config.json.

## Rules that make it work (each learned from a real failure)
- **Save every supplied file byte-identical before reading.** If more than one reviewer is involved, record who has which files; different inputs change conclusions.
- **Members need convictions** (labelled hypotheses), earned qualities, real calibration events, the roster, and their reference lists. Without them they copy the chairs, invent seats, or claim empty lists. Include **one creative seat** that proposes the boldest true version first. A seat without its own project is **provisional** (no veto).
- **Review independently.** Use a fresh session on a different model with an adversarial role. Expect about 20 corrections of overstatement. Keep corrections visible. At most two rounds: anything still disputed is cut or kept as a labelled hypothesis. Nothing installs until **the owner says go**.
- **Test blind before going live, then run one live session by hand.** A blind test measures each seat alone; only a live floor tests the debate.
- **The live floor:** frame (with a LEAD) → the lead's most ambitious version → open floor (CALL: hand-offs, every member speaks, each red line stated once with WOULD APPROVE IF) → the lead's synthesis with drafts → both chairs close. No consensus close without drafts or `NO DELIVERABLE NEEDED:`.
- **File every owner ruling** in `memory/RULINGS.md`. The owner can also answer in the FOR file: `- [x] question ANSWER: ...`.
- **Never copy one owner's private details** into another council, this skill, or a shared kit.
- **Headless login:** run Claude's program once with `auth login` (`council.py --check-claude` names the program). The install path changes when the app updates, so look it up fresh. Create `PAUSE` if a timer exists before the owner's green light.

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
- **Conclusion first.** The lead writes `CONCLUSION:` (clear and direct, as long as the point needs and no longer, nothing the owner must answer first; the owner rejected a fixed three-sentence limit on 18 Nov 2026), `FIRST STEP:`, `NEXT STEPS:` and `NEEDED:`. The chair copies both to the top of the minutes itself.
- **Assume and mark.** A missing fact is assumed in an `ASSUMED:` line. It never becomes a blank for the owner.
- **Few questions.** Only the lead asks, at most two a meeting, one thing each, as `FOR OWNER: question | OPTIONS: a / b | IF SKIPPED: what happens`. A reply that says the question was not understood is not a ruling.
- **Follow-ups keep the earlier conclusion** and change only what the owner's answers change.
- **Members hold expertise and standing rules, never history.** Old prices, offers, events and summaries of old chats in a member file become "facts" the council argues from. They belong in the brief, each with its date and source, and reach a meeting through the brief, the topic, a file the owner attaches or a ruling.
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
- **A Claude chat can be the owner's main way in.** The meeting command runs the chair in the background, then shows the conclusion and first step word for word, at most five decided points, two visuals built from the minutes (the decision: options, who stood where, evidence; what happens next: steps, check dates, the meeting's own figures), the questions as clickable choices, and then "meet again / slides / done". Two visuals every meeting was the owner's ruling (18 Nov 2026). The hub stays as an optional overview. A first-time owner already knows the chat; a second app window is one more thing to learn.
- **The program reads and writes the council's files, never the model.** `council.py --report latest` gives the result as JSON (conclusion, first step, decided, questions with options); `council.py --answer latest <n> "<text>"` saves an answer in the hub's own line format. A model editing the questions file by hand would sooner or later break the format the hub and the chair parse.
- **Charts and slides come only from the meeting's own minutes and drafts.** Never add a number the council did not write; mark assumed figures as assumed.
- **Background calls use their own sign-in.** A meeting started from a chat inherits that chat's own settings unless the chair removes them; then its calls depend on the chat staying open. The chair now cleans the environment for every call, wherever it was started.
- **What a member file holds:** what the seat knows how to do, its conviction, questions, red lines, voice and boundaries. Never prices, offers, plans, numbers or past events: those go in the brief, with their date and source. Each proposed member is shown to the owner with the reason from their own material ("pricing comes up in most of your emails").
- **How seats are chosen:** decisions first (what the owner keeps deciding, counted in the coverage record), grouped into areas; weight decides (too little material means fold it in or seat it provisional); the fewest that cover everything, three to seven; one creative seat; different angles, never forced disagreement (two seats that would say the same thing on a real decision are one seat; no seat is contrary for its own sake); roles, never people from the material; every seat in the seat table. Each seat is shown to the owner with its reason and count, Keep or Leave out.
- **Role models** are seats built only from a public figure's own recorded words (the persona-research skill): `Status: provisional` (object, never veto), named in full, speaking as "<name>'s approach", never as the person, and saying "nothing in their interviews" where the person is silent. A role model kept in a pack holds `member-<name>.md`, `dossier.md`, the research and a `roster-line.txt`.
- **A seat missing from the roster is never seated.** The opening co-chair chooses seats from the roster table. In the first real test a role model was left out of a pricing meeting, its own field, because its row was missing; with the row and one sentence in the seating rule ("a role model sits whenever the topic is in its field") the second test seated it, and it caught a real flaw. Test every new seat in one real cheap meeting on a topic in its field.
- **Debate can lower accuracy.** A 2025 study (Wynn, Satija and Hadfield) found agents switching from right answers to wrong ones to agree. Keep independent first views, keep strong models in real meetings, and keep the floor short. An anonymous ranking of the first views (as in Karpathy's LLM Council) is a candidate step, not yet built or tested.
- **Read the whole program end to end before calling it final.** A full read on 18 Nov found two bugs no test had reached (a daily-cap crash, a name used before it was defined) and a hub button that would have started an old agenda built on a strategy the owner had set aside.

## Two kinds of meeting, and what the owner actually wants (18 Nov 2026, evening)
- **Ask what the council is for before designing it.** An unattended decision engine is not what every owner needs; a whole-picture review of the person and the business often is. There are two kinds of meeting: `/council-meet` for one decision, `/council-review` for "where do I stand".
- **The review:** a rich brief first; every member answers the same six questions alone (strengths, blind spots, desires, how the owner is seen, the way forward, the support needed); an open floor (agreed without asking, disagreements as pairs with where they land, red lines, the leading view, a named contrarian against it); a pulled-together view with every line marked [record], [council] or [my view]; three to five questions, each saying what it would change; rounds after the answers with a "your answer | what it changes" table and dated corrections at the top of earlier files; an overview page the owner marks True, Not quite or Not true and copies back. Setup now ends with a review as the first meeting.
- **A thin brief makes a confident wrong reading.** In the first test the whole council gave a confident verdict on sales from a record that held no sales figures at all; the contrarian (the truth seat) caught it, and four multiple-choice answers overturned it in one round. The contrarian and the questions are how a review recovers from a thin record.
- **A corrected reading comes back unless each helper is told (21 Nov 2026).** A helper repeated "supply-limited, raise the price" three days after the owner corrected it to "demand is the limit"; the rulings file alone did not stop it. Each helper prompt now carries the owner's corrections in one block, "do not argue from these", and a repeated line is struck through with a note. Dossier codes are [council], not [record]. Helpers that end without a report are asked again for the report only.
- **The overview is a page to read, not a quiz (21 Nov 2026).** The owner asked "where is the full council overview? all i get are true or false questions". The page now opens as reading; the True / Not quite / Not true boxes appear only after one "I want to correct something" button; the chat asks at most two questions, one at a time.
- **A council question round (23 and 24 Nov 2026).** When the owner asks for "as many true or false questions" as possible, from every member, the council can write the questions instead of answering. First, Claude wrote six per member from the member files (42). Then one Sonnet helper per member read the owner's voice note, the facts, the rulings and every question already asked, with the corrected readings marked "do not argue from these". Each wrote 8 to 12 questions that were *not obvious*: tensions between two answers, untested assumptions, a decision hiding inside a yes. Each question was TF, CLARITY or CONFIRM, with its basis and what it would change. Seventy-seven came back, 69 after merging overlaps. The owner answered all 69 in one sitting. The question format the owner set: True and False each say plainly what they mean for this statement; Partly names what is true and what is not; multiple choice always ends with "All of the above". Ask every question before reviewing, then ask only the checks the review turns up. Read a "how much could you hold" answer as capacity, not a forecast ("you are assuming i wil get booked out whcih is not true"). Before building a true/false statement on a vague phrase from the owner's voice note, ask what it means ("So I don't guess: ...").
- **Questions:** the problem on 17 Nov was not the number but questions that did not say what they would change. Three to five, each with its reason, were answered gladly.
- **Conclusions:** no fixed length (the three-sentence cap was the assistant's own invention); clear, direct, as long as the point needs, then `FIRST STEP`, `NEXT STEPS`, `NEEDED`, and two simple, high-contrast visuals.
- **Template settings:** the topic's lead member (who writes the conclusion) on Opus, the others on Sonnet, all at high effort; members look up files only, the lead keeps the web in its decision and repair turns. Setup sorts material into read fully / skim / count only, with up to ten helper readers on one fixed sheet (`references/reader-brief.md`), and the main chat checks their notes.

## Final checks before handing over a template (18 Nov 2026)
- **Validate the inner plugin folder** (`claude plugin validate <marketplace>/plugins/<name>`), not only the marketplace root: the root check does not parse command headers. A description containing `": "` breaks YAML and the header is silently dropped.
- **Every "did not run" path needs its own signal.** A chat that starts a meeting and then reads "the latest report" will show the previous meeting when nothing started; the chair exits with NOT STARTED (code 6) for a meeting asked from a chat.
- **Have a fresh reviewer read the template cold,** as the new owner's Claude would, on their operating system, and check every finding on the page before fixing.

## What the first real install taught (19 Nov 2026, the new owner's own debrief)
- **About 8 in 10 checked facts matched.** The errors came in six kinds: who said it (a team member's words put in the owner's name), a proposal recorded as a decision, wrong dates, overstatement, misread numbers, and "no reply" when the reply was in another channel.
- **Fixes that belong in every build:** a kind tag on every fact as it is written (decided / proposed / said by <name> / heard on a call / inferred; no tag, no use); a quote counts as the owner's only from the owner's own message or voice; every price, money figure, quote in the owner's name and veto rule checked 100% against the original, the rest one in ten; a checker on each batch as it lands, not after; one facts register (fact, value, date, source, kind, checked) that the brief is built from; a one-page "top 20 facts" the owner marks True / Not quite / Not true before seating; the strongest model only for the brief, the member review and the decision-critical checks.
- **Blind spots no reading pass fixes:** voice notes and Telegram voice answers (need transcription), and a fact the owner's team states in different ways (the owner settles it once, in one sentence).

## Long or short member files: tested (November 2026)
- 7 role-model members x 3 questions x 2 runs x 3 versions, graded blind by Opus, plus one meeting per version. Long files (about 4,500 words carried every turn) gave the same usefulness and voice as one-page files, slightly safer facts, and cost about two thirds more per meeting.
- **Use a one-page member file with the dossier on disk and look-ups on.** Members read the dossier when a question needs a detail (half the method questions, most "what does the record say" questions) and never for a plain judgement; accuracy then matches long files. Without look-ups, members invented a stance on a silent topic 3 times in 14.
- The error left in every version was a rule credited to the wrong person: tell members to check the dossier before attributing a rule, figure or quote.
- Medium files (about 2,000 words) were tested too and did worst on facts: members looked things up far less (about 10% against 45%) without the file holding the whole record. One page with look-ups stays the choice.

## Owner-facing checks stay small (19 Nov 2026)
- A facts page holds at most 25 items; the rest wait for a later round or a meeting's question. No bookkeeping columns the owner never reads. An after-meeting check says nothing when all is right and at most three lines when not.
- A fact sheet (one shared search, conflicts flagged) beats letting every member launch helpers: seven members searching in parallel multiplies cost and time for the same searches. Members keep their own file look-ups.
- **The fact sheet is for big decisions only** (money, prices, offers, direction), at most ten facts, one line each. Everyday questions go in without one. A long sheet full of UNCONFIRMED flags pulls the debate onto the facts instead of the decision. (Owner's ruling, 20 Nov 2026.)
- In a council with a blank slate, old dossiers and reports are history, never facts on a fact sheet.
- Four confirmation questions per round is enough; list the rest for later instead of opening a second round at once.

## How many members (tested 20 Nov 2026)
- The chair seats three or four members per meeting whatever the roster holds, so roster size barely changes the cost of one meeting and did not change the decision (five against seven, two questions, blind judge split one each; five about a fifth cheaper). Five to seven are all workable: keep a seat only if real questions would seat it and it brings a view no other seat holds. After five to ten meetings, read the seating lines in `chair.log` ("Seated for this topic") and offer to drop a member that was never seated. Two seats that look alike on paper can still add different views in practice; judge by what each says, not by the remit line.

## A real owner's first day of meetings (20 Nov 2026)
From the second owner's own system brief, each claim checked against the chair program before anything was changed. Fixed in template v2.4.4.
- **Auto-resume must match the real message.** "You've hit your 5-hour limit · resets 1:30pm" matched none of the usage phrases, so a meeting stopped at turn 19 instead of waiting. Match "hit your", "hour limit" and "weekly limit" too, and add a test with the exact text. Never let a stop message promise a timer that does not exist on that system.
- **Setup that never overwrites means updates never arrive.** A plugin update reached the commands but never the council's own copy of the program. Give an explicit update step (`new_council.py --update-program`: program files only, old copies kept, the council's files untouched, nothing copied in that does not parse) and run it at the start of a refresh.
- **An owner's local change to the program must survive an update.** Before replacing her copy, adopt what she added (here `second_chair_effort`), or the update silently removes it.
- **"Decided" in the minutes read as the owner's decision.** Council figures and prices were listed as hers in three of four meetings. The clerk now writes "Proposed:" for anything the owner has not ruled on, and the chat keeps the word.
- **Run meetings as tracked background jobs, never detached with `&`.** A detached meeting stopped with no signal and was found an hour later.
- **Before saying "her council does not get the fixes", compare the versions.** The program had not changed since her install; only the instructions had.

## Seats from the owner's own record, beside role models (21 Nov 2026)
- **Two kinds of fit, kept apart:** members *like* the owner (path, values, way of working) and members the owner *needs* (who speaks to the blind spots). Ranking only by likeness builds an echo; only by need builds a lecture.
- **Created seats come from the owner's record, decisions first.** A hand sort of the owner's own list of open questions beat keyword counts: 26 of 52 open questions were about what is true or may be said, which made "Truth" its own seat. Keyword counts across files mostly measure common words.
- **One area, one seat:** a created seat and a role model that would say the same thing are one seat; the role model goes on call (its file kept, brought in when a question is in its field).
- **Quotes beside each other need their speaker on each one.** A member's line placed under "You:" was read as the owner's (caught by another session).
- **A council run through chat helpers (no chair program) misses the chair's safeguards:** the challenger, the sign-off check, the facts sheet and after-check, usage logging and auto-resume. Say so when offering it, and prefer setting the council up with the template when decisions matter.

## How every answer reads (21 Nov 2026, `references/answer-style.md`)
A real owner found the council's answers "erratic, chaotic and unorganised" and ended up asking her Claude to talk "as a friend". The causes were in our own instructions: "plain and short" fighting "show everything for big decisions", the conclusion copied word for word (so council terms reached her), stacks of bold labels, four or five figures per paragraph repeated in every message, and every message restarting the story. Every answer now follows `references/answer-style.md`: a warm friend's everyday words, about one screen, in one line what it means, what the council thinks in two or three short paragraphs, what changed since last time, numbered next steps (at most five), what is still the owner's to decide, one question; at most three numbers a paragraph with the currency; guesses drawn and labelled as guesses; the overview page as the one home for detail; charts with the app's built-in visual tool and the dataviz skill when available.
- **Revised the same day (21 Nov 2026):** an owner then asked for the whole answer in the chat and more context. The chat now carries the full answer told like a friend (in one line, the overall picture, the suggested steps with why, what each member said and why, disagreements, still yours to decide, at most two questions last), with no one-screen cap; every review and big decision gets a produced overview page with a member map and a steps timeline; corrections on the page are hidden behind one button. Template v2.5.1.

## This plugin's extras: the hub and the commands

Installing the plugin adds four commands and a desktop-style app.
- **`/council-build`** builds a council from the owner's own material: their files, notes and meeting transcripts, from local folders or connected tools (Google Drive, Notion, Zoom, Granola, Fireflies, Otter or any other connector the session has). Claude guides the owner one step at a time through connecting their apps, reads all of it in stages, writes the owner's profile and proposes the members; at the end the owner confirms by multiple choice only, with nothing to type, and the council brings the most important decisions and matters to the table as its first agenda. The look and the members' final names are decided afterwards.
- **`/council-meet <question>`** runs a meeting and brings the result back into the chat: the conclusion and first step first, the council's questions as multiple choice (answers recorded with `council.py --answer`), two visuals every meeting (the decision, and what happens next) and an overview page on request, built only from the meeting's own minutes. Before a big decision (money, prices, offers, direction) it prepares a short fact sheet, at most ten facts with conflicts flagged, and attaches it; other questions go in without one; afterwards it checks the figures and credited quotes in the minutes, and says nothing unless something is wrong. It reads the result with `council.py --report latest`. This chat is the owner's main way in.
- **`/council-review`** runs a whole-picture review, "where do I stand": every member answers the same six questions alone (strengths, blind spots, desires, how the owner is seen, the way forward, the support needed), then an open floor with a contrarian, a pulled-together view with every line marked [record], [council] or [my view], three to five questions that would change it, rounds after the answers, and an overview page the owner marks True, Not quite or Not true.
- **`/council-hub`** (optional) opens the hub: Home, the live meeting, the round table, Talk with Claude, Files, Questions, the Library and the track record.

**Facts.** Setup keeps one facts register, `outputs/council/inputs/FACTS.md` (each fact with its kind, exact source and check status), and builds the brief from it. Every price, money figure, quote in the owner's name and veto rule is checked 100% against its source as each batch lands; the owner confirms the 25 facts that matter most on one page; anything that cannot be verified stays UNCONFIRMED and is never argued from. The brief is the biggest lever on a council's accuracy, because every member reads it in every turn.

**Member files stay one page, with look-ups on.** A test in November 2026 (seven role-model members, three questions, two runs, three versions, graded blind, plus one meeting each) found that carrying the whole dossier in every turn made members no more useful, cost about two thirds more per meeting, and was only slightly safer on facts; one-page members that may read their dossier were as accurate. Members look things up when a question needs a detail, and not for a plain judgement. Every member file ends with the line telling it to check before it states a figure or credits a rule or quote.

**Role-model members.** Seats built only from a public figure's own recorded words (the **persona-research** skill), kept in `outputs/council/members/role-models/<name>/` with a `dossier.md`, the research, and a `member-<name>.md` that is copied into `members/approved/` when the owner keeps it. A pack can arrive as a zip ending in `-role-model.zip`; unpack it there and ask the owner Keep / Leave out. Role models are always `Status: provisional`, named in full, and speak as the person's recorded approach, never as the person.

`scripts/new_council.py` installs everything into a project: `tools/council/council.py` (the chair), `tools/council/chamber/` (the hub, served on http://127.0.0.1:8790), and `outputs/council/` (the council's files). The owner's name goes in `outputs/council/config.json` as `owner_name`.
