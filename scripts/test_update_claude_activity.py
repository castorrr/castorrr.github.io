"""Unit tests for scripts/update-claude-activity.py (stdlib only).

Run: python3 scripts/test_update_claude_activity.py -v
"""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

# The script filename has hyphens, so load it via importlib instead of import.
_MOD_PATH = Path(__file__).with_name("update-claude-activity.py")
_spec = importlib.util.spec_from_file_location("update_claude_activity", _MOD_PATH)
uca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uca)


def line(**kwargs):
    return json.dumps(kwargs)


def msg(type="user", ts="2026-07-11T03:00:00Z", sidechain=False, blocks=None):
    entry = {"type": type, "timestamp": ts, "isSidechain": sidechain}
    if blocks is not None:
        entry["message"] = {"content": blocks}
    return json.dumps(entry)


class ScanSessionLinesTest(unittest.TestCase):
    def test_counts_user_and_assistant_messages_only(self):
        days = uca.scan_session_lines([
            msg(type="user"),
            msg(type="assistant"),
            line(type="summary", timestamp="2026-07-11T03:00:00Z"),
            line(type="queue-operation", timestamp="2026-07-11T03:00:00Z"),
        ])
        self.assertEqual(days, {"2026-07-11": {"m": 2, "t": 0}})

    def test_sidechain_messages_excluded(self):
        days = uca.scan_session_lines([msg(), msg(sidechain=True)])
        self.assertEqual(days["2026-07-11"]["m"], 1)

    def test_utc_evening_buckets_to_next_manila_day(self):
        # 16:00 UTC == 00:00 in Asia/Manila (UTC+8) — the day boundary
        days = uca.scan_session_lines([
            msg(ts="2026-07-10T15:59:59Z"),
            msg(ts="2026-07-10T16:00:00Z"),
        ])
        self.assertEqual(days, {
            "2026-07-10": {"m": 1, "t": 0},
            "2026-07-11": {"m": 1, "t": 0},
        })

    def test_tool_use_blocks_counted_in_assistant_messages(self):
        blocks = [{"type": "text", "text": "hi"},
                  {"type": "tool_use", "id": "1", "name": "Bash", "input": {}},
                  {"type": "tool_use", "id": "2", "name": "Read", "input": {}}]
        days = uca.scan_session_lines([msg(type="assistant", blocks=blocks)])
        self.assertEqual(days["2026-07-11"], {"m": 1, "t": 2})

    def test_tool_use_blocks_ignored_in_user_messages(self):
        blocks = [{"type": "tool_use", "id": "1", "name": "Bash", "input": {}}]
        days = uca.scan_session_lines([msg(type="user", blocks=blocks)])
        self.assertEqual(days["2026-07-11"], {"m": 1, "t": 0})

    def test_malformed_lines_skipped_silently(self):
        days = uca.scan_session_lines([
            "not json{",
            "42",                          # valid JSON, not an object
            json.dumps({"type": "user"}),  # object with no timestamp
            msg(),
        ])
        self.assertEqual(days, {"2026-07-11": {"m": 1, "t": 0}})


class ScanProjectsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.projects = Path(self.tmp.name)

    def write_session(self, project, name, lines):
        d = self.projects / project
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text("\n".join(lines) + "\n")

    def test_session_counted_once_per_active_day(self):
        self.write_session("proj-a", "s1.jsonl", [
            msg(ts="2026-07-10T02:00:00Z"),
            msg(ts="2026-07-10T03:00:00Z"),
            msg(ts="2026-07-11T02:00:00Z"),
        ])
        days = uca.scan_projects(self.projects)
        self.assertEqual(days["2026-07-10"], {"m": 2, "s": 1, "t": 0})
        self.assertEqual(days["2026-07-11"], {"m": 1, "s": 1, "t": 0})

    def test_sessions_sum_across_files(self):
        self.write_session("proj-a", "s1.jsonl", [msg()])
        self.write_session("proj-b", "s2.jsonl", [msg()])
        self.assertEqual(uca.scan_projects(self.projects)["2026-07-11"]["s"], 2)

    def test_subagent_transcripts_excluded(self):
        self.write_session("proj-a", "s1.jsonl", [msg()])
        # subagent files live one level deeper — must not be scanned
        self.write_session("proj-a/s1-dir/subagents", "agent-x.jsonl", [msg(), msg()])
        self.assertEqual(uca.scan_projects(self.projects)["2026-07-11"]["m"], 1)


class LedgerTest(unittest.TestCase):
    def test_upsert_replaces_scanned_days(self):
        ledger = uca.new_ledger()
        ledger["days"]["2026-07-10"] = {"m": 5, "s": 1, "t": 0}
        changed = uca.upsert_days(ledger, {"2026-07-10": {"m": 9, "s": 2, "t": 3}})
        self.assertTrue(changed)
        self.assertEqual(ledger["days"]["2026-07-10"], {"m": 9, "s": 2, "t": 3})

    def test_upsert_identical_scan_reports_no_change(self):
        ledger = uca.new_ledger()
        scanned = {"2026-07-10": {"m": 9, "s": 2, "t": 3}}
        uca.upsert_days(ledger, scanned)
        self.assertFalse(uca.upsert_days(ledger, dict(scanned)))

    def test_upsert_never_touches_seeded_dates(self):
        ledger = uca.new_ledger()
        ledger["seededThrough"] = "2026-06-10"
        ledger["days"]["2026-06-10"] = {"m": 100, "s": 4, "t": 9}
        changed = uca.upsert_days(ledger, {"2026-06-10": {"m": 1, "s": 1, "t": 1}})
        self.assertFalse(changed)
        self.assertEqual(ledger["days"]["2026-06-10"], {"m": 100, "s": 4, "t": 9})

    def test_totals_recomputed_from_days(self):
        ledger = uca.new_ledger()
        ledger["days"] = {
            "2026-07-10": {"m": 5, "s": 1, "t": 2},
            "2026-07-11": {"m": 7, "s": 2, "t": 4},
        }
        uca.recompute_totals(ledger)
        self.assertEqual(ledger["totals"], {
            "sessions": 3, "messages": 12, "toolCalls": 6, "activeDays": 2})
        self.assertEqual(ledger["firstDate"], "2026-07-10")

    def test_write_ledger_roundtrip_preserves_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data" / "claude-activity.json"
            ledger = uca.new_ledger()
            ledger["futureField"] = {"keep": "me"}  # forward-compat contract
            ledger["days"]["2026-07-11"] = {"m": 1, "s": 1, "t": 0}
            uca.write_ledger(path, ledger)
            loaded = uca.load_ledger(path)
            self.assertEqual(loaded["futureField"], {"keep": "me"})
            self.assertEqual(loaded["days"]["2026-07-11"], {"m": 1, "s": 1, "t": 0})
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_load_ledger_missing_file_returns_new_ledger(self):
        self.assertEqual(uca.load_ledger(Path("/nonexistent/x.json")),
                         uca.new_ledger())


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.projects = root / "projects"
        proj = self.projects / "proj-a"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(msg() + "\n")
        self.repo = root / "repo"
        self.repo.mkdir()
        self.ledger_path = self.repo / "data" / "claude-activity.json"

    def run_cli(self, *extra):
        return uca.main(["--no-git", "--repo", str(self.repo),
                         "--projects-dir", str(self.projects), *extra])

    def test_dry_run_writes_nothing(self):
        rc = uca.main(["--dry-run", "--repo", str(self.repo),
                       "--projects-dir", str(self.projects)])
        self.assertEqual(rc, 0)
        self.assertFalse(self.ledger_path.exists())

    def test_normal_run_writes_ledger(self):
        self.assertEqual(self.run_cli(), 0)
        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(ledger["days"]["2026-07-11"], {"m": 1, "s": 1, "t": 0})
        self.assertEqual(ledger["totals"], {
            "sessions": 1, "messages": 1, "toolCalls": 0, "activeDays": 1})
        self.assertEqual(ledger["timezone"], "Asia/Manila")
        self.assertTrue(ledger["generatedAt"].startswith("2026-"))

    def test_second_run_is_a_byte_identical_noop(self):
        self.run_cli()
        first = self.ledger_path.read_text()
        self.run_cli()
        # generatedAt is only restamped when day data changes
        self.assertEqual(self.ledger_path.read_text(), first)

    def test_empty_projects_dir_exits_nonzero_without_writing(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        with self.assertRaises(SystemExit):
            uca.main(["--no-git", "--repo", str(self.repo),
                      "--projects-dir", str(empty)])
        self.assertFalse(self.ledger_path.exists())


class SeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.projects = root / "projects"
        proj = self.projects / "proj-a"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(msg() + "\n")  # oldest transcript day: 2026-07-11
        self.repo = root / "repo"
        self.repo.mkdir()
        self.cache = root / "stats-cache.json"
        self.cache.write_text(json.dumps({
            "version": 4,
            "dailyActivity": [
                {"date": "2026-03-03", "messageCount": 99, "sessionCount": 4, "toolCallCount": 17},
                {"date": "2026-07-10", "messageCount": 500, "sessionCount": 9, "toolCallCount": 60},
                {"date": "2026-07-11", "messageCount": 9999, "sessionCount": 99, "toolCallCount": 999},
            ],
        }))

    def run_seed(self):
        return uca.main(["--seed", "--no-git", "--repo", str(self.repo),
                         "--projects-dir", str(self.projects),
                         "--stats-cache", str(self.cache)])

    def test_seed_imports_history_and_scan_owns_recent_days(self):
        self.assertEqual(self.run_seed(), 0)
        ledger = json.loads((self.repo / "data/claude-activity.json").read_text())
        # boundary = oldest transcript day (2026-07-11) minus one = 2026-07-10
        self.assertEqual(ledger["seededThrough"], "2026-07-10")
        self.assertEqual(ledger["days"]["2026-03-03"], {"m": 99, "s": 4, "t": 17})
        self.assertEqual(ledger["days"]["2026-07-10"], {"m": 500, "s": 9, "t": 60})
        # 2026-07-11 must come from the transcript scan, not the cache entry
        self.assertEqual(ledger["days"]["2026-07-11"], {"m": 1, "s": 1, "t": 0})
        self.assertEqual(ledger["firstDate"], "2026-03-03")
        self.assertEqual(ledger["totals"]["messages"], 99 + 500 + 1)

    def test_seed_refuses_second_run(self):
        self.run_seed()
        with self.assertRaises(SystemExit):
            self.run_seed()


if __name__ == "__main__":
    unittest.main()
