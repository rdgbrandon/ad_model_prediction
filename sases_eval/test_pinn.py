"""Gate for the physics-informed sweep: the hand-written gradient must match
finite differences, and the physics penalty must actually enforce the law.
Run before trusting anything physics_informed_audit.py prints."""
import numpy as np

from pinn import PINN, DU


def _setup(B=3, seed=0):
    rng = np.random.default_rng(seed)
    m = PINN(seed)
    m.shapes = m._shapes(B)
    theta = m._init(B) + 0.1 * rng.normal(size=sum(int(np.prod(s)) for s in m.shapes))
    Xd = rng.normal(size=(20, 1)); Yd = rng.normal(size=(20, B))
    Xc = rng.normal(size=(7, 1)); Xs = Xc + 0.05
    step = rng.normal(size=(1, B)) * 0.1
    return m, theta, (Xd, Yd, Xc, Xs, step)


def test_gradient_matches_finite_differences():
    for w in (0.0, 1.0, 100.0):
        m, theta, args = _setup()
        _, g = m.loss_grad(theta, *args, w)
        eps = 1e-6
        num = np.empty_like(theta)
        for i in range(len(theta)):
            tp, tm = theta.copy(), theta.copy()
            tp[i] += eps; tm[i] -= eps
            num[i] = (m.loss_grad(tp, *args, w)[0] - m.loss_grad(tm, *args, w)[0]) / (2 * eps)
        rel = np.max(np.abs(num - g)) / max(1.0, np.max(np.abs(num)))
        assert rel < 1e-6, (w, rel)


def test_penalty_enforces_the_law():
    """On synthetic data with a different slope beyond the band, a large weight
    must drive the surrogate's own law residual toward zero."""
    rng = np.random.default_rng(1)
    U = np.repeat(np.linspace(2.5, 4.0, 12), 10) + rng.normal(0, .01, 120)
    Y = np.stack([2 * U, -U, 0.5 * U], 1) + rng.normal(0, .05, (120, 3))
    q = np.array([5.0, 1.0, 3.0])                 # deliberately not the data slope
    free = PINN(0).fit(U, Y, q, 0.0, 4.0, 5.5)
    tied = PINN(0).fit(U, Y, q, 1000.0, 4.0, 5.5)
    assert tied.law_residual() < 0.1 * free.law_residual(), (tied.law_residual(), free.law_residual())
    assert tied.law_residual() < 0.05 * np.linalg.norm(q) * DU * 10


if __name__ == '__main__':
    test_gradient_matches_finite_differences()
    test_penalty_enforces_the_law()
    print('pinn gate passed')
