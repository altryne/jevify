"""Boundary checks for preserving partial results without exposing submitted data."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jev_client import JevClient, load_key


class ClientTests(unittest.TestCase):
    def test_bad_response_does_not_abort_other_requests_or_expose_body(self):
        client = JevClient(api_key="synthetic-key", retries=0, requests_per_minute=0)
        bodies = [{"state": "synthetic", "questions": {"q": {"type": "noul", "instructions": "Relevant?"}}}] * 3
        responses = []
        for status, body in [(200, b'not JSON PRIVATE_SOURCE'), (400, b'PRIVATE_SOURCE'),
                             (200, b'{"answers":{"q":{"type":"noul","noul":0.8}}}')]:
            response = Mock(status=status)
            response.read.return_value = body
            responses.append(response)
        connection = Mock()
        connection.getresponse.side_effect = responses
        with patch.object(client, "_connection", return_value=connection):
            results = client.ask_many(bodies, concurrency=1)
        self.assertIn("error", results[0])
        self.assertEqual(results[1]["status"], 400)
        self.assertEqual(results[2]["answers"]["q"]["noul"], 0.8)
        self.assertNotIn("PRIVATE_SOURCE", str(results))

    def test_partial_answers_are_flagged_and_not_cached(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            client = JevClient(api_key="synthetic-key", retries=0, requests_per_minute=0, cache_dir=cache_dir)
            questions = {"q1": {"type": "noul", "instructions": "A?"}, "q2": {"type": "noul", "instructions": "B?"}}
            response = Mock(status=200)
            response.read.return_value = b'{"answers":{"q1":{"type":"noul","noul":0.9}}}'
            connection = Mock()
            connection.getresponse.return_value = response
            with patch.object(client, "_connection", return_value=connection):
                first = client.ask("synthetic", questions)
                second = client.ask("synthetic", questions)
            self.assertEqual(first["missing"], ["q2"])
            self.assertEqual(first["answers"]["q1"]["noul"], 0.9)
            self.assertNotIn("cached", second)
            self.assertEqual(connection.request.call_count, 2)
            self.assertEqual(list(Path(cache_dir).iterdir()), [])

    def test_unreadable_cache_entry_is_a_miss(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            client = JevClient(api_key="synthetic-key", retries=0, requests_per_minute=0, cache_dir=cache_dir)
            questions = {"q": {"type": "noul", "instructions": "A?"}}
            response = Mock(status=200)
            response.read.return_value = b'{"answers":{"q":{"type":"noul","noul":0.7}}}'
            connection = Mock()
            connection.getresponse.return_value = response
            with patch.object(client, "_connection", return_value=connection):
                client.ask("synthetic", questions)
                (entry,) = Path(cache_dir).iterdir()
                entry.write_text("")
                result = client.ask("synthetic", questions)
                again = client.ask("synthetic", questions)
            self.assertEqual(result["answers"]["q"]["noul"], 0.7)
            self.assertTrue(again["cached"])
            self.assertEqual([p.name for p in Path(cache_dir).iterdir()], [entry.name])

    def test_empty_quoted_key_falls_through_to_next_env_file(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            empty, real = Path(folder, "empty.env"), Path(folder, "real.env")
            empty.write_text("TYPESAFE_API_KEY=''\n")
            real.write_text('TYPESAFE_API_KEY="synthetic-key"\n')
            self.assertEqual(load_key((empty, real)), "synthetic-key")


if __name__ == "__main__":
    unittest.main()
