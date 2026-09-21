import json
import unittest
from pathlib import Path

import numpy as np

from external_audit import certificate, cp_lower, drift_slope

HERE = Path(__file__).resolve().parent


class CertificateTests(unittest.TestCase):
    def test_reverse_triangle_holds_for_targets_inside_the_ball(self):
        rng = np.random.default_rng(5)
        for _ in range(300):
            y, q, pred = rng.normal(size=(3, 9))
            delta, rate = float(rng.uniform(0, 2)), float(rng.uniform(0, 4))
            centre, radius, S = certificate(pred, y, q, delta, rate)
            off = rng.normal(size=9)
            truth = centre + off * radius * rng.uniform(0, 1) / np.linalg.norm(off)
            self.assertLessEqual(S, np.linalg.norm(pred - truth) + 1e-9)

    def test_negative_inputs_rejected(self):
        with self.assertRaises(ValueError):
            certificate(np.zeros(3), np.zeros(3), np.zeros(3), -1.0, 1.0)
        with self.assertRaises(ValueError):
            certificate(np.zeros(3), np.zeros(3), np.zeros(3), 1.0, -1.0)

    def test_drift_slope_recovers_an_exact_log_law(self):
        control = np.geomspace(1, 50, 9)
        q = np.array([0.3, -1.2, 2.0])
        targets = 4.0 + np.outer(np.log(control), q)
        np.testing.assert_allclose(drift_slope(control, targets), q, atol=1e-9)

    def test_constant_control_is_rejected(self):
        with self.assertRaises(ValueError):
            drift_slope(np.ones(4), np.zeros((4, 2)))

    def test_cp_lower_is_finite_at_both_extremes(self):
        # beta.ppf returns nan at a=0; zero successes must give a 0.0 bound.
        self.assertEqual(cp_lower(0, 7), 0.0)
        self.assertEqual(cp_lower(5, 0), 0.0)
        self.assertTrue(0 < cp_lower(7, 7) < 1)
        self.assertTrue(0 < cp_lower(5, 7) < 1)


class PublishedResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = HERE / 'external/results.json'
        if not path.exists():
            raise unittest.SkipTest('run external_audit.py first')
        cls.result = json.loads(path.read_text())

    def test_every_covered_row_is_a_valid_lower_bound(self):
        for r in self.result['rows']:
            for cov, s in (('covered', 'S'), ('covered_b', 'S_b'), ('covered_c', 'S_c')):
                if r[cov]:
                    self.assertLessEqual(r[s], r['e'] + 1e-8)

    def test_the_boundary_term_only_widens_the_ball(self):
        for r in self.result['rows']:
            self.assertGreaterEqual(r['radius_b'], r['radius'] - 1e-12)
            self.assertLessEqual(r['S_b'], r['S'] + 1e-12)
            if r['covered']:
                self.assertTrue(r['covered_b'])

    def test_original_capillary_split_still_covers_completely(self):
        """The earlier 78/78 result must survive; only new splits may fail."""
        rows = [r for r in self.result['rows']
                if r['dataset'] == 'capillary_psdt'
                and r['ceiling_control'] in (146.0, 192.0)
                and r['test_control'] >= 250.0]
        self.assertTrue(rows)
        self.assertTrue(all(r['covered_c'] for r in rows))

    def test_coverage_is_not_claimed_to_be_perfect_overall(self):
        # Guards the write-up: if a change ever makes everything cover again,
        # that is a bug in the audit, not a discovery.
        pooled = self.result['summary']['ALL_MEASURED']
        self.assertLess(pooled['pooled_coverage_c'], 1.0)
        self.assertGreaterEqual(pooled['distinct_cases'], 20)


if __name__ == '__main__':
    unittest.main()
