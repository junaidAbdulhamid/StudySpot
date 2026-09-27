"""Run with: python3 -m unittest discover relay/tests"""
import json
import os
import stat
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from relay import junaid
from relay.adam import Adam
from relay.codex_log import exec_commands, written_files

LIMIT_MSG = "You've hit your usage limit. Upgrade to Pro ... or try again at 5:08 PM."


def ts(offset_s=0.0):
    t = datetime.now(timezone.utc) + timedelta(seconds=offset_s)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def meta(thread_id, cwd, root_id=None, source="vscode", thread_source="user"):
    return {"timestamp": ts(-600), "type": "session_meta", "payload": {
        "id": thread_id, "session_id": root_id or thread_id, "cwd": cwd,
        "source": source, "thread_source": thread_source}}


def ev(ptype, offset_s=0.0, **payload):
    return {"timestamp": ts(offset_s), "type": "event_msg", "payload": {"type": ptype, **payload}}


def exec_call(cmd):
    script = "text(await tools.exec_command({cmd:" + json.dumps(cmd) + "}));"
    return {"timestamp": ts(), "type": "response_item",
            "payload": {"type": "custom_tool_call", "name": "exec", "input": script}}


def limit_error(turn="t1"):
    return ev("task_complete", turn_id=turn, last_agent_message=None,
              error={"message": LIMIT_MSG, "codex_error_info": "usage_limit_exceeded"})


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sessions = self.tmp / "sessions" / "2026" / "09" / "25"
        self.sessions.mkdir(parents=True)
        self.project = self.tmp / "project"
        self.project.mkdir()
        self.handoff = self.project / ".handoff"
        attach = self.tmp / ".codex" / "attachments" / "abc"
        attach.mkdir(parents=True)
        self.spec = attach / "Pasted text.txt"
        self.spec.write_text("Build StudySpot: a map of the least crowded study spots at GMU.")

    def rollout(self, name, rows):
        path = self.sessions / f"rollout-2026-09-25T10-00-00-{name}.jsonl"
        self.append(path, rows)
        return path

    def append(self, path, rows):
        with open(path, "a") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    def adam(self, **kw):
        kw.setdefault("junaid_opts", None)
        return Adam(self.project, self.handoff, sessions_dir=self.tmp / "sessions", quiet=True, **kw)


class ParsingTests(unittest.TestCase):
    def test_exec_commands_decodes_js_strings(self):
        script = 'text(await tools.exec_command({cmd:"cat > app/main.py <<\'EOF\'\\nprint(\\"hi\\")\\nEOF",x:1}));'
        self.assertEqual(exec_commands(script), ["cat > app/main.py <<'EOF'\nprint(\"hi\")\nEOF"])

    def test_written_files(self):
        cmd = "cat > web/app.tsx <<'EOF'\necho nope > inside.txt\nEOF\nnpm test 2>&1 > /dev/null | tee logs/out.log"
        self.assertEqual([p for p, _ in written_files(cmd)], ["web/app.tsx", "logs/out.log"])
        patch = "apply_patch <<'P'\n*** Begin Patch\n*** Update File: src/a.py\n*** Add File: src/b.py\nP"
        self.assertEqual(written_files(patch)[:2], [("src/a.py", "update"), ("src/b.py", "add")])


class AdamTests(Fixture):
    def test_history_does_not_trigger_but_live_usage_limit_does(self):
        path = self.rollout("root", [
            meta("root", str(self.project)),
            ev("task_started", turn_id="t0"),
            ev("user_message", message=f"Files pasted: {self.spec}\n## My request:"),
            limit_error("t0"),  # old stop: must not re-trigger on startup
        ])
        adam = self.adam()
        adam.watcher.poll()
        adam.tick()
        self.assertFalse((self.handoff / "LATEST_HANDOFF.md").exists())

        self.append(path, [
            ev("task_started", turn_id="t1"),
            ev("agent_message", message="Adding the crowd heatmap next.", phase="commentary"),
            exec_call("cat > web/heatmap.tsx <<'EOF'\nexport {}\nEOF"),
            limit_error("t1"),
        ])
        adam.tick()
        brief = (self.handoff / "LATEST_HANDOFF.md").read_text()
        self.assertIn("Codex ran out of usage credits", brief)
        self.assertIn("least crowded study spots", brief)  # attachment inlined
        self.assertIn("Adding the crowd heatmap next.", brief)
        self.assertIn("`web/heatmap.tsx` (write)", brief)

        # The same stop is never handed off twice, even after a restart.
        (self.handoff / "LATEST_HANDOFF.md").unlink()
        adam2 = self.adam()
        adam2.handle_stop(adam.watcher.sessions["root"], adam.watcher.sessions["root"].stop)
        self.assertFalse((self.handoff / "LATEST_HANDOFF.md").exists())

    def test_user_requests_from_either_log_format_are_captured_once(self):
        msg = f"Files pasted: {self.spec}\n## My request:"
        item = ev("item_completed", item={"type": "UserMessage",
                                          "content": [{"type": "text", "text": msg}]})
        self.rollout("root", [
            meta("root", str(self.project)),
            item,  # migrated rollouts only keep this form
            ev("user_message", message=msg),  # newer ones log both forms
            ev("item_completed", item={"type": "UserMessage",
                                       "content": [{"type": "text", "text": "now add auth"}]}),
        ])
        adam = self.adam()
        adam.watcher.poll()
        requests = [text for _, text in adam.watcher.sessions["root"].user_requests]
        self.assertEqual(len(requests), 2)
        self.assertIn("least crowded study spots", requests[0])
        self.assertEqual(requests[1], "now add auth")

    def test_ignores_other_projects_and_guardian_threads(self):
        self.rollout("root", [meta("root", str(self.project))])
        g = self.rollout("guard", [meta("guard", str(self.project), root_id="root",
                                        source={"subagent": {"other": "guardian"}},
                                        thread_source="guardian_review")])
        o = self.rollout("other", [meta("other", str(self.tmp / "elsewhere"))])
        adam = self.adam()
        adam.watcher.poll()
        self.append(g, [ev("task_started", turn_id="g1"), limit_error("g1")])
        self.append(o, [ev("task_started", turn_id="o1"), limit_error("o1")])
        adam.tick()
        self.assertEqual(list(adam.watcher.sessions), ["root"])
        self.assertFalse((self.handoff / "LATEST_HANDOFF.md").exists())

    def test_subagent_work_is_merged_but_its_errors_do_not_trigger(self):
        self.rollout("root", [meta("root", str(self.project))])
        sub = self.rollout("sub", [meta("sub", str(self.project), root_id="root",
                                        source={"subagent": {"thread_spawn": {}}})])
        adam = self.adam()
        adam.watcher.poll()
        self.append(sub, [exec_call("cat > api/rooms.py <<'EOF'\nEOF"), limit_error("s1")])
        adam.tick()
        state = adam.watcher.sessions["root"]
        self.assertIn(str(self.project / "api/rooms.py"), state.files_touched)
        self.assertFalse((self.handoff / "LATEST_HANDOFF.md").exists())

    def test_interrupt_is_not_handed_off_by_default(self):
        path = self.rollout("root", [meta("root", str(self.project))])
        adam = self.adam()
        adam.watcher.poll()
        self.append(path, [ev("task_started", turn_id="t1"),
                           ev("turn_aborted", turn_id="t1", reason="interrupted")])
        adam.tick()
        self.assertFalse((self.handoff / "LATEST_HANDOFF.md").exists())

        adam = self.adam(on_interrupt=True)
        adam.watcher.poll()
        self.append(path, [ev("task_started", turn_id="t2"),
                           ev("turn_aborted", turn_id="t2", reason="interrupted")])
        adam.tick()
        self.assertTrue((self.handoff / "LATEST_HANDOFF.md").exists())

    def test_stall_mid_turn_triggers_handoff(self):
        path = self.rollout("root", [meta("root", str(self.project))])
        adam = self.adam(stall_minutes=1)
        adam.watcher.poll()
        self.append(path, [ev("task_started", -120, turn_id="t1")])
        adam.tick()
        self.assertIn("went silent", (self.handoff / "LATEST_HANDOFF.md").read_text())

    def test_finished_turn_is_not_a_stop(self):
        path = self.rollout("root", [meta("root", str(self.project))])
        adam = self.adam(stall_minutes=1)
        adam.watcher.poll()
        self.append(path, [ev("task_started", -120, turn_id="t1"),
                           ev("task_complete", -119, turn_id="t1", last_agent_message="Done.")])
        adam.tick()
        self.assertFalse((self.handoff / "LATEST_HANDOFF.md").exists())

    def test_junaid_is_launched_with_the_brief(self):
        fake = self.tmp / "fake-claude"
        record = self.tmp / "argv.json"
        fake.write_text(
            "#!/usr/bin/env python3\nimport json,sys,os\n"
            f"json.dump({{'argv': sys.argv[1:], 'cwd': os.getcwd()}}, open({str(record)!r}, 'w'))\n"
            "print(json.dumps({'type':'assistant','message':{'content':[{'type':'text','text':'On it'}]}}))\n"
            "print(json.dumps({'type':'result','subtype':'success','total_cost_usd':0.01}))\n")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

        path = self.rollout("root", [meta("root", str(self.project))])
        adam = self.adam(junaid_opts=junaid.Options(claude_bin=str(fake)))
        adam.watcher.poll()
        self.append(path, [ev("task_started", turn_id="t1"), limit_error("t1")])
        adam.tick()
        adam.junaid_run.wait()
        time.sleep(0.2)  # let the output pump flush

        call = json.loads(record.read_text())
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.project))
        self.assertIn("-p", call["argv"])
        self.assertIn(".handoff/LATEST_HANDOFF.md", call["argv"][-1])
        self.assertIn("You are Junaid", call["argv"][call["argv"].index("--append-system-prompt") + 1])
        self.assertIn('"subtype": "success"', adam.junaid_run.log_path.read_text())


if __name__ == "__main__":
    unittest.main()
