from src.ecc import Point, Curve
from src.demo_params import get_demo_params

def naive_mul_add(curve: Curve, u1: int, G: Point, u2: int, Q: Point) -> Point:
    """
    Computes u1*G + u2*Q using two separate scalar multiplications.
    """
    p1 = curve.scalar_mul(u1, G)
    p2 = curve.scalar_mul(u2, Q)
    return curve.point_add(p1, p2)

def shamir_mul(curve: Curve, u1: int, G: Point, u2: int, Q: Point) -> Point:
    """
    Computes u1*G + u2*Q using Shamir's trick (simultaneous scalar multiplication).
    """
    # Precompute table
    # (0,0) -> Inf
    # (1,0) -> G
    # (0,1) -> Q
    # (1,1) -> G + Q
    table = {
        (0, 0): Point(None, None),
        (1, 0): G,
        (0, 1): Q,
        (1, 1): curve.point_add(G, Q)
    }
    
    # Get bit length of the larger scalar
    max_bits = max(u1.bit_length(), u2.bit_length())
    
    res = Point(None, None)
    for i in range(max_bits - 1, -1, -1):
        # 1. Double
        res = curve.point_add(res, res)
        
        # 2. Add from table
        b1 = (u1 >> i) & 1
        b2 = (u2 >> i) & 1
        points_to_add = table[(b1, b2)]
        if not points_to_add.is_infinity:
            res = curve.point_add(res, points_to_add)
            
    return res

def benchmark_shamir():
    params = get_demo_params()
    toy_curve = params.curve
    G = params.G
    # Pick small scalars for the educational comparison.
    u1, u2 = 13, 19
    Q = toy_curve.scalar_mul(5, G) # Q = 5*G
    
    print(f"--- Shamir's Trick Benchmark (u1={u1}, u2={u2}) ---")
    
    # Naive
    toy_curve.reset_counters()
    p_naive = naive_mul_add(toy_curve, u1, G, u2, Q)
    naive_add, naive_double = toy_curve.add_count, toy_curve.double_count
    
    # Shamir
    toy_curve.reset_counters()
    p_shamir = shamir_mul(toy_curve, u1, G, u2, Q)
    shamir_add, shamir_double = toy_curve.add_count, toy_curve.double_count
    
    assert p_naive == p_shamir
    
    print(f"Naive:  {naive_add} additions, {naive_double} doublings")
    print(f"Shamir: {shamir_add} additions, {shamir_double} doublings")
    print(f"Reduction in additions: {naive_add - shamir_add}")
    print(f"Reduction in doublings: {naive_double - shamir_double}")

if __name__ == "__main__":
    benchmark_shamir()
