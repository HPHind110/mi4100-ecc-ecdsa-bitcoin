"""Mini Bitcoin transaction / toy UTXO demo.

Module nay minh hoa cach ECDSA duoc dat vao ngu canh chi tieu UTXO trong
mot **P2PKH-like educational model**. Day KHONG phai la Bitcoin that:

- khong co binary serialization cua Bitcoin,
- khong co Script interpreter,
- khong co sighash consensus rules,
- khong co wallet, mining, mempool, network hay broadcast.

Y tuong can thay:

    UTXO khoa boi hash(public key)
    -> input dua ra signature + public key
    -> node kiem tra public key hash khop va signature dung voi transaction

Tat ca khoa va chu ky o day chi dung toy ECC/ECDSA trong repo de phuc vu hoc
tap. Khong dung module nay cho tien that hoac he thong production.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from src.demo_params import get_demo_params
from src.ecc import Point
from src.ecdsa_toy import ECDSAParams, sign, verify


Signature = Tuple[int, int]


@dataclass(frozen=True)
class TxOutput:
    """Output trong toy UTXO set.

    `pubkey_hash` dong vai tro locking condition trong P2PKH-like educational
    model: ai dua duoc public key co hash khop va chu ky hop le thi duoc xem
    la da chung minh quyen chi tieu trong mo hinh nay.
    """

    amount: int
    pubkey_hash: str


@dataclass(frozen=True)
class OutPoint:
    """Tham chieu den mot output cu: txid + output index."""

    txid: str
    index: int


@dataclass
class TxInput:
    """Input mo khoa mot UTXO cu.

    `signature` va `public_key` la unlocking data trong demo. Day chi la mo
    phong truc tiep cua "signature + public key", khong phai Bitcoin Script.
    """

    previous_output: OutPoint
    signature: Optional[Signature] = None
    public_key: Optional[Point] = None


@dataclass
class Transaction:
    """Giao dich giao duc gom danh sach input va output.

    `version` chi giup serialization on dinh hon trong demo. Gia tri nay khong
    dai dien cho version field cua Bitcoin transaction that.
    """

    inputs: List[TxInput]
    outputs: List[TxOutput]
    version: int = 1


@dataclass
class UTXOSet:
    """Toy UTXO set de kiem tra UTXO ton tai, con unspent, va double spend."""

    utxos: Dict[OutPoint, TxOutput] = field(default_factory=dict)
    spent: Set[OutPoint] = field(default_factory=set)

    def add_utxo(self, outpoint: OutPoint, output: TxOutput) -> None:
        """Them mot UTXO moi vao toy set."""

        self.utxos[outpoint] = output
        self.spent.discard(outpoint)

    def exists(self, outpoint: OutPoint) -> bool:
        """Kiem tra output duoc tham chieu co ton tai trong toy set khong."""

        return outpoint in self.utxos

    def is_unspent(self, outpoint: OutPoint) -> bool:
        """Kiem tra output co ton tai va chua bi danh dau spent khong."""

        return self.exists(outpoint) and outpoint not in self.spent

    def get_output(self, outpoint: OutPoint) -> Optional[TxOutput]:
        """Lay output neu ton tai, neu khong tra ve None."""

        return self.utxos.get(outpoint)

    def mark_spent(self, outpoint: OutPoint) -> None:
        """Danh dau mot UTXO da bi chi tieu.

        Ham nay chi nen duoc goi sau khi transaction da verify thanh cong.
        """

        if not self.exists(outpoint):
            raise ValueError("Cannot mark missing UTXO as spent")
        if outpoint in self.spent:
            raise ValueError("UTXO is already spent")
        self.spent.add(outpoint)

    def apply_transaction(self, params: ECDSAParams, tx: Transaction) -> bool:
        """Xac minh va cap nhat toy UTXO set neu transaction hop le.

        Day la buoc "accept in toy model": tat ca input phai hop le va unspent.
        Neu hop le, cac input cu bi danh dau spent va output moi duoc them vao
        set voi `txid_demo(tx)`. Day khong phai consensus cua Bitcoin.
        """

        for input_index in range(len(tx.inputs)):
            if not verify_transaction_input(params, tx, input_index, self):
                return False

        for tx_input in tx.inputs:
            self.mark_spent(tx_input.previous_output)

        new_txid = txid_demo(tx)
        for output_index, output in enumerate(tx.outputs):
            self.add_utxo(OutPoint(new_txid, output_index), output)
        return True


def serialize_pubkey_demo(Q: Point) -> bytes:
    """Serialize public key toy theo JSON xac dinh.

    Real Bitcoin dung encoding public key rieng (compressed/uncompressed SEC).
    Demo nay chi can mot representation on dinh de bam hash trong P2PKH-like
    educational model.
    """

    if Q.is_infinity:
        raise ValueError("Public key cannot be point at infinity")
    payload = {"x": Q.x, "y": Q.y}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash160_demo(data: bytes) -> str:
    """Tinh HASH160 demo: RIPEMD160(SHA256(data)) neu moi truong ho tro.

    Neu Python/OpenSSL hien tai khong expose RIPEMD160, ham fallback sang 20
    byte dau cua SHA256(SHA256(data)). Fallback nay chi de demo chay duoc va
    khong duoc xem la HASH160 Bitcoin that.
    """

    sha_digest = hashlib.sha256(data).digest()
    try:
        ripemd160 = hashlib.new("ripemd160")
    except ValueError:
        return hashlib.sha256(sha_digest).hexdigest()[:40]
    ripemd160.update(sha_digest)
    return ripemd160.hexdigest()


def pubkey_hash_demo(Q: Point) -> str:
    """Hash public key toy de tao locking condition kieu P2PKH-like."""

    return hash160_demo(serialize_pubkey_demo(Q))


def serialize_unsigned_tx(tx: Transaction) -> bytes:
    """Serialize transaction khong gom unlocking data.

    Signature va public key trong input bi loai bo co chu dich, de chu ky rang
    buoc vao noi dung transaction can chi tieu: previous outputs va outputs
    moi. JSON duoc sort key va dung separators co dinh de hash on dinh.
    """

    payload = {
        "version": tx.version,
        "inputs": [
            {
                "previous_output": {
                    "txid": tx_input.previous_output.txid,
                    "index": tx_input.previous_output.index,
                }
            }
            for tx_input in tx.inputs
        ],
        "outputs": [
            {
                "amount": output.amount,
                "pubkey_hash": output.pubkey_hash,
            }
            for output in tx.outputs
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def txid_demo(tx: Transaction) -> str:
    """Tinh demo transaction id bang SHA256 tren unsigned serialization.

    Day khong phai txid cua Bitcoin that. Muc dich la tao dinh danh on dinh de
    cac `OutPoint` trong toy UTXO set co the tham chieu output.
    """

    return hashlib.sha256(serialize_unsigned_tx(tx)).hexdigest()


def sign_transaction_input(
    params: ECDSAParams,
    tx: Transaction,
    input_index: int,
    private_key: int,
) -> Signature:
    """Ky mot input cua transaction bang toy ECDSA.

    Ham nay tinh public key `Q = dG`, tao chu ky tren deterministic unsigned
    transaction data, roi gan `signature + public_key` vao input tuong ung.
    Day chi chung minh y tuong "private key tao chu ky de mo khoa UTXO"; khong
    phai real Bitcoin transaction signing hay real sighash.
    """

    if not 0 <= input_index < len(tx.inputs):
        raise IndexError("input_index is out of range")
    if not 1 <= private_key < params.n:
        raise ValueError("private_key must be in range 1 <= d < n for toy ECDSA")

    public_key = params.curve.scalar_mul(private_key, params.G)
    if public_key.is_infinity or not params.curve.is_on_curve(public_key):
        raise ValueError("private_key produced an invalid public key")

    signature = sign(params, private_key, serialize_unsigned_tx(tx))
    tx.inputs[input_index].signature = signature
    tx.inputs[input_index].public_key = public_key
    return signature


def verify_transaction_input(
    params: ECDSAParams,
    tx: Transaction,
    input_index: int,
    utxo_set: UTXOSet,
) -> bool:
    """Xac minh mot input theo P2PKH-like educational model.

    Cac dieu kien kiem tra:

    1. UTXO duoc tham chieu phai ton tai.
    2. UTXO do chua bi spent.
    3. Hash cua public key trong input phai khop locking condition cua UTXO.
    4. Chu ky phai verify dung tren deterministic unsigned transaction data.

    Neu amount/recipient trong output bi sua, serialization thay doi va chu ky
    se verify fail. Neu dung public key sai hoac Mallory ky bang khoa khac,
    public-key-hash mismatch hoac signature mismatch se lam giao dich bi tu
    choi trong toy model.
    """

    if not 0 <= input_index < len(tx.inputs):
        return False

    tx_input = tx.inputs[input_index]
    referenced_output = utxo_set.get_output(tx_input.previous_output)
    if referenced_output is None:
        return False
    if not utxo_set.is_unspent(tx_input.previous_output):
        return False
    if tx_input.signature is None or tx_input.public_key is None:
        return False
    if tx_input.public_key.is_infinity:
        return False
    if not params.curve.is_on_curve(tx_input.public_key):
        return False

    if pubkey_hash_demo(tx_input.public_key) != referenced_output.pubkey_hash:
        return False

    return verify(
        params,
        tx_input.public_key,
        serialize_unsigned_tx(tx),
        tx_input.signature,
    )


def demo_bitcoin_spending_flow() -> dict:
    """Chay tron ven mini Bitcoin transaction / toy UTXO signing demo.

    Kich ban:

    - Alice co mot UTXO khoa boi hash(public key Alice).
    - Alice tao transaction chi tieu UTXO do sang Bob.
    - Node toy verify public-key-hash va ECDSA signature.
    - Cac truong hop sua amount, sua recipient, dung sai public key, Mallory ky,
      double spend, missing UTXO va public-key-hash mismatch deu bi tu choi.

    Tat ca deu chay tren toy curve giao duc, chi de minh hoa bai hoc:
    chu ky khong "troi noi" mot minh; no mo khoa mot UTXO cu the duoi mot
    spending condition cu the.
    """

    params = get_demo_params()

    alice_private_key = 2
    bob_private_key = 5
    mallory_private_key = 10

    alice_public_key = params.curve.scalar_mul(alice_private_key, params.G)
    bob_public_key = params.curve.scalar_mul(bob_private_key, params.G)
    mallory_public_key = params.curve.scalar_mul(mallory_private_key, params.G)

    funding_tx = Transaction(
        inputs=[],
        outputs=[TxOutput(amount=10, pubkey_hash=pubkey_hash_demo(alice_public_key))],
    )
    funding_outpoint = OutPoint(txid_demo(funding_tx), 0)

    utxo_set = UTXOSet()
    utxo_set.add_utxo(funding_outpoint, funding_tx.outputs[0])

    spend_tx = Transaction(
        inputs=[TxInput(previous_output=funding_outpoint)],
        outputs=[TxOutput(amount=10, pubkey_hash=pubkey_hash_demo(bob_public_key))],
    )
    sign_transaction_input(params, spend_tx, 0, alice_private_key)

    valid_spend_accepted = verify_transaction_input(params, spend_tx, 0, utxo_set)

    tampered_amount_tx = copy.deepcopy(spend_tx)
    tampered_amount_tx.outputs[0] = TxOutput(
        amount=9,
        pubkey_hash=tampered_amount_tx.outputs[0].pubkey_hash,
    )

    tampered_recipient_tx = copy.deepcopy(spend_tx)
    tampered_recipient_tx.outputs[0] = TxOutput(
        amount=tampered_recipient_tx.outputs[0].amount,
        pubkey_hash=pubkey_hash_demo(mallory_public_key),
    )

    wrong_public_key_tx = copy.deepcopy(spend_tx)
    wrong_public_key_tx.inputs[0].public_key = mallory_public_key

    mallory_signed_tx = Transaction(
        inputs=[TxInput(previous_output=funding_outpoint)],
        outputs=[TxOutput(amount=10, pubkey_hash=pubkey_hash_demo(bob_public_key))],
    )
    sign_transaction_input(params, mallory_signed_tx, 0, mallory_private_key)

    mismatch_utxo_set = UTXOSet()
    mismatch_utxo_set.add_utxo(
        funding_outpoint,
        TxOutput(amount=10, pubkey_hash=pubkey_hash_demo(mallory_public_key)),
    )

    missing_utxo_set = UTXOSet()

    spent_utxo_set = copy.deepcopy(utxo_set)
    first_accept = spent_utxo_set.apply_transaction(params, spend_tx)
    double_spend_accepted = verify_transaction_input(params, spend_tx, 0, spent_utxo_set)

    return {
        "model": "mini Bitcoin transaction demo / P2PKH-like educational model",
        "warning": "not real Bitcoin signing, not real serialization, not Script, not consensus",
        "funding_txid": funding_outpoint.txid,
        "spend_txid": txid_demo(spend_tx),
        "valid_spend_accepted": valid_spend_accepted,
        "tampered_amount_rejected": not verify_transaction_input(
            params, tampered_amount_tx, 0, utxo_set
        ),
        "tampered_recipient_rejected": not verify_transaction_input(
            params, tampered_recipient_tx, 0, utxo_set
        ),
        "wrong_public_key_rejected": not verify_transaction_input(
            params, wrong_public_key_tx, 0, utxo_set
        ),
        "mallory_signature_rejected": not verify_transaction_input(
            params, mallory_signed_tx, 0, utxo_set
        ),
        "double_spend_rejected": first_accept and not double_spend_accepted,
        "missing_utxo_rejected": not verify_transaction_input(
            params, spend_tx, 0, missing_utxo_set
        ),
        "public_key_hash_mismatch_rejected": not verify_transaction_input(
            params, spend_tx, 0, mismatch_utxo_set
        ),
    }
