"""Adam: watches Codex step by step and hands off to Junaid the moment Codex stops."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import junaid
from .codex_log import CodexWatcher, SessionState, Step, StopEvent, clip

STOP_REASONS = {
    "usage_limit": "Codex ran out of usage credits",
    "error": "Codex's turn ended with an error",
    "interrupted": "Codex's turn was interrupted",
    "stalled": "Codex went silent in the middle of a turn",
    "manual": "Handoff requested manually",
}

ICONS = {
    "user": "👤", "say": "💬", "cmd": "▸ ", "edit": "✎ ", "turn_start": "▶ ",
    "turn_end": "✓ ", "stop": "⛔", "compact": "↺ ",
}


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] Adam  {msg}", flush=True)


def notify(title: str, body: str) -> None:
    """macOS notification; silently skipped elsewhere."""
    script = f"display notification {json.dumps(body)} with title {json.dumps(title)} sound name \"Glass\""
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def local(ts: datetime) -> str:
    return ts.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def git(project: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return f"(git failed: {e})"
    return (r.stdout or r.stderr).strip() or "(nothing)"


def limit_reset_text(rate_limits: dict) -> str:
    parts = []
    for key, label in (("primary", "5-hour window"), ("secondary", "weekly window")):
        win = rate_limits.get(key) or {}
        if win.get("resets_at"):
            when = datetime.fromtimestamp(win["resets_at"]).strftime("%a %b %d %I:%M %p")
            parts.append(f"{label}: {win.get('used_percent', '?')}% used, resets {when}")
    return "; ".join(parts)


def build_handoff(state: SessionState, stop: StopEvent, project: Path) -> str:
    """Render everything Junaid needs to continue Codex's work as one markdown brief."""
    lines: List[str] = []
    add = lines.append
    add("# Codex → Junaid handoff")
    add(f"_Written by Adam at {datetime.now():%Y-%m-%d %H:%M:%S}_\n")

    add("## Why Codex stopped")
    add(f"- **Reason:** {STOP_REASONS.get(stop.kind, stop.kind)}")
    add(f"- **When:** {local(stop.ts)}")
    add(f"- **Codex said:** {stop.message}")
    resets = limit_reset_text(state.rate_limits)
    if resets:
        add(f"- **Codex limits:** {resets}")
    add("")

    add("## Project")
    add(f"- **Directory:** `{project}`")
    if state.title:
        add(f"- **Codex thread:** {state.title}")
    add(f"- **Codex session id:** `{state.root_id}`")
    for f in state.files:
        add(f"- **Rollout log:** `{f}`")
    add("")

    add("## What the user asked Codex to do")
    add("Everything the user sent in this Codex conversation, oldest first. "
        "The first request is usually the full spec; later ones are follow-ups or course corrections.\n")
    requests = state.user_requests
    if len(requests) > 12:
        omitted = len(requests) - 12
        requests = requests[:2] + requests[-10:]
        add(f"_({omitted} middle messages omitted; see the rollout log)_\n")
    for i, (ts, text) in enumerate(requests, 1):
        add(f"### Request {i} ({local(ts)})")
        add("```text")
        add(clip(text.strip(), 24000).replace("```", "ʼʼʼ"))
        add("```\n")
    if not state.user_requests:
        add("_No user message was captured (the conversation may predate the lookback window)._\n")

    if state.last_turn_summary:
        add("## Codex's summary of its last completed turn")
        add(clip(state.last_turn_summary, 6000))
        add("")

    add("## What Codex was saying most recently")
    add("Codex's own narration, oldest first. The last entries show what it was in the middle of.\n")
    for ts, msg in list(state.messages)[-10:]:
        add(f"- **{ts.astimezone():%H:%M:%S}**: {clip(msg.strip(), 1500)}")
    if not state.messages:
        add("_(none captured)_")
    add("")

    if state.files_touched:
        add("## Files Codex changed in this session")
        for path, ctype in sorted(state.files_touched.items()):
            add(f"- `{state.rel(path)}` ({ctype})")
        add("")

    add("## Step-by-step timeline (most recent 80 steps)")
    add("```text")
    for s in list(state.steps)[-80:]:
        add(f"{s.ts.astimezone():%H:%M:%S} {s.kind:<10} {s.text}")
    add("```\n")

    add("## Repository state right now")
    add("`git status --short`:")
    add("```text\n" + clip(git(project, "status", "--short"), 6000) + "\n```")
    add("`git diff --stat` (changes to files git already tracks):")
    add("```text\n" + clip(git(project, "diff", "--stat"), 6000) + "\n```")
    untracked = git(project, "ls-files", "--others", "--exclude-standard")
    if untracked != "(nothing)":
        paths = untracked.splitlines()
        add(f"**{len(paths)} untracked files.** Codex's work is mostly here, so `git diff` does **not** "
            "show it and there is no committed version to compare against or fall back on:")
        add("```text\n" + clip("\n".join(paths), 6000) + "\n```")
    add("Recent commits:")
    add("```text\n" + git(project, "log", "--oneline", "-8") + "\n```\n")

    add("## Your job, Junaid")
    add("1. Treat the user's requests above as the goal. Codex's narration shows how far it got.")
    add("2. Codex may have stopped mid-edit. Check the files it touched last and the uncommitted diff first.")
    add("3. Continue from where Codex stopped. Don't redo finished work and don't restart with a new design.")
    add("4. Verify as you go (build, tests, run the app), then keep building until the request is done.")
    add("5. Finish by writing `.handoff/JUNAID_REPORT.md`: what you did, what's verified, what's left.")
    return "\n".join(lines) + "\n"


class Adam:
    def __init__(self, project: Path, handoff_dir: Path, stall_minutes: float = 15,
                 warn_percent: float = 90, on_interrupt: bool = False,
                 lookback_hours: float = 24, junaid_opts: Optional[junaid.Options] = None,
                 sessions_dir: Optional[Path] = None, quiet: bool = False):
        self.project = project
        self.handoff_dir = handoff_dir
        self.stall_seconds = stall_minutes * 60
        self.warn_percent = warn_percent
        self.on_interrupt = on_interrupt
        self.junaid_opts = junaid_opts
        self.quiet = quiet
        self.watcher = CodexWatcher(project, sessions_dir, lookback_hours)
        self.state_file = handoff_dir / "adam_state.json"
        self.activity_log = handoff_dir / "codex_activity.log"
        self.handled = set(self._load_state().get("handled", []))
        self.warned: set = set()
        self.junaid_run: Optional[junaid.Run] = None
        handoff_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        try:
            return json.loads(self.state_file.read_text())
        except (OSError, ValueError):
            return {}

    def _save_state(self) -> None:
        self.state_file.write_text(json.dumps({"handled": sorted(self.handled)}, indent=2))

    # ---- watching ---------------------------------------------------------

    def watch(self, interval: float = 1.0) -> None:
        self.watcher.poll()  # replay recent history silently so Adam starts with full context
        log(f"watching Codex in {self.project}")
        latest = self.watcher.latest()
        if latest:
            status = "mid-turn" if latest.turn_open else "idle"
            log(f"latest Codex session: {latest.title or latest.root_id} ({status}, "
                f"last activity {local(latest.last_activity)}, {len(latest.steps)} steps known)")
        else:
            log("no Codex sessions for this project yet. Start Codex here and Adam will pick it up")
        if self.junaid_opts is None:
            log("Junaid launch is OFF. Adam will only write handoff briefs")
        try:
            while True:
                self.tick()
                time.sleep(interval)
        except KeyboardInterrupt:
            log("stopped watching")

    def tick(self) -> None:
        for state, step, live in self.watcher.poll():
            if not live:
                continue
            self._record(state, step)
            if step.kind == "turn_start" and self.junaid_run and self.junaid_run.running():
                log("⚠️  Codex is working again while Junaid is still running. They may edit the same files")
                notify("Codex is back", "Junaid is still working in the same project. Check for conflicts.")
            if step.kind == "stop" and state.stop:
                self.handle_stop(state, state.stop)
        self._check_rate_limits()
        self._check_stalls()
        if self.junaid_run:
            self.junaid_run.poll()

    def _record(self, state: SessionState, step: Step) -> None:
        line = f"{step.ts.astimezone():%H:%M:%S} {ICONS.get(step.kind, '• ')} {step.text}"
        if not self.quiet:
            print(f"   codex {line}", flush=True)
        with open(self.activity_log, "a") as fh:
            fh.write(f"{step.ts.astimezone():%Y-%m-%d} {line}\n")

    def _check_rate_limits(self) -> None:
        for state in self.watcher.sessions.values():
            primary = (state.rate_limits or {}).get("primary") or {}
            pct = primary.get("used_percent")
            key = (primary.get("resets_at"), int((pct or 0) // 5))
            if state.live and pct is not None and pct >= self.warn_percent and key not in self.warned:
                self.warned.add(key)
                log(f"Codex has used {pct:.0f}% of its 5-hour limit. Adam is ready to hand off")
                notify("Codex almost out of usage", f"{pct:.0f}% of the 5-hour limit used")

    def _check_stalls(self) -> None:
        now = datetime.now(timezone.utc)
        for state in self.watcher.sessions.values():
            if not (state.live and state.turn_open and state.last_activity):
                continue
            idle = (now - state.last_activity).total_seconds()
            if idle >= self.stall_seconds:
                state.turn_open = False
                stop = StopEvent("stalled", now, state.current_turn or "",
                                 f"No activity from Codex for {idle / 60:.0f} minutes mid-turn")
                state.stop = stop
                self._record(state, Step(now, "stop", stop.message, stop.turn_id))
                self.handle_stop(state, stop)

    # ---- handing off ------------------------------------------------------

    def handle_stop(self, state: SessionState, stop: StopEvent) -> Optional[Path]:
        key = f"{state.root_id}:{stop.turn_id}:{stop.kind}"
        if key in self.handled:
            return None
        self.handled.add(key)
        self._save_state()
        if stop.kind == "interrupted" and not self.on_interrupt:
            log("Codex's turn was interrupted (usually you pressed stop). Not handing off; "
                "run with --on-interrupt to change this")
            return None

        log(f"⛔ {STOP_REASONS.get(stop.kind, stop.kind)}: {stop.message}")
        brief = self.write_handoff(state, stop)
        log(f"handoff brief written: {brief}")
        notify("Codex stopped: Adam is handing off", STOP_REASONS.get(stop.kind, stop.kind))

        if self.junaid_opts is None:
            return brief
        if self.junaid_run and self.junaid_run.running():
            log("Junaid is already working. Updated the brief but did not start a second Junaid")
            return brief
        self.junaid_run = junaid.launch(self.project, brief, self.handoff_dir, self.junaid_opts)
        return brief

    def write_handoff(self, state: SessionState, stop: StopEvent) -> Path:
        text = build_handoff(state, stop, self.project)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.handoff_dir / f"handoff-{stamp}.md"
        path.write_text(text)
        latest = self.handoff_dir / "LATEST_HANDOFF.md"
        latest.write_text(text)
        return latest

    # ---- one-shot commands ------------------------------------------------

    def load(self) -> Optional[SessionState]:
        self.watcher.poll()
        return self.watcher.latest()

    def status(self) -> int:
        state = self.load()
        if not state:
            print(f"No Codex sessions found for {self.project} in the last {self.watcher.lookback_hours:g}h.")
            return 1
        print(f"Codex session : {state.title or state.root_id}")
        print(f"State         : {'working (turn open)' if state.turn_open else 'idle'}")
        print(f"Last activity : {local(state.last_activity)}")
        if state.stop:
            print(f"Last stop     : {STOP_REASONS.get(state.stop.kind)}: {state.stop.message}")
        resets = limit_reset_text(state.rate_limits)
        if resets:
            print(f"Limits        : {resets}")
        print(f"Files changed : {len(state.files_touched)}")
        print("\nRecent steps:")
        for s in list(state.steps)[-15:]:
            print(f"  {s.ts.astimezone():%H:%M:%S} {ICONS.get(s.kind, '• ')} {s.text}")
        return 0

    def manual_handoff(self) -> int:
        state = self.load()
        if not state:
            print(f"No Codex sessions found for {self.project} in the last {self.watcher.lookback_hours:g}h.",
                  file=sys.stderr)
            return 1
        stop = state.stop or StopEvent("manual", datetime.now(timezone.utc), state.current_turn or "",
                                       "Handoff requested manually via `relay handoff`")
        brief = self.write_handoff(state, stop)
        log(f"handoff brief written: {brief}")
        if self.junaid_opts is not None:
            run = junaid.launch(self.project, brief, self.handoff_dir, self.junaid_opts)
            run.wait()
        return 0
