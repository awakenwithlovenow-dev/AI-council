"""Council memory tool: measure it, index it, pull from it.

The council's memory has two layers. CORE is loaded into every seat's prompt every turn (charter, brief, rulings,
precedents, decisions, minutes, the seat's own file) and must stay inside a budget. ARCHIVE (dossiers, inputs,
old reports) is never loaded whole: pull() hands the chair the few sections that match a meeting's topic, each
labelled with its file and line so every seat sees the same extract and can re-check it.

  python memory_tool.py health  [--council DIR]
  python memory_tool.py pull "topic words" [--budget 12000] [--council DIR]
"""
import argparse, hashlib, math, re, sys
from pathlib import Path

# What shared_pack() really puts in every prompt (PRECEDENTS.md is NOT inserted; DECISIONS-LOG only its last 6000 chars)
CORE_FILES = ["CHARTER.md", "BRIEF.md", "AGENDA.md", "LATEST-MINUTES.md", "memory/RULINGS.md", "memory/DECISIONS-LOG.md"]
CAPS = {"memory/DECISIONS-LOG.md": 6000}
ARCHIVE_DIRS = ["members/dossiers", "inputs"]
STOP = set("the a an and or of to in on for with is are was were be by at as it its this that from not but have has "
           "had will would can could should we you i he she they them our your his her their there which what when "
           "who how all any one two into than then so if no yes do does did".split())
CHUNK = 1400
MAX_FILE_BYTES = 8_000_000     # a larger file is skipped, not loaded
CORE_BUDGET_CHARS = 90000      # per seat per turn; measured 58k in Oct 2026, the model window is several times this


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8-sig", errors="replace")   # -sig: a Notepad BOM is not text
    except OSError:
        return ""


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def words(t):
    return [stem(w) for w in re.findall(r"[a-z0-9$%']{3,}", t.lower()) if w not in STOP]


def load_aliases(council):
    """Optional owner-written synonym groups in memory/aliases.json: {"induction": ["programme", "course"]}.
    A query word is also matched by its listed aliases. Empty when the file is absent."""
    import json
    try:
        raw = json.loads(read(Path(council) / "memory" / "aliases.json") or "{}")
    except ValueError:
        return {}
    out = {}
    for k, vs in raw.items():
        group = {stem(w) for w in [k, *vs]}
        for w in group:
            out.setdefault(w, set()).update(group - {w})
    return out


def chunks(path):
    """Split a file into sections on headings, then into pieces of about CHUNK characters, keeping line numbers."""
    out, buf, start, size = [], [], 1, 0
    lines = []
    for raw in read(path).splitlines():          # a physical line longer than CHUNK is split, so it can be selected
        while len(raw) > CHUNK:
            cut = raw.rfind(" ", 0, CHUNK)
            cut = cut if cut > CHUNK // 2 else CHUNK
            lines.append(raw[:cut])
            raw = raw[cut:].lstrip()
        lines.append(raw)
    stack, ctx_at = [], {}
    for i, line in enumerate(lines, 1):
        heading = line.startswith("#")
        if heading:
            lvl = len(line) - len(line.lstrip("#"))
            stack = [h for h in stack if h[0] < lvl] + [(lvl, line.strip())]
        if buf and (size >= CHUNK or (heading and size > 300)):
            out.append((start, "\n".join(buf), ctx_at[start]))
            buf, start, size = [], i, 0
        if not buf:       # ancestors of this chunk: headings above it that are not its own first line
            ctx_at[i] = [h[1] for h in (stack[:-1] if heading else stack)]
        buf.append(line)
        size += len(line) + 1
    if buf:
        out.append((start, "\n".join(buf), ctx_at[start]))
    return out


def build_index(council):
    idx = []
    for d in ARCHIVE_DIRS:
        for p in sorted((council / d).glob("*.md")):
            try:                                  # stay inside the council folder; skip links that leave it and huge files
                if not p.resolve().is_relative_to(council.resolve()) or p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            for ln, text, ctx in chunks(p):
                ws = words(" ".join(ctx) + " " + text)
                if ws:
                    idx.append(dict(file=p.relative_to(council).as_posix(), line=ln, text=text, ctx=ctx, words=ws))
    return idx


def norm(t):
    return re.sub(r"\s+", " ", t).strip().lower()


def open_items(agenda):
    """The open part of an agenda, for searching: drops done items ("- [x]" with their indented lines) and
    struck-through text, which would otherwise pull sections about finished work."""
    out, skip_at = [], None
    for line in agenda.splitlines():
        indent = len(line) - len(line.lstrip())
        if skip_at is not None:
            if not line.strip() or indent > skip_at:
                continue
            skip_at = None
        if re.match(r"\s*[-*]\s*\[[xX]\]", line):
            skip_at = indent
            continue
        out.append(re.sub(r"~~.*?~~", "", line))
    return "\n".join(out)


SEGMENT_OVER = 25  # a query with more distinct words than this (a whole agenda, a plan file) is searched item by item


def segments(query):
    """A short query is one search. A long one (an agenda, a plan) is split into its items: lines and sentences,
    joined until each holds at least 6 distinct words and cut so none holds more than SEGMENT_OVER. Without this a
    long query matches nothing, because no single section covers 30% of a whole agenda's words."""
    if len(set(words(query))) <= SEGMENT_OVER:
        return [query]
    pieces = []
    for p in re.split(r"\n+|(?<=[.!?;])\s+", query):
        ws = p.split()
        while len(set(words(" ".join(ws)))) > SEGMENT_OVER:
            pieces.append(" ".join(ws[:30]))
            ws = ws[30:]
        if ws:
            pieces.append(" ".join(ws))
    out, buf = [], []
    for p in pieces:
        if not words(p):
            continue
        buf.append(p)
        if len(set(words(" ".join(buf)))) >= 6:
            out.append(" ".join(buf))
            buf = []
    if buf:
        if out and len(set(words(out[-1] + " " + " ".join(buf)))) <= SEGMENT_OVER:
            out[-1] += " " + " ".join(buf)
        else:
            out.append(" ".join(buf))
    return out or [query]


def link_keys(idx):
    """Section headings a body can point to, such as "segment R10". Only real headings with two content words or a
    number count, matched as a whole phrase, so a generic heading ("Notes", "Pricing") is not dragged in."""
    keys = {}
    for c in idx:
        first = c["text"].splitlines()[0].strip() if c["text"].strip() else ""
        if not first.startswith("#"):
            continue
        h = re.sub(r"^\d+[.)]\s*", "", norm(first.lstrip("# ")))     # "7. voice" is a list number plus "voice"
        content = [w for w in re.findall(r"[a-z0-9$%']+", h) if w not in STOP and w not in ("been", "being", "about")]
        if len(h) >= 4 and (len(content) >= 2 or any(ch.isdigit() for ch in h)):
            keys.setdefault(h, c)
    return keys


def pull(council, query, budget=12000, exclude_text=""):
    """Top sections for the query, within a character budget measured on the final serialized text.
    TF-IDF over chunks. Exact duplicates are removed by full normalised content, with the other file kept as an
    alias in the label. A section is skipped only if its whole normalised text already sits in exclude_text,
    which must be the text actually delivered to the seats. Returns (text, receipt)."""
    council = Path(council)
    idx = build_index(council)
    receipt = dict(query_terms=len(set(words(query))), candidates=0, selected=[], skipped_budget=0)
    if not idx or not query.strip():
        return "", receipt
    df = {}
    for c in idx:
        for w in set(c["words"]):
            df[w] = df.get(w, 0) + 1
    n = len(idx)
    aliases = load_aliases(council)
    qx_all = set(words(query))
    for w in list(qx_all):
        qx_all |= aliases.get(w, set())
    segs = segments(query)
    receipt["segments"] = len(segs)
    best = {}                                     # chunk position -> (score, segment number)
    for si, seg in enumerate(segs):
        q = set(words(seg))
        qx = set(q)
        for w in q:
            qx |= aliases.get(w, set())
        need = 1 if len(q) <= 1 else 2
        for ci, c in enumerate(idx):
            tf = c.get("tf")
            if tf is None:
                tf = c["tf"] = {}
                for w in c["words"]:
                    tf[w] = tf.get(w, 0) + 1
            # coverage counts distinct query ideas: a query word or any of its aliases
            ideas = sum(1 for w in q if w in tf or any(a in tf for a in aliases.get(w, ())))
            if ideas < need or ideas / max(len(q), 1) < 0.3:
                continue                          # one shared word is not relevance: abstain
            s = sum((1 + math.log(tf[w])) * math.log(1 + n / df.get(w, 1)) for w in qx if w in tf)
            s /= math.sqrt(len(c["words"]) + 50)
            low = c["text"].lower() + " " + " ".join(c["ctx"]).lower()
            if re.search(r"superseded|withdrawn|obsolete|no longer (current|valid)|\[ai-draft\]|unapproved", low):
                s *= 0.5                          # history or unapproved: shown, but ranked below current
            if re.search(r"supersedes|confirmed owner|owner ruling|current as of", low):
                s *= 1.3
            if s > 0 and s > best.get(ci, (0, 0))[0]:
                best[ci] = (s, si)
    # one search: best first. Several items: take turns, so every agenda item gets its best sections before any
    # item gets its second
    per = {}
    for ci, (s, si) in best.items():
        per.setdefault(si, []).append((s, idx[ci]))
    for v in per.values():
        v.sort(key=lambda x: -x[0])
    scored = []
    for rank in range(max((len(v) for v in per.values()), default=0)):
        scored += sorted((v[rank] for v in per.values() if rank < len(v)), key=lambda x: -x[0])
    receipt["candidates"] = len(scored)
    delivered = norm(exclude_text)
    out, used, groups = [], 0, {}
    for s, c in scored:
        key = norm(c["text"])
        if key in groups:
            groups[key]["aliases"].append(f"{c['file']}:{c['line']}")
            continue
        if delivered and key in delivered:
            continue
        groups[key] = dict(c=c, score=s, aliases=[])
    heads = {h: (hc, norm(hc["text"]), re.compile(r"(?<![a-z0-9])" + re.escape(h) + r"(?![a-z0-9])"))
             for h, hc in link_keys(idx).items()}
    for g in list(groups.values()):               # follow a reference such as "segment R10" to the section it names
        body = norm(g["c"]["text"])
        for h, (hc, k, pat) in heads.items():
            if k not in groups and h in body and pat.search(body) and not (delivered and k in delivered) and hc is not g["c"]:
                groups[k] = dict(c=hc, score=g["score"] * 0.5, aliases=[], via=g["c"]["file"] + ":" + str(g["c"]["line"]))
    for g in groups.values():
        c = g["c"]
        ctx = ("\n| (under: " + " > ".join(c["ctx"]) + ")") if c["ctx"] else ""
        alias = f" (same text also in {', '.join(g['aliases'])})" if g["aliases"] else ""
        via = (" (linked from " + g["via"] + ")") if g.get("via") else ""
        block = f"--- {c['file']} line {c['line']}{alias}{via} ---{ctx}\n" + "\n".join("| " + l for l in c["text"].splitlines())
        add = len(block) + (2 if out else 0)
        if used + add > budget:
            room = budget - used - (2 if out else 0) - len(block.split("\n", 1)[0]) - 110
            if room >= 200:
                # the section is larger than what is left: keep the stretch that holds the most query words,
                # marked as an excerpt, instead of dropping the section altogether
                text = c["text"]
                qs = qx_all
                best, best_at, step = -1, 0, max(40, room // 8)
                for at in range(0, max(1, len(text) - room + 1), step):
                    win = set(words(text[at:at + room]))
                    sc = sum(1 for w in qs if w in win)
                    if sc > best:
                        best, best_at = sc, at
                piece = text[best_at:best_at + room]
                if best > 0:
                    block = (block.split("\n", 1)[0] + f" [excerpt, chars {best_at}-{best_at + len(piece)} of {len(text)}]"
                             + "\n" + "\n".join("| " + l for l in piece.splitlines()))
                    add = len(block) + (2 if out else 0)
            if used + add > budget:
                receipt["skipped_budget"] += 1
                continue
        out.append(block)
        used += add
        receipt["selected"].append(dict(file=c["file"], line=c["line"], score=round(g["score"], 3),
                                        sha=hashlib.sha256(norm(c["text"]).encode()).hexdigest()[:12]))
    return "\n\n".join(out), receipt


def ledger_block(council, query, budget=5000):
    """The claims ledger: memory/claims.jsonl, one JSON object per line with
    id, entity, claim, scope, status (current|proposed|superseded|withdrawn|historical|unresolved),
    authority (owner|council|ai-draft|record), effective (date), supersedes (id or ""), source (file:line), verified.
    Claims matching the query are shown with their status, authority and source. A match always brings the claim it
    supersedes and the claim that superseded it, so a seat sees the replacement chain, not one line alone.
    Returns (text, ids)."""
    import json
    rows = []
    for line in read(Path(council) / "memory" / "claims.jsonl").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("id") and r.get("claim"):
            rows.append(r)
    if not rows or not query.strip():
        return "", []
    aliases = load_aliases(council)
    qsets = []
    for seg in segments(query):
        q = set(words(seg))
        for w in list(q):
            q |= aliases.get(w, set())
        qsets.append(q)
    by_id = {r["id"]: r for r in rows}
    replaced_by = {}
    for r in rows:
        if r.get("supersedes"):
            replaced_by.setdefault(r["supersedes"], []).append(r)
    hits = []
    for r in rows:
        ws = set(words(" ".join(str(r.get(k, "")) for k in ("entity", "claim", "scope"))))
        if any(len(ws & q) >= (1 if len(q) <= 1 else 2) for q in qsets):
            hits.append(r)
    chosen, seen = [], set()
    def add(r):
        if r["id"] not in seen:
            seen.add(r["id"]); chosen.append(r)
    for r in hits:              # the whole replacement chain, both ways, however many steps it has
        todo = [r]
        while todo:
            x = todo.pop()
            if x["id"] in seen:
                continue
            add(x)
            if x.get("supersedes") in by_id:
                todo.append(by_id[x["supersedes"]])
            todo += replaced_by.get(x["id"], [])
    order = {"current": 0, "proposed": 1, "unresolved": 2, "historical": 3, "superseded": 4, "withdrawn": 5}
    chosen.sort(key=lambda r: order.get(r.get("status"), 9))

    def flat(v):                # one line per claim, quoted: text inside a claim can never start a new prompt line
        return re.sub(r"[\x00-\x1f\x7f  ]+", " ", str(v)).strip()
    out, used = [], 0
    for r in chosen:
        line = (f"| [{flat(r['id'])}] ({flat(r.get('status', '?'))}, {flat(r.get('authority', '?'))}, "
                f"effective {flat(r.get('effective', '?'))}{', verified by the owner' if r.get('verified') is True else ', not verified'}) "
                f"{flat(r.get('entity', ''))}: {flat(r['claim'])}"
                f"{' | scope: ' + flat(r['scope']) if r.get('scope') else ''}"
                f"{' | supersedes ' + flat(r['supersedes']) if r.get('supersedes') else ''}"
                f" | source: {flat(r.get('source', '?'))}")
        if used + len(line) + 1 > budget:
            break
        out.append(line)
        used += len(line) + 1
    return "\n".join(out), [r["id"] for r in chosen[:len(out)]]


def health(council):
    council = Path(council)
    print(f"Council memory health: {council}\n")
    core = 0
    print("CORE (in every seat's prompt, every turn)")
    for f in CORE_FILES:
        n = min(len(read(council / f)), CAPS.get(f, 10**9))
        core += n
        print(f"  {f:28} {n:>8} chars")
    seats = sorted((council / "members" / "approved").glob("*.md"))
    sizes = [len(read(p)) for p in seats]
    big = max(sizes) if sizes else 0
    print(f"  seat file (largest of {len(seats)})   {big:>8} chars")
    total = core + big
    print(f"  shared pack + largest seat file {total:>8} chars  ({total * 100 // CORE_BUDGET_CHARS}% of the {CORE_BUDGET_CHARS} reporting figure; not an enforced limit)")
    lessons = sum(len(read(p)) for p in (council / "memory" / "member-lessons").glob("*.md"))
    print(f"  member lessons (all seats)   {lessons:>8} chars")
    print("\nARCHIVE (never loaded whole; pulled by topic)")
    tot = 0
    for d in ARCHIVE_DIRS:
        for p in sorted((council / d).glob("*.md")):
            n = len(read(p))
            tot += n
            print(f"  {p.relative_to(council).as_posix():60} {n:>8}")
    print(f"  archive total                {tot:>8} chars in {len(build_index(council))} sections")
    print(f"\nArchive is {tot // max(core, 1)}x the core. Headroom in the core budget: {CORE_BUDGET_CHARS - total} chars.")
    dups = {}
    for c in build_index(council):
        dups.setdefault(norm(c["text"]), []).append(c["file"])
    d = [(k, v) for k, v in dups.items() if len(set(v)) > 1]
    print(f"Duplicated sections across archive files: {len(d)} (the same text held in more than one file)")


def ledger_health(council):
    """Health of the claims ledger and intake: what needs the owner, what has gone stale, what conflicts."""
    import datetime, json
    council = Path(council)
    rows = []
    for line in read(council / "memory" / "claims.jsonl").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("id"):
            rows.append(r)
    print("\nCLAIMS LEDGER")
    if not rows:
        print("  none yet (memory/claims.jsonl). Add sources, run intake_tool.py extract-prompt.")
        return
    by = {}
    for r in rows:
        by[r.get("status", "?")] = by.get(r.get("status", "?"), 0) + 1
    print("  rows:", len(rows), "| by status:", ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    cur = [r for r in rows if r.get("status") == "current"]
    print(f"  current and verified by the owner: {sum(1 for r in cur if r.get('verified'))} of {len(cur)}")
    print(f"  unresolved: {by.get('unresolved', 0)} | ai-draft rows: {sum(1 for r in rows if r.get('authority') == 'ai-draft')}")
    groups = {}
    for r in cur:
        groups.setdefault(r.get("entity", "").strip().lower(), set()).add(r["claim"])
    conf = [k for k, v in groups.items() if len(v) > 1]
    print(f"  entities with more than one current claim (check for conflict): {len(conf)}")
    for k in conf[:8]:
        print("     -", k)
    ids = {r["id"] for r in rows}
    broken = [r["id"] for r in rows if r.get("supersedes") and r["supersedes"] not in ids]
    print(f"  supersedes links pointing nowhere: {len(broken)}")
    today = datetime.date.today()
    stale = 0
    for r in cur:
        m = re.match(r"(\d{4})-(\d{2})", str(r.get("effective", "")))
        if m and not r.get("verified"):
            try:
                if (today - datetime.date(int(m.group(1)), int(m.group(2)), 1)).days > 90:
                    stale += 1
            except ValueError:
                pass
    print(f"  current, unverified and older than 90 days (confirm or retire): {stale}")
    ans = read(council / "memory" / "intake-answers.jsonl").count("\n")
    print(f"  intake answers recorded: {ans}")
    src = read(council / "memory" / "sources.jsonl").count("\n")
    print(f"  sources recorded: {src}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["health", "pull"])
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--council", default=str(Path(__file__).resolve().parents[2] / "outputs" / "council"))
    ap.add_argument("--budget", type=int, default=12000)
    ap.add_argument("--write", action="store_true", help="also save the report to HEALTH.md in the council folder")
    a = ap.parse_args()
    if a.cmd == "health":
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            health(a.council)
            ledger_health(a.council)
        print(buf.getvalue())
        if a.write:
            (Path(a.council) / "HEALTH.md").write_text("# Council memory health\n\n```\n" + buf.getvalue() + "```\n", encoding="utf-8")
            print("saved HEALTH.md")
    else:
        print(pull(a.council, a.query, a.budget)[0])
