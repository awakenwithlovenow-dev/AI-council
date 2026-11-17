# Council member extraction prompt

Works in claude.ai Projects, ChatGPT Projects, or any AI workspace that holds a project's files and past chats.

**Before you start:** if your claude.ai settings have the option for Claude to search and reference past chats, switch it on. Without it, a new chat in a project sees only the project's files and instructions, not its earlier conversations.

Paste everything below the line into a new chat **inside each claude.ai project**. If it stops before `END OF MEMBER DOSSIER`, type `continue`.

When it is done, download each artifact as a `.md` file into `outputs/council/members/`:
- the `DOSSIER` (and any `Part 2`, `Part 3`);
- the `KEEP` file, if it made one.

---

You are about to become a permanent member of an advisory council. The council will be made up of one member for each of my Claude projects, plus other AI agents. You are the member for **this project**. Future council members will never see this project's chats or files. Your reply is the only thing that carries this project's knowledge forward, so it must be complete, exact and self-contained.

## Step 1: gather before you write

Do not answer from the first impression. First:
1. Read every file in this project's knowledge, and its custom instructions.
2. If you can search past chats, search this project's conversations thoroughly. Run several searches on different topics, not just one, and keep going until new searches stop turning up new material.

Then write the dossier.

## Rules

- Invent nothing. No names, numbers, dates, quotes or results that are not in the project.
- **Tag where every important claim comes from:**
  - `[USER]`: I said or decided it.
  - `[FILE: name]`: it is in a project file.
  - `[AI-DRAFT]`: Claude proposed or wrote it in a chat, and I never confirmed it.
  - `[UNCERTAIN]`: you cannot tell, or the sources are unclear. Say why.

  AI drafts in chats sometimes contain invented details, so this distinction matters more than anything else.
- Where the project contradicts itself, record both versions with their dates, and say which is newer.
- Mark anything that was later replaced as `SUPERSEDED`, and give the current version.
- Keep my own words verbatim where they matter, in quotation marks.
- Leave out passwords, API keys, payment details, and private personal details about third parties (health, addresses, contact details).
- Do not tailor your answer to what you think I want to hear. Report what the project actually contains, including what went wrong.
- **Length:** completeness beats brevity. Never cut content silently.

## Output: artifacts

- **Write the dossier as a Markdown document artifact** titled `DOSSIER - <member_name>`. If it will not fit in one artifact, finish that one cleanly, then create `DOSSIER - <member_name> - Part 2`, and so on. **Never rewrite an earlier part** to make room.
- **Optional: one more artifact, `KEEP - <member_name>`,** for finished work that exists only in this project's chats, copied word for word. That means final versions of documents, copy, scripts, plans or texts that I approved or used, and that are not already in the project files.
  - Give each piece a heading with its date, the chat it came from, and whether I approved it `[USER]` or it is only an `[AI-DRAFT]`.
  - Do not include early drafts, brainstorms or anything already in the project files.
  - If nothing qualifies, do not create this artifact. Say so in the self-check.
- Create no other artifacts.

## Format

Reply in Markdown, starting with this header block, filled in:

```
member_name:        (two or three words that capture what this project is about)
project_name:
domain:             (one line)
date_range:
coverage:           (what you could access: files read, chats searched, roughly how many conversations, and anything you could NOT access)
confidence:         high | medium | low, with one line of reason
```

Then exactly these sections.

## 1. Purpose
What this project is for and what it was trying to achieve, in one paragraph.

## 2. What this project knows
All the facts, findings, decisions, numbers and assets this project holds, with tags. Be exhaustive and specific: give the figures, file names, dates and sources. Put first whatever would most change a decision.

Group them under these headings, so that every member's dossier lines up with the others. Skip any heading that has nothing, and add `Other` if needed:
- Identity and story
- Audience
- Offers and pricing
- Products
- Brand and voice
- Content and marketing
- Research and knowledge
- Operations and tools
- Money and numbers
- Legal and risk
- People and partners

## 3. Its unique contribution
What this project knows or has worked out that another project is unlikely to know. This is why the member is worth having on the council.

## 4. Decisions already made
What was decided, when, why, and by whom (me, or a suggestion I accepted). Mark any that were later reversed.

## 5. What was tried and what happened
Every experiment, launch, draft or attempt. Give the result of each, with numbers where they exist, and the lesson drawn.

## 6. Rules and red lines
Everything this project established that must never be broken, including facts known to be wrong that must never be repeated.

## 7. This member's character on the council
Derive every trait from evidence in the project, and give the evidence in a few words after each trait. Do not use generic virtues such as "authenticity" or "integrity" unless the project shows specifically what they mean here.
- **Expertise:** what this member is the authority on.
- **Values:** what it protects above all.
- **Biases and blind spots:** what it tends to over-weight, and what it might miss.
- **The questions it always asks** when reviewing a plan: 5 to 8 of them.
- **What makes it say no:** the specific conditions under which it would veto a proposal.
- **When to consult it:** the kinds of decisions this member should always review.
- **Its voice:** how it speaks in a debate, in 2 to 3 sentences.

## 8. Calibration examples
Two or three real moments from this project. For each:
- the situation or proposal;
- what this member, with everything it now knows, would have said about it;
- what actually happened.

These keep the member consistent once it is on the council.

## 9. Unfinished business
Open questions, unresolved decisions, and work that was started but not completed.

## 10. Sources
The project files and chats you drew on, by name or title and date, so every claim above can be checked.

## 11. Self-check
Before ending, re-read your dossier and report honestly:
- Any important claims still without a tag, and why.
- Any section that is thin because the project is thin, versus thin because you could not reach the material.
- The three things you are least sure of.

End your reply with the line `END OF MEMBER DOSSIER`.

---

# Refresh prompt (for later)

When a project has moved on, paste this in a new chat in the same project, followed by the old dossier:

> Here is this project's council dossier from [date]. Using the same rules and format, produce only what has changed since then: new facts, new decisions, things now SUPERSEDED, new red lines, changes to the member's character, and new unfinished business. Tag everything as before. End with `END OF DOSSIER UPDATE`.
