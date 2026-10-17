import copy
import unittest
from compare_official_times import compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {'submission_id': 'a', 'contest_id': 'c', 'problem_id': 'p',
                         'status': 'Pass', 'testcases': [
                             {'testcase_id': str(i), 'testcase_status': 'Pass', 'time': 10}
                             for i in range(15)]}
        self.candidate = copy.deepcopy(self.baseline)
        self.candidate['submission_id'] = 'b'

    def test_reorder_and_delta(self):
        self.candidate['testcases'].reverse()
        self.candidate['testcases'][0]['time'] = 12
        r = compare(self.baseline, self.candidate)
        self.assertEqual(r['slower_cases'], 1)
        self.assertEqual(r['testcases'][14]['delta_time'], 2)
        self.assertAlmostEqual(r['testcases'][14]['relative_change_percent'], 20)

    def test_bad_context(self):
        self.candidate['problem_id'] = 'other'
        with self.assertRaises(ValueError):
            compare(self.baseline, self.candidate)

    def test_bad_cases(self):
        for mode in ('duplicate', 'missing', 'nan', 'zero', 'wrong_answer', 'different_id'):
            with self.subTest(mode=mode):
                r = copy.deepcopy(self.candidate)
                if mode == 'duplicate': r['testcases'][0] = r['testcases'][1]
                if mode == 'missing': r['testcases'].pop()
                if mode == 'nan': r['testcases'][0]['time'] = float('nan')
                if mode == 'zero': r['testcases'][0]['time'] = 0
                if mode == 'wrong_answer': r['testcases'][0]['testcase_status'] = 'Wrong Answer'
                if mode == 'different_id': r['testcases'][0]['testcase_id'] = 'other'
                with self.assertRaises(ValueError):
                    compare(self.baseline, r)


if __name__ == '__main__':
    unittest.main()
