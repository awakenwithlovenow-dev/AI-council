---
description: A whole-picture review of where you stand. Every member looks at you and your business from its own angle, and you answer between rounds.
argument-hint: "[what to look at, optional]"
---
Run a review of the owner and the business with the whole council, here in the chat. A review asks "where do I stand", not "what do I do about one thing"; for one decision use `/council-meet`. The owner's words: $ARGUMENTS

Talk to the owner in plain words, one short message at a time. No file paths, commands or technical terms in anything the owner reads. Members are always named in full.

Keep everything in `outputs/council/reviews/<today's date>/`. Nothing is published, sent or bought.

1. **Check the brief.** Read `outputs/council/BRIEF.md`, `outputs/council/inputs/FACTS.md` (where it exists) and `outputs/council/memory/RULINGS.md`. A fact marked UNCONFIRMED stays marked so in every file of the review. A review is only as good as the brief: it should hold who the owner is, the story in their own words with dates, what they sell and for how much, the numbers, what is settled and what is not. If the brief is thin, say so in one line and offer: read more material first (run `/council-build` again, which then refreshes only what is new) / go on with what there is.
2. **Solo round.** One helper subagent per approved member (every `.md` in `outputs/council/members/approved/`, role models included), all at once, on Sonnet. Each helper gets: the brief, the rulings, its member file, and a role model's own `dossier.md` when the member file names one. It may read files, never the web. Each answers alone, without seeing the others, these six questions:
   1. Strengths and expertise;
   2. Weaknesses and blind spots;
   3. Desires and outcomes;
   4. How the owner is seen, and their angle;
   5. The way forward;
   6. The support the owner needs.
   Rules for every helper: speak only from the member file (and dossier) and the brief; where they hold nothing on a point, write "nothing found"; mark each line **[record]** (the owner's own words or files, quoted exactly, with the date) or **[council]** (the member's own principle); a principle held against the owner's record starts "Applied to you:"; a role model speaks as "<full name>'s approach", never as the person; no health effect stated as fact, no legal or shipping advice; at most about 450 words. Save all answers, member by member, as `01-solo-round.md`.
3. **Open floor** (you, not a helper). Read every answer and write `02-open-floor.md`: where they agreed without being asked; each real disagreement as a pair, both sides in their own terms, then where they land; a table of red lines; the leading view in two or three sentences; then the member whose material most argues against the leading view makes the case against it, the others answer, and what stands. Never smooth a real disagreement over.
4. **Pulled together.** Write `03-pulled-together.md` under the six headings, every line marked **[record]**, **[council]** or **[my view]** (your own reading, which the owner may reject). End with "Where the council could not help" and "How this was checked" (what was read, what was not).
5. **Show the owner, then ask.** In the chat: the leading view first, then the strongest three strengths and three blind spots, each in one line. Then ask three to five questions whose answers would change the view, one at a time with the question tool: each says in its help text what it would change; give ready answers where the material allows, and the owner can always write their own.
6. **After the answers.** Write `04-after-your-answers.md`: a table "Your answer | What it changes"; the members whose view an answer touches answer again (helpers, as in step 2, given the answers); the leading view revised. Where an answer overturns an earlier line, put a dated correction at the top of that earlier file, never a silent rewrite. File each answer in `outputs/council/memory/RULINGS.md` with its date, in the owner's words. Repeat steps 5 and 6 while the owner wants to.
7. **The overview page.** Write `overview.html` in the same folder, one self-contained page, and open it. Chapters: where you stand now (the headline numbers from the record, if any); strengths; patterns and blind spots; what you want; how you are seen; what each member saw (one line each); where they disagreed; the way forward, in small steps; the support you need; still open. Every finding carries its mark and three choices, True / Not quite / Not true, with a box for the owner's own words; choices are kept in the browser, and a button copies them all so the owner can paste them back here. Simple, clear and direct: large text, strong contrast, black or white text on solid colour, one strong colour for the main point, no decoration.
8. **Answers pasted back** from the page are filed in `outputs/council/memory/RULINGS.md` (Not true and Not quite with the owner's words), and the next review or meeting reads them.
