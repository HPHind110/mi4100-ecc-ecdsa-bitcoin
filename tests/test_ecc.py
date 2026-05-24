import pytest
from src.ecc import Point
from src.demo_params import DEMO_N, get_demo_params

toy_params = get_demo_params()
toy_curve = toy_params.curve
G = toy_params.G

def test_is_on_curve():
    assert toy_curve.is_on_curve(G) is True
    
    p2 = Point(G.x, (G.y + 1) % toy_curve.p)
    assert toy_curve.is_on_curve(p2) is False
    
    # Infinity point is on curve
    inf = Point(None, None)
    assert toy_curve.is_on_curve(inf) is True

def test_point_add_and_neg():
    p1 = G
    p1_neg = toy_curve.point_neg(p1)
    assert p1_neg == Point(1, 14)
    
    # P + (-P) = Inf
    assert toy_curve.point_add(p1, p1_neg).is_infinity is True
    
    p2 = toy_curve.point_add(p1, p1)
    assert p2 == Point(16, 16)
    assert toy_curve.is_on_curve(p2)

def test_scalar_mul():
    p1 = G
    
    # 0 * P = Inf
    assert toy_curve.scalar_mul(0, p1).is_infinity is True
    
    # 1 * P = P
    assert toy_curve.scalar_mul(1, p1) == p1
    
    # 2 * P = P + P
    p2 = toy_curve.scalar_mul(2, p1)
    assert p2 == toy_curve.point_add(p1, p1)
    assert toy_curve.is_on_curve(p2)
    
    assert toy_curve.scalar_mul(DEMO_N, p1).is_infinity is True
    assert toy_curve.scalar_mul(DEMO_N - 1, p1) == toy_curve.point_neg(p1)
