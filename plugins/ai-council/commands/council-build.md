---
description: Build an AI council from your own files, notes and meeting transcripts
argument-hint: "[folders or sources to read, optional]"
---
Build an AI council for this project from the owner's own material. Load the **ai-council** skill first and follow it; also load **headless-ai-calls** and **local-app-build** before changing any code.

Sources named by the owner: $ARGUMENTS

## How to talk to the owner (this overrides the skill's intake wording)

The owner may never have used Claude on a computer. Guide them like a first-time user.
- **One step per message.** Say what to click or type, in one or two short sentences, then stop and wait.
- **Explain only what they must do.** Do not describe what you are doing behind the scenes, the folders, the files or the method. A short progress line now and then is enough ("Reading your email: 400 of 1,200").
- **Every question is multiple choice.** Use the question tool with two to four ready answers. Never ask the owner to type an answer, a name, a path or a setting. If you need a fact, find it in their material and offer it as a choice to confirm.
- **Do the technical parts yourself.** Never ask the owner to run a command you can run.
- Plain words. No jargon ("connector" becomes "connect your email").

## The steps

1. **Set up, silently.** Find Python 3 (`python3` on a Mac). If it is missing, guide the install one click at a time. Run the skill's `scripts/new_council.py --project .` with it (the skill's base directory is shown when it loads). Say only: "Your council's home is ready."
2. **Connect, one app at a time.** Check which apps this session can already read. Then, for each of these in turn, ask one multiple-choice question ("Do you use Gmail for work?" Yes / No / A different one): work email, documents (Google Drive, Notion or folders on this computer), meeting and call recordings or transcripts (Zoom, Granola, Fireflies, Otter), messages (Slack or similar), and the website or sales pages (find the address in their material and offer it to confirm).
   - For each app they use that is not connected, give the steps exactly as this session shows them, one per message, and after each ask "Did that work?" (Yes / No / Skip this one). On No, try once more with a simpler route, then skip it and note it.
   - Test each connection by reading one item, and say "Connected: your email" in one line.
   - Read only. Never write to, send from or delete in a source.
3. **One question on limits, multiple choice, several answers allowed:** "Is anything off limits?" Read all my work material / Leave out personal and family email / Leave out money and banking / Leave out staff and HR.
4. **Read all of it, in stages, quietly.** The owner should not have to explain their business; the material does that.
   - **Inventory first:** list what exists in each source and save it as `outputs/council/inputs/INVENTORY.md` with counts. Tell the owner the totals in one line and that the reading may take more than one sitting.
   - **Read everything in scope, batch by batch,** newest first: work email, sales pages and the website, offers and prices, transcripts, documents, notes and customer messages. Write what was learned to disk after each batch, and save a text copy of each source that matters into `outputs/council/inputs/`.
   - **Keep a coverage record,** `outputs/council/inputs/COVERAGE.md`: every source, how many items exist, how many were read, what was skipped and why. Never say everything was read unless this record shows it.
   - **If the allowance runs out,** stop cleanly, tell the owner in one line when to come back, and continue from the record.
   - **Write the owner's profile into `outputs/council/BRIEF.md`:** who they are, what the business sells and to whom, offers and prices, how customers arrive and why they stay or leave, the owner's own way of speaking (quoted from their writing), the numbers that exist, and the decisions that keep coming back. Every statement carries its source and date; keep **decided** apart from **discussed**; mark anything inferred.
   - **Write one dossier per body of work** in `outputs/council/members/dossiers/`, citing source and date.
5. **Propose the members.** One seat per body of work (three to seven), designed with `references/member-design.md`: convictions as labelled hypotheses, the questions they always ask, veto conditions and evidence rules. Members are **roles, never imitations of real people** named in the material. A member file holds what the seat knows how to do, its conviction, its questions, its red lines, its voice and its boundaries. **Prices, offers, plans, numbers and past events never go in a member file:** they date, and a council once argued from stale prices that sat in its member files. Put them in `BRIEF.md` with their date and source. For each member, note in one line which part of the material calls for it ("pricing comes up in most of your emails"). Write them to `outputs/council/members/final/`.
6. **Independent review.** Run `prompts/03-CROSS-REVIEW.md` in a fresh session on a different model, and strike anything invented or weakly sourced.
7. **Confirm, by multiple choice only.** Ask only what truly needs the owner's word, one question at a time, each with ready answers drawn from their own material and your recommendation first:
   - their name as the hub should greet them (the forms found in their material);
   - what the business is, in one sentence (two or three versions to choose from);
   - what the council is for (the two or three recurring decisions you found);
   - what it must never do (several answers allowed: spend money, publish, contact people, change prices);
   - each proposed member in one line, under a plain working name for its role ("Sales Lead"), with the reason from their own material in a few words ("pricing comes up in most of your emails"): Keep / Leave out;
   - anything in the profile you could not settle from the material, as "Which is right?" with the candidates.
   Record every answer in `BRIEF.md`, charter rules 4 and 10, `memory/RULINGS.md` and `config.json` (`owner_name`). Do not ask about anything the material already settles.
8. **Role models (optional).** A role model is a seat built only from a public figure's own recorded words, read word for word: a lens on their approach, never an imitation of the person, always named in full.
   - **Packs first.** Look for role-model packs the owner was given: a zip whose name ends in `-role-model.zip` in their Downloads, on the Desktop or in this folder, and folders already in `outputs/council/members/role-models/`. Unpack each into `outputs/council/members/role-models/<name>/`, never straight into `members/approved/`.
   - For each pack, one question: "Add <full name> to your council as a role model? This seat speaks from their own recorded words." (Keep / Leave out). On Keep, copy its `member-<name>.md` into `members/approved/` and add the row in its `roster-line.txt` to the seat table in `members/approved/SEATS-ROSTER.txt` (the co-chair chooses seats from that table, so a role model missing from it is never seated).
   - **Then:** "Is there anyone else whose work you look up to?" with up to three names the owner's own material quotes, follows or mentions, plus "No one else" (several answers allowed). For each name chosen, say in one line that this takes time and usage and offer "Now / Later". To build one, load the **persona-research** skill and follow it exactly: the four-point bar first (anyone who falls short becomes a case study, not a seat), one person at a time, every line sourced. Write the research, a `dossier.md`, a `member-<name>.md` and a one-row `roster-line.txt` (role, full name marked provisional, field) into `outputs/council/members/role-models/<name>/`, in the same layout as a pack, then ask Keep / Leave out as above.
   - A role-model member file says `Status: provisional` (it may object, never veto), points to its own dossier, lists where the person is silent, and never puts an unrecorded opinion in their mouth.
9. **Bring the important matters to the table.** From everything read, write the council's first agenda in `outputs/council/AGENDA.md`: the five to seven decisions and matters that most need tackling, most important first. For each: one plain sentence, why it matters now, what the material shows (with source and date), and what a good result would produce. Choose by what recurs, what is overdue, what money or customers depend on, and what the owner keeps putting off. Show the owner the list as one multiple-choice question, several answers allowed ("Which of these should your council take on?"), with your top three ticked first, and keep the rest lower on the agenda.
10. **Check the council can work on its own.** Run `tools/council/council.py --check-claude` with the same Python. It makes one small real call the way the desktop icon will. If it prints READY, say nothing. If it prints SIGN-IN NEEDED, start the sign-in yourself: run the program it names with `auth login` in the background, tell the owner in one line ("A page will open in your browser. Click the button to approve."), wait for "Done" (Done / It did not open), then run the check again. If it still fails after two tries, say so in one plain line and go on: the hub will open, but meetings will not run until this check passes.
11. **Finish.** Copy the kept members to `members/approved/` and run one dry run. Last question: "Shall your council hold its first short meeting now, on the first matter?" (Yes / Later). On Yes, run it exactly as `/council-meet` does, here in this chat. Then tell the owner, in three lines at most: to ask the council something, come back to this chat in the sidebar and type `/council-meet` and the question; the answer comes back here; `/council-hub` opens an overview window, if they ever want one.

**Decided afterwards, not during this build:** the look of the hub (colours, emblem), the council's own name, and the members' final names and signs. Use the standard look and plain working role names for now, and do not ask about any of them. They are settled later, once the owner has seen the council work.

Nothing leaves the project folder. Nothing is published, sent or bought.
