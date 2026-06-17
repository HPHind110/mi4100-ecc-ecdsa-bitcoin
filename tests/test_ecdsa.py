import pytest
from src.demo_params import get_demo_params
from src.ecdsa_toy import keygen, sign, verify
from src.ecc import Point

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

def test_keygen_rejects_invalid_private_key():
    with pytest.raises(ValueError, match="private key d"):
        keygen(toy_params, d=0)
    with pytest.raises(ValueError, match="private key d"):
        keygen(toy_params, d=toy_params.n)

def test_sign_rejects_invalid_private_key():
    with pytest.raises(ValueError, match="private key d"):
        sign(toy_params, 0, b"message", k=3)
    with pytest.raises(ValueError, match="private key d"):
        sign(toy_params, toy_params.n, b"message", k=3)

def test_sign_rejects_invalid_nonce_zero():
    with pytest.raises(ValueError, match="not coprime"):
        sign(toy_params, 2, b"message", k=0)

def test_sign_rejects_nonce_not_invertible_mod_n():
    with pytest.raises(ValueError, match="not coprime"):
        sign(toy_params, 2, b"message", k=toy_params.n)

def test_sign_rejects_nonce_that_produces_zero_s():
    with pytest.raises(ValueError, match="s=0"):
        sign(toy_params, 2, b"\x00", k=5)

def test_verify_rejects_out_of_range_signature_values():
    _, Q = keygen(toy_params, d=2)
    message = b"message"

    assert verify(toy_params, Q, message, (0, 1)) is False
    assert verify(toy_params, Q, message, (1, 0)) is False
    assert verify(toy_params, Q, message, (toy_params.n, 1)) is False
    assert verify(toy_params, Q, message, (1, toy_params.n)) is False

def test_verify_rejects_invalid_signature_shape_and_type():
    _, Q = keygen(toy_params, d=2)
    message = b"message"

    assert verify(toy_params, Q, message, (1,)) is False
    assert verify(toy_params, Q, message, (1, 2, 3)) is False
    assert verify(toy_params, Q, message, None) is False
    assert verify(toy_params, Q, message, ("1", 2)) is False

def test_verify_with_wrong_public_key_fails():
    d, Q = keygen(toy_params, d=2)
    _, wrong_Q = keygen(toy_params, d=5)
    signature = sign(toy_params, d, b"message", k=3)

    assert verify(toy_params, Q, b"message", signature) is True
    assert verify(toy_params, wrong_Q, b"message", signature) is False

def test_verify_rejects_invalid_public_key_gracefully():
    invalid_Q = Point(1, 4)
    signature = sign(toy_params, 2, b"message", k=3)

    assert toy_curve.is_on_curve(invalid_Q) is False
    assert verify(toy_params, invalid_Q, b"message", signature) is False

def test_verify_rejects_public_key_at_infinity():
    signature = sign(toy_params, 2, b"message", k=3)

    assert verify(toy_params, Point(None, None), b"message", signature) is False
