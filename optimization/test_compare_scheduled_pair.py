import copy
import unittest

from compare_scheduled_pair import COMMON, compare


class PairTests(unittest.TestCase):
    def setUp(self):
        fp = {key: 'shared' for key in COMMON}
        fp.update(source_sha256='source', binary_sha256='binary')
        self.result = dict(fingerprint=fp, binary_sha256='binary',
                           int32_mismatches=0, int32_scale_ok=True,
                           task_cycles=100, total_ticks=110)
        self.task = dict(task_id='task', status='passed', returncode=0,
                         metadata=dict(source_sha256='source', binary_sha256='binary'), env={})

    def test_valid_and_delta(self):
        candidate = copy.deepcopy(self.result)
        candidate['task_cycles'] = 80
        out = compare([self.task, self.task], [self.result, candidate])
        self.assertTrue(out['valid_pair'])
        self.assertEqual(out['delta']['task_cycles']['absolute'], -20)

    def test_rejects_failed_pending_and_mismatch(self):
        for key, value in [('status', 'running'), ('returncode', 1)]:
            bad = dict(self.task, **{key: value})
            with self.assertRaises(ValueError):
                compare([self.task, bad], [self.result, self.result])
        for key, value in [('int32_mismatches', 1), ('int32_scale_ok', False),
                           ('task_cycles', 0), ('total_ticks', float('nan'))]:
            bad = dict(self.result, **{key: value})
            with self.assertRaises(ValueError):
                compare([self.task, self.task], [self.result, bad])

    def test_rejects_identity_and_environment(self):
        for key in (*COMMON, 'source_sha256', 'binary_sha256'):
            bad = copy.deepcopy(self.result)
            bad['fingerprint'][key] = 'changed'
            with self.assertRaises(ValueError):
                compare([self.task, self.task], [self.result, bad])
        with self.assertRaises(ValueError):
            compare([self.task, dict(self.task, env={'X': 'Y'})], [self.result, self.result])


if __name__ == '__main__':
    unittest.main()
