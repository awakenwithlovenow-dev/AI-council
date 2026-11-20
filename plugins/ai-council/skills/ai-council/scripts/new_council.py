"""new_council.py: set up an AI council in a project folder.

  python new_council.py                          set it up in the current folder
  python new_council.py --project PATH           set it up in PATH
  python new_council.py --owner "Sam Rivera"     also record the owner's name (shown in the hub)
  python new_council.py --update-program         bring an existing council's program up to date with this version

Creates outputs/council/ (rules, brief, agenda, settings, memory) and tools/council/ (the meeting program and the
hub app), runs a dry-run meeting with no AI calls to prove the plumbing, and prints the next steps.
Never overwrites an existing file. One AI (Claude, with a Claude challenger) is the default.
"""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def desktop_icon(root, tools):
    """A The Council icon on the desktop that opens the hub in its own window. Never replaces an existing icon.
    Windows is tested; the Mac and Linux versions are written but not yet tried on those systems."""
    launch = tools / "chamber" / "launch.py"
    py = Path(sys.executable)
    try:
        if os.name == "nt":
            pyw = py.with_name("pythonw.exe") if py.with_name("pythonw.exe").exists() else py
            q = lambda p: "'" + str(p).replace("'", "''") + "'"
            ps = ("$d=[Environment]::GetFolderPath('Desktop'); $f=Join-Path $d 'The Council.lnk'; "
                  "if (Test-Path $f) { 'exists' } else { $s=(New-Object -ComObject WScript.Shell).CreateShortcut($f); "
                  f"$s.TargetPath={q(pyw)}; $s.Arguments={q(chr(34) + str(launch) + chr(34))}; "
                  f"$s.WorkingDirectory={q(root)}; $s.IconLocation={q(tools / 'chamber' / 'council.ico')}; "
                  "$s.Description='Open your AI council'; $s.Save(); 'made' }")
            out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                                 timeout=60).stdout.strip()
            print("  desktop icon   ", "kept the existing The Council icon" if out == "exists" else "created The Council")
            return
        desk = Path.home() / "Desktop"
        if sys.platform == "darwin":
            f = desk / "The Council.command"
            body = f"#!/bin/sh\ncd '{root}'\nexec '{py}' '{launch}'\n"
        else:
            f = desk / "the-council.desktop"
            body = (f"[Desktop Entry]\nType=Application\nName=The Council\nExec='{py}' '{launch}'\n"
                    f"Path={root}\nTerminal=false\n")
        if f.exists():
            print("  desktop icon    kept the existing", f.name)
            return
        desk.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
        f.chmod(0o755)
        print("  desktop icon    created", f.name)
    except Exception as e:                      # an icon is a convenience: never fail the setup over it
        print("  desktop icon    skipped:", str(e)[:200])


def update_program(root, tools):
    """Bring the council program in tools/council/ up to date with this plugin version (added 20 Nov 2026: a
    plugin update alone never reached a council already set up, because setup never overwrites a file).
    The council's own files in outputs/council/ are never touched. Each replaced file is kept first in
    tools/council/archive/before-update-<date>/, so nothing is lost."""
    import ast, datetime, filecmp
    if not (tools / "council.py").exists():
        print("No council here yet: run without --update-program to set one up.")
        return 1
    keep = tools / "archive" / ("before-update-" + datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    pairs = [(SKILL / "scripts" / f, tools / f)
             for f in ["council.py", "memory_tool.py", "intake_tool.py", "converse.py", "run-council.cmd"]]
    pairs += [(f, tools / "chamber" / f.name) for f in sorted((SKILL / "scripts" / "chamber").iterdir()) if f.is_file()]
    for src, _ in pairs:                       # never copy in a program that does not parse
        if src.suffix == ".py":
            ast.parse(src.read_text(encoding="utf-8"))
    changed = 0
    for src, dest in pairs:
        if dest.exists() and filecmp.cmp(src, dest, shallow=False):
            continue
        if dest.exists():
            old = keep / dest.relative_to(tools)
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, old)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        changed += 1
        print("  updated         " + str(dest.relative_to(root)))
    if changed:
        print(f"Updated {changed} program file(s). The old copies are kept in {keep.relative_to(root)}.")
    else:
        print("The council program is already up to date.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--owner", default="")
    ap.add_argument("--no-icon", action="store_true", help="do not put a The Council icon on the desktop")
    ap.add_argument("--update-program", action="store_true",
                    help="bring an existing council's program up to date; the council's own files are not touched")
    args = ap.parse_args()
    if sys.version_info < (3, 9):
        print(f"Python 3.9 or newer is needed; this is {sys.version.split()[0]}.")
        return 1
    root = Path(args.project).resolve()
    council, tools = root / "outputs" / "council", root / "tools" / "council"
    if args.update_program:
        return update_program(root, tools)
    made = []

    def put(src, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f"  kept existing   {dest.relative_to(root)}")
            return
        shutil.copyfile(src, dest)
        made.append(dest)
        print(f"  created         {dest.relative_to(root)}")

    for d in ["members/dossiers", "members/final", "members/approved", "memory/member-lessons",
              "inputs", "drafts", "sessions", "files"]:
        (council / d).mkdir(parents=True, exist_ok=True)
    put(SKILL / "references" / "charter-template.md", council / "CHARTER.md")
    put(SKILL / "templates" / "BRIEF.md", council / "BRIEF.md")
    put(SKILL / "templates" / "AGENDA.md", council / "AGENDA.md")
    put(SKILL / "templates" / "config.json", council / "config.json")
    put(SKILL / "templates" / "SEATS.md", council / "members" / "final" / "SEATS.md")
    put(SKILL / "references" / "extraction-prompt.md", council / "members" / "EXTRACTION-PROMPT.md")
    if args.owner:
        cfg_path = council / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not cfg.get("owner_name"):
            cfg["owner_name"] = args.owner
            cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            print(f"  owner name set  {args.owner}")
    rulings = council / "memory" / "RULINGS.md"
    if not rulings.exists():
        rulings.write_text("# Rulings\n\nWhat the owner has decided. Every session reads this; it outranks drafts, "
                           "dossiers and the council's own opinions.\n\n", encoding="utf-8")
        made.append(rulings)
    for f in ["council.py", "memory_tool.py", "intake_tool.py", "converse.py", "run-council.cmd"]:
        put(SKILL / "scripts" / f, tools / f)
    for f in sorted((SKILL / "scripts" / "chamber").iterdir()):
        if f.is_file():
            put(f, tools / "chamber" / f.name)
    put(SKILL / "scripts" / "bridge_mcp.py", root / "tools" / "agent-bridge" / "bridge_mcp.py")
    if not args.no_icon:
        desktop_icon(root, tools)

    print("\nChecking the plumbing with a dry run (no AI is called)...")
    r = subprocess.run([sys.executable, str(tools / "council.py"), "--dry-run", "--turns", "4"],
                       cwd=str(root), capture_output=True, text=True)
    ok = r.returncode == 0 and "closed" in (r.stdout + r.stderr)
    for sub in ("sessions", "drafts"):
        for p in (council / sub).glob("*-dry"):
            shutil.rmtree(p, ignore_errors=True)
    print("  dry run:", "PASSED" if ok else "FAILED\n" + (r.stdout + r.stderr)[-1500:])
    print(f"""
Council ready at {council}

Next: run /council-build in Claude Code to design the members from your own files, notes and meetings,
or follow the six prompts in {SKILL / 'prompts'} by hand.
Ask the council something:  /council-meet your question   (in the Claude chat; the answer comes back there)
Run a meeting by hand:      {sys.executable} {tools / 'council.py'} --topic "your question"
Open the hub (optional):    {sys.executable} {tools / 'chamber' / 'launch.py'}   (or /council-hub)
Check that the council can reach Claude in the background:  {sys.executable} {tools / 'council.py'} --check-claude""")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
