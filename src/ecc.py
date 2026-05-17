from dataclasses import dataclass
from typing import Optional
from src.field import mod_inv, mod_div

@dataclass(frozen=True)
class Point:
    x: Optional[int]
    y: Optional[int]

    @property
    def is_infinity(self) -> bool:
        return self.x is None and self.y is None

@dataclass
class Curve:
    p: int
    a: int
    b: int
    # Counters for benchmarking
    add_count: int = 0
    double_count: int = 0

    def reset_counters(self):
        self.add_count = 0
        self.double_count = 0

    def is_on_curve(self, P: Point) -> bool:
        if P.is_infinity:
            return True
        # y^2 = x^3 + ax + b (mod p)
        left = (P.y**2) % self.p
        right = (P.x**3 + self.a * P.x + self.b) % self.p
        return left == right

    def point_neg(self, P: Point) -> Point:
        if P.is_infinity:
            return P
        return Point(P.x, (-P.y) % self.p)

    def point_add(self, P: Point, Q: Point) -> Point:
        if P.is_infinity:
            return Q
        if Q.is_infinity:
            return P
        
        if P == self.point_neg(Q):
            return Point(None, None)

        if P == Q:
            # Case P == Q (Doubling)
            self.double_count += 1
            # lambda = (3x^2 + a) / 2y (mod p)
            num = (3 * P.x**2 + self.a) % self.p
            den = (2 * P.y) % self.p
            l = mod_div(num, den, self.p)
        else:
            # Case P != Q (Addition)
            self.add_count += 1
            # lambda = (y2 - y1) / (x2 - x1) (mod p)
            num = (Q.y - P.y) % self.p
            den = (Q.x - P.x) % self.p
            l = mod_div(num, den, self.p)

        # x3 = lambda^2 - x1 - x2 (mod p)
        # y3 = lambda(x1 - x3) - y1 (mod p)
        x3 = (l**2 - P.x - Q.x) % self.p
        y3 = (l * (P.x - x3) - P.y) % self.p
        
        return Point(x3, y3)

    def scalar_mul(self, k: int, P: Point) -> Point:
        # Double-and-add algorithm
        res = Point(None, None)
        temp = P
        
        # Handle k=0 or negative (though k usually > 0 in ECDSA)
        if k == 0:
            return res
        if k < 0:
            k = -k
            temp = self.point_neg(temp)

        while k > 0:
            if k & 1:
                res = self.point_add(res, temp)
            temp = self.point_add(temp, temp)
            k >>= 1
        return res
