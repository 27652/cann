"""Lightweight fail-closed checks against the explicitly selected toolkit."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from audit import audit


@unittest.skipUnless(os.environ.get('AUDIT_TOOLKIT'), 'Set AUDIT_TOOLKIT explicitly')
class AuditTests(unittest.TestCase):
    def setUp(self):
        self.toolkit = Path(os.environ['AUDIT_TOOLKIT']).resolve()

    def test_installed_sources_and_current_baseline(self):
        result = audit(self.toolkit)
        self.assertFalse(result['direct_l0c_to_ub_supported_by_installed_matmul'])
        self.assertEqual(len(result['baseline_times']), 15)
        self.assertEqual(len({c['testcase_id'] for c in result['baseline_times']}), 15)
        self.assertAlmostEqual(result['baseline_times'][10]['time_over_best'],
                               327.58 / 52.73)

    def test_reject_transport_change(self):
        original = Path.read_text

        def changed(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.name == 'matmul_client.h':
                return text.replace('client->AllocUB(size, kfcMsg_.ubAddr)',
                                    'different_transport(size)')
            return text

        with patch.object(Path, 'read_text', changed):
            with self.assertRaisesRegex(ValueError, 'Toolkit implementation changed'):
                audit(self.toolkit)

    def test_reject_capability_change(self):
        original = Path.read_text

        def changed(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.name == 'matmul_chip_cap.h':
                start = text.index('/*220*/')
                end = text.index('/*300*/', start)
                row = text[start:end]
                # Flip the final boolean before the trailing true,false pair:
                # this is the named ifSupportL0CToUB field for this fingerprint.
                updated = row.replace('false, false, false,\n          true, false',
                                      'false, false, true,\n          true, false')
                self.assertNotEqual(row, updated)
                return text[:start] + updated + text[end:]
            return text

        with patch.object(Path, 'read_text', changed):
            with self.assertRaises(AssertionError):
                audit(self.toolkit)


if __name__ == '__main__':
    unittest.main()
