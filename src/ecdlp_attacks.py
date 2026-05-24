"""Toy ECDLP attack demonstrations.

Module nay chi dung cho toy curve giao duc. Brute force discrete log o day
minh hoa bai toan:

    Given G and Q = dG, find d.

Voi tham so nho, co the thu tung k. Voi secp256k1 that, cach nay khong kha thi
va module nay KHONG tan cong Bitcoin, KHONG xu ly real keys, KHONG scan wallet.
"""

from dataclasses import dataclass
from math import ceil, sqrt
import random
from typing import Optional

from src.ecc import Curve, Point
from src.field import mod_inv


@dataclass(frozen=True)
class DLogResult:
    """Ket qua discrete log tren toy curve.

    `recovered_k` la k neu tim thay Q = kG, hoac None neu khong tim thay trong
    gioi han tim kiem. `steps` la so buoc kiem tra/lap bang don gian de sinh
    vien so sanh chi phi giua cac cach lam. Ket qua nay chi co y nghia giao
    duc tren curve nho, khong phai cong cu tan cong secp256k1.
    """

    recovered_k: Optional[int]
    steps: int


def brute_force_dlog(curve: Curve, G: Point, Q: Point, max_k: int) -> DLogResult:
    """Brute force ECDLP tren toy curve.

    Tim k trong khoang 0..max_k sao cho kG == Q. Neu tim thay, tra ve
    `DLogResult(recovered_k=k, steps=...)`. Neu khong, `recovered_k` la None.

    Day la demo toy-only de minh hoa do phuc tap O(max_k). Khong dung ham nay
    voi secp256k1, real Bitcoin public keys, wallet keys, hay bat ky tai san
    that nao.
    """

    if max_k < 0:
        raise ValueError("max_k must be non-negative")
    if not curve.is_on_curve(G):
        raise ValueError("G must be on the curve")
    if not curve.is_on_curve(Q):
        raise ValueError("Q must be on the curve")

    for steps, k in enumerate(range(max_k + 1), start=1):
        if curve.scalar_mul(k, G) == Q:
            return DLogResult(recovered_k=k, steps=steps)

    return DLogResult(recovered_k=None, steps=max_k + 1)


def baby_step_giant_step_dlog(curve: Curve, G: Point, Q: Point, n: int) -> DLogResult:
    """Baby-step Giant-step ECDLP tren toy curve.

    Tim k trong khoang 0..n-1 sao cho Q = kG. Y tuong la viet:

        k = i*m + j, voi m = ceil(sqrt(n))

    Sau do luu bang baby step jG va di giant step Q - i*mG de tim diem trung.
    Tren toy curve nho, cach nay minh hoa trade-off:

    - brute force: O(n) thoi gian, gan nhu O(1) bo nho
    - BSGS: O(sqrt(n)) thoi gian va O(sqrt(n)) bo nho

    Can nhan manh: day chi la demo giao duc. Voi secp256k1 that, sqrt(n) van
    qua lon de kha thi; ham nay KHONG tan cong Bitcoin, KHONG dung real keys,
    KHONG scan wallet.
    """

    if n <= 0:
        raise ValueError("n must be positive")
    if not curve.is_on_curve(G):
        raise ValueError("G must be on the curve")
    if not curve.is_on_curve(Q):
        raise ValueError("Q must be on the curve")

    m = ceil(sqrt(n))
    steps = 0

    # Baby steps: luu jG cho j = 0..m-1.
    baby_steps: dict[Point, int] = {}
    for j in range(m):
        point = curve.scalar_mul(j, G)
        baby_steps.setdefault(point, j)
        steps += 1

    # Giant steps: Q - i*mG. Neu trung voi jG thi Q = (i*m + j)G.
    mG = curve.scalar_mul(m, G)
    neg_mG = curve.point_neg(mG)
    gamma = Q

    for i in range(m + 1):
        steps += 1
        if gamma in baby_steps:
            candidate = i * m + baby_steps[gamma]
            if candidate < n and curve.scalar_mul(candidate, G) == Q:
                return DLogResult(recovered_k=candidate, steps=steps)
        gamma = curve.point_add(gamma, neg_mG)

    return DLogResult(recovered_k=None, steps=steps)


def pollard_rho_dlog(
    curve: Curve,
    G: Point,
    Q: Point,
    n: int,
    max_steps: int = 10000,
    seed: Optional[int] = None,
) -> dict[str, object]:
    """Experimental Pollard rho discrete log demo for toy curves only.

    Ham nay minh hoa y tuong Pollard rho (ky vong O(sqrt(n)) voi bo nho thap)
    tren toy curve. Day KHONG phai cong cu tan cong secp256k1, KHONG dung cho
    Bitcoin thuc te, va co the that bai do va cham khong huu ich hoac gioi han
    buoc lap. Vi vay ket qua luon kem `caveat` ro rang.
    """

    if n <= 0:
        raise ValueError("n must be positive")
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    if not curve.is_on_curve(G):
        raise ValueError("G must be on the curve")
    if not curve.is_on_curve(Q):
        raise ValueError("Q must be on the curve")

    rng = random.Random(seed)

    def _partition(P: Point) -> int:
        # Fixed 3-way partition for deterministic behavior in tests.
        if P.is_infinity:
            return 0
        return P.x % 3

    def _step(X: Point, a: int, b: int) -> tuple[Point, int, int]:
        bucket = _partition(X)
        if bucket == 0:
            X2 = curve.point_add(X, G)
            return X2, (a + 1) % n, b
        if bucket == 1:
            X2 = curve.point_add(X, X)
            return X2, (2 * a) % n, (2 * b) % n
        X2 = curve.point_add(X, Q)
        return X2, a, (b + 1) % n

    # Randomized start, but deterministic when seed is provided.
    a0 = rng.randrange(n)
    b0 = rng.randrange(n)
    X0 = curve.point_add(curve.scalar_mul(a0, G), curve.scalar_mul(b0, Q))

    Xt, at, bt = X0, a0, b0
    Xh, ah, bh = X0, a0, b0

    for step_idx in range(1, max_steps + 1):
        Xt, at, bt = _step(Xt, at, bt)
        Xh, ah, bh = _step(*_step(Xh, ah, bh))

        if Xt == Xh:
            denominator = (bh - bt) % n
            numerator = (at - ah) % n

            if denominator == 0:
                return {
                    "method": "pollard_rho",
                    "recovered_k": None,
                    "success": False,
                    "steps": step_idx,
                    "caveat": (
                        "Experimental Pollard rho hit a degenerate collision "
                        "(denominator = 0). Retry with a different seed."
                    ),
                }

            try:
                inv_denominator = mod_inv(denominator, n)
            except ValueError:
                return {
                    "method": "pollard_rho",
                    "recovered_k": None,
                    "success": False,
                    "steps": step_idx,
                    "caveat": (
                        "Experimental Pollard rho failed because denominator is "
                        "not invertible mod n. Retry with a different seed."
                    ),
                }

            candidate = (numerator * inv_denominator) % n
            if curve.scalar_mul(candidate, G) == Q:
                return {
                    "method": "pollard_rho",
                    "recovered_k": candidate,
                    "success": True,
                    "steps": step_idx,
                    "caveat": (
                        "Experimental toy-curve result only; not applicable to "
                        "real secp256k1 or Bitcoin security."
                    ),
                }

            return {
                "method": "pollard_rho",
                "recovered_k": None,
                "success": False,
                "steps": step_idx,
                "caveat": (
                    "Experimental Pollard rho produced a non-matching candidate. "
                    "Retry with a different seed."
                ),
            }

    return {
        "method": "pollard_rho",
        "recovered_k": None,
        "success": False,
        "steps": max_steps,
        "caveat": (
            "Experimental Pollard rho reached max_steps without a useful "
            "collision. Increase max_steps or change seed."
        ),
    }
