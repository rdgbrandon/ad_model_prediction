"""A small Kolmogorov-Arnold network in numpy (no torch in this venv).

Each edge carries a learnable univariate function
    phi(x) = a * silu(x) + sum_k c_k B_k(x),
with B_k cubic B-splines on a uniform grid over [lo, hi]; a node sums its incoming
edges plus a bias (Liu et al. 2024, "KAN: Kolmogorov-Arnold Networks"). Trained by
full-batch Adam on mean squared error plus a ridge penalty on (a, c) and a
second-difference penalty on c that keeps each phi smooth. The hand-written
gradient is checked against finite differences by test_kan.py.
"""
import numpy as np


def silu(x):
    return x / (1.0 + np.exp(-x))


def dsilu(x):
    s = 1.0 / (1.0 + np.exp(-x))
    return s * (1.0 + x * (1.0 - s))


class Basis:
    """Uniform-knot B-splines of order k with G intervals on [lo, hi]."""

    def __init__(self, G=5, k=3, lo=-2.5, hi=2.5):
        self.k, self.h = k, (hi - lo) / G
        self.t = lo + self.h * np.arange(-k, G + k + 1)
        self.n = G + k

    def _order(self, x, p):
        t = self.t
        B = ((x[:, None] >= t[None, :-1]) & (x[:, None] < t[None, 1:])).astype(float)
        for q in range(1, p + 1):
            left = (x[:, None] - t[None, :-q - 1]) / (q * self.h) * B[:, :-1]
            right = (t[None, q + 1:] - x[:, None]) / (q * self.h) * B[:, 1:]
            B = left + right
        return B

    def __call__(self, x):
        """Values (N, n) and derivatives (N, n) at x (N,)."""
        Bk1 = self._order(x, self.k - 1)                 # (N, n + 1)
        B = self._order(x, self.k)                       # (N, n)
        dB = (Bk1[:, :-1] - Bk1[:, 1:]) / self.h
        return B, dB


class KAN:
    def __init__(self, widths, G=5, k=3, lo=-2.5, hi=2.5, ridge=1e-3, smooth=1e-2,
                 steps=3000, lr=1e-2, seed=0):
        self.widths, self.basis = list(widths), Basis(G, k, lo, hi)
        self.ridge, self.smooth, self.steps, self.lr, self.seed = ridge, smooth, steps, lr, seed

    # ---- parameters as one flat vector
    def _shapes(self):
        out = []
        for n_in, n_out in zip(self.widths[:-1], self.widths[1:]):
            out += [(n_in, n_out), (n_in, n_out, self.basis.n), (n_out,)]
        return out

    def _unpack(self, theta):
        parts, i = [], 0
        for s in self._shapes():
            n = int(np.prod(s))
            parts.append(theta[i:i + n].reshape(s)); i += n
        return [parts[j:j + 3] for j in range(0, len(parts), 3)]

    def _init(self):
        rng = np.random.default_rng(self.seed)
        out = []
        for (n_in, n_out), s in zip(zip(self.widths[:-1], self.widths[1:]), self._shapes()[1::3]):
            out += [rng.normal(0, 1 / np.sqrt(n_in), (n_in, n_out)).ravel(),
                    rng.normal(0, 0.1 / np.sqrt(n_in), s).ravel(), np.zeros(n_out)]
        return np.concatenate(out)

    # ---- forward / backward
    def _layer_basis(self, H):
        Bs = [self.basis(H[:, i]) for i in range(H.shape[1])]
        return np.stack([v[0] for v in Bs], 1), np.stack([v[1] for v in Bs], 1)   # (N, n_in, nb)

    def _forward(self, theta, X, first=None):
        """first: precomputed (B, dB) for the input layer, which depends on X only."""
        cache, H = [], X
        for li, (a, c, b) in enumerate(self._unpack(theta)):
            B, dB = first if (li == 0 and first is not None) else self._layer_basis(H)
            N, n_in, nb = B.shape
            Hn = silu(H) @ a + B.reshape(N, n_in * nb) @ c.transpose(0, 2, 1).reshape(n_in * nb, -1) + b
            cache.append((H, B, dB, a, c))
            H = Hn
        return H, cache

    def loss_grad(self, theta, X, y, first=None):
        out, cache = self._forward(theta, X, first)
        r = out[:, 0] - y
        loss = np.mean(r ** 2)
        g = 2 * r[:, None] / len(y)
        grads = []
        for li in range(len(cache) - 1, -1, -1):
            H, B, dB, a, c = cache[li]
            N, n_in, nb = B.shape
            ga = silu(H).T @ g
            gc = (B.reshape(N, n_in * nb).T @ g).reshape(n_in, nb, -1).transpose(0, 2, 1)
            gb = g.sum(0)
            if li > 0:     # the input layer needs no gradient with respect to its input
                gH = dsilu(H) * (g @ a.T) + np.einsum('nik,nik->ni', dB, np.einsum('no,iok->nik', g, c))
            loss += self.ridge * (np.sum(a ** 2) + np.sum(c ** 2))
            d2 = np.diff(c, 2, axis=2)
            loss += self.smooth * np.sum(d2 ** 2)
            ga = ga + 2 * self.ridge * a
            gd2 = np.zeros_like(c)
            gd2[:, :, :-2] += d2; gd2[:, :, 1:-1] -= 2 * d2; gd2[:, :, 2:] += d2
            gc = gc + 2 * self.ridge * c + 2 * self.smooth * gd2
            grads.append([ga, gc, gb])
            if li > 0:
                g = gH
        flat = np.concatenate([x.ravel() for layer in reversed(grads) for x in layer])
        return loss, flat

    # ---- sklearn-like interface
    def fit(self, X, y):
        X = np.asarray(X, float); y = np.asarray(y, float)
        self.mx, self.sx = X.mean(0), X.std(0) + 1e-12
        self.my, self.sy = y.mean(), y.std() + 1e-12
        Xs, ys = (X - self.mx) / self.sx, (y - self.my) / self.sy
        th = self._init()
        first = self._layer_basis(Xs)
        m, v = np.zeros_like(th), np.zeros_like(th)
        b1, b2, eps = 0.9, 0.999, 1e-8
        for t in range(1, self.steps + 1):
            _, g = self.loss_grad(th, Xs, ys, first)
            m = b1 * m + (1 - b1) * g; v = b2 * v + (1 - b2) * g * g
            th -= self.lr * (m / (1 - b1 ** t)) / (np.sqrt(v / (1 - b2 ** t)) + eps)
        self.theta = th
        return self

    def predict(self, X):
        Xs = (np.asarray(X, float) - self.mx) / self.sx
        return self._forward(self.theta, Xs)[0][:, 0] * self.sy + self.my

    def edge(self, layer, i, j, x):
        """The learned univariate function on edge (i -> j) of a layer, at x."""
        a, c, b = self._unpack(self.theta)[layer]
        B, _ = self.basis(np.asarray(x, float))
        return a[i, j] * silu(x) + B @ c[i, j]
