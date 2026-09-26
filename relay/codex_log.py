"""Reading Codex's rollout logs.

The Codex CLI and the VS Code extension both append every step of a session to
~/.codex/sessions/YYYY/MM/DD/rollout-<time>-<thread id>.jsonl: the user's
requests, Codex's messages, every command and file edit, rate-limit readings,
and the error Codex records when it runs out of usage. Those files are the only
thing Adam reads.
"""
from __future__ import annotations

import json
import os
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))

# Pasted prompts are stored as files and only referenced by path in the message.
# File names can contain spaces ("Pasted text.txt"), so match the folder and read what's in it.
ATTACHMENT_RE = re.compile(r"(/\S*?\.codex/attachments/[\w-]+)/")

USAGE_LIMIT = "usage_limit_exceeded"


def parse_ts(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return datetime.now(timezone.utc)


def clip(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [{len(text) - limit} more characters truncated]"


def one_line(text: str, limit: int = 160) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def expand_attachments(message: str, limit: int = 20000) -> str:
    """Inline the contents of pasted-text attachments referenced in a user message."""
    extras = []
    for folder in dict.fromkeys(ATTACHMENT_RE.findall(message or "")):
        try:
            files = sorted(p for p in Path(folder).iterdir() if p.is_file())
        except OSError:
            continue
        for path in files:
            if path.suffix.lower() not in (".txt", ".md", ".json", ".yaml", ".yml", ""):
                continue
            try:
                body = path.read_text(errors="replace")
            except OSError:
                continue
            extras.append(f"\n--- attachment: {path} ---\n{clip(body, limit)}\n--- end attachment ---")
    return (message or "") + "".join(extras)


def command_text(command) -> str:
    if isinstance(command, list):
        # ["/bin/zsh", "-lc", "<script>"] -> "<script>"
        if len(command) == 3 and command[1] in ("-lc", "-c"):
            return command[2]
        return " ".join(str(c) for c in command)
    return str(command or "")


# Newer Codex builds run commands through an `exec` tool whose input is a small JS
# script: text(await tools.exec_command({cmd:"<shell>", ...}))
EXEC_CMD_RE = re.compile(r"""\bcmd\s*:\s*"((?:[^"\\]|\\.)*)\"""", re.S)
EXIT_CODE_RE = re.compile(r'\\?"exit_code\\?"\s*:\s*(-?\d+)')
SHELL_WRITE_RE = re.compile(r"""(?:(?<![\d&])>{1,2}|\btee\s+(?:-a\s+)?)\s*['"]?([\w./@+-]+\.\w+)['"]?""")
PATCH_FILE_RE = re.compile(r"\*\*\* (Add|Update|Delete) File: (\S+)")


def js_string(raw: str) -> str:
    try:
        return json.loads('"' + raw.replace("\\'", "'") + '"')
    except ValueError:
        return raw.replace("\\n", "\n").replace('\\"', '"')


def exec_commands(script: str) -> List[str]:
    return [js_string(m) for m in EXEC_CMD_RE.findall(script or "")]


def written_files(cmd: str) -> List[Tuple[str, str]]:
    """Best-effort guess at files a shell command writes: heredocs, tee, apply_patch."""
    found = [(m.group(2), m.group(1).lower()) for m in PATCH_FILE_RE.finditer(cmd)]
    in_heredoc = None
    for line in cmd.splitlines():
        if in_heredoc is not None:  # skip heredoc bodies, they are file contents
            if line.strip() == in_heredoc:
                in_heredoc = None
            continue
        for path in SHELL_WRITE_RE.findall(line):
            if not path.startswith("/dev/") and not path.startswith("/tmp/"):
                found.append((path, "write"))
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
        if m:
            in_heredoc = m.group(1)
    return found


def read_meta(path: Path) -> Optional[dict]:
    """The first line of every rollout file is its session_meta."""
    try:
        with open(path, "r", errors="replace") as fh:
            first = fh.readline()
        obj = json.loads(first)
    except (OSError, ValueError):
        return None
    if obj.get("type") != "session_meta":
        return None
    return obj.get("payload") or {}


def thread_role(meta: dict) -> str:
    """'root' for the conversation the user drives, 'subagent' for helpers Codex
    spawned, 'ignore' for the auto-review guardian that only judges commands."""
    if meta.get("thread_source") == "guardian_review":
        return "ignore"
    source = meta.get("source")
    if isinstance(source, dict) and "subagent" in source:
        return "subagent"
    return "root"


def load_thread_names() -> Dict[str, str]:
    names: Dict[str, str] = {}
    try:
        with open(CODEX_HOME / "session_index.jsonl", errors="replace") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("id") and row.get("thread_name"):
                    names[row["id"]] = row["thread_name"]
    except OSError:
        pass
    return names


@dataclass
class Step:
    ts: datetime
    kind: str  # user | say | cmd | edit | turn_start | turn_end | stop | compact
    text: str
    turn_id: Optional[str] = None


@dataclass
class StopEvent:
    kind: str  # usage_limit | error | interrupted | stalled | manual
    ts: datetime
    turn_id: str
    message: str


@dataclass
class SessionState:
    """Everything Adam knows about one Codex conversation (root thread plus its subagents)."""

    root_id: str
    cwd: str = ""
    title: str = ""
    files: List[Path] = field(default_factory=list)
    user_requests: List[Tuple[datetime, str]] = field(default_factory=list)
    messages: Deque[Tuple[datetime, str]] = field(default_factory=lambda: deque(maxlen=40))
    steps: Deque[Step] = field(default_factory=lambda: deque(maxlen=500))
    files_touched: Dict[str, str] = field(default_factory=dict)
    last_turn_summary: str = ""
    turn_open: bool = False
    current_turn: Optional[str] = None
    last_activity: Optional[datetime] = None
    rate_limits: dict = field(default_factory=dict)
    stop: Optional[StopEvent] = None
    live: bool = False  # has produced events since Adam started watching
    saw_exec: bool = False

    def apply(self, obj: dict, role: str) -> List[Step]:
        """Fold one rollout line into the state and return the steps it produced."""
        kind = obj.get("type")
        p = obj.get("payload") or {}
        ptype = p.get("type")
        ts = parse_ts(obj.get("timestamp", ""))
        if self.last_activity is None or ts > self.last_activity:
            self.last_activity = ts
        root = role == "root"
        out: List[Step] = []

        def step(k: str, text: str) -> None:
            s = Step(ts, k, text, self.current_turn)
            self.steps.append(s)
            out.append(s)

        who = "" if root else "[subagent] "
        if kind == "response_item":
            if ptype == "custom_tool_call" and p.get("name") == "exec":
                self.saw_exec = True
                for cmd in exec_commands(p.get("input", "")):
                    step("cmd", f"{who}$ {one_line(cmd, 220)}")
                    for path, how in written_files(cmd):
                        full = path if path.startswith("/") else os.path.join(self.cwd, path)
                        self.files_touched[full] = how
            elif ptype == "custom_tool_call_output":
                text = json.dumps(p.get("output"))
                codes = [int(c) for c in EXIT_CODE_RE.findall(text)]
                failed = [c for c in codes if c != 0]
                if failed:
                    step("cmd", f"{who}  ↳ command failed (exit {failed[-1]})")
            elif ptype == "function_call" and p.get("name") == "spawn_agent":
                step("say", f"{who}Codex spawned a subagent: {one_line(p.get('arguments', ''), 200)}")
            return out
        if kind != "event_msg":
            return out

        if ptype == "task_started" and root:
            self.turn_open = True
            self.current_turn = p.get("turn_id")
            self.stop = None
            step("turn_start", "Codex started working")
        elif ptype == "user_message" and root:
            text = p.get("message", "")
            self.user_requests.append((ts, expand_attachments(text)))
            step("user", one_line(text, 300))
        elif ptype == "agent_message" and root:
            msg = p.get("message", "")
            self.messages.append((ts, msg))
            step("say", one_line(msg, 300))
        elif ptype == "token_count":
            if p.get("rate_limits"):
                self.rate_limits = p["rate_limits"]
        elif ptype == "task_complete" and root:
            self.turn_open = False
            err = p.get("error")
            if err:
                info = err.get("codex_error_info") or "error"
                self.stop = StopEvent(
                    kind="usage_limit" if info == USAGE_LIMIT else "error",
                    ts=ts,
                    turn_id=p.get("turn_id") or "",
                    message=err.get("message") or str(info),
                )
                step("stop", f"Codex stopped: {self.stop.message}")
            else:
                self.last_turn_summary = p.get("last_agent_message") or self.last_turn_summary
                step("turn_end", "Codex finished the turn")
        elif ptype == "turn_aborted" and root:
            self.turn_open = False
            self.stop = StopEvent(
                kind="interrupted",
                ts=ts,
                turn_id=p.get("turn_id") or "",
                message=f"Turn aborted ({p.get('reason', 'unknown reason')})",
            )
            step("stop", self.stop.message)
        elif ptype == "context_compacted" and root:
            step("compact", "Codex compacted its context")
        elif ptype == "item_completed":
            item = p.get("item") or {}
            itype = item.get("type")
            # Sessions that log `exec` tool calls also log each command here; count them once.
            if itype == "CommandExecution" and not self.saw_exec:
                code = item.get("exit_code")
                suffix = "" if code in (0, None) else f"  (exit {code})"
                step("cmd", f"{who}$ {one_line(command_text(item.get('command')), 220)}{suffix}")
            elif itype == "FileChange":
                changes = item.get("changes") or {}
                for path, change in changes.items():
                    ctype = change.get("type", "update") if isinstance(change, dict) else "update"
                    self.files_touched[path] = ctype
                    step("edit", f"{who}{ctype} {self.rel(path)}")
        return out

    def rel(self, path: str) -> str:
        if self.cwd and path.startswith(self.cwd.rstrip("/") + "/"):
            return path[len(self.cwd.rstrip("/")) + 1 :]
        return path


class FileCursor:
    """Incrementally reads new complete lines from a growing JSONL file."""

    def __init__(self, path: Path, root_id: str, role: str, live_from: int):
        self.path = path
        self.root_id = root_id
        self.role = role
        self.offset = 0
        self.live_from = live_from  # byte offset where "live" (post-startup) lines begin

    def read(self) -> List[Tuple[dict, bool]]:
        try:
            size = self.path.stat().st_size
        except OSError:
            return []
        if size < self.offset:  # file was rewritten
            self.offset = 0
        if size == self.offset:
            return []
        with open(self.path, "rb") as fh:
            fh.seek(self.offset)
            chunk = fh.read(size - self.offset)
        end = chunk.rfind(b"\n")
        if end < 0:
            return []  # partial line; wait for the rest
        rows = []
        pos = self.offset
        for raw in chunk[: end + 1].split(b"\n")[:-1]:
            live = pos >= self.live_from
            pos += len(raw) + 1
            try:
                rows.append((json.loads(raw), live))
            except ValueError:
                continue
        self.offset += end + 1
        return rows


def within(path: str, project: Path) -> bool:
    try:
        real = os.path.realpath(path)
    except (TypeError, ValueError):
        return False
    proj = os.path.realpath(str(project))
    return real == proj or real.startswith(proj + os.sep)


class CodexWatcher:
    """Tracks every Codex session whose working directory is inside `project`."""

    def __init__(self, project: Path, sessions_dir: Optional[Path] = None, lookback_hours: float = 24):
        self.project = project
        self.sessions_dir = sessions_dir or (CODEX_HOME / "sessions")
        self.lookback_hours = lookback_hours
        self.cursors: Dict[Path, FileCursor] = {}
        self.skipped: set = set()
        self.sessions: Dict[str, SessionState] = {}
        self.names = load_thread_names()
        self.started = False

    def discover(self) -> None:
        now = datetime.now().timestamp()
        paths = sorted(self.sessions_dir.glob("**/rollout-*.jsonl"))
        for path in paths:
            if path in self.cursors or path in self.skipped:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if not self.started and now - stat.st_mtime > self.lookback_hours * 3600:
                self.skipped.add(path)
                continue
            meta = read_meta(path)
            if meta is None:
                continue  # may still be being created; retry next pass
            role = thread_role(meta)
            if role == "ignore" or not within(meta.get("cwd", ""), self.project):
                self.skipped.add(path)
                continue
            root_id = meta.get("session_id") or meta.get("id") or path.stem
            if root_id not in self.sessions:
                self.sessions[root_id] = SessionState(root_id=root_id, cwd=meta.get("cwd", ""))
            state = self.sessions[root_id]
            state.files.append(path)
            state.title = self.names.get(root_id, state.title)
            # Files present at startup are history; anything written after is live.
            live_from = stat.st_size if not self.started else 0
            self.cursors[path] = FileCursor(path, root_id, role, live_from)

    def poll(self) -> List[Tuple[SessionState, Step, bool]]:
        self.discover()
        events = []
        for cursor in list(self.cursors.values()):
            state = self.sessions[cursor.root_id]
            for obj, live in cursor.read():
                if live:
                    state.live = True
                for s in state.apply(obj, cursor.role):
                    events.append((state, s, live))
        self.started = True
        return events

    def latest(self) -> Optional[SessionState]:
        roots = [s for s in self.sessions.values() if s.last_activity]
        return max(roots, key=lambda s: s.last_activity) if roots else None
