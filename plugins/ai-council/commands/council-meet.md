---
description: Ask your council a question. It meets and brings back one clear answer here in the chat.
argument-hint: "<your question> [quick]"
---
Run a council meeting on the owner's question and bring the result back into this chat. This chat is the owner's main way to use the council; the hub (`/council-hub`) is only an optional overview. The owner's words: $ARGUMENTS

Talk to the owner in plain words, one short message at a time. No file paths, commands, session ids or technical terms in anything the owner reads.

1. **The question.** If the owner's words hold no question, ask what the council should decide, with the top three open matters from `outputs/council/AGENDA.md` as the answers (the owner can still type their own), and wait. Use a full meeting unless the owner says "quick"; mention once that "quick" gives a faster, lighter answer.
2. **Start it.** With the project's Python (`python3` on a Mac), run `tools/council/council.py --topic "<the question, in the owner's own words>"`, adding `--quick` when asked, in the background. If the owner attached a file in this chat, first save a copy into `outputs/council/files/`; files there go in with `--files <name>`. Never start a meeting while another is running. Tell the owner in one line: "Your council is meeting now. It usually takes 3 to 10 minutes." Then wait quietly for the meeting to finish.
3. **If it did not run.** If the program's output says `NOT STARTED` (today's limit of meetings, another meeting still running, or the council paused), tell the owner that in one plain line and stop here: never read `--report latest` then, because it would show the previous meeting as if it were this one. If the program failed in any other way, run `tools/council/council.py --check-claude`. On SIGN-IN NEEDED, start the sign-in yourself as `/council-build` step 10 does (run the program it names with `auth login` in the background, tell the owner "A page will open in your browser. Click the button to approve.", wait for Done, check again), then start the meeting again. On USAGE, tell the owner in one line to try again later. Otherwise say in one plain line that the meeting could not run. Never show an error message as it came.
4. **Read the result** with `tools/council/council.py --report latest`. It prints the meeting's result: `conclusion`, `first_step`, `next_steps`, `needed`, `decided`, `questions` (each with `n`, `ask`, `options`, `if_skipped`, `state`) and `outcome`.
5. **Show the answer first,** in this order and nothing more:
   - the conclusion, word for word;
   - "First step:" and the first step, word for word;
   - "Next steps:" and "Needed:", word for word, when the report has them;
   - at most five short bullets from `decided`.
   Leave out the debate, the outcome record and the costs unless the owner asks.
   Then show **the two visuals** (step 8), before any question.
6. **Ask the council's open questions, one at a time,** with the question tool: the question exactly as written, its `options` as the answers (the owner can still type their own; if it has fewer than two, offer Yes / No), and the `if_skipped` line as the help text. After each answer run `tools/council/council.py --answer latest <n> "<the owner's answer, word for word>"`. If the owner skips one, leave it open.
7. **Then one multiple-choice question:** "What next?" Meet again with my answers / Show it as slides / That is all for now.
   - **Meet again:** run `tools/council/council.py --follow-up <the session from the report> --quick` and repeat steps 4 to 7.
   - **Slides:** see step 8.
8. **Two visuals every meeting, slides on request.** Build them only from this meeting's own minutes and drafts (the minutes file named in the report, and `outputs/council/drafts/<session>/`). Never add a number, option or name the council did not write; mark assumed figures as assumed; keep the words plain and short.
   - **Simple, clear, direct, strong contrast:** each visual says one thing, and its title says it as a plain sentence. At most five items. Large text. Solid colour blocks with white text, or black text on white; no pale tints, no small grey print. One strong colour for the answer, grey for the rest. No decoration, and no legend or footnote unless the visual cannot be read without it.
   - **Visual 1, the decision:** the options the council weighed and the one it chose, where each seated member stood (agreed, objected, disagreed), and how strong the evidence was (from the minutes' outcome record).
   - **Visual 2, what happens next:** the first step and the steps after it, with the dates the minutes set for checking the result. If the meeting wrote figures (prices, targets, counts), add a simple chart of them here.
   Show them in the clearest way this Claude can show a picture in the chat; otherwise write one simple self-contained HTML page holding both into `outputs/council/visuals/<session>/` and open it. On "Show it as slides": one idea per slide: the conclusion and first step; the numbers; the options weighed and why this one won; the risks and what would change the decision; the open questions.
9. **"Why?"** If the owner asks why the council decided something, read the minutes and the meeting record and answer in a few plain sentences.

If no council exists yet, say so in one line and run `/council-build` instead. Nothing is published, sent or bought.
