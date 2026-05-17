import pytest
from src.ecc import Point, Curve
from src.ecdsa_toy import ECDSAParams, keygen, sign, hash_message_to_int
from src.nonce_attack import recover_nonce_from_reuse, recover_private_key_from_nonce

def test_nonce_reuse_recovery():
    # Setup
    toy_curve = Curve(p=223, a=0, b=7)
    G = Point(47, 71)
    n = 21
    params = ECDSAParams(curve=toy_curve, G=G, n=n)
    
    msg1 = b"\x02" # h=0
    msg2 = b"\x03" # h=1
    
    h1 = hash_message_to_int(msg1, n)
    h2 = hash_message_to_int(msg2, n)
    
    # Find a working (d, k)
    d, k = None, 4
    r1, s1, s2 = None, None, None
    for d_try in [2, 4, 5, 8]:
        try:
            d, Q = keygen(params, d=d_try)
            r1, s1 = sign(params, d, msg1, k=k)
            r2, s2 = sign(params, d, msg2, k=k)
            break
        except ValueError:
            continue

    # Step 1: Recover k
    k_recovered = recover_nonce_from_reuse(h1, h2, s1, s2, n)
    assert k_recovered == k
    
    # Step 2: Recover d
    d_recovered = recover_private_key_from_nonce(h1, r1, s1, k_recovered, n)
    assert d_recovered == d
