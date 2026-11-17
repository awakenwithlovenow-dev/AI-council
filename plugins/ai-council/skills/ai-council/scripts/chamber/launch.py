"""Opens the Council hub in its own window, like a desktop app.

Starts the hub's program quietly in the background if it is not already running (no console window), then opens
http://127.0.0.1:8790/ as an app window in Microsoft Edge or Chrome, or in the default browser if neither is found.
Closing the window leaves the program running, so meetings and talks with Claude carry on; the next launch just
reopens the window. Run with pythonw.exe (the desktop shortcut does this).
"""
import os, shutil, socket, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
PORT = 8790
URL = f"http://127.0.0.1:{PORT}/"
DETACHED, NEW_GROUP = 0x00000008, 0x00000200


def running():
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
        return True
    except OSError:
        return False


def is_hub():
    """True when the program answering on the port is this hub, not some other program that took the port."""
    try:
        with urllib.request.urlopen(URL + "api/state", timeout=5) as r:
            return r.status == 200 and b'"roster"' in r.read(200000)
    except Exception:
        return False


def start_server():
    py = Path(sys.executable)
    quiet = py.with_name("pythonw.exe") if py.with_name("pythonw.exe").exists() else py
    subprocess.Popen([str(quiet), str(HERE / "server.py"), "--no-open", "--port", str(PORT)], cwd=str(PROJECT),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=(DETACHED | NEW_GROUP) if os.name == "nt" else 0,
                     start_new_session=os.name != "nt")       # Mac and Linux: the hub outlives this launcher too
    for _ in range(60):
        if running():
            return True
        time.sleep(0.25)
    return False


def app_browser():
    roots = [os.environ.get(k, "") for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
        for root in roots:
            exe = Path(root) / rel
            if root and exe.exists():
                return exe
    for mac in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",        # Mac (not yet tried on one)
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
        if Path(mac).exists():
            return Path(mac)
    for name in ("microsoft-edge", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):   # Linux
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def main():
    if not running() and not start_server():
        webbrowser.open(URL)                     # the page will say it cannot reach its program
        return 1
    if not is_hub():                             # another program holds the port: say so instead of opening its page
        print(f"Port {PORT} is in use by another program, so the Council hub could not start. "
              f"Close that program, or run server.py with --port and another number.")
        return 1
    exe = app_browser()
    if exe:
        subprocess.Popen([str(exe), f"--app={URL}", "--window-size=1440,920"])
    else:
        webbrowser.open(URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
