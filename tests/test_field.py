import pytest
from src.field import mod_inv, mod_div

def test_mod_inv():
    # 3 * 5 = 15 = 1 (mod 7)
    assert mod_inv(3, 7) == 5
    # Inverse of 1 is always 1
    assert mod_inv(1, 11) == 1
    # Inverse of 2 mod 5 is 3
    assert mod_inv(2, 5) == 3

def test_mod_inv_error():
    # 2 and 4 are not coprime, so no inverse
    with pytest.raises(ValueError, match="Modular inverse does not exist"):
        mod_inv(2, 4)
    # 0 has no inverse
    with pytest.raises(ValueError):
        mod_inv(0, 7)

def test_mod_div():
    # -1 / 3 mod 7
    # -1 mod 7 = 6
    # 1/3 mod 7 = 5
    # 6 * 5 = 30 = 2 (mod 7)
    assert mod_div(-1, 3, 7) == 2
    # 10 / 2 mod 13 = 5
    assert mod_div(10, 2, 13) == 5

def test_mod_div_error():
    with pytest.raises(ValueError):
        mod_div(1, 0, 7)
