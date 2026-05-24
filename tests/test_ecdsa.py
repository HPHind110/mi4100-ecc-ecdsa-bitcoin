import pytest
from src.demo_params import get_demo_params
from src.ecdsa_toy import keygen, sign, verify

toy_params = get_demo_params()
toy_curve = toy_params.curve

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
    d, Q = keygen(toy_params, d=2)
    message = b"secret"
    k = 3
    r, s = sign(toy_params, d, message, k=k)
    assert verify(toy_params, Q, message, (r, s)) is True

    assert r == 4
