from src.field import mod_div
from src.ecdsa_toy import keygen, sign, hash_message_to_int
from src.demo_params import get_demo_params

def recover_nonce_from_reuse(h1: int, h2: int, s1: int, s2: int, n: int) -> int:
    """
    Recovers the nonce k if it was used for two different messages.
    k = (h1 - h2) / (s1 - s2) mod n
    """
    num = (h1 - h2) % n
    den = (s1 - s2) % n
    return mod_div(num, den, n)

def recover_private_key_from_nonce(h: int, r: int, s: int, k: int, n: int) -> int:
    """
    Recovers the private key d given the nonce k.
    d = (s * k - h) / r mod n
    """
    num = (s * k - h) % n
    return mod_div(num, r, n)

def demo_reused_nonce_attack():
    """
    Demonstrates the attack on a toy curve.
    """
    # 1. Setup toy params
    params = get_demo_params()
    n = params.n

    # 2. Messages with different hashes mod n
    msg1 = b"\x02"
    msg2 = b"\x03"
    
    h1 = hash_message_to_int(msg1, n)
    h2 = hash_message_to_int(msg2, n)
    
    # 3. Use a fixed toy private key and intentionally reuse nonce k.
    d_original, _ = keygen(params, d=2)
    k_fixed = 1
    r1, s1 = sign(params, d_original, msg1, k=k_fixed)
    _, s2 = sign(params, d_original, msg2, k=k_fixed)

    print("--- ECDSA Reused Nonce Attack Demo ---")
    print(f"Original Private Key (d): {d_original}")
    print(f"Reused Nonce (k): {k_fixed}")
    print(f"Message 1 Hash (h1): {h1}, Signature 1: (r={r1}, s={s1})")
    print(f"Message 2 Hash (h2): {h2}, Signature 2: (r={r1}, s={s2})")
    
    # 5. Attack!
    try:
        k_recovered = recover_nonce_from_reuse(h1, h2, s1, s2, n)
        d_recovered = recover_private_key_from_nonce(h1, r1, s1, k_recovered, n)
        
        print(f"Recovered Nonce (k): {k_recovered}")
        print(f"Recovered Private Key (d): {d_recovered}")
        
        if d_original == d_recovered:
            print("SUCCESS: Private key recovered successfully!")
        else:
            print("FAILURE: Recovered key does not match original.")
            
    except ValueError as e:
        print(f"ATTACK FAILED: {e}")

if __name__ == "__main__":
    demo_reused_nonce_attack()
