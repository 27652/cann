"""Mock-only tests of the CLI used by Fast Track; no real network or waits."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    'rate_limit_cli', Path(__file__).resolve().parents[1] / 'gitlabcann/cannjudge_cli.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class RateLimitTests(unittest.TestCase):
    def test_explicit_wait_then_same_payload(self):
        client = Mock()
        client.request.side_effect = [
            cli.ApiError(429, '提交过于频繁，请在 104 秒后再提交'),
            {'data': {'submissionId': 'accepted'}}]
        payload = {'files': [{'path': 'kernel.asc', 'content': 'frozen'}]}
        with patch.object(cli.time, 'sleep') as sleep:
            self.assertEqual(cli.submit_with_rate_limit_retry(client, payload),
                             {'data': {'submissionId': 'accepted'}})
        sleep.assert_called_once_with(104)
        self.assertEqual(client.request.call_count, 2)
        for call in client.request.call_args_list:
            self.assertIs(call.args[2], payload)

    def test_fail_closed(self):
        errors = [cli.ApiError(429, 'rate limited'),
                  cli.ApiError(401, 'retry after 10 seconds'),
                  cli.ApiError(503, 'retry after 10 seconds'),
                  cli.ApiError(429, 'retry after 10 seconds',
                               {'data': {'submissionId': 'possibly-accepted'}}),
                  RuntimeError('network timeout')]
        for error in errors:
            with self.subTest(error=str(error)):
                client = Mock(); client.request.side_effect = error
                with patch.object(cli.time, 'sleep') as sleep:
                    with self.assertRaises(type(error)):
                        cli.submit_with_rate_limit_retry(client, {})
                sleep.assert_not_called()
                self.assertEqual(client.request.call_count, 1)

    def test_bounded_retries(self):
        client = Mock(); client.request.side_effect = cli.ApiError(429, 'retry after 8 seconds')
        with patch.object(cli.time, 'sleep') as sleep:
            with self.assertRaises(cli.ApiError):
                cli.submit_with_rate_limit_retry(client, {})
        self.assertEqual(client.request.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [8, 8])

    def test_interrupted_wait_never_reposts(self):
        client = Mock(); client.request.side_effect = cli.ApiError(429, 'retry after 1 seconds')
        with patch.object(cli.time, 'sleep', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                cli.submit_with_rate_limit_retry(client, {})
        self.assertEqual(client.request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
