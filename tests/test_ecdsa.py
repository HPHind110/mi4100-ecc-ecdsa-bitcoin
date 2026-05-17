import pytest
from src.ecc import Point, Curve
from src.ecdsa_toy import ECDSAParams, keygen, sign, verify

# Toy parameters for testing
# Curve: y^2 = x^3 + 7 mod 223
# Generator G = (47, 71)
# Order n = 21 (for this specific G on this curve)
toy_curve = Curve(p=223, a=0, b=7)
G = Point(47, 71)
n = 21 # Order of G(47, 71) is 21: 21*G = Inf

toy_params = ECDSAParams(curve=toy_curve, G=G, n=n)

def test_ecdsa_flow():
    # 1. Keygen
    d, Q = keygen(toy_params)
    assert toy_curve.is_on_curve(Q)
    
    message = b"hello bitcoin"
    
    # 2. Sign
    r, s = sign(toy_params, d, message)
    
    # 3. Verify
    assert verify(toy_params, Q, message, (r, s)) is True

def test_ecdsa_invalid_message():
    d, Q = keygen(toy_params)
    message = b"hello bitcoin"
    r, s = sign(toy_params, d, message)
    
    # Wrong message
    assert verify(toy_params, Q, b"hello world", (r, s)) is False

def test_ecdsa_invalid_signature():
    d, Q = keygen(toy_params)
    message = b"hello bitcoin"
    r, s = sign(toy_params, d, message)
    
    # Corrupt signature
    assert verify(toy_params, Q, message, (r + 1, s)) is False
    assert verify(toy_params, Q, message, (r, s + 1)) is False

def test_ecdsa_fixed_k():
    # Use a private key that is coprime to n=21, e.g., d=2
    d, Q = keygen(toy_params, d=2)
    message = b"secret"
    # Use a fixed k=4 (P=4*G=(194,51), r=194%21=5)
    # gcd(4, 21) = 1, so k is valid
    k = 4 
    r, s = sign(toy_params, d, message, k=k)
    assert verify(toy_params, Q, message, (r, s)) is True
    
    # Verify r matches expectation
    # P = 4 * G = (194, 51)
    # r = 194 mod 21 = 5
    assert r == 5
