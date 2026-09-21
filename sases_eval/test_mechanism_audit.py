import unittest
import numpy as np
from mechanism_audit import geometry, hidden_excursion


class MechanismTests(unittest.TestCase):
    def test_margin_decomposition_with_cancellation(self):
        g=geometry(np.array([3.,0.]),np.array([-2.,0.]),1.)
        self.assertEqual(g['growth_slack'],-1.)
        self.assertEqual(g['cancellation'],4.)
        self.assertEqual(g['margin'],3.)
        self.assertAlmostEqual(g['margin'],g['growth_slack']+g['cancellation'])

    def test_endpoint_pass_does_not_imply_continuous_bound(self):
        r=hidden_excursion()
        self.assertTrue(r['endpoint_covered'])
        self.assertAlmostEqual(r['max_interior_excess'],2.)
        self.assertAlmostEqual(hidden_excursion(0)['max_interior_excess'],0.)

    def test_vector_identity_and_triangle_slack(self):
        rng=np.random.default_rng(6)
        for _ in range(100):
            r0,inc=rng.normal(size=(2,12))
            g=geometry(r0,inc,2.)
            self.assertGreaterEqual(g['cancellation'],-1e-12)
            self.assertAlmostEqual(g['margin'],g['growth_slack']+g['cancellation'])


if __name__=='__main__':
    unittest.main()
