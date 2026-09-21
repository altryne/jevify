"""Boundary checks for preserving partial results without exposing submitted data."""

import unittest
from unittest.mock import Mock, patch

from jev_client import JevClient


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


if __name__ == "__main__":
    unittest.main()
