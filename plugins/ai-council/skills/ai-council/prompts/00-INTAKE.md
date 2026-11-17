# Prompt 00: Intake (the owner's goal, brief, agenda and existing rulings)

Paste into the AI that will build the council (Claude Code, Claude, ChatGPT). Fill in the brackets, or leave them and let it ask.

---

You are setting up an AI council for me: a standing group of AI advisers that will debate my agenda, on paper, and hand me drafts and decisions. Before any members are built, establish the foundation.

**Interview me with at most eight short questions, in one message.** Ask only what you cannot infer from what I give you. Cover:
1. The one question the council exists to answer for me (for example: "how do I build a sustainable business around X").
2. What the council should produce: drafts, plans, reviews, copy, research summaries.
3. My standing rules for anything written in my name: voice, words I never use, claims I never make, things never named in public.
4. Decisions I have already made that the council must not reopen.
5. Facts about my situation that change advice: time available, priorities, budget, constraints.
6. Anything the council must never do or say. For example: I may not want lawyer referrals or medical caveats in its output.
7. My first three to six agenda items, in priority order.
8. Which existing material it should draw on: projects, documents, reports.

Then write these four files, plain markdown, no invented facts (mark anything missing as MISSING):
- **BRIEF.md**: the question; a table of inputs (file, what it is); "Settled (do not reopen without new evidence)"; "Facts from the owner (dated)"; "Known conflicts (the owner must settle)".
- **AGENDA.md**: my items as `- [ ] 1. **Title.** What a good result looks like.` The owner owns this file.
- **memory/RULINGS.md**: every decision and rule I have stated, each dated, in my words where possible. Rulings outrank everything else the council reads.
- **Charter rules 4 and 10**: my voice and brand rules (rule 4), and my owner-specific rulings (rule 10), ready to paste into the charter template.

Rules: invent nothing; keep my wording where it matters; one fact per line; date everything; if two of my statements conflict, record both under "Known conflicts" and do not pick one.
