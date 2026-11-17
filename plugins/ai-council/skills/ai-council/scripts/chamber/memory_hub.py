"""Local source intake and memory screens. No model calls or retrieval changes."""
import datetime as dt
import hashlib
import json
import re
import shutil
import tempfile
import uuid
import zipfile
from collections import Counter
from pathlib import Path

import intake_tool as intake
import memory_tool as memory

MAX_UPLOAD = 8_000_000
CAP = 15


def text(p):
    return p.read_text(encoding='utf-8-sig', errors='replace') if p.is_file() else ''   # -sig: a Notepad BOM is not text


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def records(p):
    rows = []
    for i, line in enumerate(text(p).splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if not isinstance(r, dict):
                raise ValueError()
            rows.append(r)
        except ValueError:
            raise ValueError(f'{p.name}, line {i} cannot be read. No records were removed.')
    return rows


class MemoryHub:
    def __init__(self, council, running=lambda: False):
        self.c = Path(council).resolve()
        self.running = running

    def safe(self, rel):
        if not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or rel.startswith('/') or '..' in rel.split('/'):
            raise ValueError('Use a path inside this council.')
        p = (self.c / rel).resolve()
        if self.c not in p.parents:
            raise ValueError('That path leaves this council.')
        return p

    def check_store(self):
        for rel in ('memory', 'inputs', 'config.json', 'memory/claims.jsonl', 'memory/intake-answers.jsonl',
                    'memory/sources.jsonl', 'memory/ui-sitting.json', 'memory/intake-pending.json', 'memory/intake-write.lock',
                    'memory/source-events.jsonl', 'memory/settings-events.jsonl', 'memory/source-originals', 'memory/source-archive'):
            self.safe(rel)

    def writable(self):
        self.check_store()
        if self.running():
            raise RuntimeError('A meeting is running. Save memory changes after it finishes.')

    def append(self, name, obj):
        p = self.safe('memory/' + name)
        old = text(p)
        intake.atomic(p, old + ('' if not old or old.endswith('\n') else '\n') + json.dumps(obj, ensure_ascii=False) + '\n')

    def source_list(self):
        self.check_store()
        registered = records(self.safe('memory/sources.jsonl'))
        events = records(self.safe('memory/source-events.jsonl'))
        out, seen = [], set()
        for r in registered:
            stored = r.get('stored', '')
            if stored in seen:
                continue
            seen.add(stored)
            try:
                p = self.safe(stored)
            except ValueError:
                continue
            ev = next((e for e in reversed(events) if e.get('stored') == stored), {})
            out.append(dict(r, name=Path(stored).name, size=p.stat().st_size if p.is_file() else 0,
                            held=p.is_file(), removed=ev.get('kind') == 'remove', undo=ev.get('token') if ev.get('kind') == 'remove' else None,
                            registered=True, sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else r.get('sha256', '')))
        for root in ('inputs', 'members/dossiers'):
            for p in sorted(self.safe(root).glob('*')):
                if not p.is_file():
                    continue
                rel = p.relative_to(self.c).as_posix()
                try:
                    self.safe(rel)
                except ValueError:
                    continue
                if rel not in seen:
                    out.append(dict(stored=rel, name=p.name, size=p.stat().st_size, added=None, original='Already in council; origin not recorded',
                                    held=True, removed=False, registered=False, sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
                    seen.add(rel)
        # Unregistered legacy sources also keep a reload-safe Undo after removal.
        latest = {e.get('stored'): e for e in events}
        for rel, ev in latest.items():
            if rel and rel not in seen and ev.get('kind') == 'remove':
                out.append(dict(stored=rel, name=Path(rel).name, size=0, added=None, original='Already in council; origin not recorded',
                                held=False, removed=True, undo=ev['token'], registered=False, sha256=''))
        groups = {}
        for r in out:
            if r['held']:
                groups.setdefault(r['sha256'], []).append(r['stored'])
        for r in out:
            r['duplicates'] = [p for p in groups.get(r['sha256'], []) if p != r['stored']]
        return dict(sources=out, prompt=intake.EXTRACT_PROMPT, max_bytes=MAX_UPLOAD)

    def add_source(self, name, data, origin='File picker'):
        self.writable()
        if not isinstance(name, str) or '/' in name or '\\' in name or ':' in name or name in ('.', '..') or len(name) > 240:
            raise ValueError('That filename is not allowed. Choose a file without path separators.')
        ext = Path(name).suffix.lower()
        if ext not in intake.TEXT_EXT:
            raise ValueError(f'{name}: type refused. Use md, txt, html or docx.')
        if len(data) > MAX_UPLOAD:
            raise ValueError(f'{name}: larger than 8 MB (8,000,000 bytes).')
        if not data:
            raise ValueError(f'{name}: the file is empty.')
        if ext == '.docx':
            try:
                import io
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    info = z.getinfo('word/document.xml')
                    if info.file_size > MAX_UPLOAD or sum(i.file_size for i in z.infolist()) > 32_000_000:
                        raise ValueError('The Word file expands beyond the safe size limit.')
            except (zipfile.BadZipFile, KeyError):
                raise ValueError('That Word file has no readable document text.')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ('source' + ext)
            p.write_bytes(data)
            try:
                content = intake.to_markdown(p)
            except Exception:
                raise ValueError('That file could not be converted to readable text.')
        if not content.strip():
            raise ValueError('No readable text was found in that file.')
        sha = hashlib.sha256(content.encode()).hexdigest()
        with intake.intake_lock(self.c):
            for r in self.source_list()['sources']:
                # Reading normalizes Windows CRLF, just like to_markdown().
                # Compare the full converted text, not platform-dependent bytes.
                if r['held'] and hashlib.sha256(text(self.safe(r['stored'])).encode()).hexdigest() == sha:
                    return dict(duplicate=True, stored=r['stored'], message=f"{name}: duplicate of {r['stored']}. Existing copy kept.")
            stem = re.sub('[^A-Za-z0-9._-]+', '-', Path(name).stem).strip('.-')[:100] or 'source'
            dest = self.safe('inputs/' + stem + '.md')
            n = 2
            while dest.exists():
                dest = self.safe(f'inputs/{stem}-{n}.md'); n += 1
            token = uuid.uuid4().hex
            original = self.safe('memory/source-originals/' + token + ext)
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(data)
            intake.atomic(dest, content)
            record = dict(stored=dest.relative_to(self.c).as_posix(), original=name, origin=str(origin)[:500],
                          original_stored=original.relative_to(self.c).as_posix(), added=dt.datetime.now(dt.timezone.utc).isoformat(),
                          chars=len(content), original_bytes=len(data), sha256=sha)
            self.append('sources.jsonl', record)
            return dict(duplicate=False, stored=record['stored'], message=f'{name}: added.')

    def source_content(self, rel, line=1):
        p = self.safe(rel)
        if not (rel.startswith(('inputs/', 'members/dossiers/', 'memory/')) or rel in ('BRIEF.md', 'LATEST-MINUTES.md', 'CHARTER.md', 'AGENDA.md')):
            raise ValueError('Only council sources can be opened here.')
        if p.suffix.lower() not in ('.md', '.txt', '.html', '.htm', '.jsonl'):
            raise ValueError('This source is not readable text.')
        if not p.is_file():
            raise ValueError('This source is missing or archived. Its claim has not been deleted.')
        if p.stat().st_size > MAX_UPLOAD:
            raise ValueError('This source exceeds the 8 MB reading limit.')
        lines = text(p).splitlines()
        line = max(1, int(line))
        start = max(1, line - 5)
        return dict(path=rel, line=line, total=len(lines), start=start, lines=lines[start-1:start+39],
                    line_exists=line <= len(lines))

    def remove_source(self, rel):
        self.writable()
        with intake.intake_lock(self.c):
            p = self.safe(rel)
            if not rel.startswith(('inputs/', 'members/dossiers/')) or not p.is_file():
                raise ValueError('Choose an existing source in inputs or member dossiers.')
            token = uuid.uuid4().hex
            target = self.safe('memory/source-archive/' + token + '/' + p.name)
            target.parent.mkdir(parents=True)
            record = dict(kind='remove', stored=rel, archived=target.relative_to(self.c).as_posix(), token=token,
                          at=dt.datetime.now(dt.timezone.utc).isoformat())
            # Record an undo location before moving. If moving fails the source stays held.
            self.append('source-events.jsonl', record)
            shutil.move(str(p), str(target))
            return record

    def undo_source(self, token):
        self.writable()
        with intake.intake_lock(self.c):
            events = records(self.safe('memory/source-events.jsonl'))
            r = next((e for e in reversed(events) if e.get('token') == token), None)
            if not r or r.get('kind') != 'remove':
                raise ValueError('This removal has already been undone or was not found.')
            src, dest = self.safe(r['archived']), self.safe(r['stored'])
            if dest.exists():
                raise ValueError('A file now occupies that name. Both copies were kept; nothing was overwritten.')
            if not src.is_file():
                raise ValueError('The archived source was not found.')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            self.append('source-events.jsonl', dict(r, kind='restore'))
            return {'restored': r['stored']}

    def question_groups(self, rows, answers):
        """Same entity is a review candidate, not proof of contradiction."""
        groups, grouped = [], set()
        for group in intake.conflicts(rows):
            key = digest(group)
            noted = any(a.get('group_key') == key and a.get('resolution') in ('both', 'neither') for a in answers)
            if not noted:
                groups.append(dict(key=key, kind='conflict', rows=group))
                grouped.update(r['id'] for r in group)
        weight = {'unresolved': 0, 'proposed': 1, 'current': 2}
        singles = [r for r in rows if r['id'] not in grouped and not r.get('verified') and r.get('status') in weight and r.get('authority') != 'ai-draft']
        singles.sort(key=lambda r: (weight[r['status']], 0 if r.get('authority') == 'owner' else 1, r['id']))
        groups.extend(dict(key=digest([r]), kind='claim', rows=[r]) for r in singles)
        return groups

    def sitting(self):
        p = self.safe('memory/ui-sitting.json')
        return json.loads(text(p)) if p.is_file() else None

    def intake_state(self):
        self.check_store()
        with intake.intake_lock(self.c):
            rows = intake.load_claims(self.c)
            answers = records(self.safe('memory/intake-answers.jsonl'))
            sit = self.sitting()
            groups = self.question_groups(rows, answers)
            deferred = set(sit.get('seen', [])) if sit and not sit['closed'] else set()
            available = [g for g in groups if g['key'] not in deferred]
            current = [r for r in rows if r.get('status') == 'current']
            return dict(groups=available, rows=rows, sitting=sit, cap=CAP,
                        progress=dict(answered=len({a.get('id') for a in answers if a.get('answer') != 'imported'} & {r['id'] for r in rows}),
                                      open=len(groups), verified=sum(bool(r.get('verified')) for r in current), current=len(current), total=len(rows)),
                        answer_events=len(answers))

    def start_sitting(self):
        self.writable()
        with intake.intake_lock(self.c):
            sit = self.sitting()
            if not sit or sit['closed'] or sit['count'] >= CAP:
                sit = dict(id=uuid.uuid4().hex, count=0, closed=False, seen=[], started=dt.datetime.now(dt.timezone.utc).isoformat())
                intake.atomic(self.safe('memory/ui-sitting.json'), json.dumps(sit))
            return sit

    def finish_sitting(self, sid):
        self.writable()
        with intake.intake_lock(self.c):
            sit = self.sitting()
            if not sit or sit['id'] != sid:
                raise ValueError('This sitting changed. Refresh the questions.')
            sit['closed'] = True
            intake.atomic(self.safe('memory/ui-sitting.json'), json.dumps(sit))
            return sit

    def answer(self, body):
        self.writable()
        with intake.intake_lock(self.c):
            sit = self.sitting()
            if not sit or sit['id'] != body.get('sitting') or sit['closed'] or sit['count'] >= CAP:
                raise ValueError('This sitting is complete. Start another when you are ready.')
            rows = intake.load_claims(self.c)
            groups = self.question_groups(rows, records(self.safe('memory/intake-answers.jsonl')))
            key = body.get('key')
            group = next((g for g in groups if g['key'] == key), None)
            if not group or key in sit['seen']:
                raise ValueError('This claim changed or was already answered. Refresh before answering.')
            result, choice = [], body.get('answer')
            note = str(body.get('note', ''))[:4000]
            if group['kind'] == 'conflict' and choice != 'edited':
                if choice not in ('pick', 'both', 'neither', 'unsure'):
                    raise ValueError('Choose one claim, both in different cases, neither, or Not sure.')
                if choice == 'pick' and body.get('id') not in [r['id'] for r in group['rows']]:
                    raise ValueError('Choose a claim shown in this question.')
                for row in group['rows']:
                    ans = ('yes' if row['id'] == body.get('id') else 'no') if choice == 'pick' else 'unsure'
                    rec = intake.apply_answer(row, ans, note or {'both': 'Both apply in different cases.', 'neither': 'Neither claim is accepted.', 'unsure': 'Not sure.', 'pick': 'Owner chose one current claim.'}[choice])
                    rec['resolution'] = choice
                    result.append(rec)
                new_key = digest(group['rows'])
                for rec in result:
                    rec['group_key'] = new_key
                sit['seen'].append(new_key)
                sit['seen'].extend(digest([row]) for row in group['rows'])
            else:
                row = next((r for r in group['rows'] if r['id'] == body.get('id')), None)
                if row is None:
                    raise ValueError('That claim is not in the current question.')
                result.append(intake.apply_answer(row, choice, note, body.get('text')))
                sit['seen'].append(digest(group['rows']))
            sit['seen'].append(key)
            sit['count'] += 1
            sit['closed'] = sit['count'] >= CAP
            for rec in result:
                rec['sitting'] = sit['id']
            intake.commit_intake(self.c, rows, result, sit)
            return dict(records=result, sitting=sit)

    def import_claims(self, pasted):
        """Rows the owner's own Claude extracted, pasted into the hub. Same rules as intake_tool.py import-claims:
        new ids only, all unverified, nothing existing is changed."""
        self.writable()
        if not isinstance(pasted, str) or not pasted.strip():
            raise ValueError('Paste the lines Claude gave you first.')
        # keep only the rows: Claude often wraps them in a ```json fence or a sentence of its own
        rows = [l.strip() for l in pasted.splitlines() if l.strip().startswith('{')]
        if not rows:
            raise ValueError('No fact lines found. Each line Claude gives back should start with {"id":')
        new = intake.import_claims(self.c, chr(10).join(rows))
        return dict(added=len(new), ids=[r['id'] for r in new])

    def settings(self):
        p = self.safe('config.json')
        cfg = json.loads(text(p) or '{}')
        return {k: cfg.get(k, 0) for k in ('memory_pull_chars', 'claims_ledger_chars')}

    def update_settings(self, body):
        self.writable()
        with intake.intake_lock(self.c):
            p = self.safe('config.json')
            cfg = json.loads(text(p) or '{}')
            if body.get('expected') != self.settings():
                raise ValueError('Settings changed in another window. Refresh before saving.')
            values = body.get('values', {})
            if set(values) != {'memory_pull_chars', 'claims_ledger_chars'}:
                raise ValueError('Choose both memory budgets.')
            for k, v in values.items():
                maximum = 20000 if k == 'claims_ledger_chars' else 60000
                if type(v) is not int or not 0 <= v <= maximum:
                    raise ValueError(f'{k} must be a whole number from 0 to {maximum} characters.')
            rec = dict(token=uuid.uuid4().hex, before={k: cfg.get(k) for k in values}, after=values,
                       at=dt.datetime.now(dt.timezone.utc).isoformat())
            self.append('settings-events.jsonl', rec)
            intake.atomic(p, json.dumps(dict(cfg, **values), indent=2))
            return rec

    def undo_settings(self, token):
        self.writable()
        with intake.intake_lock(self.c):
            records_ = records(self.safe('memory/settings-events.jsonl'))
            rec = next((r for r in reversed(records_) if r.get('token') == token), None)
            if not rec or rec.get('undone') or self.settings() != rec['after']:
                raise ValueError('Settings changed since this save. Nothing was overwritten.')
            cfg = json.loads(text(self.safe('config.json')) or '{}')
            for k, v in rec['before'].items():
                if v is None:
                    cfg.pop(k, None)
                else:
                    cfg[k] = v
            intake.atomic(self.safe('config.json'), json.dumps(cfg, indent=2))
            self.append('settings-events.jsonl', dict(rec, undone=True))
            return self.settings()

    def health(self):
        state = self.intake_state()
        rows = state['rows']
        core = [{'file': f, 'chars': min(len(text(self.safe(f))), memory.CAPS.get(f, 10**12))} for f in memory.CORE_FILES]
        seats = [len(text(p)) for p in self.safe('members/approved').glob('*.md') if self.c in p.resolve().parents]
        sources = self.source_list()['sources']
        groups = intake.conflicts(rows)
        stale = []
        today = dt.date.today()
        for r in rows:
            m = re.match(r'^(\d{4})-(\d{2})', str(r.get('effective', '')))
            if m and r.get('status') == 'current' and not r.get('verified'):
                try:
                    if (today - dt.date(int(m[1]), int(m[2]), 1)).days > 90:
                        stale.append(r['id'])
                except ValueError:
                    pass
        dups, seen = [], set()
        for r in sources:
            paths = sorted([r['stored']] + r['duplicates'])
            if r['held'] and r['duplicates'] and any(p.startswith('inputs/') for p in paths) and any(p.startswith('members/dossiers/') for p in paths):
                if tuple(paths) not in seen:
                    dups.append(paths); seen.add(tuple(paths))
        receipt = next((l for l in reversed(text(self.safe('chair.log')).splitlines()) if 'Memory pull:' in l), None)
        last_setting = records(self.safe('memory/settings-events.jsonl'))
        return dict(core=core, core_chars=sum(r['chars'] for r in core) + max(seats, default=0), largest_seat=max(seats, default=0),
                    reporting_figure=90000, archive_chars=sum(len(text(self.safe(r['stored']))) for r in sources if r['held'] and r['stored'].endswith('.md')),
                    statuses=dict(Counter(r.get('status', 'unknown') for r in rows)), progress=state['progress'],
                    conflicts=[dict(entity=g[0].get('entity', ''), ids=[r['id'] for r in g]) for g in groups], stale=stale, duplicates=dups,
                    sources_recorded=sum(r['registered'] for r in sources), sources_held=sum(r['held'] for r in sources),
                    last_receipt=receipt, settings=self.settings(), last_setting=last_setting[-1] if last_setting else None)
