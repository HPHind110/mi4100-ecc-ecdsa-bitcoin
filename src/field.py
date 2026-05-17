from typing import Tuple

def egcd(a: int, b: int) -> Tuple[int, int, int]:
    """
    Extended Euclidean Algorithm.
    Returns (g, x, y) such that a*x + b*y = g = gcd(a, b).
    """
    if a == 0:
        return b, 0, 1
    else:
        g, y, x = egcd(b % a, a)
        return g, x - (b // a) * y, y

def mod_inv(a: int, p: int) -> int:
    """
    Returns the modular multiplicative inverse of a modulo p.
    Raises ValueError if the inverse does not exist.
    """
    g, x, _ = egcd(a % p, p)
    if g != 1:
        raise ValueError(f"Modular inverse does not exist: {a} mod {p}")
    else:
        return x % p

def mod_div(a: int, b: int, p: int) -> int:
    """
    Returns (a / b) modulo p.
    Equivalent to (a * mod_inv(b, p)) modulo p.
    """
    return ((a % p) * mod_inv(b, p)) % p
