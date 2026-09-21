import unittest
import numpy as np
from theory_audit import theory_parameters, allowance, score, summarize, binomial_reference


class TheoryAuditTests(unittest.TestCase):
    def test_boundary_is_necessary_for_affine_truth(self):
        # Exact KZ slope, nonzero residual at ceiling; origin-only fails there.
        q = np.array([2., 3.])
        ya, y0, shift = np.array([2., 1.]), np.zeros(2), np.zeros(2)
        fit = theory_parameters(q, ya, y0, shift)
        self.assertGreater(fit['boundary'], 0)
        for d in (0., .1, 1., 3.):
            residual = ya + (q-.5)*d
            self.assertLessEqual(np.linalg.norm(residual),
                                 allowance('theory_boundary', d, 0, fit) + 1e-12)
        self.assertEqual(allowance('theory_slope', 0, 0, fit), 0)

    def test_trial_grouping_does_not_count_seed_repeats(self):
        row = dict(trial='t', S=2., e=3., covered=True, valid=True,
                   margin=1., anchor_covered=True)
        s = summarize([row]*100)
        self.assertEqual(s['unique_test_trials'], 1)
        self.assertAlmostEqual(s['cp95_lower_nominal'], .05)
        self.assertAlmostEqual(binomial_reference(3, 3), .05**(1/3))

    def test_abstention_is_not_a_valid_zero_score(self):
        self.assertIsNone(score(10, 1, float('nan')))
        s = summarize([dict(trial='t', S=None)])
        self.assertEqual(s['scored'], 0)
        self.assertIsNone(s['pooled_validity'])

    def test_triangle_bound_and_exact_law_blind_spot(self):
        rng = np.random.default_rng(27)
        for _ in range(100):
            ya, yt, fa, ft, shift = rng.normal(size=(5, 12))
            b, bt = np.linalg.norm(fa-ya), np.linalg.norm(ya-yt-shift)
            S = score(np.linalg.norm(fa-ft-shift), b, bt)
            self.assertLessEqual(S, np.linalg.norm(ft-yt) + 1e-12)
            self.assertEqual(score(np.linalg.norm(fa-(fa-shift)-shift), b, bt), 0)
            # Exact surrogate must be silent whenever the law allowance holds.
            self.assertEqual(score(bt, 0, bt), 0)

    def test_test_labels_cannot_change_calibration_fit(self):
        # Exercise the actual fitting path, not just the pure helper.
        from piecewise import NAMES, TP, TM, TRAIN, ANCHOR, slopes, lp
        from honest_beta import law_from
        from setupc import kappa_defensible
        lc = [n for n in NAMES if 106 <= TP[n] <= 192]
        ts = [n for n in NAMES if TP[n] > 192]
        def fit():
            c, c0, _, _ = law_from(lc)
            top = max(lc, key=lambda n: TP[n])
            return (theory_parameters(slopes(lc), TM[ANCHOR], TM[top], c(lp[ANCHOR], lp[top])+c0),
                    kappa_defensible(lc, ANCHOR))
        before = fit()
        saved = {n: TM[n].copy() for n in ts}
        try:
            for n in ts:
                TM[n] = np.full_like(TM[n], 1e9)
            self.assertEqual(before, fit())
        finally:
            TM.update(saved)


if __name__ == '__main__':
    unittest.main()
