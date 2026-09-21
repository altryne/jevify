"""Offline behavior checks. No credentials or network required."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scan


class ScanTests(unittest.TestCase):
    def test_windows_cover_source_and_keep_exact_offsets(self):
        text = "First paragraph.\n" + "word α " * 50 + "\nAn exception at the boundary.\n" + "more " * 50
        parts = list(scan.windows(text, 100, 20))
        covered = set()
        for start, end, part in parts:
            self.assertEqual(part, text[start:end])
            covered.update(range(start, end))
        self.assertEqual(covered, set(range(len(text))))
        self.assertTrue(all(right[0] < left[1] for left, right in zip(parts, parts[1:])))

    def test_jsonl_locations_resolve_long_records_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            records = [{"id": "duplicate", "role": "user", "conversation_id": "c1", "text": "Unicode αβ " * 30},
                       {"id": "duplicate", "text": "A different record"}]
            path.write_text("\n".join(json.dumps(item) for item in records))
            units, digest = scan.load_units(path, 80, 10)
            self.assertEqual(len(digest), 64)
            self.assertEqual(len({unit["id"] for unit in units}), len(units))
            self.assertEqual(units[0]["metadata"], {"id": "duplicate", "role": "user", "conversation_id": "c1"})
            body = scan.request_for(units[:1], "query", scan.DEFAULT_MODEL)
            self.assertEqual(body["state"]["items"][0]["role"], "user")
            for unit in units:
                loc = unit["source"]
                self.assertEqual(unit["text"], records[loc["line"] - 1]["text"][loc["char_start"]:loc["char_end"]])

    def test_batches_cover_every_unit_with_complete_question_targets(self):
        units = [{"id": f"u{i}", "text": "data " * 800} for i in range(30)]
        bodies = scan.batch_requests(units, "Which items describe a failure?", scan.DEFAULT_MODEL)
        self.assertEqual([uid for body in bodies for uid in body["questions"]], [u["id"] for u in units])
        self.assertGreater(len(bodies), 1)
        for body in bodies:
            self.assertLessEqual(scan.request_size(body), scan.REQUEST_BYTES)
            self.assertEqual(len(body["questions"]), len(body["state"]["items"]))
            for index, q in enumerate(body["questions"].values()):
                self.assertIn(f"items[{index}].text", q["instructions"]["question"])

    def test_partial_failures_are_unjudged_while_zero_is_a_judgment(self):
        units = [{"id": f"u{i}", "text": "evidence", "source": {"char_start": i}} for i in range(5)]
        bodies = scan.batch_requests(units, "query", scan.DEFAULT_MODEL, batch_size=2)
        responses = [
            {"answers": {"u0": {"type": "score", "score": 0}, "u1": {"type": "score", "score": 2}},
             "usage": {"input_tokens": 20}, "model": scan.DEFAULT_MODEL},
            {"error": "provider response containing private material"},
            {"answers": {"u4": {"type": "score", "score": float("nan")}}},
        ]
        rows, usage = scan.collect(units, bodies, responses)
        self.assertEqual([row["status"] for row in rows], ["judged", "judged", "unjudged", "unjudged", "unjudged"])
        self.assertEqual(usage["requests_without_usage"], 2)
        self.assertEqual(usage["returned_input_tokens"], 20)
        selected = scan.shortlist(rows, units, top=2, excerpt_chars=3)
        self.assertEqual([row["id"] for row in selected], ["u1", "u0"])
        self.assertTrue(all(row["excerpt_truncated"] for row in selected))
        self.assertNotIn("private material", json.dumps(rows))


    def test_audit_includes_low_and_uncertain_without_repeating_shortlist(self):
        units = [{"id": f"u{i}", "text": "evidence", "source": {}} for i in range(5)]
        rows = [{**unit, "status": "judged", "answer": {"score": score, "confidence": confidence}}
                for unit, score, confidence in zip(units, [3, 0, 2, 1, 2.5], [0.9, 0.9, 0.1, 0.8, None])]
        selected = scan.shortlist(rows, units, 1, 10)
        samples = scan.audit_samples(rows, units, selected, 1, 10)
        self.assertEqual(samples["low_ranked"][0]["id"], "u1")
        self.assertEqual(samples["least_certain"][0]["id"], "u2")

    def test_dry_run_never_initializes_client_or_prints_corpus(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.txt"
            path.write_text("SOURCE_MARKER " * 1000)
            output = io.StringIO()
            with patch.object(sys, "argv", ["scan.py", str(path), "--query", "query", "--dry-run"]), \
                    patch.object(scan, "JevClient", side_effect=AssertionError("Must not load a key or call API")), \
                    contextlib.redirect_stdout(output):
                scan.main()
            result = json.loads(output.getvalue())
            self.assertTrue(result["dry_run"])
            self.assertGreater(result["units"], 1)
            self.assertNotIn("SOURCE_MARKER", output.getvalue())

    def test_live_path_saves_all_locations_but_prints_only_shortlist(self):
        with tempfile.TemporaryDirectory() as directory:
            source, report = Path(directory) / "records.jsonl", Path(directory) / "report.json"
            source.write_text("\n".join(json.dumps({"text": f"record {i} " + "evidence " * 100}) for i in range(20)))

            def fake_answers(bodies, concurrency):
                return [{"model": scan.DEFAULT_MODEL, "usage": {"input_tokens": 50}, "answers": {
                    uid: {"type": "score", "score": 2, "confidence": 0.8} for uid in body["questions"]
                }} for body in bodies]

            stdout = io.StringIO()
            argv = ["scan.py", str(source), "--query", "query", "--output", str(report),
                    "--top", "2", "--excerpt-chars", "20"]
            with patch.object(sys, "argv", argv), patch.object(scan, "JevClient") as client, \
                    contextlib.redirect_stdout(stdout):
                client.return_value.ask_many.side_effect = fake_answers
                scan.main()
            summary, saved = json.loads(stdout.getvalue()), json.loads(report.read_text())
            self.assertEqual(len(saved["results"]), 20)
            self.assertEqual(len(summary["selected"]), 2)
            self.assertEqual(summary["judged_not_shown"], 14)
            audit = summary["audit_samples"]
            self.assertEqual(len(audit["low_ranked"]), 2)
            self.assertEqual(len(audit["least_certain"]), 2)
            self.assertEqual(summary["unjudged"], 0)
            self.assertTrue(all(len(row["excerpt"]) <= 20 for row in summary["selected"]))
            self.assertEqual(saved["input"], str(source.resolve()))
            before = report.read_bytes()
            with patch.object(sys, "argv", argv), patch.object(scan, "JevClient") as client, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                scan.main()
            client.assert_not_called()
            self.assertEqual(report.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
