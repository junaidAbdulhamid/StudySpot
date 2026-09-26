"""Junaid: a Claude Code session that picks up where Codex stopped.

Two ways to run him:
  headless: `claude -p` in the background. Adam streams his progress and saves a log.
            Works unattended (Codex dies at 2am, Junaid keeps building).
  terminal: opens a new Terminal window with an interactive Claude Code session
            already briefed, so you can watch and steer.
"""
from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

PROMPT_FILE = Path(__file__).parent / "prompts" / "junaid.md"

KICKOFF = (
    "Codex stopped working on this project. Adam's handoff brief is at {brief}. "
    "Read it fully, check the actual state of the code, then pick up exactly where Codex left off "
    "and keep building until the user's request is done. "
    "Finish by writing .handoff/JUNAID_REPORT.md."
)


@dataclass
class Options:
    mode: str = "headless"  # headless | terminal
    permission_mode: str = "auto"
    model: Optional[str] = None
    claude_bin: str = "claude"


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] Junaid {msg}", flush=True)


def claude_args(brief: Path, project: Path, opts: Options, interactive: bool) -> List[str]:
    try:
        brief_ref = str(brief.relative_to(project))
    except ValueError:
        brief_ref = str(brief)
    args = [opts.claude_bin]
    if not interactive:
        args += ["-p", "--output-format", "stream-json", "--verbose"]
    args += ["--name", "Junaid", "--permission-mode", opts.permission_mode,
             "--append-system-prompt", PROMPT_FILE.read_text()]
    if opts.model:
        args += ["--model", opts.model]
    args.append(KICKOFF.format(brief=brief_ref))
    return args


class Run:
    """A running (or finished) Junaid session."""

    def __init__(self, proc: Optional[subprocess.Popen], log_path: Optional[Path]):
        self.proc = proc
        self.log_path = log_path
        self._reported = False

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def poll(self) -> None:
        if self.proc is None or self._reported or self.proc.poll() is None:
            return
        self._reported = True
        log(f"finished (exit {self.proc.returncode}). Log: {self.log_path}")

    def wait(self) -> None:
        if self.proc is not None:
            self.proc.wait()
            self.poll()


def _summarize(event: dict) -> Optional[str]:
    """Turn one stream-json event into a short progress line."""
    etype = event.get("type")
    if etype == "assistant":
        parts = []
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") == "text" and block.get("text", "").strip():
                parts.append("💬 " + " ".join(block["text"].split())[:220])
            elif block.get("type") == "tool_use":
                inp = block.get("input") or {}
                detail = (inp.get("command") or inp.get("file_path") or inp.get("pattern")
                          or inp.get("description") or "")
                parts.append(f"▸ {block.get('name')} {' '.join(str(detail).split())[:180]}")
        return "\n".join(parts) or None
    if etype == "result":
        cost = event.get("total_cost_usd")
        cost_text = f", ${cost:.2f}" if isinstance(cost, (int, float)) else ""
        return f"done: {event.get('subtype')}{cost_text}"
    return None


def _pump(proc: subprocess.Popen, log_path: Path) -> None:
    with open(log_path, "a") as fh, proc.stdout:  # type: ignore[union-attr]
        for raw in proc.stdout:  # type: ignore[union-attr]
            fh.write(raw)
            fh.flush()
            try:
                event = json.loads(raw)
            except ValueError:
                if raw.strip():
                    log(raw.rstrip()[:300])
                continue
            summary = _summarize(event)
            if summary:
                for line in summary.splitlines():
                    print(f"   junaid {line}", flush=True)


def launch(project: Path, brief: Path, handoff_dir: Path, opts: Options) -> Run:
    if shutil.which(opts.claude_bin) is None:
        log(f"can't find `{opts.claude_bin}` on PATH. Install Claude Code or pass --claude-bin")
        return Run(None, None)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if opts.mode == "terminal":
        script = handoff_dir / f"junaid-{stamp}.command"
        cmd = " ".join(shlex.quote(a) for a in claude_args(brief, project, opts, interactive=True))
        script.write_text(f"#!/bin/zsh\ncd {shlex.quote(str(project))}\nexec {cmd}\n")
        script.chmod(0o755)
        subprocess.run(["open", "-a", "Terminal", str(script)], check=False)
        log("opened in a new Terminal window")
        return Run(None, None)

    log_path = handoff_dir / f"junaid-{stamp}.jsonl"
    proc = subprocess.Popen(
        claude_args(brief, project, opts, interactive=False),
        cwd=str(project),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(target=_pump, args=(proc, log_path), daemon=True).start()
    log(f"started (pid {proc.pid}, permission mode {opts.permission_mode}). Log: {log_path}")
    return Run(proc, log_path)
