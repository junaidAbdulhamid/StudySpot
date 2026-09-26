"""CLI: python3 -m relay {watch,status,handoff}

  watch    Adam watches Codex live and launches Junaid when Codex stops.
  status   Show what Codex is doing (or last did) in this project.
  handoff  Write a brief from the latest Codex session now and launch Junaid.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import junaid
from .adam import Adam

DEFAULT_PROJECT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m relay", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["watch", "status", "handoff"])
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT,
                        help="project Codex is working in (default: %(default)s)")
    parser.add_argument("--handoff-dir", type=Path,
                        help="where briefs and logs go (default: <project>/.handoff)")
    parser.add_argument("--junaid", choices=["headless", "terminal", "off"], default="headless",
                        help="how to launch Junaid: background claude -p, a new Terminal window, "
                             "or not at all (brief only). Default: headless")
    parser.add_argument("--permission-mode", default="auto",
                        help="Claude Code permission mode for Junaid (default: auto)")
    parser.add_argument("--model", help="Claude model for Junaid (default: your Claude Code default)")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--stall-minutes", type=float, default=15,
                        help="treat Codex as stopped after this long silent mid-turn (default: 15)")
    parser.add_argument("--warn-percent", type=float, default=90,
                        help="warn when Codex's 5-hour usage passes this percent (default: 90)")
    parser.add_argument("--on-interrupt", action="store_true",
                        help="also hand off when a Codex turn is interrupted (e.g. you pressed stop)")
    parser.add_argument("--lookback-hours", type=float, default=24,
                        help="how far back to load Codex history for context (default: 24)")
    parser.add_argument("--quiet", action="store_true", help="don't echo every Codex step")
    args = parser.parse_args(argv)

    project = args.project.resolve()
    opts = None
    if args.junaid != "off":
        opts = junaid.Options(mode=args.junaid, permission_mode=args.permission_mode,
                              model=args.model, claude_bin=args.claude_bin)
    adam = Adam(project, (args.handoff_dir or project / ".handoff").resolve(),
                stall_minutes=args.stall_minutes, warn_percent=args.warn_percent,
                on_interrupt=args.on_interrupt, lookback_hours=args.lookback_hours,
                junaid_opts=opts, quiet=args.quiet)

    if args.command == "watch":
        adam.watch()
        return 0
    if args.command == "status":
        return adam.status()
    return adam.manual_handoff()


if __name__ == "__main__":
    sys.exit(main())
