"""Council intake: bring sources in, then correct what the council believes by tapping Yes / No / Not sure.

Local files only. Nothing here calls a model.

  python intake_tool.py sources add PATH [PATH ...]   copy files or a folder into outputs/council/inputs/ (md, txt, html, docx)
  python intake_tool.py sources list                  what is held, with hashes and where it came from
  python intake_tool.py questions [--max 15]          the next questions about claims in memory/claims.jsonl
  python intake_tool.py answer ID yes|no|unsure|outdated [--note "..."]
  python intake_tool.py edit ID "corrected claim text"
  python intake_tool.py extract-prompt                prints the prompt that turns sources into ledger rows (run it with
                                                      your own Claude; save its JSON lines to a file)
  python intake_tool.py import-claims FILE            adds those rows to memory/claims.jsonl safely (new ids only, unverified)

Every answer is appended to memory/intake-answers.jsonl with the exact question, answer, date and target claim.
"Not sure" keeps a claim unverified; it never becomes a ruling. "No" and "outdated" never delete a row: the claim
is marked withdrawn or superseded and stays visible.
"""
import argparse, datetime, hashlib, html, json, re, shutil, sys, zipfile
import contextlib, os, time, uuid
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[2] / "outputs" / "council"
TEXT_EXT = {".md", ".txt", ".html", ".htm", ".docx"}
MAX_BYTES = 8_000_000


def council_dir(a):
    return Path(a.council) if a.council else DEFAULT


def sha(b):
    return hashlib.sha256(b).hexdigest()


def to_markdown(p):
    """Readable text from md, txt, html or docx. Anything else is refused by the caller."""
    ext = p.suffix.lower()
    if ext == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        text = re.sub(r"</w:p>", "\n", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", text))
    raw = p.read_text(encoding="utf-8-sig", errors="replace")
    if ext in (".html", ".htm"):
        raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", raw)
        raw = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|br)>|<br\s*/?>", "\n", raw)
        return html.unescape(re.sub(r"<[^>]+>", "", raw))
    return raw


def sources_add(a):
    c = council_dir(a)
    dest = c / "inputs"
    dest.mkdir(parents=True, exist_ok=True)
    manifest_p = c / "memory" / "sources.jsonl"
    manifest_p.parent.mkdir(parents=True, exist_ok=True)
    known = {}
    if manifest_p.exists():
        for line in manifest_p.read_text(encoding="utf-8-sig").splitlines():
            try:
                r = json.loads(line)
                known[r["sha256"]] = r
            except (ValueError, KeyError):
                pass
    files = []
    for s in a.paths:
        p = Path(s)
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*")) if f.is_file()]
        elif p.is_file():
            files.append(p)
        else:
            print(f"missing: {s}")
    added = skipped = refused = 0
    for f in files:
        if f.suffix.lower() not in TEXT_EXT or f.stat().st_size > MAX_BYTES:
            print(f"refused (type or size): {f}")
            refused += 1
            continue
        try:
            text = to_markdown(f)
        except (OSError, zipfile.BadZipFile) as e:
            print(f"could not read {f}: {e}")
            refused += 1
            continue
        h = sha(text.encode("utf-8"))
        if h in known:
            print(f"duplicate of {known[h]['stored']}: {f.name}")
            skipped += 1
            continue
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", f.stem).strip("-") or "source"
        out = dest / f"{name}.md"
        n = 2
        while out.exists():
            out = dest / f"{name}-{n}.md"
            n += 1
        out.write_text(text, encoding="utf-8")
        rec = dict(sha256=h, stored=out.relative_to(c).as_posix(), original=str(f),
                   added=datetime.date.today().isoformat(), chars=len(text))
        with open(manifest_p, "a", encoding="utf-8") as m:
            m.write(json.dumps(rec) + "\n")
        known[h] = rec
        added += 1
        print(f"added {out.relative_to(c).as_posix()} ({len(text)} chars)")
    print(f"\n{added} added, {skipped} duplicate, {refused} refused. Next: python intake_tool.py extract-prompt")


def sources_list(a):
    p = council_dir(a) / "memory" / "sources.jsonl"
    if not p.exists():
        print("No sources recorded yet.")
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        print(f"{r['added']}  {r['sha256'][:10]}  {r['chars']:>8}  {r['stored']}   <- {r['original']}")


def load_claims(c):
    p = c / "memory" / "claims.jsonl"
    rows = []
    if p.exists():
        rows = parse_claims(p.read_text(encoding="utf-8-sig"), "claims.jsonl")
    return rows


def parse_claims(text, label="claims", known=()):
    """Claim rows from JSON lines. Blank lines are skipped. A bad row stops everything and names its line, so
    nothing is half-read and nothing is silently dropped."""
    rows, ids = [], set(known)
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError as e:
            raise ValueError(f'{label}, line {i} is not valid JSON. Repair it; no rows were removed.') from e
        if not isinstance(r, dict) or not r.get('id') or not isinstance(r.get('claim'), str):
            raise ValueError(f'{label}, line {i}: a claim needs an id and text. No rows were removed.')
        if r['id'] in ids:
            where = 'is already in the ledger' if r['id'] in known else 'is used twice'
            raise ValueError(f'{label}, line {i}: claim id {r["id"]} {where}. Give it a new id. No rows were added.')
        ids.add(r['id'])
        rows.append(r)
    return rows


def import_claims(c, text):
    """Add extracted claim rows to the ledger under the intake lock. New rows only: an id already in the ledger is
    refused, and every imported row starts unverified, whatever the extractor wrote."""
    with intake_lock(c):
        rows = load_claims(c)
        new = parse_claims(text, "pasted rows", known=[r['id'] for r in rows])
        if not new:
            raise ValueError('No claim rows found to add.')
        for r in new:
            r['verified'] = False
        commit_intake(c, rows + new, [dict(date=datetime.date.today().isoformat(), id=r['id'], claim=r['claim'],
                                           answer='imported', note='', before=None, after=dict(r)) for r in new])
        return new


def save_claims(c, rows):
    p = c / "memory" / "claims.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic(p, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


def load_answers(c):
    p = c / "memory" / "intake-answers.jsonl"
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def group_key(rows):
    """The same key the hub files with a 'both' or 'neither' answer."""
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def conflicts(rows):
    """Pairs of current claims on the same entity with different text: the owner picks one, or says both apply."""
    by = {}
    for r in rows:
        if r.get("status") == "current":
            by.setdefault(r.get("entity", "").strip().lower(), []).append(r)
    return [v for v in by.values() if len(v) > 1 and len({x["claim"] for x in v}) > 1]


def questions(a):
    c = council_dir(a)
    rows = load_claims(c)
    if not rows:
        print("No claims yet. Add sources, run extract-prompt, and import them with import-claims (or paste them in the hub).")
        return
    answers = load_answers(c)
    answered = {x["id"] for x in answers if x.get("answer") in ("yes", "no", "outdated")}
    asked = []
    for group in conflicts(rows):                     # conflicts first: they change decisions
        # a conflict stays open until one side is no longer current, or the owner said both apply or neither
        if not any(x.get("group_key") == group_key(group) and x.get("resolution") in ("both", "neither") for x in answers):
            asked.append(("PICK ONE (keep one: answer it yes and the other no; 'both' and 'neither' are in the hub)", group))
    weight = {"unresolved": 0, "proposed": 1, "current": 2}
    singles = [r for r in rows if r["id"] not in answered and not r.get("verified")
               and r.get("status") in weight and r.get("authority") != "ai-draft"]
    singles.sort(key=lambda r: (weight[r["status"]], 0 if r.get("authority") == "owner" else 1, r["id"]))
    for r in singles:
        if all(r not in g for _, g in asked):
            asked.append(("YES / NO / NOT SURE / OUTDATED", [r]))
    for i, (kind, group) in enumerate(asked[: a.max], 1):
        print(f"[{i}] {kind}")
        for r in group:
            print(f"    {r['id']}  ({r.get('status')}, {r.get('authority')}, {r.get('effective', '?')})  {r['claim']}")
            print(f"          source: {r.get('source', '?')}")
        ids = " / ".join(r["id"] for r in group)
        print(f"    answer with: python intake_tool.py answer {group[0]['id']} yes|no|unsure|outdated"
              + (f"   (ids in this question: {ids})" if len(group) > 1 else ""))
        print()
    print(f"{min(len(asked), a.max)} of {len(asked)} open questions shown. Cap per sitting: {a.max}.")


def answer(a):
    write_answer(council_dir(a), a.id, a.answer, a.note or '')
    print(f"{a.id}: {a.answer}. Recorded.")


def edit(a):
    write_answer(council_dir(a), a.id, 'edited', text=a.text)
    print(f"{a.id} rewritten and marked verified. Old wording is kept in intake-answers.jsonl.")


EXTRACT_PROMPT = """Read the source files listed in memory/sources.jsonl (stored under outputs/council/inputs/).
Write one JSON object per line, fields exactly:
id (a new unused ID, never an existing claim ID), entity (short noun phrase), claim (ONE atomic sentence), scope (audience, product or time limits, or ""),
status (current | proposed | superseded | withdrawn | historical | unresolved), authority (owner | council | ai-draft | record),
effective (YYYY-MM-DD, YYYY-MM or "unknown"), supersedes (id of the claim it replaces, or ""), source (file:line), verified (false).
Rules: nothing invented, every row traceable to a line you read; split compound sentences into several claims; take the status
from the source's own wording (superseded, tentative, draft, confirmed); an AI draft is never authority "owner"; if a field
cannot be known write "unknown". Give back only the JSON lines, nothing else. Do not edit memory/claims.jsonl yourself: the
owner pastes your lines into the hub (Check facts, Add claims), or saves them to a file and runs: python intake_tool.py import-claims FILE"""



def atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(text, encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@contextlib.contextmanager
def intake_lock(c):
    """OS lock shared by CLI and hub. Process exit releases it even after a crash."""
    p = Path(c) / 'memory' / 'intake-write.lock'
    p.parent.mkdir(parents=True, exist_ok=True)
    f = open(p, 'a+b')
    if p.stat().st_size == 0:
        f.write(b' '); f.flush()
    acquired = False
    try:
        for _ in range(100):
            try:
                f.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                time.sleep(.05)
        if not acquired:
            raise RuntimeError('Another edit is being saved. Try again.')
        f.seek(1); f.truncate(); f.write(str(os.getpid()).encode()); f.flush()
        recover_intake(c)
        yield
    finally:
        if acquired:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def recover_intake(c):
    pending = Path(c) / 'memory' / 'intake-pending.json'
    if pending.exists():
        obj = json.loads(pending.read_text(encoding='utf-8'))
        for name, text in obj.items():
            if name not in ('claims.jsonl', 'intake-answers.jsonl', 'ui-sitting.json'):
                raise ValueError('Invalid intake recovery file.')
            atomic(Path(c) / 'memory' / name, text)
        pending.unlink()


def commit_intake(c, rows, records, sitting=None):
    """Write-ahead recovery keeps ledger, audit history and sitting progress together."""
    mem = Path(c) / 'memory'
    old = (mem / 'intake-answers.jsonl').read_text(encoding="utf-8-sig") if (mem / 'intake-answers.jsonl').exists() else ''
    obj = {'claims.jsonl': ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows),
           'intake-answers.jsonl': old + ('' if not old or old.endswith('\n') else '\n') + ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records)}
    if sitting is not None:
        obj['ui-sitting.json'] = json.dumps(sitting, ensure_ascii=False)
    atomic(mem / 'intake-pending.json', json.dumps(obj, ensure_ascii=False))
    recover_intake(c)


def apply_answer(row, answer, note='', text=None):
    """One rule implementation for CLI answers, edits and hub conflict choices."""
    rec = dict(date=datetime.date.today().isoformat(), id=row['id'], claim=row['claim'],
               answer=answer, note=note, before=dict(row))
    if answer == 'yes':
        row['verified'], row['authority'] = True, 'owner'
    elif answer == 'no':
        row['status'] = 'withdrawn'
    elif answer == 'outdated':
        row['status'] = 'superseded' if row.get('status') == 'current' else 'historical'
    elif answer == 'unsure':
        row['verified'] = False
    elif answer == 'edited':
        if not isinstance(text, str) or not text.strip() or len(text) > 12000:
            raise ValueError('Write a claim of 1 to 12000 characters.')
        row['claim'], row['verified'], row['authority'] = text.strip(), True, 'owner'
        rec['note'] = text.strip()
    else:
        raise ValueError('Choose Yes, No, Not sure or Outdated.')
    rec['after'] = dict(row)
    return rec


def write_answer(c, rid, answer, note='', text=None):
    with intake_lock(c):
        rows = load_claims(c)
        row = next((r for r in rows if r['id'] == rid), None)
        if row is None:
            raise ValueError('That claim was not found.')
        record = apply_answer(row, answer, note, text)
        commit_intake(c, rows, [record])
        return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--council", default="")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sources")
    ss = s.add_subparsers(dest="sub", required=True)
    sa = ss.add_parser("add")
    sa.add_argument("paths", nargs="+")
    ss.add_parser("list")
    q = sub.add_parser("questions")
    q.add_argument("--max", type=int, default=15)
    an = sub.add_parser("answer")
    an.add_argument("id")
    an.add_argument("answer", choices=["yes", "no", "unsure", "outdated"])
    an.add_argument("--note", default="")
    ed = sub.add_parser("edit")
    ed.add_argument("id")
    ed.add_argument("text")
    sub.add_parser("extract-prompt")
    ic = sub.add_parser("import-claims")
    ic.add_argument("file")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if a.cmd == "sources":
        (sources_add if a.sub == "add" else sources_list)(a)
    elif a.cmd == "questions":
        questions(a)
    elif a.cmd == "answer":
        answer(a)
    elif a.cmd == "import-claims":
        new = import_claims(council_dir(a), Path(a.file).read_text(encoding="utf-8-sig"))
        print(f"{len(new)} claim(s) added, all unverified. Next: python intake_tool.py questions")
    elif a.cmd == "edit":
        edit(a)
    else:
        print(EXTRACT_PROMPT)


if __name__ == "__main__":
    main()
