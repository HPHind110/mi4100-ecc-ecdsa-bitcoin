# MI4100 ECC/ECDSA Bitcoin Project — Agent Instructions

## Project identity

This repository is an educational course project for **MI4100: Mật mã và độ phức tạp thuật toán**.

Topic:

> Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin

The project does **not** propose a new cryptosystem, wallet, blockchain, or cryptocurrency product.

The goal is to explain, simulate, and demonstrate how:

```text
ECC → ECDLP → ECDSA → Bitcoin transaction authentication
```

connect together in a clear course-project storyline.

Use Vietnamese for explanations, comments, docs, README, report, slide notes, and Streamlit UI text when appropriate.

Use English for code identifiers, function names, class names, file names, and test names.

---

## Core thesis

The central thesis of the project is:

> Bitcoin does not use ECC/ECDSA to encrypt transactions. Bitcoin uses ECDSA to prove spending authority. ECC provides the mathematical structure, ECDLP provides the computational hardness assumption, ECDSA provides the digital signature mechanism, and Bitcoin uses that signature mechanism to verify who is allowed to spend a UTXO.

All code, docs, reports, slides, and UI pages should support this thesis.

Avoid turning the project into:

* a Bitcoin price/investment discussion
* a generic blockchain hype project
* a full wallet implementation
* a real Bitcoin transaction broadcaster
* a pure ECC formula dump with no Bitcoin connection
* a pure attack demo that forgets ECDSA is mainly a signature algorithm

---

## Question-driven storyline

The project should be told as a chain of questions, not as disconnected modules.

### Q0. Bitcoin cần giải bài toán gì?

In an untrusted environment, how can a digital asset be transferred without a bank or central database?

Key idea:

```text
Need: proof of spending authority
```

Do not start the story from elliptic curve formulas. Start from the ownership problem.

---

### Q1. Quyền sở hữu trong Bitcoin được biểu diễn thế nào?

Ownership is not username/password.

Ownership is not simply a balance field in a bank database.

In a Bitcoin-like UTXO model:

```text
Ownership = ability to produce a valid digital signature that unlocks a UTXO
```

A P2PKH-like explanation is allowed:

```text
locking condition  ≈ public key hash
unlocking data     ≈ signature + public key
verification       ≈ hash(public key) matches lock and signature verifies
```

Use the phrase **P2PKH-like educational demo**, not “full real Bitcoin script implementation”.

---

### Q2. Private key sinh ra public key như thế nào?

ECC gives:

```text
Q = dG
```

where:

```text
d = private key
G = generator point
Q = public key
```

This is scalar multiplication on an elliptic curve group.

The toy demo should show:

```text
point addition
point doubling
scalar multiplication
double-and-add
```

---

### Q3. Vì sao biết public key mà không suy ra private key?

Because of ECDLP:

```text
Given G and Q = dG, find d.
```

On a small toy curve, this can be brute-forced.

On real parameters such as secp256k1, recovering `d` from `Q` is computationally infeasible with known classical generic attacks.

Allowed educational demos:

```text
brute force discrete log on toy curve
Baby-step Giant-step on toy curve
Pollard rho on toy curve, only if robust and clearly marked experimental
```

Do not claim that the repo attacks real secp256k1.

Do not generate, scan, import, or recover real Bitcoin private keys.

---

### Q4. ECDSA ký và xác minh như thế nào?

Private key signs.

Public key verifies.

The verifier does not need the private key.

A simple message-signing demo should show:

```text
sign(message, private_key)
verify(message, signature, public_key) = True
tamper(message)
verify(tampered_message, signature, public_key) = False
```

This demonstrates integrity and authentication.

---

### Q5. ECDSA đi vào Bitcoin transaction như thế nào?

ECDSA should be connected to a mini Bitcoin transaction/UTXO flow.

Required educational flow:

```text
Alice owns a UTXO
Alice creates a transaction spending that UTXO to Bob
transaction data is serialized in a deterministic educational format
transaction data is hashed
Alice signs the hash with her private key
a node verifies the signature using Alice's public key
if valid and UTXO is unspent, the transaction is accepted in the toy model
```

Required failure cases:

```text
tampered output amount        → verification fails
wrong public key              → verification fails
Mallory signs with another key → verification fails
same UTXO spent twice         → rejected as double spend in toy UTXO set
missing UTXO                  → rejected
```

This is the most important missing layer if the repo only signs ordinary text messages.

Use honest naming:

```text
mini Bitcoin transaction demo
P2PKH-like educational model
toy UTXO set
demo transaction hash
```

Do not call it:

```text
real Bitcoin transaction signing
real Bitcoin consensus
real sighash implementation
real script interpreter
```

---

### Q6. ECDSA có chắc chắn an toàn không?

No.

ECDSA is secure only when its mathematical assumptions and implementation requirements are respected.

Important implementation failure:

```text
reusing nonce k can reveal the private key
```

The reused nonce demo should show:

```text
two signatures using the same k
recover k
recover private key d
```

Frame it correctly:

```text
This does not mean correct ECDSA is broken.
It means ECDSA implementations die if nonce generation is wrong.
```

Do not overstate the attack.

---

### Q7. Có thể tối ưu verification không?

ECDSA verification computes:

```text
u1G + u2Q
```

Shamir's trick can optimize simultaneous scalar multiplication.

This is a bonus optimization demo, not the central thesis.

Use it to support the course angle on algorithms and complexity.

Do not let it overshadow the Bitcoin ownership and transaction-signing story.

---

### Q8. Toy demo có liên hệ công cụ thật không?

Toy curve code explains the mathematics.

OpenSSL secp256k1 demo connects the toy model to real cryptographic tooling.

OpenSSL demo may include:

```text
generate secp256k1 private key
extract public key
sign a message/file
verify signature successfully
tamper message/file
verify failure
benchmark RSA/ECDSA carefully
```

Be precise:

```text
OpenSSL message signing on secp256k1 is real cryptographic tooling.
It is not full Bitcoin transaction signing.
```

---

## Existing architecture

Expected current files:

```text
src/
  field.py          modular inverse and finite-field helpers
  ecc.py            Point, Curve, point addition, point doubling, scalar multiplication
  ecdsa_toy.py      toy ECDSA key generation, signing, verification
  nonce_attack.py   reused nonce attack
  shamir.py         Shamir's trick and naive verification comparison

openssl_demo/
  gen_keys.ps1
  sign_verify.ps1
  benchmark.ps1

tests/
  test_field.py
  test_ecc.py
  test_ecdsa.py
  test_nonce_attack.py
  test_shamir.py

app.py
README.md
PROJECT_PLAN.md
report/
slides/
docs/
results/
```

Recommended additions:

```text
docs/storyline_q0_q8.md
docs/modern_bitcoin_crypto_notes.md

src/bitcoin_tx.py
src/ecdlp_attacks.py

tests/test_bitcoin_tx.py
tests/test_ecdlp_attacks.py
```

---

## Required deliverables

The repo should ultimately support these deliverables:

1. Toy ECC over a small finite field.
2. Toy ECDSA keygen/sign/verify demo.
3. Mini Bitcoin transaction/UTXO signing demo.
4. Tampered transaction verification failure.
5. Wrong-key verification failure.
6. Double-spend rejection in toy UTXO set.
7. Reused nonce attack demo recovering the private key.
8. Optional ECDLP toy attacks:

   * brute force
   * Baby-step Giant-step
   * Pollard rho only if robust and marked experimental
9. Optional verification optimization:

   * Shamir's trick for `u1G + u2Q`
10. OpenSSL secp256k1 sign/verify demo.
11. Careful RSA/ECDSA benchmark discussion.
12. Report outline and slide outline following Q0–Q8.

---

## Safety constraints

Do not implement real wallet software.

Do not generate real Bitcoin wallets.

Do not scan for real Bitcoin private keys.

Do not import real wallet files.

Do not recover, guess, derive, or test ownership of real funds.

Do not interact with the real Bitcoin network.

Do not broadcast transactions.

Do not produce code intended for stealing funds, brute-forcing real keys, or attacking real users.

All attacks must be educational and limited to:

```text
toy curves
toy keys
locally generated temporary test keys
```

Never claim the toy code is production-safe.

---

## Cryptography correctness constraints

Do not say:

```text
Bitcoin encrypts transactions with ECC.
Private key contains bitcoin.
ECDSA is broken because nonce reuse leaks the key.
Toy curve security represents real Bitcoin security.
OpenSSL message signing is the same as full Bitcoin transaction signing.
ECDSA is always faster than RSA in every operation.
secp256k1 can be brute-forced with the demo code.
```

Prefer saying:

```text
Bitcoin uses ECDSA to authenticate spending authority.
Private key gives the ability to sign.
Public key verifies the signature.
ECC gives Q = dG.
ECDLP makes recovering d from Q infeasible for real parameters.
Toy curves are educational only.
Nonce reuse is an implementation failure.
OpenSSL secp256k1 connects the toy model to real cryptographic tooling.
Benchmark results depend on operation type, key size, curve, implementation, and machine.
```

---

## Toy curve limitations

If the project uses a small toy curve such as:

```text
p = 223
a = 0
b = 7
G = (47, 71)
n = 21
```

then clearly state:

```text
This curve is educational only.
The order n = 21 is composite.
Some edge cases appear that do not represent real ECDSA on secp256k1.
The toy curve is useful for visualization, not security.
```

When possible, add defensive validation around:

```text
d = 0
d >= n
k = 0
k not invertible modulo n
s = 0
r = 0
invalid public key
point not on curve
```

Do not silently ignore invalid cryptographic inputs.

---

## Mini Bitcoin transaction scope

If implementing `src/bitcoin_tx.py`, keep the scope educational.

Allowed data structures:

```text
TxOutput
OutPoint
TxInput
Transaction
UTXOSet
```

Allowed helper functions:

```text
serialize_pubkey_demo(Q)
hash160_demo(data)
pubkey_hash_demo(Q)
serialize_unsigned_tx(tx)
txid_demo(tx)
sign_transaction_input(params, tx, input_index, private_key)
verify_transaction_input(params, tx, input_index, utxo_set)
demo_bitcoin_spending_flow()
```

Required validation logic:

```text
referenced UTXO exists
referenced UTXO is unspent
public key hash matches locking condition
signature verifies against unsigned transaction data
tampering invalidates signature
wrong key invalidates signature
double spend is rejected
```

Use deterministic JSON/string serialization for the educational demo.

Do not implement real Bitcoin binary serialization unless explicitly requested.

Do not implement full Bitcoin Script.

Do not implement full sighash consensus logic.

Do not implement mempool, mining, network, block validation, or PoW.

---

## ECDLP attack demo scope

If implementing `src/ecdlp_attacks.py`, keep it educational.

Required:

```text
brute_force_dlog(curve, G, Q, max_k)
```

Recommended:

```text
baby_step_giant_step_dlog(curve, G, Q, n)
```

Optional:

```text
pollard_rho_dlog(curve, G, Q, n, max_steps=10000, seed=None)
```

Pollard rho must be marked experimental if toy curve edge cases make it unreliable.

The comparison function may return:

```text
method
recovered_k
success
operation_count_or_steps
caveat
```

Do not use these demos against real secp256k1 keys.

Do not claim these demos reduce Bitcoin security.

The intended lesson is:

```text
Brute force is O(n).
Baby-step Giant-step is O(sqrt(n)) time and memory.
Pollard rho is O(sqrt(n)) expected time with low memory.
For real secp256k1, sqrt(n) is still infeasible.
```

---

## Streamlit app requirements

The Streamlit app should follow the Q0–Q8 storyline.

Recommended navigation:

```text
0. Big Picture
1. Ownership in Bitcoin
2. ECC: Q = dG
3. ECDLP: Why Q does not reveal d
4. ECDSA Sign/Verify
5. Mini Bitcoin Transaction Signing
6. ECDSA Reused Nonce Attack
7. Shamir's Trick
8. OpenSSL secp256k1 Demo
```

Each page should start with:

```text
Câu hỏi
Ý tưởng
Demo chứng minh điều gì?
```

Warnings should be visible where relevant:

```text
toy curve only
n = 21 is composite
not real Bitcoin consensus
not real Bitcoin transaction serialization
OpenSSL signs a message/file, not a full Bitcoin transaction
nonce reuse attack demonstrates implementation failure
```

Do not make the app look like a real wallet.

Do not ask users to input real private keys.

---

## README/report/slides requirements

Docs should follow the same storyline:

```text
Bitcoin problem
→ ownership as signature over UTXO spending
→ ECC and Q = dG
→ ECDLP hardness
→ ECDSA sign/verify
→ mini Bitcoin transaction demo
→ nonce reuse failure
→ verification optimization
→ OpenSSL secp256k1 connection
→ limitations and conclusion
```

Recommended README table:

```text
Question | Code demo | What it proves
```

Required limitations section:

```text
Toy curve is not secure.
Mini transaction model is not full Bitcoin.
OpenSSL demo is real cryptographic tooling but not full Bitcoin signing.
Nonce reuse attack is an implementation failure demo.
ECDLP attacks are toy demonstrations.
```

Avoid hype.

Prioritize correctness, clarity, and course relevance.

---

## Benchmark rules

Benchmarking may compare RSA and ECDSA, but wording must be careful.

Do not claim:

```text
ECDSA is always faster than RSA.
ECDSA beats RSA in every operation.
Benchmark proves Bitcoin chose ECDSA only because it is faster.
```

Prefer:

```text
ECC can provide comparable security with smaller keys.
Benchmark results depend on operation type, key size, curve, implementation, and machine.
RSA verification can be fast depending on exponent and implementation.
ECDSA often has advantages in key/signature size and signing performance under certain settings.
```

If `openssl_demo/benchmark.ps1` benchmarks P-256, label it P-256.

If it benchmarks secp256k1, make sure the command actually uses secp256k1.

Do not label P-256 results as secp256k1 results.

---

## Development workflow

Before editing:

1. Inspect relevant files.
2. Identify the exact task.
3. Make a small plan.
4. Modify only the necessary files.
5. Preserve existing working demos and tests.

After editing Python code, run:

```powershell
pytest -q
```

After editing the Streamlit app, run:

```powershell
streamlit run app.py
```

After editing OpenSSL scripts, run when available:

```powershell
openssl version
.\openssl_demo\gen_keys.ps1
.\openssl_demo\sign_verify.ps1
.\openssl_demo\benchmark.ps1
```

If a command cannot run in the current environment, state clearly:

```text
I could not run this command in the current environment.
```

Do not pretend tests passed if they were not run.

---

## Code style

Use clear, small functions.

Prefer dataclasses for simple data containers.

Keep code readable for students.

Avoid over-engineering.

Avoid hidden global state.

Add docstrings for cryptographic functions.

For educational functions, docstrings should explain:

```text
what the function demonstrates
what assumptions it makes
why it is not production-safe
```

Use type hints when practical.

Prefer explicit error messages over silent failure.

---

## Test requirements

Maintain and extend unit tests.

Important test cases:

```text
modular inverse works
invalid inverse raises error
point addition works
scalar multiplication works
ECDSA sign/verify succeeds
tampered message fails
wrong public key fails
nonce reuse recovers private key
Shamir result matches naive result
Bitcoin toy transaction valid spend succeeds
tampered transaction fails
wrong-key transaction fails
double-spend fails
missing UTXO fails
public-key-hash mismatch fails
ECDLP brute force recovers toy private key
BSGS recovers toy private key if implemented
Pollard rho tests are deterministic and non-flaky if implemented
```

Tests should not depend on real Bitcoin network access.

Tests should not use real private keys.

---

## Dependency policy

Keep dependencies minimal.

Core toy ECC/ECDSA code should rely mostly on the Python standard library.

Acceptable dependencies if used:

```text
pytest
streamlit
plotly
pandas
```

Only keep other dependencies if they are actually imported and needed.

Do not add heavy packages for simple educational tasks.

Do not add cryptographic libraries just to replace existing toy code unless explicitly requested.

---

## Documentation sources

If `docs/context/extracted/` exists, it may be used as local reference material.

If those files are missing, do not assume or invent their content.

When citing external material in report/docs, prefer primary or official sources:

```text
Bitcoin whitepaper
Bitcoin Developer Documentation
SEC 2 secp256k1 parameters
RFC 6979
NIST/FIPS digital signature standards
OpenSSL documentation
Bitcoin BIPs for Schnorr/Taproot/MuSig2 if discussed
Bitcoin Core libsecp256k1 documentation
```

Do not fabricate citations.

---

## Modern Bitcoin crypto notes

The main project remains ECC/ECDSA in Bitcoin.

It is acceptable to add a short discussion of modern extensions:

```text
Taproot
Schnorr signatures
BIP340
MuSig2
BIP327
libsecp256k1
```

But these should be framed as future/modern context, not the main implementation target.

Do not implement full BIP340 or MuSig2 unless explicitly requested.

Do not let Schnorr replace the ECDSA focus of the project.

---

## File cleanup policy

Do not delete files unless they are clearly:

```text
obsolete
duplicated
generated
unused
misleading
```

Prefer moving generated outputs to:

```text
results/
```

Never commit:

```text
.venv/
__pycache__/
*.pyc
*.pem
*.key
*.bin
.env
```

Do not commit large extracted papers or private local assistant context unless explicitly needed.

If adding `GEMINI.md`, keep it short and make it point to this file:

```markdown
# Gemini CLI instructions

Read and follow AGENTS.md first.
```

Avoid maintaining two long conflicting instruction files.

---

## Final quality target

The final project should make this chain obvious:

```text
Bitcoin needs ownership without banks
→ ownership means valid signature over UTXO spending
→ private key creates public key by Q = dG
→ ECDLP protects private key from public key
→ ECDSA signs transaction data
→ nodes verify signature with public key
→ tampering or wrong key fails
→ nonce reuse leaks private key
→ Shamir's trick optimizes verification
→ OpenSSL secp256k1 connects toy math to real tooling
```

If a change does not support this chain, reconsider whether it belongs in the project.
