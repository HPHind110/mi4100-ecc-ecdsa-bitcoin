"""Shared educational curve parameters for the toy ECC/ECDSA demos.

This curve is intentionally tiny so students can inspect the arithmetic by
hand. It is not secp256k1, not secure, and must never be used for real keys,
wallets, or Bitcoin transaction signing.
"""

from src.ecc import Curve, Point
from src.ecdsa_toy import ECDSAParams


DEMO_P = 17
DEMO_A = 3
DEMO_B = 5
DEMO_G = Point(1, 3)
DEMO_N = 23


def get_demo_params() -> ECDSAParams:
    """Return fresh toy ECDSA parameters for demos and tests.

    A new ``Curve`` is returned on each call because ``Curve`` tracks operation
    counters for visualization/benchmark demos. Sharing one curve globally can
    make those counters harder for students to reason about.
    """

    return ECDSAParams(curve=Curve(p=DEMO_P, a=DEMO_A, b=DEMO_B), G=DEMO_G, n=DEMO_N)
