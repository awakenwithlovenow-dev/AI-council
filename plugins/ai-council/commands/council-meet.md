---
description: Ask your council a question. It meets and brings back one clear answer here in the chat.
argument-hint: "<your question> [quick]"
---
Run a council meeting on the owner's question and bring the result back into this chat. This chat is the owner's main way to use the council; the hub (`/council-hub`) is only an optional overview. The owner's words: $ARGUMENTS

Talk to the owner in plain words, one short message at a time. No file paths, commands, session ids or technical terms in anything the owner reads.

1. **The question.** If the owner's words hold no question, ask in one line what the council should decide, and wait. Use a full meeting unless the owner says "quick"; mention once that "quick" gives a faster, lighter answer.
2. **Start it.** With the project's Python (`python3` on a Mac), run `tools/council/council.py --topic "<the question, in the owner's own words>"`, adding `--quick` when asked, in the background. Files the owner attached in `outputs/council/files/` go in with `--files <name>`. Never start a meeting while another is running. Tell the owner in one line: "Your council is meeting now. It usually takes 3 to 10 minutes." Then wait quietly for the meeting to finish.
3. **If it did not run,** run `tools/council/council.py --check-claude` and tell the owner in one plain line what to do (sign in again, wait for the usage allowance to return, or nothing). Never show an error message as it came.
4. **Read the result** with `tools/council/council.py --report latest`. It prints the meeting's result: `conclusion`, `first_step`, `decided`, `questions` (each with `n`, `ask`, `options`, `if_skipped`, `state`) and `outcome`.
5. **Show the answer first,** in this order and nothing more:
   - the conclusion, word for word;
   - "First step:" and the first step, word for word;
   - at most five short bullets from `decided`.
   Leave out the debate, the outcome record and the costs unless the owner asks.
6. **Ask the council's open questions, one at a time,** with the question tool: the question exactly as written, its `options` as the answers (the owner can still type their own), and the `if_skipped` line as the help text. After each answer run `tools/council/council.py --answer latest <n> "<the owner's answer, word for word>"`. If the owner skips one, leave it open.
7. **Then one multiple-choice question:** "What next?" Meet again with my answers / Show it as a chart or slides / That is all for now.
   - **Meet again:** run `tools/council/council.py --follow-up <the session from the report> --quick` and repeat steps 4 to 7.
   - **Chart or slides:** see below.
8. **Charts and slides.** Build them only from this meeting's own minutes and drafts (the minutes file named in the report, and `outputs/council/drafts/<session>/`). Never add a number the council did not write, and mark assumed figures as assumed. Show them in the clearest way this Claude can show a picture in the chat; otherwise write a simple self-contained HTML page into `outputs/council/visuals/<session>/` and open it. Slides hold one idea each: the conclusion and first step; the numbers; the options weighed and why this one won; the risks and what would change the decision; the open questions.
9. **"Why?"** If the owner asks why the council decided something, read the minutes and the meeting record and answer in a few plain sentences.

If no council exists yet, say so in one line and run `/council-build` instead. Nothing is published, sent or bought.
