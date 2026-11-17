"""The Council hub: the owner's own app for their council. Meetings live around a round table, their questions, a one-to-one
talk with Claude, a file library the council can read, and the record of every meeting.

  python tools/council/chamber/server.py            serve on http://127.0.0.1:8790 and open the browser
  python tools/council/chamber/server.py --no-open  serve only
  python tools/council/chamber/server.py --port N   another port

It reads outputs/council/ as the chair writes it (the chair appends each turn to transcript.md as it lands),
so a running meeting appears turn by turn. It writes only on the owner's click:
  - an answer in FOR-OWNER.md, as the ticked line the chair files into memory/RULINGS.md at the next meeting;
  - the PAUSE file;
  - it can start tools/council/council.py, which then runs exactly as it does from the command line;
  - files he uploads, into outputs/council/files/ (a removed file moves to files/_removed/, never deleted);
  - his talks with Claude, in outputs/council/talks/ (each message is one headless, read-only claude -p call).
Bound to 127.0.0.1 only. Writes need the page's own header, so another website cannot trigger them.
"""
import argparse, json, mimetypes, os, re, shutil, subprocess, sys, threading, time, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote

HERE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get("COUNCIL_PROJECT") or HERE.parents[2])   # tools/council/chamber is three below
COUNCIL = PROJECT / "outputs" / "council"
SESSIONS, DRAFTS, MEMBERS = COUNCIL / "sessions", COUNCIL / "drafts", COUNCIL / "members"
CHAIR = HERE.parent / "council.py"          # the chair beside the chamber; COUNCIL_PROJECT passes through to it
FOR_FILE = COUNCIL / "FOR-OWNER.md"
LOCKF, PAUSE, CHAIRLOG = COUNCIL / ".lock", COUNCIL / "PAUSE", COUNCIL / "chair.log"
LAUNCH_LOG = COUNCIL / "chamber-launch.log"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
NEW_GROUP = 0x00000200 if os.name == "nt" else 0
CO_CHAIRS = ("CLAUDE", "CHALLENGER", "CODEX")
PROFILE_DIRS = [MEMBERS / "approved", MEMBERS / "final"]
launched = {"with_codex": False, "at": 0.0}
FILES_DIR, TALKS = COUNCIL / "files", COUNCIL / "talks"
MAX_UPLOAD = 100 * 1024 * 1024
STATIC = {"/memory-ui.js": "text/javascript; charset=utf-8", "/memory-ui.css": "text/css; charset=utf-8", "/theme-plain.css": "text/css; charset=utf-8", "/no-art.css": "text/css; charset=utf-8", "/manifest.webmanifest": "application/manifest+json", "/icon-192.png": "image/png",
          "/icon-512.png": "image/png", "/favicon.png": "image/png"}
TEXT_VIEW = {".txt", ".md", ".csv", ".tsv", ".json", ".log", ".yaml", ".yml"}       # shown as plain text
SAFE_VIEW = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
             ".webp": "image/webp", ".bmp": "image/bmp", ".pdf": "application/pdf"}  # shown as themselves
# Everything else is handed over as a download, never opened inside the hub (Codex review, 10 Oct: .shtml and
# .xht slipped past a list of dangerous types; an allowlist cannot be slipped past).
RECORD_RE = re.compile(r"^## (Turn \d+, .+|Owner(?:, on turn \d+)?, live during the meeting|Chair note)\s*$", re.M)
sys.path.insert(0, str(HERE.parent))
from memory_hub import MemoryHub
import connector_fetch
import council as chair                     # the chair's own helpers: finding Claude, running it, usage-limit check

TURN_RE = re.compile(r"^## Turn (\d+), (.+?)\s*$", re.M)
CALL_RE = re.compile(r"^\s*\**CALL:\**\s*(.+)$", re.M | re.I)
STATUS_RE = re.compile(r"STATUS:\s*\**\s*(CONTINUE|CONSENSUS|BLOCKED|VETO)", re.I)
FORALI_RE = re.compile(r"^\s*\**FOR (?:OWNER|USER):\**\s*(.+)$", re.M)
ITEM_RE = re.compile(r"^\s*\**ITEM:\**\s*(.+)$", re.M | re.I)
LEAD_RE = re.compile(r"^\s*\**LEAD:\**\s*(.+)$", re.M | re.I)
DRAFT_SAVED_RE = re.compile(r"\[draft saved: outputs/council/drafts/[^/\]]+/([^\]]+?) \((\d+) words\)")
QUESTION_RE = re.compile(r"^\s*-\s*\[( |x|filed)\]\s*(.+?)\s*$", re.I)
SOURCE_RE = re.compile(r"\*\(session ([\w-]+), turn (\d+), ([^)]+)\)\*")


def read(p):
    p = Path(p)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def pid_alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes                      # never os.kill on Windows: signal 0 there terminates the process
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259


def running():
    if not LOCKF.exists():
        return False
    try:
        return pid_alive(int(read(LOCKF).strip() or 0))
    except ValueError:
        return False


def match_speaker(text, names):
    """The chair's own rule: the addressee is named first, so match the head of the line before the rest."""
    t = text.upper().strip()
    head = t.split(",")[0].split(":")[0].split(" - ")[0].strip()
    common = {w for n in names for w in set(n.split()) if sum(w in m.split() for m in names) > 1}
    def words(n):                     # distinctive words only: a word shared by two seats picks neither
        return [w for w in n.split() if len(w) > 4 and w not in common]
    for scope in (head, t):
        for n in names:
            if n in scope:
                return n
        for n in names:
            if any(w in scope.split() or w in scope for w in words(n)):
                return n
    return None


def log_lines():
    return read(CHAIRLOG).splitlines()


def live_session_id():
    """The session the chair opened last and has not yet closed, while the chair is running."""
    if not running():
        return None
    for line in reversed(log_lines()[-400:]):
        m = re.search(r"Session (\S+) (opened|closed)", line)
        if m:
            return m.group(1) if m.group(2) == "opened" else None
    return None


def timings(sid):
    """Per-turn durations and the open/close times, from the chair's log."""
    out, opened, closed, inside = {}, None, None, False
    for line in log_lines():
        if f"Session {sid} opened" in line:
            inside, opened, out = True, line[:19], {}
            continue
        if not inside:
            continue
        m = re.search(r"Turn (\d+) \((.+?), \w+\) done in (\d+) s", line)
        if m:
            out[m.group(1)] = int(m.group(3))
        if f"Session {sid} closed" in line:
            closed = line[:19]
            inside = False
    return out, opened, closed


def stage(sid, turns, limit):
    """What the chair is doing right now: starting, floor, waiting (for the owner, attended meetings), minutes, filing."""
    if not running():
        return None
    if not sid:
        return "starting"
    tail = []
    for line in reversed(log_lines()[-300:]):
        tail.append(line)
        if f"Session {sid} opened" in line:
            break
    for line in tail:                                # newest first: the latest of these decides
        if "Paused by the owner" in line:                  # Pause holds a running meeting between turns (10 Oct)
            return "paused"
        if "Resumed by the owner" in line:
            break
        if "Waiting for the owner's answer" in line:
            return "waiting"
        if "Usage ran out" in line or "Trying again (" in line:
            return "usage"
        if "The owner answered" in line or "No answer from the owner" in line or re.search(r"Turn \d+ \(", line):
            break
    text = "\n".join(tail)
    if "Minutes written" in text:
        return "filing"
    # only a failed turn ends the floor (an own view that could not be written does not: the meeting goes on)
    if "closing the floor" in text or (limit and turns >= limit) or re.search(r"Turn \d+ \([^)]*\) failed", text):
        return "minutes"
    return "floor"


def predict_next(turns, opener, chairs, members, lead, limit, owner_pick=None, k=0, quick=False):
    """The chair's own next_floor_speaker rule, so the page can show who is preparing to speak. k is the number of
    opening views (turns 2 to k+1); during the opening round nobody is next, everyone is writing."""
    t = len(turns) + 1
    if not opener or t > limit:
        return None
    other = next((c for c in chairs if c != opener), None)
    if t == 1:
        return opener
    if not members:                      # pair mode: the two chairs alternate
        return opener if t % 2 else other
    if k and t <= k + 1:
        return None
    if t == limit - 2 and lead:
        return lead
    if t == limit - 1:
        return opener
    if t == limit:
        return other
    if not quick and t == k + 2 and lead:
        return lead
    if owner_pick:
        return owner_pick
    prev = turns[-1]
    spoken = {}
    for tr in turns:
        if tr["phase"] != "opening":     # the chair counts floor turns only
            spoken[tr["speaker"]] = spoken.get(tr["speaker"], 0) + 1
    unspoken = [m for m in members if not spoken.get(m) and m != prev["speaker"]]
    if unspoken and len(unspoken) >= (limit - 3) - t + 1:
        return unspoken[0]
    names = [opener, other] + members
    pick = match_speaker(prev["call"], names) if prev["call"] else None
    if not pick or pick == prev["speaker"]:
        pick = min((n for n in names if n != prev["speaker"]), key=lambda n: (spoken.get(n, 0), names.index(n)))
    return pick


def read_notes(sdir):
    out = []
    for line in read(sdir / "owner-notes.jsonl").splitlines():
        try:
            n = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(n.get("text", "")).strip():
            out.append(n)
    return out


def parse_session(sid):
    sdir = SESSIONS / sid
    t = read(sdir / "transcript.md")
    if not t:
        return None
    first = RECORD_RE.search(t)
    head = t[:first.start()] if first else t
    opener = re.search(r"Session number (\d+)\. (\S+) opens\. Turn limit (\d+)", head)
    floor = re.search(r"Full council floor: (.+?)\. Turn limit (\d+)", head)
    topic = re.search(r"^Topic set by the owner: (.+)$", head, re.M)
    follow = re.search(r"^Follow-up to meeting (\S+?)\.$", head, re.M)
    members = [n.strip() for n in floor.group(1).split(",")] if floor else []
    limit = int(floor.group(2)) if floor else (int(opener.group(3)) if opener else 0)
    heads = list(RECORD_RE.finditer(t))
    turns, speakers, inter = [], [], []
    for i, h in enumerate(heads):
        body = t[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(t)].strip()
        m = re.match(r"Turn (\d+), (.+)$", h.group(1))
        if not m:                                   # the owner's live notes and chair notes sit between turns
            inter.append(dict(kind="owner" if h.group(1).startswith("Owner") else "chair", after=len(turns), text=body))
            continue
        label = m.group(2)
        failed = label.endswith(": FAILED")
        label = label[:-8] if failed else label
        pm = re.search(r"\s*\[(\w+)\]$", label)
        phase = pm.group(1) if pm else "pair"
        label = label[:pm.start()] if pm else label
        is_lead = label.endswith(" (lead)")
        name = label[:-7] if is_lead else label
        speakers.append(name)
        st = STATUS_RE.findall(body)
        calls = CALL_RE.findall(body)
        turns.append(dict(n=int(m.group(1)), speaker=name, lead=is_lead, phase=phase, failed=failed, text=body,
                          status=(st[-1].upper() if st else ("FAILED" if failed else "CONTINUE")),
                          call=calls[-1].strip() if calls else "",
                          questions=[q.strip() for q in FORALI_RE.findall(body)],
                          drafts=[dict(path=d[0], words=int(d[1])) for d in DRAFT_SAVED_RE.findall(body)]))
    chairs = [c for c in CO_CHAIRS if c in speakers or (opener and opener.group(2) == c)]
    if len(chairs) < 2:                 # the second chair has not spoken yet
        guess = "CODEX" if launched["with_codex"] and time.time() - launched["at"] < 6 * 3600 else "CHALLENGER"
        if "CODEX" in chairs:
            guess = "CLAUDE"
        if guess not in chairs:
            chairs.append(guess)
    names = chairs + [n for n in members if n not in chairs] + [s for s in speakers if s not in chairs + members]
    for tr in turns:
        tr["call_target"] = match_speaker(tr["call"], [n for n in names if n != tr["speaker"]]) if tr["call"] else None
    item = ITEM_RE.findall(turns[0]["text"]) if turns else []
    lead = LEAD_RE.findall(turns[0]["text"]) if turns else []
    secs, opened, closed = timings(sid)
    for tr in turns:
        tr["seconds"] = secs.get(str(tr["n"]))
    sd = DRAFTS / sid
    drafts = sorted(p.relative_to(sd).as_posix() for p in sd.rglob("*") if p.is_file()) if sd.exists() else []
    minutes = read(sdir / "MINUTES.md")
    live = live_session_id() == sid
    # the owner's notes: those the chair has placed on the floor sit where it placed them; the rest wait or are saved
    placed = [x for x in inter if x["kind"] == "owner"]
    notes, owner_pick = [], None
    for i, n in enumerate(read_notes(sdir)):
        seen = i < len(placed)
        notes.append(dict(text=str(n["text"]).strip(), about_turn=n.get("about_turn"), ts=n.get("ts", ""),
                          after=placed[i]["after"] if seen else int(n.get("after_turn", len(turns))),
                          state="seen" if seen else ("waiting" if live else "saved")))
        if not seen and live:
            hm = re.match(r"^\s*([^,:\n]{2,40})[,:]", str(n["text"]))
            if hm and len(hm.group(1).split()) <= 3:
                owner_pick = match_speaker(hm.group(1), names) or owner_pick
    chair_notes = [dict(after=x["after"], text=x["text"]) for x in inter if x["kind"] == "chair"]
    for c in chair_notes:                       # a lost own view or a repair round moves the limit (10 Oct)
        lm = re.search(r"Turn limit is now (\d+)", c["text"])
        if lm:
            limit = int(lm.group(1))
    # The opening round: every seat writes its own view at once; until all are in, the page shows who is still writing
    mode = re.search(r"^Mode: (quick|full)\.$", head, re.M)
    planned = re.search(r"^Opening round: (\d+) seats", head, re.M)
    planned = int(planned.group(1)) if planned else 0
    opened = [tr for tr in turns if tr["phase"] == "opening"]
    lost = [n for n in chairs + members if any(f"{n.title()}'s opening view could not be written" in c["text"] for c in chair_notes)]
    in_round = bool(planned) and len(turns) >= 1 and len(opened) + len(lost) < planned and \
        all(tr["phase"] == "opening" for tr in turns[1:])
    writing = [n for n in chairs + members if n not in {tr["speaker"] for tr in opened} and n not in lost] if live and in_round else []
    k_open = planned if in_round else len(opened)
    statuses = [tr["status"] for tr in turns]
    rec = chair.load_json(sdir / "outcome.json", {})
    recorded = rec.get("outcome")
    if live:
        outcome = "In session"
    elif any(tr["failed"] for tr in turns):
        outcome = f"Stopped at turn {next(tr['n'] for tr in turns if tr['failed'])}"
    elif recorded:
        outcome = {"consensus": "Consensus", "no consensus": "Closed without consensus"}.get(recorded, "Stopped with an error")
    elif len(statuses) >= 2 and statuses[-1] == statuses[-2] == "CONSENSUS":
        outcome = "Consensus"
    elif minutes:
        outcome = "Closed without consensus"
    else:
        outcome = "Unfinished"
    lead_name = match_speaker(lead[0], members) if lead and members else None
    st = stage(sid, len(turns), limit) if live else None
    nxt = predict_next(turns, opener.group(2) if opener else None, chairs, members, lead_name, limit, owner_pick,
                       k_open, bool(mode and mode.group(1) == "quick")) \
        if live and st == "floor" and not any(tr["failed"] for tr in turns) else None
    return dict(id=sid, number=int(opener.group(1)) if opener else None, opener=opener.group(2) if opener else None,
                next=nxt, limit=limit, seats=names, chairs=chairs, members=members,
                mode=mode.group(1) if mode else ("full" if members else "pair"), opening=planned,
                writing=writing if st == "floor" else [],
                evidence=rec.get("evidence", ""), changed=rec.get("changed"), defects=rec.get("defects", []),
                repaired=bool(rec.get("repaired")), reclosed=bool(rec.get("reclosed")),
                item=item[0].strip() if item else "", topic=topic.group(1).strip() if topic else "",
                follow_up=follow.group(1) if follow else "",
                attend="The owner is attending in person." in head and not any("The owner has stepped away" in c["text"] for c in chair_notes),
                stepped_away=any("The owner has stepped away" in c["text"] for c in chair_notes),
                lead=lead_name, turns=turns, notes=notes, chair_notes=chair_notes, drafts=drafts, minutes=minutes,
                outcome=outcome, live=live, stage=st, opened=opened, closed=closed,
                mtime=max((sdir / "transcript.md").stat().st_mtime,
                          (sdir / "owner-notes.jsonl").stat().st_mtime if (sdir / "owner-notes.jsonl").exists() else 0))


def list_sessions():
    out, live = [], live_session_id()
    dirs = [d for d in SESSIONS.glob("*") if d.is_dir()] if SESSIONS.exists() else []
    for d in sorted(dirs, key=lambda d: ((d / "transcript.md").stat().st_mtime if (d / "transcript.md").exists() else 0), reverse=True):
        if not d.is_dir() or (d.name.endswith("-dry") and d.name != live):
            continue
        s = parse_session(d.name)
        if s:
            out.append(dict(id=s["id"], item=s["item"], topic=s["topic"], turns=len(s["turns"]), outcome=s["outcome"], live=s["live"],
                            mtime=s["mtime"], mode=s["mode"], evidence=s["evidence"], changed=s["changed"]))
    return out


def profile(name):
    """A member's file, found by its '# ' title, in the current or archived seats."""
    for d in PROFILE_DIRS:
        for f in sorted(d.glob("*.md")) if d.exists() else []:
            text = read(f)
            title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), "")
            if title.upper() == name:
                seat = re.search(r"\*\*Seat:\*\*\s*([^.\n]+)", text)
                conv = re.search(r"^## Convictions?[^\n]*\n+(.+)$", text, re.M)   # a line, or the first of a list
                if conv:
                    first = re.sub(r"^\d+\.\s*", "", conv.group(1).strip())
                    bold = re.match(r"\*\*(.+?)\*\*", first)
                    conv = re.match(r"(.*)", (bold.group(1) if bold else first).strip("* "))
                cut = [m.start() for m in re.finditer(r"^## ", text, re.M)]
                head = text[:cut[1]] if len(cut) > 1 else text[:4000]
                return dict(name=name, title=title, seat=seat.group(1).strip() if seat else "",
                            conviction=conv.group(1).strip() if conv else "",
                            status="provisional" if re.search(r"status:\**\s*provisional", text, re.I) else "full",
                            archived=False, file=f.relative_to(PROJECT).as_posix(), profile=head)
    return None


def roster():
    out = []
    d = MEMBERS / "approved"
    for f in sorted(d.glob("*.md")) if d.exists() else []:
        title = next((l[2:].strip() for l in read(f).splitlines() if l.startswith("# ")), f.stem)
        p = profile(title.upper())
        if p:
            out.append(p)
    return out


def questions():
    out = []
    for i, line in enumerate(read(FOR_FILE).splitlines()):
        m = QUESTION_RE.match(line)
        if not m:
            continue
        mark, rest = m.group(1).lower(), m.group(2)
        q, _, answer = rest.partition(" ANSWER:")
        src = SOURCE_RE.search(q)
        out.append(dict(key=q.strip(), text=SOURCE_RE.sub("", q).strip(), answer=answer.strip(),
                        state={" ": "open", "x": "answered", "filed": "filed"}[mark],
                        session=src.group(1) if src else None, turn=int(src.group(2)) if src else None,
                        speaker=src.group(3).strip() if src else None))
    return out


def rulings(limit=6):
    """The newest of the owner's rulings, for Home: what they have already decided."""
    out = []
    for line in read(COUNCIL / "memory" / "RULINGS.md").splitlines():
        m = re.match(r"^\s*-\s+(.+)$", line)
        if not m or m.group(1).lstrip().startswith("(duplicate"):    # the filing record's own duplicates stay off Home
            continue
        text = re.sub(r"\*\*", "", m.group(1)).strip()
        date = re.match(r"^(\d{4}-\d\d-\d\d)\s*", text)
        text = text[date.end():] if date else text
        text = re.sub(r"^(\[[0-9a-f]+\]\s*)?\((?:the owner, [^)]*|answered in [^)]*|relayed by [^)]*)\):\s*", "", text)   # source tags
        out.append(dict(date=date.group(1) if date else "", text=text))
    return out[-limit:][::-1]


def next_item():
    for path in (COUNCIL / "NEXT-AGENDA.md", COUNCIL / "AGENDA.md"):
        for line in read(path).splitlines():
            m = re.match(r"^\s*(?:\d+\.|-\s*\[ \])\s+(.+)$", line)
            if m and "~~" not in line[:6]:
                return re.sub(r"\*\*", "", m.group(1)).strip()
    return ""


def estimate():
    """What a meeting will use, for the Start window (10 Oct): calls by model from the settings, and the time from how
    long this laptop's past turns took. An estimate, and labelled as one."""
    cfg = dict(chair.DEFAULTS, **chair.load_json(COUNCIL / "config.json", {}))
    m = len(list((MEMBERS / "approved").glob("*.md"))) if (MEMBERS / "approved").exists() else 0
    secs = [int(x) for x in re.findall(r"\) done in (\d+) s", "\n".join(log_lines()[-800:])) if int(x) > 0]
    turn_s = round(sum(secs) / len(secs)) if secs else 60     # the average: a few slow turns decide how long it takes
    seats = m + 2
    waves = -(-seats // max(1, int(cfg.get("opening_parallel", 4))))      # own views run a few at a time
    out = dict(turn_s=turn_s, from_history=bool(secs))
    floor = max(int(cfg.get("council_turns", 14)), m + 4)
    for mode, body in (("quick", 4), ("full", floor)):
        calls = body + seats + 1                       # the turns, every seat's own view, the minutes
        # Opus: Claude's own view, its close, and either the frame or the minutes; a full meeting usually adds a floor turn
        opus = 3 + (1 if mode == "full" else 0)
        secs_total = (body + waves + 1) * turn_s
        out[mode] = dict(calls=calls, opus=opus, sonnet=calls - opus,
                         low=max(5, int(round(secs_total * 0.7 / 300)) * 5), high=max(10, int(round(secs_total * 1.5 / 300)) * 5))
    return out


OUTCOMES = COUNCIL / "memory" / "OUTCOMES.jsonl"


def list_outcomes():
    """The track record: what is due a check first, then what is still to come, then what the owner has marked."""
    today, rows = time.strftime("%Y-%m-%d"), chair.load_outcomes(OUTCOMES)
    for r in rows:
        r["due"] = not r.get("verdict") and str(r.get("look", "")) <= today
    open_ = sorted((r for r in rows if not r.get("verdict")), key=lambda r: str(r.get("look", "")))
    done = sorted((r for r in rows if r.get("verdict")), key=lambda r: str(r.get("marked", "")), reverse=True)
    return open_ + done


def mark_outcome(rid, verdict, note=""):
    verdict = (verdict or "").strip().lower()
    if verdict and verdict not in chair.VERDICTS:
        raise ValueError("Mark it confirmed, revised, reversed or inconclusive.")
    with chair.for_ali_lock(OUTCOMES):
        rows = chair.load_outcomes(OUTCOMES)
        row = next((r for r in rows if r.get("id") == rid), None)
        if not row:
            raise LookupError("That decision is no longer in the track record.")
        row.update(verdict=verdict, note=" ".join(str(note or "").split())[:600] if verdict else "",
                   marked=now() if verdict else "")
        chair.write_atomic(OUTCOMES, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def state():
    cfg = {}
    try:
        cfg = json.loads(read(COUNCIL / "config.json") or "{}")
    except json.JSONDecodeError:
        pass
    sessions = list_sessions()
    tail = log_lines()[-1:] or [""]
    usage_wait = running() and ("Usage ran out" in tail[0] or "Trying again (" in tail[0])
    return dict(ui_no_models=os.environ.get("COUNCIL_UI_NO_MODELS") == "1", running=running(), paused=PAUSE.exists(), live=live_session_id(), sessions=sessions, usage_wait=usage_wait,
                roster=roster(), questions=questions(), next_item=next_item(), files=list_files(), talks=list_talks(), rulings=rulings(),
                outcomes=list_outcomes(), estimate=estimate(),
                last_reset=(sorted(p.name for p in ARCHIVE.glob("reset-*")) or [""])[-1] if ARCHIVE.exists() else "",
                config={k: cfg.get(k) for k in ("owner_name", "claude_model", "second_chair_model", "member_model_claude",
                                                 "council_turns", "two_ai")},
                version=max([s["mtime"] for s in sessions] + [FOR_FILE.stat().st_mtime if FOR_FILE.exists() else 0,
                             PAUSE.exists() and 1 or 0]))


def answer(key, text):
    text = " ".join(text.split())
    if not text:
        raise ValueError("Write an answer first.")
    with chair.for_ali_lock(FOR_FILE):
        lines = read(FOR_FILE).splitlines()
        for i, line in enumerate(lines):
            m = QUESTION_RE.match(line)
            if m and m.group(1).lower() in (" ", "x") and m.group(2).partition(" ANSWER:")[0].strip() == key:
                lines[i] = f"- [x] {key} ANSWER: {text}"
                chair.write_atomic(FOR_FILE, "\n".join(lines) + "\n")
                return
    raise LookupError("That question is no longer open. The council may have filed it already.")


def answer_question(key, text):
    """The Questions page's answer. If the question came from the meeting running now, the meeting hears it too,
    so an attended meeting waiting for this answer carries on (Codex review, 10 Oct)."""
    answer(key, text)
    src = SOURCE_RE.search(key)
    if src and src.group(1) == live_session_id():
        q = SOURCE_RE.sub("", key).strip()
        add_note(src.group(1), f"Answer to {src.group(3).strip().title()}'s question ({q[:90]}{'...' if len(q) > 90 else ''}): "
                 + " ".join(text.split()))


def add_note(sid, text, about_turn=None, answer_key=None, step_away=False):
    """The owner speaks into a meeting. While it runs, the chair puts the note on the floor before the next turn;
    after it ends, the note is saved for a follow-up meeting. An answer to a listed question is also ticked
    in FOR-OWNER.md, so it reaches the council's memory as a ruling."""
    sid = re.sub(r"[^\w-]", "", sid or "")
    sdir = SESSIONS / sid
    if not sid or not (sdir / "transcript.md").exists():
        raise LookupError("That meeting was not found.")
    text = (text or "").strip()
    if not text:
        raise ValueError("Write or say something first.")
    s = parse_session(sid)
    rec = dict(ts=time.strftime("%Y-%m-%d %H:%M:%S"), after_turn=len(s["turns"]), text=text[:4000])
    if about_turn:
        rec["about_turn"] = int(about_turn)
    if step_away:                                   # the chair stops waiting for the owner for the rest of the meeting
        rec["step_away"] = True
    with open(sdir / "owner-notes.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if answer_key:
        try:
            answer(answer_key, re.sub(r"^Answer to .*?:\s*", "", text, flags=re.S) or text)
        except LookupError:
            pass


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def safe_name(name):
    name = re.sub(r"[^\w.\- ()]", "_", Path(str(name)).name).strip(" .")
    return name[:140] or "file"


def list_files():
    if not FILES_DIR.exists():
        return []
    files = [f for f in FILES_DIR.iterdir() if f.is_file()]
    return [dict(name=f.name, size=f.stat().st_size, mtime=f.stat().st_mtime, kind=f.suffix.lower().lstrip("."))
            for f in sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)]


def save_upload(name, data):
    if not data:
        raise ValueError("That file is empty.")
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    base = Path(safe_name(name))
    dest, n = FILES_DIR / base.name, 2
    while dest.exists():                          # never overwrite: keep both
        dest = FILES_DIR / f"{base.stem} ({n}){base.suffix}"
        n += 1
    dest.write_bytes(data)
    return dest.name


def remove_file(name):
    src = FILES_DIR / safe_name(name)
    if not src.is_file():
        raise LookupError("That file is no longer in the library.")
    gone = FILES_DIR / "_removed"
    gone.mkdir(exist_ok=True)
    src.rename(gone / f"{time.strftime('%Y%m%d-%H%M%S')} {src.name}")


TALK_INTRO = (
    "You are Claude, talking one-to-one with the owner in their Council Hub, before anything goes to their council. "
    "Help them think it through: listen, ask what you need to know, and give your honest view plainly. Keep replies "
    "short unless they ask for depth. You can read files in their project and search the web; you cannot edit "
    "anything or contact anyone. Useful context if it helps: outputs/council/BRIEF.md (their work) and "
    "outputs/council/memory/RULINGS.md (decisions they have made). When an idea is ready they can take this "
    "conversation to their council with one button. Write in plain English.\n\n")


def talk_path(tid):
    return TALKS / (re.sub(r"[^\w-]", "", tid or "") + ".json")   # no backslash inside an f-string: that needs Python 3.12


def load_talk(tid):
    talk = chair.load_json(talk_path(tid), None)
    if talk and talk.get("pending") and time.time() - talk.get("pending_at", 0) > 1200:
        talk.update(pending=False, error="Claude took too long to answer. Send it again.")   # a lost call never sticks
    return talk


def save_talk(talk):
    TALKS.mkdir(parents=True, exist_ok=True)
    chair.save_json(talk_path(talk["id"]), talk)


def list_talks():
    out = []
    for f in sorted(TALKS.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True) if TALKS.exists() else []:
        talk = load_talk(f.stem)
        if talk:
            out.append(dict(id=talk["id"], title=talk.get("title", ""), updated=talk.get("updated", ""),
                            pending=talk.get("pending", False), count=len(talk.get("messages", []))))
    return out


def talk_prompt(talk, msg, resume):
    files = [f"outputs/council/files/{n}" for n in msg.get("files") or [] if (FILES_DIR / n).is_file()]
    shared = ("He has shared these files with you. Read them before you answer:\n"
              + "\n".join(f"- {f}" for f in files) + "\n\n") if files else ""
    if resume:
        return shared + "The owner says:\n" + msg["text"]
    history = [m for m in talk["messages"] if m is not msg]
    past = ("Your conversation so far:\n" + "\n\n".join(
        f"{'Owner' if m['role'] == 'owner' else 'You'}: {m['text']}" for m in history) + "\n\n") if history else ""
    return TALK_INTRO + past + shared + "The owner says:\n" + msg["text"]


def ask_claude(prompt, cfg):
    """One read-only, unsaved Claude call (11 Oct: saved sessions were imported into the owner's Codex list as threads,
    so a talk now sends its whole conversation each time instead of resuming a saved session)."""
    exe = chair.claude_exe()
    if not exe:
        return "", None, "Claude Code was not found on this laptop."
    cmd = [exe, "-p", "--output-format", "json", "--strict-mcp-config", "--no-session-persistence",
           "--allowedTools", *cfg["claude_allowed_tools"],
           "--disallowedTools", "Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "Agent", "Task",
           "--model", cfg.get("hub_chat_model") or cfg.get("claude_model") or "opus"]
    code, out, err = chair.run(cmd, prompt, 900)
    data = {}
    for chunk in (out.strip(), (out.strip().splitlines() or [""])[-1]):
        try:
            data = json.loads(chunk)
            break
        except json.JSONDecodeError:
            continue
    reply = str(data.get("result") or "").strip()
    if data.get("is_error") or not reply:
        raw = reply or err or out or f"exit {code}"
        return "", None, ("Your Claude usage has run out. Send it again when it returns." if chair.is_usage_limit(raw)
                          else chair.sign_in_help() if chair.needs_sign_in(raw[:600])
                          else f"Claude did not answer: {raw.strip()[-300:]}")
    return reply, data.get("session_id"), ""


def talk_worker(tid):
    talk = load_talk(tid)
    reply, err = "", ""
    try:
        msg = next(m for m in reversed(talk["messages"]) if m["role"] == "owner")
        cfg = dict(chair.DEFAULTS, **chair.load_json(COUNCIL / "config.json", {}))
        reply, _, err = ask_claude(talk_prompt(talk, msg, False), cfg)    # the whole conversation, every time
    except Exception as e:                          # never leave the talk stuck on "thinking"
        reply, err = "", f"Something went wrong while asking Claude: {type(e).__name__}: {e}"
    talk = load_talk(tid)
    if reply:
        talk["messages"].append(dict(role="claude", text=reply, ts=now()))
    talk.update(pending=False, error=err, session_id=None, updated=now())
    save_talk(talk)


def talk_send(tid, text, files):
    text = (text or "").strip()
    if not text:
        raise ValueError("Write or say something first.")
    talk = load_talk(tid) if tid else None
    if not talk:
        tid = time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex()   # never two talks with one id
        talk = dict(id=tid, title=" ".join(text.split())[:80], created=now(), messages=[], session_id=None)
    if talk.get("pending"):
        raise RuntimeError("Claude is still answering your last message.")
    files = [safe_name(f) for f in files or [] if (FILES_DIR / safe_name(f)).is_file()]
    talk["messages"].append(dict(role="owner", text=text[:8000], ts=now(), files=files))
    talk.update(pending=True, pending_at=time.time(), error="", updated=now())
    save_talk(talk)
    threading.Thread(target=talk_worker, args=(tid,), daemon=True).start()
    return tid


def talk_retry(tid):
    """Send the owner's last message again after a failed answer, without adding it twice."""
    talk = load_talk(tid)
    if not talk:
        raise LookupError("That conversation was not found.")
    if talk.get("pending"):
        raise RuntimeError("Claude is still answering.")
    if not talk["messages"] or talk["messages"][-1]["role"] != "owner":
        raise ValueError("There is nothing waiting for an answer.")
    talk.update(pending=True, pending_at=time.time(), error="", updated=now())
    save_talk(talk)
    threading.Thread(target=talk_worker, args=(tid,), daemon=True).start()


def export_talk(tid):
    """A talk becomes a file in the library, so a meeting can take it up."""
    talk = load_talk(tid)
    if not talk:
        raise LookupError("That conversation was not found.")
    lines = [f"# Conversation with Claude: {talk.get('title', '')}", "", f"Held in the Council Hub, started {talk.get('created', '')}.", ""]
    for m in talk["messages"]:
        lines += [f"## {'Owner' if m['role'] == 'owner' else 'Claude'}", "", m["text"], ""]
        if m.get("files"):
            lines += ["Files shared: " + ", ".join(m["files"]), ""]
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    name = safe_name(f"talk-{talk['id']}.md")
    (FILES_DIR / name).write_text("\n".join(lines), encoding="utf-8")
    return name


ARCHIVE = COUNCIL / "archive"
RESET_PARTS = {     # what "Start fresh" can clear; each is moved into archive/reset-<time>/, never deleted
    "meetings": ["sessions", "drafts", "LATEST-MINUTES.md", "NEXT-AGENDA.md", "LOG.md", "state.json", "memory/DECISIONS-LOG.md"],
    "questions": ["FOR-OWNER.md"],
    "talks": ["talks"],
    "files": ["files"],
    "lessons": ["memory/member-lessons"],
    "decisions": ["memory/RULINGS.md"],
    "track": ["memory/OUTCOMES.jsonl"],
}


def start_fresh(parts):
    """The owner's blank slate (10 Oct): the chosen parts of the council's record move into one archive folder.
    The members, charter, brief and the owner's own agenda always stay."""
    if running():
        raise RuntimeError("A meeting is running. Start fresh once it has finished.")
    chosen = [k for k in RESET_PARTS if parts.get(k)]
    if not chosen:
        raise ValueError("Choose at least one thing to clear.")
    dest = ARCHIVE / f"reset-{time.strftime('%Y-%m-%d-%H%M%S')}"
    moved = []
    for key in chosen:
        for rel in RESET_PARTS[key]:
            src = COUNCIL / rel
            if src.exists():
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest / rel))
                moved.append(rel)
    if "questions" in chosen:
        FOR_FILE.write_text("", encoding="utf-8")       # an empty list: the chair adds new questions as they come
    (dest / "RESET.json").write_text(json.dumps({"at": now(), "parts": chosen, "moved": moved}, indent=2), encoding="utf-8")
    return dest.relative_to(PROJECT).as_posix(), moved


def undo_fresh():
    """Put the latest fresh start back, as long as nothing new has taken its place."""
    resets = sorted(ARCHIVE.glob("reset-*")) if ARCHIVE.exists() else []
    if not resets:
        raise LookupError("There is no fresh start to undo.")
    src_dir = resets[-1]
    info = chair.load_json(src_dir / "RESET.json", {})
    restored, kept = [], []
    for rel in info.get("moved", []):
        here, back = COUNCIL / rel, src_dir / rel
        if not back.exists():
            continue
        empty = here.exists() and ((here.is_dir() and not any(here.iterdir())) or (here.is_file() and not read(here).strip()))
        if here.exists() and not empty:
            kept.append(rel)                            # something new is here now; leave both, say so
            continue
        if here.exists():
            shutil.rmtree(here) if here.is_dir() else here.unlink()   # only an empty stand-in is replaced
        here.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(back), str(here))
        restored.append(rel)
    if not kept:
        (src_dir / "RESET.json").unlink(missing_ok=True)
        try:
            src_dir.rename(src_dir.with_name(src_dir.name.replace("reset-", "undone-")))
        except OSError:
            pass
    return restored, kept


def convene(with_codex=False, dry_run=False, topic="", attend=False, follow_up="", files=None, quick=False):
    if running():
        raise RuntimeError("A meeting is already running.")
    if PAUSE.exists():
        raise RuntimeError("The council is paused. Resume it first.")
    topic = " ".join(str(topic or "").split())[:2000]      # the owner's blank-slate topic, one line
    args = [sys.executable, str(CHAIR)] + (["--with-codex"] if with_codex else []) + (["--dry-run"] if dry_run else []) \
        + (["--quick"] if quick else []) \
        + (["--topic", topic] if topic else []) + (["--attend"] if attend else []) \
        + (["--follow-up", re.sub(r"[^\w-]", "", follow_up)] if follow_up else []) \
        + [a for f in files or [] if (FILES_DIR / safe_name(f)).is_file() for a in ("--files", safe_name(f))]
    log = open(LAUNCH_LOG, "a", encoding="utf-8")
    log.write(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}  chamber started: {' '.join(args[1:])}\n")
    log.flush()
    subprocess.Popen(args, cwd=str(PROJECT), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     creationflags=NO_WINDOW | NEW_GROUP)
    launched.update(with_codex=with_codex, at=time.time())


def safe_under(base, rel):
    p = (base / rel).resolve()
    if base.resolve() not in p.parents:
        raise PermissionError("Outside the council folder.")
    return p


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else (json.dumps(body, ensure_ascii=False) if not isinstance(body, str)
                                                     else body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")     # the browser never guesses a file's type
        self.send_header("X-Frame-Options", "DENY")                # no other page can frame the hub and disguise its buttons
        for k, v in ({"Content-Security-Policy": "frame-ancestors 'none'"} | (extra or {})).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def local_host(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self.local_host():
            return self.send(403, {"error": "Local only."})
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, read(HERE / "index.html"), "text/html; charset=utf-8")
            if u.path in STATIC and (HERE / u.path[1:]).is_file():
                return self.send(200, (HERE / u.path[1:]).read_bytes(), STATIC[u.path])
            if u.path.startswith("/files/"):
                f = safe_under(FILES_DIR, unquote(u.path[7:]))
                if not f.is_file():
                    return self.send(404, {"error": "Not in the library."})
                ext = f.suffix.lower()
                kind = ("text/plain; charset=utf-8" if ext in TEXT_VIEW else SAFE_VIEW.get(ext, "application/octet-stream"))
                extra = {"Content-Security-Policy": "sandbox; default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"}
                if kind == "application/octet-stream":
                    extra["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(f.name)}"
                return self.send(200, f.read_bytes(), kind, extra)
            if u.path == "/api/sources":
                return self.send(200, MEMORY_HUB.source_list())
            if u.path == "/api/sources/fetch":
                return self.send(200, FETCH.status())
            if u.path == "/api/source":
                return self.send(200, MEMORY_HUB.source_content(q.get('path', ''), q.get('line', 1)))
            if u.path == "/api/intake":
                return self.send(200, MEMORY_HUB.intake_state())
            if u.path == "/api/memory-health":
                return self.send(200, MEMORY_HUB.health())
            if u.path == "/api/talk":
                talk = load_talk(q.get("id", ""))
                return self.send(200 if talk else 404, talk or {"error": "That conversation was not found."})
            if u.path == "/api/state":
                return self.send(200, state())
            if u.path == "/api/session":
                s = parse_session(re.sub(r"[^\w-]", "", q.get("id", "")))
                return self.send(200 if s else 404, s or {"error": "No such meeting."})
            if u.path == "/api/member":
                p = profile(q.get("name", "").upper())
                return self.send(200 if p else 404, p or {"error": "No member file found."})
            if u.path == "/api/draft":
                sid = re.sub(r"[^\w-]", "", q.get("session", ""))
                p = safe_under(DRAFTS / sid, q.get("path", ""))
                if not p.is_file():                   # a turn's link to a version that was later replaced (10 Oct)
                    want = (re.escape(p.stem[:-1]) + r", replaced at turn \d+\)" if p.stem.endswith(")")
                            else re.escape(p.stem) + r" \(replaced at turn \d+\)") + re.escape(p.suffix) + "$"
                    p = next((c for c in sorted(p.parent.glob("*")) if re.match(want, c.name)), p) if p.parent.exists() else p
                replaced = "replaced at turn" in p.name
                return self.send(200 if p.is_file() else 404, {"path": q.get("path"), "text": read(p), "replaced": replaced})
            return self.send(404, {"error": "Not found."})
        except PermissionError as e:
            return self.send(403, {"error": str(e)})
        except Exception as e:                     # the page shows the message; the server keeps running
            return self.send(500, {"error": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        if not self.local_host() or self.headers.get("X-Chamber") != "1":
            return self.send(403, {"error": "Only the chamber page can do this."})
        try:
            path, size = urlparse(self.path).path, int(self.headers.get("Content-Length") or 0)
            if size < 0:
                raise ValueError('Invalid request size.')
            if os.environ.get('COUNCIL_UI_NO_MODELS') == '1' and path in ('/api/talk', '/api/talk/retry', '/api/convene'):
                raise RuntimeError('Provider calls are disabled in this isolated UI preview.')
            if path == '/api/sources/upload':
                if size > 8_000_000:
                    raise ValueError('File refused: larger than 8 MB (8,000,000 bytes).')
                result = MEMORY_HUB.add_source(unquote(self.headers.get('X-Filename', '')), self.rfile.read(size),
                                               unquote(self.headers.get('X-Source-Origin', 'File picker')))
                return self.send(200, result)
            if path not in ('/api/upload', '/api/intake/import') and size > 64_000:
                raise ValueError('That request is too large.')
            if path == '/api/intake/import' and size > 2_000_000:
                raise ValueError('That is too much to paste at once. Add it in parts of under 2 MB.')
            if path == "/api/upload":                 # the raw file is the body; its name rides in a header
                if size > MAX_UPLOAD:
                    raise ValueError("That file is over 100 MB.")
                name = save_upload(unquote(self.headers.get("X-Filename") or "file"), self.rfile.read(size))
                return self.send(200, {"ok": True, "name": name})
            body = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(body, dict):
                raise ValueError('Expected an object.')
            memory_routes = {
                '/api/sources/remove': lambda: MEMORY_HUB.remove_source(body.get('path', '')),
                '/api/sources/undo': lambda: MEMORY_HUB.undo_source(body.get('token')),
                '/api/sources/fetch': lambda: FETCH.start(body.get('app', ''), body.get('request', '')),
                '/api/intake/start': lambda: MEMORY_HUB.start_sitting(),
                '/api/intake/finish': lambda: MEMORY_HUB.finish_sitting(body.get('sitting')),
                '/api/intake/answer': lambda: MEMORY_HUB.answer(body),
                '/api/intake/import': lambda: MEMORY_HUB.import_claims(body.get('text', '')),
                '/api/memory-settings': lambda: MEMORY_HUB.update_settings(body),
                '/api/memory-settings/undo': lambda: MEMORY_HUB.undo_settings(body.get('token')),
            }
            if path in memory_routes:
                return self.send(200, memory_routes[path]())
            if path == "/api/talk":
                return self.send(200, {"ok": True, "id": talk_send(body.get("id"), body.get("text"), body.get("files"))})
            if path == "/api/reset":
                where, moved = start_fresh(body)
                return self.send(200, {"ok": True, "archive": where, "moved": moved})
            if path == "/api/reset/undo":
                restored, kept = undo_fresh()
                return self.send(200, {"ok": True, "restored": restored, "kept": kept})
            if path == "/api/talk/retry":
                talk_retry(body.get("id"))
                return self.send(200, {"ok": True})
            if path == "/api/talk/export":
                return self.send(200, {"ok": True, "name": export_talk(body.get("id"))})
            if path == "/api/answer":
                answer_question(body.get("key", ""), body.get("answer", ""))
            elif path == "/api/convene":
                convene(bool(body.get("with_codex")), bool(body.get("dry_run")), body.get("topic", ""),
                        bool(body.get("attend")), body.get("follow_up", ""), body.get("files") or [], bool(body.get("quick")))
            elif path == "/api/outcome":
                mark_outcome(str(body.get("id", "")), body.get("verdict", ""), body.get("note", ""))
            elif path == "/api/file/remove":
                remove_file(body.get("name", ""))
            elif path == "/api/note":
                add_note(body.get("session", ""), body.get("text", ""), body.get("about_turn"), body.get("answer_key"),
                         bool(body.get("step_away")))
            elif path == "/api/pause":
                PAUSE.write_text("Paused from the council chamber.\n", encoding="utf-8") if body.get("paused") \
                    else PAUSE.unlink(missing_ok=True)
            else:
                return self.send(404, {"error": "Not found."})
            return self.send(200, {"ok": True})
        except (ValueError, LookupError, RuntimeError) as e:
            return self.send(409, {"error": str(e)})
        except Exception as e:
            return self.send(500, {"error": f"{type(e).__name__}: {e}"})


MEMORY_HUB = MemoryHub(COUNCIL, running)


def connector_call(prompt, allowed, cheap):
    """One background Claude call that may use the owner's connectors, but only the tools in `allowed`.
    No saved session, no file tools, no shell. Raises with a plain message on failure."""
    exe = chair.claude_exe()
    if not exe:
        raise RuntimeError("Claude Code was not found on this computer.")
    cfg = chair.load_json(chair.CONFIG, {})
    model = "haiku" if cheap else (cfg.get("fetch_model") or cfg.get("member_model_claude") or "sonnet")
    cmd = [exe, "-p", "--output-format", "text", "--no-session-persistence", "--model", model,
           "--allowedTools", *allowed, "--disallowedTools", *connector_fetch.NO_CHANGE_TOOLS]
    try:
        p = subprocess.run(cmd, cwd=str(PROJECT), input=prompt, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=180 if cheap else 900, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude took too long. Try asking for fewer items.")
    text = (p.stdout or "").strip()
    head = text.lower()[:300]
    if not text or p.returncode != 0 or (len(text) < 600 and (any(s in head for s in chair.STOP_PHRASES) or chair.is_usage_limit(head))):
        if chair.is_usage_limit(text or p.stderr or ""):
            raise RuntimeError("Your Claude usage has run out for now. Try again when it resets.")
        raise RuntimeError("Claude could not finish: " + ((text or p.stderr or "no reply").strip()[-300:]))
    return text


def connector_save(title, origin, text):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", title).strip()[:100] or "Brought in"
    return MEMORY_HUB.add_source(name + ".md", text.encode("utf-8"), origin="Connected app: " + origin)


FETCH = connector_fetch.FetchJob(connector_call, connector_save, MEMORY_HUB.writable)


def main():
    chair.remember_claude()
    ap = argparse.ArgumentParser(description="Serve the council chamber.")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Council chamber at {url}  (Ctrl+C to close)", flush=True)
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
