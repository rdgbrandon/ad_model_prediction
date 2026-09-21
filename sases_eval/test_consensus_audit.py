import json
import unittest
from pathlib import Path
import numpy as np
from consensus_audit import combine, weighted_bound

HERE = Path(__file__).resolve().parent


class WeightedBallTests(unittest.TestCase):
    def test_weighted_ball_contains_every_common_point(self):
        # If a point lies in all the balls, it lies in the implied weighted ball,
        # so the reported distance is a genuine lower bound on its distance.
        rng = np.random.default_rng(7)
        for _ in range(300):
            n = int(rng.integers(2, 6))
            centres = rng.normal(size=(n, 12))
            radii = rng.uniform(.5, 3, size=n)
            target = centres[0] + rng.normal(size=12) * 1e-3
            if not np.all(np.linalg.norm(centres - target, axis=1) <= radii):
                continue
            pred = rng.normal(size=12) * 4
            w = rng.dirichlet(np.ones(n))
            value, _ = weighted_bound(pred, centres, radii, w)
            if value is not None:
                self.assertLessEqual(value, np.linalg.norm(pred - target) + 1e-9)

    def test_combine_never_falls_below_any_single_ball(self):
        rng = np.random.default_rng(11)
        for _ in range(60):
            n = int(rng.integers(2, 6))
            centres = rng.normal(size=(n, 12))
            radii = rng.uniform(.5, 3, size=n)
            pred = rng.normal(size=12) * 3
            best, _, single = combine(pred, centres, radii)
            singles = np.maximum(np.linalg.norm(centres - pred, axis=1) - radii, 0)
            self.assertGreaterEqual(best + 1e-9, single)
            self.assertGreaterEqual(best + 1e-9, singles.max())

    def test_inconsistent_balls_abstain(self):
        # Disjoint balls cannot share a point; the construction must not invent one.
        centres = np.array([np.zeros(12), np.full(12, 10.)])
        value, _ = weighted_bound(np.ones(12), centres, np.array([.1, .1]), [.5, .5])
        self.assertIsNone(value)

    def test_zero_weights_are_rejected(self):
        with self.assertRaises(ValueError):
            weighted_bound(np.zeros(3), np.zeros((2, 3)), np.ones(2), [0, 0])


class PublishedResultTests(unittest.TestCase):
    """Guards on the saved audit that the write-up and the website quote."""

    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((HERE / 'consensus/results.json').read_text())

    def test_score_never_below_the_single_rule_baseline(self):
        for row in self.result['rows']:
            self.assertGreaterEqual(row['S'], row['baseline_S'] - 1e-8)

    def test_covered_rows_are_valid_lower_bounds(self):
        for row in self.result['rows']:
            if row['covered']:
                self.assertLessEqual(row['S'], row['e'] + 1e-8)

    def test_premise_is_audited_against_every_ball(self):
        for row in self.result['rows']:
            residuals = np.array(row['all_ball_residuals'])
            radii = np.array(row['all_ball_radii'])
            self.assertEqual(row['covered'], bool(np.all(residuals <= radii + 1e-9)))
            self.assertEqual(len(residuals), row['ball_count'])

    def test_three_calibration_trials_leave_no_choice(self):
        # canonical_146 has one eligible subset, so its "gain" is structural.
        for row in self.result['rows']:
            if row['config'] == 'canonical_146':
                self.assertEqual(row['ball_count'], 1)
                self.assertAlmostEqual(row['S'], row['baseline_S'], places=8)


if __name__ == '__main__':
    unittest.main()
