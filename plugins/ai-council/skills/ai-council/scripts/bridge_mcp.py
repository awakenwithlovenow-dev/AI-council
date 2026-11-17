"""agent-bridge: an MCP server that lets Claude Code and Codex talk to each other.

Plain Python 3 standard library, stdio transport (newline-delimited JSON-RPC 2.0).
Register it in BOTH apps (see README.md next to this file). Tools:

  post_message(sender, to, subject, body)   shared mailbox, always works
  read_messages(reader, unread_only, mark_read)
  ask_codex(prompt, sandbox)                runs `codex exec` in the project, returns its answer
  queue_codex(thread, message)              posts a message into an existing Codex session
  ask_claude(prompt)                        runs `claude -p` (needs a one-time `claude` /login)

Binaries are found fresh on every call (the app folders carry version hashes that change
on update). The mailbox is one JSON line per message in MAILBOX; nothing is ever deleted.
"""
import glob, json, os, subprocess, sys, tempfile, threading, time, uuid
from pathlib import Path

PROJECT = Path(os.environ.get("BRIDGE_PROJECT", os.getcwd()))
MAILBOX = PROJECT / "outputs" / "agent-bridge" / "mailbox.jsonl"
LOCK = threading.Lock()
HOME = Path(os.environ.get("USERPROFILE", str(Path.home())))
LOCALAPP = Path(os.environ.get("LOCALAPPDATA", str(HOME / "AppData" / "Local")))
ROAMING = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming")))


def newest(pattern_list):
    hits = []
    for pat in pattern_list:
        hits += glob.glob(pat)
    hits = [h for h in hits if os.path.isfile(h)]
    return max(hits, key=os.path.getmtime) if hits else None


def codex_exe():
    return os.environ.get("BRIDGE_CODEX") or newest([str(LOCALAPP / "OpenAI" / "Codex" / "bin" / "*" / "codex.exe")])


def claude_exe():
    return os.environ.get("BRIDGE_CLAUDE") or newest([
        str(ROAMING / "Claude" / "claude-code" / "*" / "*" / "claude.exe"),
        str(LOCALAPP / "Packages" / "Claude_*" / "LocalCache" / "Roaming" / "Claude" / "claude-code" / "*" / "*" / "claude.exe"),
        str(HOME / ".local" / "bin" / "claude.exe")])


# ------------------------------------------------------------------ mailbox
def _load():
    if not MAILBOX.exists():
        return []
    out = []
    for line in MAILBOX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _save(msgs):
    MAILBOX.parent.mkdir(parents=True, exist_ok=True)
    tmp = MAILBOX.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in msgs), encoding="utf-8")
    os.replace(tmp, MAILBOX)


def post_message(sender, to, subject, body):
    msg = dict(id=uuid.uuid4().hex[:12], ts=time.strftime("%Y-%m-%d %H:%M:%S"), sender=sender.lower(),
               to=to.lower(), subject=subject, body=body, read_by=[])
    with LOCK:
        msgs = _load(); msgs.append(msg); _save(msgs)
    return f"Posted message {msg['id']} from {msg['sender']} to {msg['to']}: {subject}"


def read_messages(reader, unread_only=True, mark_read=True):
    reader = reader.lower()
    with LOCK:
        msgs = _load()
        mine = [m for m in msgs if m["to"] in (reader, "all") and (not unread_only or reader not in m.get("read_by", []))]
        if mark_read and mine:
            ids = {m["id"] for m in mine}
            for m in msgs:
                if m["id"] in ids and reader not in m.setdefault("read_by", []):
                    m["read_by"].append(reader)
            _save(msgs)
    if not mine:
        return f"No {'unread ' if unread_only else ''}messages for {reader}."
    return "\n\n".join(f"[{m['id']}] {m['ts']} from {m['sender']} to {m['to']}\nSubject: {m['subject']}\n{m['body']}" for m in mine)


# ------------------------------------------------------------------ the two agents
def _run(cmd, timeout, stdin_text=None):
    try:
        p = subprocess.run(cmd, cwd=str(PROJECT), input=stdin_text, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Timed out after {timeout} s."
    except FileNotFoundError as e:
        return -2, "", str(e)


def ask_codex(prompt, sandbox="read-only", timeout=1800):
    exe = codex_exe()
    if not exe:
        return "Codex not found (looked in %LOCALAPPDATA%\\OpenAI\\Codex\\bin)."
    if sandbox not in ("read-only", "workspace-write"):
        sandbox = "read-only"
    out = Path(tempfile.gettempdir()) / f"bridge-codex-{uuid.uuid4().hex[:8]}.txt"
    code, so, se = _run([exe, "exec", "-C", str(PROJECT), "-s", sandbox, "--skip-git-repo-check", "--ephemeral",
                         "-o", str(out), "-"], timeout, stdin_text=prompt)
    answer = out.read_text(encoding="utf-8", errors="replace").strip() if out.exists() else ""
    if out.exists():
        out.unlink()
    if answer:
        return answer
    return f"Codex exited {code} with no final message.\nstderr (last 1500 chars):\n{se[-1500:]}"


def queue_codex(thread, message):
    exe = codex_exe()
    if not exe:
        return "Codex not found."
    code, so, se = _run([exe, "queue", "--thread", thread, "--message", message], 120)
    return f"exit {code}\n{(so + se).strip()[-2000:]}"


def ask_claude(prompt, timeout=1800):
    exe = claude_exe()
    if not exe:
        return "Claude Code not found."
    code, so, se = _run([exe, "-p", "--output-format", "text", "--no-session-persistence"], timeout, stdin_text=prompt)
    text = (so or se).strip()
    if "Not logged in" in text:
        return ("Claude Code is not logged in for headless use. Open a terminal, run "
                f"\"{exe}\", type /login once, then try again.")
    return text or f"Claude exited {code} with no output."


# ------------------------------------------------------------------ MCP plumbing
TOOLS = [
    dict(name="post_message", description="Leave a message in the shared Claude/Codex mailbox. Use sender 'claude' or 'codex' and to 'claude', 'codex' or 'all'.",
         inputSchema=dict(type="object", required=["sender", "to", "subject", "body"], properties=dict(
             sender=dict(type="string"), to=dict(type="string"), subject=dict(type="string"), body=dict(type="string")))),
    dict(name="read_messages", description="Read messages addressed to you (or 'all') from the shared mailbox.",
         inputSchema=dict(type="object", required=["reader"], properties=dict(
             reader=dict(type="string"), unread_only=dict(type="boolean", default=True), mark_read=dict(type="boolean", default=True)))),
    dict(name="ask_codex", description="Give Codex a task in the project folder and get its final answer back. Read-only by default; pass sandbox 'workspace-write' to let it edit files. Can take minutes.",
         inputSchema=dict(type="object", required=["prompt"], properties=dict(
             prompt=dict(type="string"), sandbox=dict(type="string", enum=["read-only", "workspace-write"], default="read-only")))),
    dict(name="queue_codex", description="Queue a message into an existing Codex session (by session UUID or exact session name).",
         inputSchema=dict(type="object", required=["thread", "message"], properties=dict(thread=dict(type="string"), message=dict(type="string")))),
    dict(name="ask_claude", description="Ask Claude Code a question or give it a task in the project folder (headless). Needs a one-time login.",
         inputSchema=dict(type="object", required=["prompt"], properties=dict(prompt=dict(type="string")))),
]
HANDLERS = dict(post_message=post_message, read_messages=read_messages, ask_codex=ask_codex,
                queue_codex=queue_codex, ask_claude=ask_claude)


def reply(mid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": mid}
    if error:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n"); sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        mid, method, params = req.get("id"), req.get("method"), req.get("params") or {}
        if mid is None:          # notifications need no answer
            continue
        if method == "initialize":
            reply(mid, {"protocolVersion": params.get("protocolVersion", "2024-11-05"),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "agent-bridge", "version": "1.0.0"}})
        elif method == "tools/list":
            reply(mid, {"tools": TOOLS})
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            fn = HANDLERS.get(name)
            if not fn:
                reply(mid, error={"code": -32601, "message": f"unknown tool {name}"}); continue
            try:
                text = fn(**args)
                reply(mid, {"content": [{"type": "text", "text": str(text)}], "isError": False})
            except Exception as e:  # report, never crash the server
                reply(mid, {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True})
        elif method == "ping":
            reply(mid, {})
        else:
            reply(mid, error={"code": -32601, "message": f"unknown method {method}"})


if __name__ == "__main__":
    main()
