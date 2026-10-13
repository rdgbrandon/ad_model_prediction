"""Gate for kan.py: the hand-written gradient must match finite differences, the
B-spline basis must be a partition of unity with the right derivative, and the
network must actually fit a smooth nonlinear function. Run before trusting any
learned allowance that uses the KAN."""
import numpy as np

from kan import KAN, Basis


def test_basis_partition_of_unity_and_derivative():
    b = Basis(G=5, k=3, lo=-2.5, hi=2.5)
    x = np.linspace(-2.49, 2.49, 400)
    B, dB = b(x)
    assert np.allclose(B.sum(1), 1.0, atol=1e-12)
    eps = 1e-6
    num = (b(x + eps)[0] - b(x - eps)[0]) / (2 * eps)
    assert np.max(np.abs(num - dB)) < 1e-5


def test_gradient_matches_finite_differences():
    rng = np.random.default_rng(0)
    for widths in ((3, 4, 1), (2, 1)):
        m = KAN(widths, ridge=1e-2, smooth=1e-1, seed=1)
        th = m._init() + 0.1 * rng.normal(size=sum(int(np.prod(s)) for s in m._shapes()))
        X = rng.normal(size=(25, widths[0])); y = rng.normal(size=25)
        _, g = m.loss_grad(th, X, y)
        num = np.empty_like(th); eps = 1e-6
        for i in range(len(th)):
            tp, tm = th.copy(), th.copy(); tp[i] += eps; tm[i] -= eps
            num[i] = (m.loss_grad(tp, X, y)[0] - m.loss_grad(tm, X, y)[0]) / (2 * eps)
        rel = np.max(np.abs(num - g)) / max(1.0, np.max(np.abs(num)))
        assert rel < 1e-6, rel


def test_fits_a_nonlinear_function():
    rng = np.random.default_rng(2)
    X = rng.uniform(-2, 2, size=(300, 2))
    y = np.sin(2 * X[:, 0]) + 0.5 * X[:, 1] ** 2
    m = KAN((2, 4, 1), steps=2000, seed=0).fit(X, y)
    resid = np.mean((m.predict(X) - y) ** 2) / np.var(y)
    assert resid < 0.05, resid


if __name__ == '__main__':
    test_basis_partition_of_unity_and_derivative()
    test_gradient_matches_finite_differences()
    test_fits_a_nonlinear_function()
    print('test_kan: all passed')
