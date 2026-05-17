import hashlib
import secrets
from dataclasses import dataclass
from typing import Tuple, Optional
from src.field import mod_inv
from src.ecc import Point, Curve

@dataclass(frozen=True)
class ECDSAParams:
    curve: Curve
    G: Point  # Generator point
    n: int    # Order of G

def keygen(params: ECDSAParams, d: Optional[int] = None) -> Tuple[int, Point]:
    """
    Generates an ECDSA keypair.
    If d is provided, use it as the private key (for testing/demo).
    Returns (private_key, public_key).
    """
    if d is None:
        while True:
            from src.field import egcd
            d = secrets.randbelow(params.n - 1) + 1
            if egcd(d, params.n)[0] == 1:
                break
    
    Q = params.curve.scalar_mul(d, params.G)
    return d, Q

def hash_message_to_int(message: bytes, n: int) -> int:
    """
    Hashes a message using SHA-256 and returns it as an integer modulo n.
    """
    h = hashlib.sha256(message).digest()
    return int.from_bytes(h, 'big') % n

def sign(params: ECDSAParams, d: int, message: bytes, k: Optional[int] = None) -> Tuple[int, int]:
    """
    Signs a message using the private key d.
    If k is provided, use it as the nonce (for testing/reused nonce demo).
    Returns signature (r, s).
    """
    z = hash_message_to_int(message, params.n)
    from src.field import egcd
    
    while True:
        if k is None:
            curr_k = secrets.randbelow(params.n - 1) + 1
            if egcd(curr_k, params.n)[0] != 1:
                continue
        else:
            curr_k = k
            if egcd(curr_k, params.n)[0] != 1:
                raise ValueError(f"Provided k={k} is not coprime to n={params.n}")
            
        # 1. Calculate P = k * G
        P = params.curve.scalar_mul(curr_k, params.G)
        
        # 2. r = x_P mod n
        r = P.x % params.n
        if r == 0:
            if k is not None:
                raise ValueError("Provided k results in r=0")
            continue
            
        # 3. s = k^-1 * (z + r*d) mod n
        try:
            k_inv = mod_inv(curr_k, params.n)
            s = (k_inv * (z + r * d)) % params.n
            if egcd(s, params.n)[0] != 1:
                if k is not None:
                    raise ValueError(f"Provided k={k} results in s={s} which is not coprime to n={params.n}")
                continue
        except ValueError:
            if k is not None:
                raise ValueError("Provided k has no modular inverse mod n")
            continue
            
        if s == 0:
            if k is not None:
                raise ValueError("Provided k results in s=0")
            continue
            
        return r, s

def verify(params: ECDSAParams, Q: Point, message: bytes, signature: Tuple[int, int]) -> bool:
    """
    Verifies an ECDSA signature (r, s) for message against public key Q.
    """
    r, s = signature
    
    # 1. Check if r and s are in [1, n-1]
    if not (1 <= r < params.n and 1 <= s < params.n):
        return False
        
    # 2. Calculate z
    z = hash_message_to_int(message, params.n)
    
    # 3. Calculate w = s^-1 mod n
    try:
        w = mod_inv(s, params.n)
    except ValueError:
        return False
        
    # 4. Calculate u1 = z*w mod n, u2 = r*w mod n
    u1 = (z * w) % params.n
    u2 = (r * w) % params.n
    
    # 5. Calculate P = u1*G + u2*Q
    p1 = params.curve.scalar_mul(u1, params.G)
    p2 = params.curve.scalar_mul(u2, Q)
    P = params.curve.point_add(p1, p2)
    
    if P.is_infinity:
        return False
        
    # 6. Verify r == x_P mod n
    return r == (P.x % params.n)
