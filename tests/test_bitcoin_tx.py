import copy
import secrets

import pytest

from src.bitcoin_tx import (
    OutPoint,
    Transaction,
    TxInput,
    TxOutput,
    UTXOSet,
    pubkey_hash_demo,
    serialize_unsigned_tx,
    sign_transaction_input,
    txid_demo,
    verify_transaction_input,
)
from src.demo_params import get_demo_params


@pytest.fixture
def toy_params():
    return get_demo_params()


@pytest.fixture
def demo_keys(toy_params):
    return {
        "alice_private": 2,
        "bob_private": 5,
        "mallory_private": 10,
        "alice_public": toy_params.curve.scalar_mul(2, toy_params.G),
        "bob_public": toy_params.curve.scalar_mul(5, toy_params.G),
        "mallory_public": toy_params.curve.scalar_mul(10, toy_params.G),
    }


@pytest.fixture
def stable_nonce(monkeypatch):
    """Make toy ECDSA signing deterministic for transaction tests.

    sign() calls secrets.randbelow(n - 1) and then adds 1. Returning 1 makes
    k = 2, which works for these toy transaction messages.
    """

    monkeypatch.setattr(secrets, "randbelow", lambda upper: 1)


@pytest.fixture
def signed_spend(toy_params, demo_keys, stable_nonce):
    funding_tx = Transaction(
        inputs=[],
        outputs=[
            TxOutput(
                amount=10,
                pubkey_hash=pubkey_hash_demo(demo_keys["alice_public"]),
            )
        ],
    )
    funding_outpoint = OutPoint(txid_demo(funding_tx), 0)

    utxo_set = UTXOSet()
    utxo_set.add_utxo(funding_outpoint, funding_tx.outputs[0])

    spend_tx = Transaction(
        inputs=[TxInput(previous_output=funding_outpoint)],
        outputs=[
            TxOutput(
                amount=10,
                pubkey_hash=pubkey_hash_demo(demo_keys["bob_public"]),
            )
        ],
    )
    sign_transaction_input(toy_params, spend_tx, 0, demo_keys["alice_private"])

    return {
        "funding_tx": funding_tx,
        "funding_outpoint": funding_outpoint,
        "utxo_set": utxo_set,
        "spend_tx": spend_tx,
    }


def test_valid_spend_succeeds(toy_params, signed_spend):
    assert verify_transaction_input(
        toy_params, signed_spend["spend_tx"], 0, signed_spend["utxo_set"]
    )


def test_tampered_output_amount_fails(toy_params, signed_spend):
    tampered_tx = copy.deepcopy(signed_spend["spend_tx"])
    tampered_tx.outputs[0] = TxOutput(
        amount=9,
        pubkey_hash=tampered_tx.outputs[0].pubkey_hash,
    )

    assert not verify_transaction_input(
        toy_params, tampered_tx, 0, signed_spend["utxo_set"]
    )


def test_tampered_recipient_locking_condition_fails(
    toy_params, demo_keys, signed_spend
):
    tampered_tx = copy.deepcopy(signed_spend["spend_tx"])
    tampered_tx.outputs[0] = TxOutput(
        amount=tampered_tx.outputs[0].amount,
        pubkey_hash=pubkey_hash_demo(demo_keys["mallory_public"]),
    )

    assert not verify_transaction_input(
        toy_params, tampered_tx, 0, signed_spend["utxo_set"]
    )


def test_wrong_public_key_fails(toy_params, demo_keys, signed_spend):
    wrong_key_tx = copy.deepcopy(signed_spend["spend_tx"])
    wrong_key_tx.inputs[0].public_key = demo_keys["mallory_public"]

    assert not verify_transaction_input(
        toy_params, wrong_key_tx, 0, signed_spend["utxo_set"]
    )


def test_mallory_signs_with_another_key_fails(
    toy_params, demo_keys, signed_spend, stable_nonce
):
    mallory_tx = Transaction(
        inputs=[TxInput(previous_output=signed_spend["funding_outpoint"])],
        outputs=[
            TxOutput(
                amount=10,
                pubkey_hash=pubkey_hash_demo(demo_keys["bob_public"]),
            )
        ],
    )
    sign_transaction_input(toy_params, mallory_tx, 0, demo_keys["mallory_private"])

    assert not verify_transaction_input(
        toy_params, mallory_tx, 0, signed_spend["utxo_set"]
    )


def test_same_utxo_spent_twice_is_rejected_by_toy_utxo_set(
    toy_params, signed_spend
):
    utxo_set = signed_spend["utxo_set"]
    spend_tx = signed_spend["spend_tx"]

    assert utxo_set.apply_transaction(toy_params, spend_tx)
    assert not verify_transaction_input(toy_params, spend_tx, 0, utxo_set)
    assert not utxo_set.apply_transaction(toy_params, spend_tx)


def test_missing_utxo_is_rejected(toy_params, signed_spend):
    missing_utxo_set = UTXOSet()

    assert not verify_transaction_input(
        toy_params, signed_spend["spend_tx"], 0, missing_utxo_set
    )


def test_public_key_hash_mismatch_is_rejected(
    toy_params, demo_keys, signed_spend
):
    mismatch_utxo_set = UTXOSet()
    mismatch_utxo_set.add_utxo(
        signed_spend["funding_outpoint"],
        TxOutput(
            amount=10,
            pubkey_hash=pubkey_hash_demo(demo_keys["mallory_public"]),
        ),
    )

    assert not verify_transaction_input(
        toy_params, signed_spend["spend_tx"], 0, mismatch_utxo_set
    )


def test_txid_demo_is_deterministic(demo_keys):
    tx1 = Transaction(
        inputs=[TxInput(previous_output=OutPoint("funding", 0))],
        outputs=[
            TxOutput(amount=7, pubkey_hash=pubkey_hash_demo(demo_keys["bob_public"]))
        ],
    )
    tx2 = copy.deepcopy(tx1)

    assert txid_demo(tx1) == txid_demo(tx2)


def test_serialize_unsigned_tx_changes_when_transaction_content_changes(
    demo_keys,
):
    original_tx = Transaction(
        inputs=[TxInput(previous_output=OutPoint("funding", 0))],
        outputs=[
            TxOutput(amount=7, pubkey_hash=pubkey_hash_demo(demo_keys["bob_public"]))
        ],
    )
    changed_amount_tx = copy.deepcopy(original_tx)
    changed_amount_tx.outputs[0] = TxOutput(
        amount=8,
        pubkey_hash=changed_amount_tx.outputs[0].pubkey_hash,
    )
    changed_recipient_tx = copy.deepcopy(original_tx)
    changed_recipient_tx.outputs[0] = TxOutput(
        amount=changed_recipient_tx.outputs[0].amount,
        pubkey_hash=pubkey_hash_demo(demo_keys["mallory_public"]),
    )

    serializations = {
        serialize_unsigned_tx(original_tx),
        serialize_unsigned_tx(changed_amount_tx),
        serialize_unsigned_tx(changed_recipient_tx),
    }

    assert len(serializations) == 3
