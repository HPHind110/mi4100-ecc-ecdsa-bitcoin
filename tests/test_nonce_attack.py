import pytest
from src.demo_params import get_demo_params
from src.ecdsa_toy import keygen, sign, hash_message_to_int
from src.nonce_attack import (
    recover_nonce_from_reuse,
    recover_private_key_from_known_nonce,
    recover_private_key_from_nonce,
)

def test_nonce_reuse_recovery():
    params = get_demo_params()
    n = params.n
    
    msg1 = b"\x02"
    msg2 = b"\x03"
    
    h1 = hash_message_to_int(msg1, n)
    h2 = hash_message_to_int(msg2, n)
    
    d, k = 2, 1
    d, Q = keygen(params, d=d)
    r1, s1 = sign(params, d, msg1, k=k)
    r2, s2 = sign(params, d, msg2, k=k)

    # Step 1: Recover k
    k_recovered = recover_nonce_from_reuse(h1, h2, s1, s2, n)
    assert k_recovered == k
    
    # Step 2: Recover d
    d_recovered = recover_private_key_from_nonce(h1, r1, s1, k_recovered, n)
    assert d_recovered == d

def test_known_nonce_recovers_private_key():
    params = get_demo_params()
    n = params.n
    message = b"known nonce toy demo"
    d, k = 2, 3
    d, _ = keygen(params, d=d)
    r, s = sign(params, d, message, k=k)
    z = hash_message_to_int(message, n)

    d_recovered = recover_private_key_from_known_nonce(r, s, z, k, n)

    assert d_recovered == d

def test_known_nonce_rejects_zero_r():
    with pytest.raises(ValueError, match="r must be non-zero"):
        recover_private_key_from_known_nonce(r=0, s=1, z=1, k=1, n=23)

def test_known_nonce_rejects_zero_k():
    with pytest.raises(ValueError, match="k must be non-zero"):
        recover_private_key_from_known_nonce(r=1, s=1, z=1, k=0, n=23)
