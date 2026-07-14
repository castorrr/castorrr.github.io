"""Unit tests for scripts/update-claude-activity.py (stdlib only).

Run: python3 scripts/test_update_claude_activity.py -v
"""
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_upsert_skips_partially_pruned_days_before_horizon(self):
        ledger = uca.new_ledger()
        ledger["days"]["2026-06-01"] = {"m": 100, "s": 5, "t": 40}
        changed = uca.upsert_days(
            ledger, {"2026-06-01": {"m": 3, "s": 1, "t": 0}}, horizon="2026-06-16")
        self.assertFalse(changed)
        self.assertEqual(ledger["days"]["2026-06-01"], {"m": 100, "s": 5, "t": 40})

    def test_upsert_applies_days_on_or_after_horizon(self):
        ledger = uca.new_ledger()
        ledger["days"]["2026-06-20"] = {"m": 100, "s": 5, "t": 40}
        changed = uca.upsert_days(
            ledger, {"2026-06-20": {"m": 3, "s": 1, "t": 0}}, horizon="2026-06-16")
        self.assertTrue(changed)
        self.assertEqual(ledger["days"]["2026-06-20"], {"m": 3, "s": 1, "t": 0})

    def test_upsert_preserves_existing_tok(self):
        ledger = uca.new_ledger()
        ledger["days"]["2026-07-10"] = {"m": 5, "s": 1, "t": 0, "tok": 12345}
        changed = uca.upsert_days(ledger, {"2026-07-10": {"m": 9, "s": 2, "t": 3}})
        self.assertTrue(changed)
        self.assertEqual(ledger["days"]["2026-07-10"],
                         {"m": 9, "s": 2, "t": 3, "tok": 12345})

    def test_upsert_identical_scan_with_tok_reports_no_change(self):
        ledger = uca.new_ledger()
        ledger["days"]["2026-07-10"] = {"m": 9, "s": 2, "t": 3, "tok": 12345}
        self.assertFalse(
            uca.upsert_days(ledger, {"2026-07-10": {"m": 9, "s": 2, "t": 3}}))

    def test_totals_recomputed_from_days(self):
        ledger = uca.new_ledger()
        ledger["days"] = {
            "2026-07-10": {"m": 5, "s": 1, "t": 2, "tok": 1500},
            "2026-07-11": {"m": 7, "s": 2, "t": 4},   # no tok — counts as 0
        }
        uca.recompute_totals(ledger)
        self.assertEqual(ledger["totals"], {
            "sessions": 3, "messages": 12, "toolCalls": 6, "activeDays": 2,
            "tokens": 1500})
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


class TokenLoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name) / "stats-cache.json"

    def test_sums_tokens_across_models_per_day(self):
        self.cache.write_text(json.dumps({"dailyModelTokens": [
            {"date": "2026-07-10",
             "tokensByModel": {"claude-opus-4-8": 1500, "claude-sonnet-5": 500}},
            {"date": "2026-07-11", "tokensByModel": {"claude-fable-5": 42}},
        ]}))
        self.assertEqual(uca.load_daily_tokens(self.cache),
                         {"2026-07-10": 2000, "2026-07-11": 42})

    def test_missing_file_returns_empty(self):
        self.assertEqual(uca.load_daily_tokens(self.cache), {})

    def test_malformed_json_returns_empty(self):
        self.cache.write_text("{not json")
        self.assertEqual(uca.load_daily_tokens(self.cache), {})

    def test_non_dict_top_level_returns_empty(self):
        self.cache.write_text("[]")
        self.assertEqual(uca.load_daily_tokens(self.cache), {})

    def test_malformed_entries_and_zero_days_skipped(self):
        self.cache.write_text(json.dumps({"dailyModelTokens": [
            {"tokensByModel": {"claude-opus-4-8": 5}},              # no date
            {"date": "2026-07-09"},                                  # no tokensByModel
            {"date": "2026-07-08", "tokensByModel": {"claude-opus-4-8": 0}},  # zero total
            {"date": "2026-07-10", "tokensByModel": {"claude-opus-4-8": 7}},
        ]}))
        self.assertEqual(uca.load_daily_tokens(self.cache), {"2026-07-10": 7})


class MergeTokensTest(unittest.TestCase):
    def _ledger(self):
        ledger = uca.new_ledger()
        ledger["days"]["2026-07-10"] = {"m": 5, "s": 1, "t": 2}
        return ledger

    def test_merges_into_existing_day(self):
        ledger = self._ledger()
        self.assertTrue(uca.merge_tokens(ledger, {"2026-07-10": 2000}))
        self.assertEqual(ledger["days"]["2026-07-10"],
                         {"m": 5, "s": 1, "t": 2, "tok": 2000})

    def test_token_only_dates_do_not_create_days(self):
        # stats-cache has ~2 token-only dates with no counted messages;
        # creating them would corrupt activeDays semantics
        ledger = self._ledger()
        self.assertFalse(uca.merge_tokens(ledger, {"2026-07-09": 999}))
        self.assertNotIn("2026-07-09", ledger["days"])

    def test_seeded_days_receive_tokens(self):
        # token merge is exempt from the seededThrough guard: the source
        # covers full history and never regresses from pruning
        ledger = self._ledger()
        ledger["seededThrough"] = "2026-07-10"
        self.assertTrue(uca.merge_tokens(ledger, {"2026-07-10": 2000}))
        self.assertEqual(ledger["days"]["2026-07-10"]["tok"], 2000)

    def test_absent_date_preserves_existing_tok(self):
        ledger = self._ledger()
        ledger["days"]["2026-07-10"]["tok"] = 1234
        self.assertFalse(uca.merge_tokens(ledger, {}))
        self.assertEqual(ledger["days"]["2026-07-10"]["tok"], 1234)

    def test_identical_merge_reports_no_change(self):
        ledger = self._ledger()
        uca.merge_tokens(ledger, {"2026-07-10": 2000})
        self.assertFalse(uca.merge_tokens(ledger, {"2026-07-10": 2000}))

    def test_changed_value_updates_tok(self):
        ledger = self._ledger()
        uca.merge_tokens(ledger, {"2026-07-10": 2000})
        self.assertTrue(uca.merge_tokens(ledger, {"2026-07-10": 2500}))
        self.assertEqual(ledger["days"]["2026-07-10"]["tok"], 2500)


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
        self.cache = root / "stats-cache.json"
        self.cache.write_text(json.dumps({"dailyModelTokens": [
            {"date": "2026-07-11",
             "tokensByModel": {"claude-opus-4-8": 1500, "claude-sonnet-5": 500}},
        ]}))

    def run_cli(self, *extra):
        return uca.main(["--no-git", "--repo", str(self.repo),
                         "--projects-dir", str(self.projects),
                         "--stats-cache", str(self.cache), *extra])

    def test_dry_run_writes_nothing(self):
        rc = uca.main(["--dry-run", "--repo", str(self.repo),
                       "--projects-dir", str(self.projects)])
        self.assertEqual(rc, 0)
        self.assertFalse(self.ledger_path.exists())

    def test_normal_run_writes_ledger(self):
        self.assertEqual(self.run_cli(), 0)
        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(ledger["days"]["2026-07-11"],
                         {"m": 1, "s": 1, "t": 0, "tok": 2000})
        self.assertEqual(ledger["totals"], {
            "sessions": 1, "messages": 1, "toolCalls": 0, "activeDays": 1,
            "tokens": 2000})
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

    def test_missing_stats_cache_run_proceeds_without_tokens(self):
        self.cache.unlink()
        self.assertEqual(self.run_cli(), 0)
        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(ledger["days"]["2026-07-11"], {"m": 1, "s": 1, "t": 0})
        self.assertEqual(ledger["totals"]["tokens"], 0)

    def test_missing_stats_cache_preserves_existing_tok(self):
        self.run_cli()                       # writes tok: 2000
        self.cache.unlink()
        self.run_cli()                       # token data must survive
        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(ledger["days"]["2026-07-11"]["tok"], 2000)
        self.assertEqual(ledger["totals"]["tokens"], 2000)

    def test_token_only_change_rewrites_ledger(self):
        self.run_cli()
        first = self.ledger_path.read_text()
        self.cache.write_text(json.dumps({"dailyModelTokens": [
            {"date": "2026-07-11", "tokensByModel": {"claude-opus-4-8": 9999}}]}))
        self.assertEqual(self.run_cli(), 0)
        self.assertNotEqual(self.ledger_path.read_text(), first)
        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(ledger["days"]["2026-07-11"]["tok"], 9999)
        self.assertEqual(ledger["totals"]["tokens"], 9999)


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
            "dailyModelTokens": [
                {"date": "2026-03-03", "tokensByModel": {"claude-sonnet-4-6": 26394}},
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
        self.assertEqual(ledger["days"]["2026-03-03"],
                         {"m": 99, "s": 4, "t": 17, "tok": 26394})
        self.assertEqual(ledger["days"]["2026-07-10"], {"m": 500, "s": 9, "t": 60})
        # 2026-07-11 must come from the transcript scan, not the cache entry
        self.assertEqual(ledger["days"]["2026-07-11"], {"m": 1, "s": 1, "t": 0})
        self.assertEqual(ledger["firstDate"], "2026-03-03")
        self.assertEqual(ledger["totals"]["messages"], 99 + 500 + 1)

    def test_seed_refuses_second_run(self):
        self.run_seed()
        with self.assertRaises(SystemExit):
            self.run_seed()

    def test_seed_run_backfills_tokens_for_seeded_days(self):
        self.run_seed()
        ledger = json.loads((self.repo / "data/claude-activity.json").read_text())
        self.assertEqual(ledger["days"]["2026-03-03"]["tok"], 26394)
        self.assertEqual(ledger["totals"]["tokens"], 26394)


class GitSyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)

        # origin: bare repo with one initial commit on main
        self.origin = root / "origin.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(self.origin)],
                       check=True, capture_output=True)
        seed = root / "seedclone"
        subprocess.run(["git", "clone", str(self.origin), str(seed)],
                       check=True, capture_output=True)
        self._git(seed, "config", "user.email", "test@test")
        self._git(seed, "config", "user.name", "test")
        (seed / "README.md").write_text("init\n")
        self._git(seed, "add", "README.md")
        self._git(seed, "commit", "-m", "init")
        self._git(seed, "push", "origin", "main")

        # the "dedicated clone" the script operates on
        self.clone = root / "clone"
        subprocess.run(["git", "clone", str(self.origin), str(self.clone)],
                       check=True, capture_output=True)
        self._git(self.clone, "config", "user.email", "test@test")
        self._git(self.clone, "config", "user.name", "test")

        self.projects = root / "projects"
        proj = self.projects / "proj-a"
        proj.mkdir(parents=True)
        (proj / "s1.jsonl").write_text(msg() + "\n")

        self.cache = root / "stats-cache.json"
        self.cache.write_text(json.dumps({"dailyModelTokens": [
            {"date": "2026-07-11", "tokensByModel": {"claude-opus-4-8": 500}}]}))

    def _git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def run_cli(self):
        return uca.main(["--repo", str(self.clone),
                         "--projects-dir", str(self.projects),
                         "--stats-cache", str(self.cache)])

    def test_run_commits_and_pushes_when_changed(self):
        self.assertEqual(self.run_cli(), 0)
        subject = self._git(self.origin, "log", "-1", "--format=%s", "main")
        self.assertEqual(subject,
                         "chore: update claude activity through 2026-07-11")

    def test_second_run_adds_no_commit(self):
        self.run_cli()
        self.run_cli()
        self.assertEqual(self._git(self.origin, "rev-list", "--count", "main"),
                         "2")  # init + exactly one update

    def test_stranded_local_commit_pushed_on_next_run(self):
        self.run_cli()
        # simulate a failed push: roll origin back one commit; clone is now ahead
        prev = self._git(self.origin, "rev-parse", "main~1")
        self._git(self.origin, "update-ref", "refs/heads/main", prev)
        self.run_cli()  # scan unchanged -> no new commit, but push-if-ahead fires
        self.assertEqual(self._git(self.origin, "rev-parse", "main"),
                         self._git(self.clone, "rev-parse", "main"))

    def test_run_git_failure_surfaces_stderr(self):
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            with self.assertRaises(subprocess.CalledProcessError):
                uca.run_git(self.clone, "rev-parse", "--verify", "no-such-ref-xyz")
        self.assertIn("fatal", captured.getvalue())

    def test_token_only_change_commits_and_pushes(self):
        self.run_cli()
        self.cache.write_text(json.dumps({"dailyModelTokens": [
            {"date": "2026-07-11", "tokensByModel": {"claude-opus-4-8": 777}}]}))
        self.run_cli()
        # init + first update + token-only update
        self.assertEqual(self._git(self.origin, "rev-list", "--count", "main"),
                         "3")

    def test_run_git_net_retries_then_succeeds(self):
        calls = []

        def flaky(repo, *args):
            calls.append(args)
            if len(calls) < 3:
                raise subprocess.CalledProcessError(1, ["git", *args])
            return "ok"

        with mock.patch.object(uca, "run_git", side_effect=flaky), \
                mock.patch.object(uca.time, "sleep"):
            self.assertEqual(uca.run_git_net(self.clone, "push"), "ok")
        self.assertEqual(len(calls), 3)  # two transient failures, then success

    def test_run_git_net_raises_after_exhausting_retries(self):
        def always_fail(repo, *args):
            raise subprocess.CalledProcessError(1, ["git", *args])

        with mock.patch.object(uca, "run_git", side_effect=always_fail), \
                mock.patch.object(uca.time, "sleep") as slept:
            with self.assertRaises(subprocess.CalledProcessError):
                uca.run_git_net(self.clone, "pull", "--rebase")
        self.assertEqual(slept.call_count, len(uca.NET_RETRY_BACKOFF))

    def test_pull_failure_writes_locally_then_heals_next_run(self):
        # Point origin at a nonexistent repo so pull (and push) fail, as a
        # boot/resume DNS failure would. Empty backoff keeps the test fast.
        broken = str(Path(self.tmp.name) / "gone.git")
        self._git(self.clone, "remote", "set-url", "origin", broken)
        with mock.patch.object(uca, "NET_RETRY_BACKOFF", ()):
            self.assertEqual(self.run_cli(), 0)  # does not abort the run
        # ledger written and committed locally despite the network being down
        self.assertTrue((self.clone / "data" / "claude-activity.json").exists())
        self.assertEqual(self._git(self.clone, "log", "-1", "--format=%s"),
                         "chore: update claude activity through 2026-07-11")
        # nothing reached origin yet (push deferred)
        self.assertEqual(self._git(self.origin, "rev-list", "--count", "main"),
                         "1")
        # heal: with the remote reachable again the stranded commit pushes
        self._git(self.clone, "remote", "set-url", "origin", str(self.origin))
        self.assertEqual(self.run_cli(), 0)
        self.assertEqual(self._git(self.origin, "rev-parse", "main"),
                         self._git(self.clone, "rev-parse", "main"))


if __name__ == "__main__":
    unittest.main()
