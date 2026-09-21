import unittest
import numpy as np
from ceiling_audit import certificate


class CeilingTests(unittest.TestCase):
    def test_reverse_triangle_for_targets_inside_ball(self):
        rng=np.random.default_rng(219)
        for _ in range(200):
            y,q,p=rng.normal(size=(3,12));d=float(rng.uniform(.1,2));k=3.
            centre,r,S=certificate(p,y,q,d,k)
            offset=rng.normal(size=12);offset*=r*rng.uniform(0,1)/np.linalg.norm(offset)
            self.assertLessEqual(S,np.linalg.norm(p-centre-offset)+1e-10)

    def test_boundary_exactness(self):
        _,r,S=certificate(np.ones(12),np.zeros(12),np.ones(12)*100,0,5)
        self.assertEqual(r,0);self.assertAlmostEqual(S,np.sqrt(12))

    def test_ceiling_bound_dominates_exact_labelled_anchor_bound(self):
        rng=np.random.default_rng(12)
        for _ in range(200):
            top,anchor,fa,ft,q,shift0=rng.normal(size=(6,12))
            d=.6;k=2.
            _,radius,new=certificate(ft,top,q,d,k)
            boundary=np.linalg.norm(anchor-top-shift0)
            b=np.linalg.norm(fa-anchor)
            shift=shift0-q*d
            old=max(np.linalg.norm(fa-ft-shift)-b-boundary-radius,0.)
            self.assertGreaterEqual(new+1e-10,old)

    def test_truth_is_not_a_scoring_input(self):
        # Pure scoring function accepts calibration label, prediction and law only.
        import inspect
        self.assertEqual(list(inspect.signature(certificate).parameters),
                         ['prediction','ceiling_label','slope','delta','rate'])
        with self.assertRaises(ValueError):certificate(np.zeros(2),np.zeros(2),np.zeros(2),-1,1)


if __name__=='__main__':unittest.main()
