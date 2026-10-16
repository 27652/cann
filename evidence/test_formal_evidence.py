"""Offline synthetic cases; never calls the online client."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from evidence.formal_evidence import eligibility, validate


BUNDLE = Path(__file__).parent / 'formal/historical-6ad2872c'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((BUNDLE / 'evidence.json').read_text())
        self.root = BUNDLE / 'source'

    def test_historical_bundle(self):
        self.assertEqual(str(validate(self.record, self.root)), '11.67')

    def test_rejections(self):
        mutations = [
            lambda r: r.pop('submission_id'),
            lambda r: r['score_evidence'].update(submission_id='a' * 24),
            lambda r: r['testcases'].pop(),
            lambda r: r['testcases'][0].update(testcase_status='Fail'),
            lambda r: r['score_evidence'].update(source='client'),
            lambda r: r['score_evidence'].update(value='NaN'),
            lambda r: r['files'].update({'kernel.asc': '0' * 64}),
            lambda r: r.update(contest_id='0' * 24),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                record = copy.deepcopy(self.record)
                mutate(record)
                with self.assertRaises(ValueError):
                    validate(record, self.root)

    def test_decision(self):
        candidate = copy.deepcopy(self.record)
        for score in ('11.67', '1'):
            candidate['score_evidence']['value'] = score
            with self.assertRaises(ValueError):
                eligibility(candidate, self.root, self.record, self.root)
        candidate['submission_id'] = 'b' * 24
        candidate['score_evidence'].update(submission_id='b' * 24, value='12.0')
        self.assertTrue(eligibility(candidate, self.root, self.record, self.root)['eligible'])
        candidate['scoring_context'] = 'other'
        with self.assertRaises(ValueError):
            eligibility(candidate, self.root, self.record, self.root)

    def test_extra_source_file(self):
        import shutil
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            root = Path(tmp) / 'source'
            shutil.copytree(self.root, root)
            (root / 'extra.txt').write_text('synthetic')
            with self.assertRaises(ValueError):
                validate(self.record, root)


if __name__ == '__main__':
    unittest.main()
