# AI Council: a Claude Code plugin

Build your own AI council: a small board of AI members designed from **your own files, notes and meeting transcripts**. They meet, debate, challenge each other and hand you decisions and finished drafts. They work only on paper: they never publish, send, buy or contact anyone.

## What you get

- **`/council-build`**: connect your material (folders, email, Google Drive, Notion, Zoom, Granola, Fireflies, Otter or any other connector you have). Claude guides you one step at a time through connecting them, reads all of it in stages, keeps a record of what it covered, writes a profile of you and your work, and proposes the members. At the end you confirm by multiple choice only; there is nothing to type. Your council then brings the most important decisions and matters to the table as its first agenda. Colours and the members' final names are chosen afterwards. No earlier experience with Claude is needed.
- **`/council-meet <your question>`**: the everyday way in. Ask in your own words, right in the Claude chat. The council meets (quick or full) and the answer comes back to the same chat: the conclusion and the first step first, then two visuals (the decision, and what happens next), any question for you with answers to click, and an overview page if you want one. Before a big decision, Claude prepares a short fact sheet (at most ten facts); afterwards it checks the figures, and tells you only if something is off.
- **`/council-review`**: "where do I stand". Every member looks at you and your business from its own angle, you answer a few questions between rounds, and it ends with an overview page where you mark each finding True, Not quite or Not true.
- **`/council-hub`** (optional): a desktop-style overview app: Home, the live meeting, the round table, Talk with Claude, Files, Questions, the Library and a track record of how decisions turned out. Sources has a "Bring in from a connected app" button: your Claude reads Gmail, Drive, Notion, Slack or meeting notes for you, read-only.
- **Meetings that hold up:**
  - every member writes an independent view first;
  - a sign-off check catches dropped objections and unsourced claims;
  - approvals are tied to the exact draft;
  - the minutes keep evidence apart from agreement and say what the meeting changed;
  - decisions get a date to check later;
  - facts live in one register, the important ones are checked against the original, and anything that cannot be verified stays "unconfirmed" until you confirm it.
- **Skills** Claude uses while building and running it: ai-council, headless-ai-calls, local-app-build, agent-handoff, citation-discipline, and persona-research (for researching a public figure as a role-model member, from their own published words).

## Requirements

- Claude Code, signed in (the Claude desktop app's Code tab is enough).
- Background meetings keep their own sign-in, apart from the app's. `/council-build` checks it and walks you through it; by hand, `python3 tools/council/council.py --check-claude` says what to do.
- Python 3.9 or newer (a Mac's own `python3` is enough).
- Windows, Mac or Linux. The hub opens best in Edge or Chrome.
- Optional: the Codex CLI, for a second AI in the second chair.
- To read your apps during setup: connect them in the Claude app under Settings, Connectors (Slack, Gmail, Google Drive and others). Apps connected there reach a chat in the Code tab. Only the hub's optional "Bring in" button, which works in the background, needs them signed in for Claude's own program as well.

## Install

**From GitHub (to share it):** put this folder in a repository, then in Claude Code:
```
/plugin marketplace add awakenwithlovenow-dev/AI-council
/plugin install ai-council@ai-council
```

**From a folder (just you):**
```
/plugin marketplace add <path to this folder>
/plugin install ai-council@ai-council
```

**For a company:** an admin of a Claude Team or Enterprise account can add it to the organization's plugin list.

Then open your project folder in Claude Code and run `/council-build`.

## First time, on a Mac

1. Install the Claude desktop app and sign in.
2. Open the Code tab and choose an empty folder for your council (for example a new folder called `Council` in Documents).
3. Add this plugin. Paste this message to Claude, with the repository's own address in place of the placeholder:

   > Please add the plugin marketplace `awakenwithlovenow-dev/AI-council` and install `ai-council@ai-council` from it, using your own program's `plugin marketplace add` and `plugin install` commands. Then tell me when to start a new chat.

   The app also has a Plugins menu under the **+** button beside the message box. Use it if it offers a place for a GitHub address.
4. Start a new chat in the same folder, type `/council-build` and press Return.

From there Claude leads: it asks one thing at a time, and every question has ready answers to click. Now and then Claude asks you to allow a step, and your Mac may ask once to let Claude see a folder such as Downloads: both are normal, click Allow.

A Mac needs Apple's Command Line Tools, which bring `python3` and `git`. The Mac offers them in a window the first time they are needed, and Claude will say when to click Install.

Checked so far: the plugin passes Claude's own validator, installs with the two commands above, and its programs run on Python 3.9, the version a Mac ships. Not yet tried on an actual Mac: the desktop icon, opening the app window, and finding Claude's program in the Mac's own folders.

## Where things live in your project

- `tools/council/council.py`: the meeting program.
- `tools/council/chamber/`: the hub. It answers only on this computer, at http://127.0.0.1:8790.
- `outputs/council/`: your council's files. This holds the members, rules, brief, settings (`config.json`, including `owner_name`), memory, meetings, drafts and questions.

## Privacy

Your material stays in your project folder and goes only to the AI accounts you are signed in to. Background AI calls are not saved as chats. The hub is local-only.
