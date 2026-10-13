"""A physics-informed surrogate in plain numpy, for the blind-spot sweep.

The physics term is the anchor-symmetry law itself, in difference form, on
unlabelled pairs of inputs beyond the training band:

    r(u) = f(u + du) - f(u) - q * du

which is exactly the defect the certificate measures, evaluated where the
surrogate has no data. Minimising it trains the surrogate toward the law the
certificate checks, which is what makes this the right instrument for asking
whether such training blinds the certificate.

Difference form rather than a derivative penalty: the loss stays a function of
network outputs only, so ordinary backpropagation gives an exact gradient with
no second derivatives. Verified against finite differences in test_pinn.py.
"""
import numpy as np
from scipy.optimize import minimize

H = 16          # two tanh layers of 16, the same width as mlp16x16
L2 = 1e-4       # weight decay, on weights only, in standardised units
DU = 0.1        # collocation pair spacing in ln(P)


class PINN:
    def __init__(self, seed):
        self.seed = seed

    # ---- parameters as one flat vector, for L-BFGS ---------------------
    def _shapes(self, B):
        return [(1, H), (H,), (H, H), (H,), (H, B), (B,)]

    def _unpack(self, theta):
        out, i = [], 0
        for s in self.shapes:
            n = int(np.prod(s))
            out.append(theta[i:i + n].reshape(s))
            i += n
        return out

    def _init(self, B):
        rng = np.random.default_rng(self.seed)
        parts = []
        for s in self._shapes(B):
            if len(s) == 2:
                parts.append(rng.normal(0, np.sqrt(1.0 / s[0]), s).ravel())
            else:
                parts.append(np.zeros(s))
        return np.concatenate(parts)

    # ---- network -------------------------------------------------------
    def _forward(self, theta, X):
        W1, b1, W2, b2, W3, b3 = self._unpack(theta)
        h1 = np.tanh(X @ W1 + b1)
        h2 = np.tanh(h1 @ W2 + b2)
        return h2 @ W3 + b3, (X, h1, h2)

    def _backward(self, theta, cache, G):
        W1, b1, W2, b2, W3, b3 = self._unpack(theta)
        X, h1, h2 = cache
        dW3 = h2.T @ G; db3 = G.sum(0)
        da2 = (G @ W3.T) * (1 - h2 ** 2)
        dW2 = h1.T @ da2; db2 = da2.sum(0)
        da1 = (da2 @ W2.T) * (1 - h1 ** 2)
        dW1 = X.T @ da1; db1 = da1.sum(0)
        return np.concatenate([g.ravel() for g in (dW1, db1, dW2, db2, dW3, db3)])

    # ---- loss: data + weight * law residual + weight decay ---------------
    def loss_grad(self, theta, Xd, Yd, Xc, Xc_shift, target_step, w):
        nd, nc = len(Xd), len(Xc)
        X = np.vstack([Xd, Xc_shift, Xc])
        out, cache = self._forward(theta, X)
        od, op, oc = out[:nd], out[nd:nd + nc], out[nd + nc:]
        rd = od - Yd
        loss = (rd ** 2).sum(1).mean()
        G = np.zeros_like(out)
        G[:nd] = 2 * rd / nd
        if w > 0 and nc:
            rp = op - oc - target_step          # law residual, standardised units
            loss += w * (rp ** 2).sum(1).mean()
            G[nd:nd + nc] = 2 * w * rp / nc
            G[nd + nc:] = -2 * w * rp / nc
        grad = self._backward(theta, cache, G)
        Ws = self._unpack(theta)
        for k in (0, 2, 4):
            loss += L2 * (Ws[k] ** 2).sum()
        i = 0
        for k, s in enumerate(self.shapes):
            n = int(np.prod(s))
            if k in (0, 2, 4):
                grad[i:i + n] += 2 * L2 * Ws[k].ravel()
            i += n
        return loss, grad

    # ---- public API ----------------------------------------------------
    def fit(self, U, Y, q, w, u_lo, u_hi, n_colloc=40, maxiter=20000):
        """U: ln(P) of training windows. q: law slope per band (per unit ln P).
        Collocation pairs span [u_lo, u_hi]: no labels are used there."""
        self.mu_u, self.sd_u = U.mean(), U.std()
        self.mu_y, self.sd_y = Y.mean(0), Y.std(0)
        B = Y.shape[1]
        self.shapes = self._shapes(B)
        Xd = ((U - self.mu_u) / self.sd_u)[:, None]
        Yd = (Y - self.mu_y) / self.sd_y
        uc = np.linspace(u_lo, u_hi - DU, n_colloc)
        Xc = ((uc - self.mu_u) / self.sd_u)[:, None]
        Xs = ((uc + DU - self.mu_u) / self.sd_u)[:, None]
        step = np.asarray(q, float) * DU / self.sd_y        # law step, standardised
        res = minimize(self.loss_grad, self._init(B),
                       args=(Xd, Yd, Xc, Xs, step[None, :], w),
                       jac=True, method='L-BFGS-B', options=dict(maxiter=maxiter))
        self.theta, self.converged, self.final_loss = res.x, bool(res.success), float(res.fun)
        self.colloc = (uc, q)
        return self

    def predict(self, U):
        X = ((np.asarray(U, float).ravel() - self.mu_u) / self.sd_u)[:, None]
        out, _ = self._forward(self.theta, X)
        return self.mu_y + self.sd_y * out

    def law_residual(self):
        """Mean norm of the surrogate's own law residual on its collocation pairs,
        in original units: the manipulation check that the penalty worked."""
        uc, q = self.colloc
        r = self.predict(uc + DU) - self.predict(uc) - np.asarray(q) * DU
        return float(np.linalg.norm(r, axis=1).mean())
