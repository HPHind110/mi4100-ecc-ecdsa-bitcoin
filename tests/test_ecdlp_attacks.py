from src.demo_params import get_demo_params
from src.ecdlp_attacks import (
    baby_step_giant_step_dlog,
    brute_force_dlog,
    pollard_rho_dlog,
)


def test_brute_force_dlog_recovers_small_toy_private_key():
    params = get_demo_params()
    d = 7
    Q = params.curve.scalar_mul(d, params.G)

    result = brute_force_dlog(params.curve, params.G, Q, max_k=params.n - 1)

    assert result.recovered_k == d
    assert result.steps == d + 1  # search includes k = 0


def test_brute_force_dlog_returns_none_when_max_k_too_small():
    params = get_demo_params()
    d = 7
    Q = params.curve.scalar_mul(d, params.G)

    result = brute_force_dlog(params.curve, params.G, Q, max_k=6)

    assert result.recovered_k is None
    assert result.steps == 7


def test_brute_force_dlog_is_toy_only_not_real_secp256k1():
    """This test intentionally uses only the shared toy curve.

    It does not construct secp256k1 parameters, import wallet data, scan keys,
    or claim that brute force is relevant to real Bitcoin keys.
    """

    params = get_demo_params()

    assert params.curve.p == 17
    assert params.n == 23
    assert params.curve.scalar_mul(params.n, params.G).is_infinity


def test_baby_step_giant_step_dlog_recovers_known_toy_private_key():
    params = get_demo_params()
    d = 11
    Q = params.curve.scalar_mul(d, params.G)

    result = baby_step_giant_step_dlog(params.curve, params.G, Q, n=params.n)

    assert result.recovered_k == d
    assert result.steps > 0


def test_baby_step_giant_step_dlog_returns_none_when_n_excludes_solution():
    params = get_demo_params()
    d = 7
    Q = params.curve.scalar_mul(d, params.G)

    result = baby_step_giant_step_dlog(params.curve, params.G, Q, n=6)

    assert result.recovered_k is None
    assert result.steps > 0


def test_baby_step_giant_step_dlog_matches_brute_force_on_small_examples():
    params = get_demo_params()

    for d in range(params.n):
        Q = params.curve.scalar_mul(d, params.G)

        brute = brute_force_dlog(params.curve, params.G, Q, max_k=params.n - 1)
        bsgs = baby_step_giant_step_dlog(params.curve, params.G, Q, n=params.n)

        assert bsgs.recovered_k == brute.recovered_k == d


def test_pollard_rho_dlog_recovers_known_key_for_at_least_one_fixed_seed():
    params = get_demo_params()
    d = 9
    Q = params.curve.scalar_mul(d, params.G)

    recovered = None
    for seed in range(20):
        result = pollard_rho_dlog(
            params.curve, params.G, Q, n=params.n, max_steps=2000, seed=seed
        )
        if result["success"]:
            recovered = result["recovered_k"]
            break

    assert recovered == d


def test_pollard_rho_dlog_fails_gracefully_when_max_steps_too_small():
    params = get_demo_params()
    d = 9
    Q = params.curve.scalar_mul(d, params.G)

    result = pollard_rho_dlog(
        params.curve, params.G, Q, n=params.n, max_steps=1, seed=0
    )

    assert result["method"] == "pollard_rho"
    assert result["success"] is False
    assert result["recovered_k"] is None
    assert isinstance(result["caveat"], str)
    assert "Experimental" in result["caveat"]


def test_pollard_rho_dlog_output_matches_expected_shape():
    params = get_demo_params()
    d = 5
    Q = params.curve.scalar_mul(d, params.G)

    result = pollard_rho_dlog(
        params.curve, params.G, Q, n=params.n, max_steps=2000, seed=3
    )

    assert set(result.keys()) == {"method", "recovered_k", "success", "steps", "caveat"}
    assert result["method"] == "pollard_rho"
    assert isinstance(result["success"], bool)
    assert isinstance(result["steps"], int)
    assert isinstance(result["caveat"], str)
