import pytest
from src.demo_params import get_demo_params
from src.ecdsa_toy import keygen, sign, hash_message_to_int
from src.nonce_attack import recover_nonce_from_reuse, recover_private_key_from_nonce

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
