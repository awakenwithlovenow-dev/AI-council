"""converse.py: one recorded exchange with Codex, outside the scheduled council.

  python converse.py <prompt-file> <log-file> [--label "Round 1"]

Sends the prompt file to headless Codex (read-only, same flags as the chair), appends
both the prompt and Codex's answer to the log file as they land, and prints the answer.
Used for direct Claude/Codex deliberation that the owner asks for between council sessions.
"""
import argparse, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import council as c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt_file")
    ap.add_argument("log_file")
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    log = Path(args.log_file)
    cfg = dict(c.DEFAULTS, **c.load_json(c.CONFIG, {}))
    cfg["turn_timeout_s"] = 3600
    stamp = time.strftime("%Y-%m-%d %H:%M")
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n\n## {args.label} : CLAUDE to CODEX ({stamp})\n\n{prompt}\n")
    started = time.time()
    try:
        answer = c.call_codex(prompt, cfg)
    except c.MemberError as e:
        answer = f"(Codex call failed: {e})"
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n\n## {args.label} : CODEX to CLAUDE ({time.strftime('%Y-%m-%d %H:%M')}, "
                f"{int(time.time() - started)} s, model {cfg.get('codex_model') or 'default'})\n\n{answer}\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print(answer)


if __name__ == "__main__":
    main()
