# Prompt 05: Launch, first live session, and keeping it learning

A checklist for the lead AI. Do nothing in this list until the owner gives the green light.

## Launch (only on the owner's explicit green light)
1. Apply the signed amendments to the member files; copy them into `members/approved/`. The roster goes in as `SEATS-ROSTER.txt`, never as `.md`.
2. Update AGENDA.md: mark finished items done, put URGENT items first, and make the first item a **real creation task** the owner will use. A test scenario is the wrong first item.
3. Headless login: run Claude's program once with `auth login` (`council.py --check-claude` names it; Codex likewise if used). The path can change when the app updates, so look up the current one. Check with a one-line headless call.
4. If a timer is already installed, create the `PAUSE` file until step 5 is ready.
5. Run **one session by hand**, and let the owner read the transcript, minutes and drafts. Only then offer the hourly marathon.

## Every interactive session afterwards
- **With a second AI only:** read the mailbox first and keep a watcher running while the session is open.
- When the owner rules on anything in chat, **file it in outputs/council/memory/RULINGS.md** (append directly, or post a `COUNCIL: RULING` mailbox note). A ruling that stays only in chat is lost.
- When the owner answers a question in the FOR file (`- [x] question ANSWER: ...`), the chair files it automatically. Check that it did.
- Read `memory/member-lessons/`. A lesson that keeps recurring for one member means its profile needs a fix, proposed to the owner (and to the other AI, if one is used).
- Re-run Prompt 04 after any big change to the members or the program.

## Explaining it to the owner (they will ask)
- "Where does the council live?" In files, in a folder. The program makes the AIs speak as those files describe. It does not live in the chat.
- "Why a login?" The program starts its own background AI sessions, which need their own one-time sign-in.
- "Does it act on its own?" It debates and drafts on its own, only on the owner's agenda and its follow-ups, and **only on paper**. It never publishes, sends, buys or contacts anyone.
- "Is it a skill?" The skill is the recipe for building a council. The owner's council is what was built with it, and lives in their project.

## Two traps found on the first live run (8 Oct 2026)
- **Dry runs never call the real AIs.** After any change to how the chair calls an AI (flags, config overrides, models), make **one real call** through the chair before a live session. A config override with a quoted TOML key passed every dry run, then stopped the first live session at turn 2 with "invalid transport".
- **File each ruling one way.** Append it directly to RULINGS.md, **or** post it as a `COUNCIL: RULING` mailbox note, never both, or it is filed twice. Never delete a mailbox-filed ruling line: the chair recognises it by its message id, and would file it again.
