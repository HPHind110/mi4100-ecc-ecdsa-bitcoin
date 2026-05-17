import pytest
from src.ecc import Point, Curve
from src.shamir import naive_mul_add, shamir_mul

def test_shamir_correctness():
    toy_curve = Curve(p=223, a=0, b=7)
    G = Point(47, 71)
    Q = toy_curve.scalar_mul(10, G)
    
    # Test multiple pairs of (u1, u2)
    test_cases = [
        (1, 1),
        (2, 3),
        (13, 19),
        (0, 5),
        (5, 0),
        (20, 20)
    ]
    
    for u1, u2 in test_cases:
        p_naive = naive_mul_add(toy_curve, u1, G, u2, Q)
        p_shamir = shamir_mul(toy_curve, u1, G, u2, Q)
        assert p_naive == p_shamir, f"Failed at u1={u1}, u2={u2}"
