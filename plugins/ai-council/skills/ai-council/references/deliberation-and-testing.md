# Deliberation and testing

**One AI is enough.** The default independent reviewer is a fresh session of the same AI, on a different model, with an adversarial role (prompts/03-CROSS-REVIEW.md). A second AI such as Codex is optional, and the mailbox notes below apply only then.

## Deliberation

- **Route.** If the user has a live Codex thread, deliberate through the agent-bridge **mailbox**: `post_message(sender, to, subject, body)` and `read_messages(reader)`. Codex then reasons with that thread's full context. Use fresh headless runs (`scripts/converse.py <prompt> <log>`) only when the user approves, and say which route you used. Headless runs lack the thread's memory.
- **Check the mailbox first, every session.** Arm a Monitor that greps `mailbox.jsonl` for new `"to": "claude"` lines every 60 s, and re-arm it on expiry. In the first build, five Codex messages sat unread for a day.
- **Message format.**
  - Subject starting `COUNCIL:`.
  - Reply per point: CONCEDE / HOLD / AMEND, with file:line evidence.
  - Sign-off: SIGN, or OBJECT with the exact replacement text.
  - End with PUBLISHED: none.
- **Hold only with evidence.** In the first build:
  - Claude held "never pitch the invitation-only tier cold" on the user's recorded ladder, and Codex conceded.
  - Codex held that testimonial matching is not verification, and that "no pull before" is not a contradiction; Claude conceded.
- **Keep corrections visible** (struck-through text, then the correction, then who and when). Never rewrite silently.
- **Do not edit the other agent's working folder, or the final files, during its review.** Draft in your own folder. Install only after both sign and the user says go.
- **Expect about 20 corrections of overstatement.** "First-hand", "no data exists", "the only record", "the biggest leak": scope every claim to what the source shows.

## Blind scenario test

1. Write one constructed scenario (labelled constructed) whose asks each hit a different seat. For example, an event offer with a false historical blurb, a disputed testimonial, an inflated credential, an ad on an ingestion video, a cold pitch of an invitation-only tier, a shipping ask, and a deadline.
2. **Write the lead reaction first**, before seeing anyone else's.
3. Get Codex's reaction blind (it may not read the `T01-*` files).
4. Get each member's reaction blind: Sonnet subagents in parallel, each given only its member file and the scenario, at most 400 words, ending `VERDICT:`.
5. Compare: an agreement matrix; unique contributions per answer; **member errors** (check each against its source); the length discipline.
6. Report the strengths, the verified weaknesses and the improvements. Fix the cheap ones in the same pass, and dry-run after any chair change.

### What test 01 taught (all fixed in `scripts/council.py` and the charter)

- Members did not know the roster → the chair now injects the seats.
- Members lacked key lists → reference facts now go into the profile.
- Vetoes piled up and nobody merged them → each review ends `WOULD APPROVE IF:`, and the synthesis merges them into one repair list.
- Everyone agreed and no one imagined (**the user called this the most important weakness**) → the **live floor**. Members debate on one floor, the lead opens with the most ambitious version, speakers pass with `CALL: <speaker>`, every member speaks, and two engines speak for the members.
- Live decisions produced analysis only → the charter now requires deliverable drafts. A zero-draft synthesis cannot close unless the lead writes `NO DELIVERABLE NEEDED:`.
- A codex review of the chair found that an early CONSENSUS could close a floor, and that seating used trailing statuses → closing now requires both co-chairs' close-phase CONSENSUS and no standing veto.

## Running it

- `council.py --dry-run` tests the plumbing with no model calls.
- `council.py` runs one session.
- `council.py --marathon` runs sessions back to back until NEXT AGENDA says `1. NONE`, a usage limit hits, or the guard of 12 is reached.
- `council.py --install-schedule --every-hours 1` and `--uninstall-schedule` manage the timer.
- A cheap Haiku preflight stops a session before any Codex call if headless Claude is logged out.
