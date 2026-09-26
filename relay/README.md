# Codex relay: Adam 👀 → Junaid 🛠️

Two agents that keep the build going when Codex stops (usually because it ran out of usage credits).

- **Adam** watches Codex step by step. He knows every request you sent, everything Codex said, every command it ran and every file it wrote. When Codex stops, he writes a handoff brief and wakes Junaid.
- **Junaid** is a Claude Code session. He reads Adam's brief, checks the real state of the code, and continues exactly where Codex left off.

## Run it

Start Adam in a terminal before (or while) Codex works on this project:

```bash
python3 -m relay watch
```

That's all. Use Codex as usual in VS Code. Adam prints each Codex step as it happens. When Codex stops, Junaid starts in the background and his progress streams into the same terminal.

Other commands:

```bash
python3 -m relay status        # what is Codex doing / what did it last do here?
python3 -m relay handoff       # hand off right now from the latest Codex session
```

Useful options:

| Flag | Default | What it does |
|---|---|---|
| `--junaid terminal` | `headless` | Open Junaid in a new Terminal window so you can watch and steer. `off` = write the brief only |
| `--permission-mode` | `auto` | Claude Code permission mode for Junaid (`acceptEdits` is stricter, `bypassPermissions` is fully unattended) |
| `--model` | your default | Claude model for Junaid |
| `--stall-minutes` | `15` | Codex silent this long **mid-turn** counts as stopped (crash, VS Code closed, …) |
| `--warn-percent` | `90` | Warn (macOS notification) when Codex's 5-hour usage passes this |
| `--on-interrupt` | off | Also hand off when a turn is interrupted. Off by default because that is usually you pressing stop |
| `--project` | this repo | Watch Codex in a different project |

## What counts as "Codex stopped"

| Signal in Codex's log | Adam's reaction |
|---|---|
| `task_complete` with `usage_limit_exceeded` | Hand off: out of credits |
| `task_complete` with any other error | Hand off |
| A turn open with no activity for `--stall-minutes` | Hand off: stalled or crashed |
| `turn_aborted` | Logged only (unless `--on-interrupt`) |
| Turn finished normally | Nothing. Codex finishing isn't a failure |

Each stop is handed off once. Adam remembers handled stops in `.handoff/adam_state.json`, and on startup he replays recent history for context without re-triggering old stops.

## How it works

Codex (CLI and the VS Code extension) appends every event of a session to `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`. Adam tails the files whose working directory is this project. He merges helper subagents into their parent conversation, ignores the auto-review guardian threads, and inlines the pasted-text attachments that hold your actual prompts.

Everything lands in `.handoff/` (git-ignored):

- `LATEST_HANDOFF.md` / `handoff-<time>.md`: the brief given to Junaid
- `codex_activity.log`: Adam's step-by-step log of Codex
- `junaid-<time>.jsonl`: Junaid's full session log
- `JUNAID_REPORT.md`: Junaid's write-up of what he did and what's left. Paste it into Codex when its credits reset.

Code: `codex_log.py` (log parsing), `adam.py` (watching, stop detection, brief), `junaid.py` (Claude Code launcher), `prompts/junaid.md` (Junaid's role). No dependencies beyond Python 3.9 and the `claude` CLI.

Tests: `python3 -m unittest discover -s relay/tests -t .`
