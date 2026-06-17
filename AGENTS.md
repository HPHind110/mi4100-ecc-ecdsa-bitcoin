# AGENTS.md

# Agent CLI instructions for MI4100 ECC/ECDSA Bitcoin project

## 1. Project identity

This repository is an educational course project for:

```text
MI4100: Mật mã và độ phức tạp thuật toán
```

Topic:

```text
Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin
```

The repository is not a real wallet, blockchain product, crypto library, Bitcoin transaction broadcaster, or key recovery tool.

The goal is to explain, simulate, and demonstrate the chain:

```text
Public-key cryptography
→ ECC
→ ECDLP
→ ECDSA
→ Bitcoin UTXO case study
→ nonce attack
→ implementation defense
→ verification optimization
→ OpenSSL secp256k1
```

Use Vietnamese for documentation, Streamlit UI text, report text, slide notes, and explanatory comments when appropriate.

Use English for code identifiers, filenames, class names, function names, test names, and command-line conventions.

---

## 2. Central thesis

Every change should support this thesis:

```text
Bitcoin does not use ECDSA to encrypt transactions.
Bitcoin uses ECDSA to prove spending authority over UTXOs.

ECC provides the mathematical structure.
ECDLP provides the hardness assumption.
ECDSA provides the digital signature mechanism.
Bitcoin is a real-world case study of ECDSA.
```

The current project structure is ECC-first, not Bitcoin-first.

The intended conceptual chain is:

```text
Why public-key crypto?
→ RSA / ElGamal-DH / ECC comparison
→ ECC math: Q = dG
→ ECDLP: why Q does not reveal d
→ ECDSA: private key signs, public key verifies
→ Bitcoin: ECDSA unlocks a UTXO in a simplified P2PKH-like model
→ nonce failure: reused/known nonce can reveal private key
→ defense: RFC6979-style, CSPRNG, constant-time, side-channel awareness, mature libraries
→ optimization: Shamir's trick for u1G + u2Q
→ OpenSSL: secp256k1 sign/verify as real tooling, not full Bitcoin transaction signing
```

Avoid turning the project into:

```text
a Bitcoin investment discussion
a generic blockchain hype project
a full Bitcoin wallet
a real Bitcoin transaction signer
a full Bitcoin Script implementation
a Schnorr/Taproot/MuSig2 implementation
a real key-recovery or attack tool
a pure ECC formula dump with no ECDSA/Bitcoin connection
```

---

## 3. Current Streamlit app storyline

The app should follow this 10-page structure.

```text
0. Mở đầu
   Introduce the full map: public-key crypto → ECC → ECDSA → Bitcoin case study.

1. Từ khóa bí mật đến khóa công khai
   Explain symmetric crypto, key distribution problem, public-key crypto, hybrid cryptosystem, one-way/trapdoor/hard problems.

2. RSA, ElGamal/DH và ECC
   Compare public-key systems and run OpenSSL benchmark for RSA/DSA/ECDSA.
   Emphasize trade-offs, not "ECC always wins".

3. Nền tảng toán học ECC
   Explain finite fields, elliptic curves, generator G, private key d, public key Q = dG, double-and-add.

4. ECDLP
   Demonstrate brute force, Baby-step Giant-step, and Pollard rho on toy curve.
   Make clear that toy attacks do not break real secp256k1.

5. Chữ ký số ECDSA
   Explain key generation, signing, verification, message integrity, and nonce k.

6. Bitcoin case study
   Model wallet, UTXO, locking condition, unlocking data, public key hash, signature in input, node verification, tampering, wrong key, and double spend.

7. Nonce attack
   Demonstrate reused nonce, known nonce, and explain partial nonce leakage.
   Frame this as implementation failure, not as ECDSA being mathematically broken.

8. Phòng thủ và tối ưu
   Tab 1: defense checklist with threat model, nonce discipline, RFC6979-style, CSPRNG, constant-time, side-channel, test vector, audit, risk gate.
   Tab 2: Shamir's trick for optimizing u1G + u2Q in ECDSA verification.

9. OpenSSL và kết luận
   Generate secp256k1 key, sign message/file, verify original, fail on tampered message, mini benchmark, final project conclusion.
```

Every page should answer:

```text
Câu hỏi là gì?
Ý tưởng chính là gì?
Demo chứng minh điều gì?
Giới hạn của demo là gì?
```

---

## 4. Repository architecture

Expected repository structure:

```text
.
├── app.py
├── requirements.txt
├── README.md
├── PROJECT_PLAN.md
├── PROJECT_SCOPE_AND_REFERENCES.md
│
├── src/
│   ├── field.py
│   ├── ecc.py
│   ├── demo_params.py
│   ├── ecdsa_toy.py
│   ├── bitcoin_tx.py
│   └── shamir.py
│
├── tests/
│   ├── test_field.py
│   ├── test_ecc.py
│   ├── test_ecdsa.py
│   ├── test_bitcoin_tx.py
│   ├── test_nonce_attack.py
│   ├── test_ecdlp_attacks.py
│   └── test_shamir.py
│
└── docs/
    ├── APP_USAGE_GUIDE.md
    └── ECDSA_NONCE_ATTACK_AND_DEFENSE.md
```

Some files may differ by revision. Inspect the repository before editing.

---

## 5. Module responsibilities

### `src/field.py`

Purpose:

```text
Finite-field and modular arithmetic helpers.
```

Expected responsibilities:

```text
egcd
gcd
mod_inv
mod_div
clear error when inverse does not exist
```

Do not silently return incorrect values for non-invertible elements.

---

### `src/ecc.py`

Purpose:

```text
Toy elliptic curve group operations.
```

Expected responsibilities:

```text
Point
Curve
point at infinity
is_on_curve
point addition
point doubling
scalar multiplication
operation counters if needed for Shamir's trick
```

Keep implementation educational and readable.

---

### `src/demo_params.py`

Purpose:

```text
Shared toy curve parameters.
```

The main educational toy curve is:

```text
p = 17
a = 3
b = 5
G = (1, 3)
n = 23
```

Always state that this curve is not secure and is not secp256k1.

---

### `src/ecdsa_toy.py`

Purpose:

```text
Toy ECDSA sign/verify implementation.
```

Expected responsibilities:

```text
hash_message_to_int
sign
verify
input validation
edge-case handling for r = 0, s = 0, invalid nonce
```

Never describe this implementation as production-safe.

---

### `src/bitcoin_tx.py`

Purpose:

```text
Educational Bitcoin-like transaction and UTXO model.
```

Allowed educational data structures:

```text
OutPoint
TxInput
TxOutput
Transaction
UTXOSet
```

Expected validation logic:

```text
referenced UTXO exists
referenced UTXO is unspent
public key hash matches locking condition
signature verifies against deterministic unsigned transaction data
tampering invalidates signature
wrong key invalidates signature
double spend is rejected
```

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
real Bitcoin Script implementation
real sighash implementation
real Bitcoin consensus
```

---

### `src/shamir.py`

Purpose:

```text
Compare naive u1G + u2Q with Shamir's trick.
```

Expected functions:

```text
naive_mul_add(curve, u1, G, u2, Q)
shamir_mul(curve, u1, G, u2, Q)
```

Required property:

```text
Shamir result must equal naive result.
```

Important wording:

```text
Shamir's trick optimizes verification.
It does not defend against nonce attacks.
```

---

### `app.py`

Purpose:

```text
Main Streamlit educational interface.
```

Rules:

```text
Keep pages aligned with the 0-9 storyline.
Do not reintroduce Bitcoin-first framing into Page 0.
Do not move benchmark into ECDSA mechanics page.
Do not make Page 6 look like a real wallet.
Do not ask the user for real private keys.
```

If `app.py` becomes too large, consider extracting non-UI logic into `src/`, but do not over-engineer during a course-project deadline.

---

## 6. Toy curve and security limitations

Always make these limitations visible in app/docs/report:

```text
Toy curve is for education only.
Toy curve is not secp256k1.
Toy curve is not secure.
Toy ECDSA is not production crypto.
Toy ECDLP attacks do not break Bitcoin.
OpenSSL message signing is not full Bitcoin transaction signing.
Benchmark measures performance, not security.
```

Validate or guard against:

```text
d = 0
d >= n
k = 0
k not invertible modulo n
r = 0
s = 0
invalid public key
point not on curve
missing UTXO
double spend
pubkey hash mismatch
```

Prefer explicit errors over silent failure.

---

## 7. Cryptography correctness rules

Do not say:

```text
Bitcoin encrypts transactions with ECC.
Private key contains bitcoin.
ECDSA is broken because nonce reuse leaks the key.
Toy curve security represents real Bitcoin security.
OpenSSL message signing is the same as full Bitcoin transaction signing.
ECDSA is always faster than RSA in every operation.
secp256k1 can be brute-forced with demo code.
Bitcoin ownership is always just one ECDSA signature.
The mini transaction demo implements real Bitcoin consensus.
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
In the P2PKH-like demo, ownership is simplified as valid signature + matching public key hash.
In real Bitcoin, spending authority means satisfying the relevant script/spending condition.
OpenSSL secp256k1 connects toy math to real cryptographic tooling.
Benchmark results depend on operation type, key size, curve, implementation, and machine.
```

---

## 8. Benchmark rules

Benchmarking may compare RSA, DSA, and ECDSA, but wording must be careful.

Do not claim:

```text
ECDSA is always faster than RSA.
ECDSA beats RSA in every operation.
Benchmark proves Bitcoin chose ECDSA only because it is faster.
P-256 benchmark is secp256k1 benchmark.
Benchmark proves security.
```

Prefer:

```text
Benchmark shows performance trade-offs.
RSA verification can be extremely fast.
ECDSA P-256 signing can be very fast.
ECDSA P-384 can be much slower than P-256.
ECC can provide strong security with smaller keys, but performance depends on curve and implementation.
ecdsap256 in OpenSSL speed is NIST P-256, not secp256k1.
Page 9 uses secp256k1 for actual OpenSSL sign/verify demo.
```

If OpenSSL output uses `nistp256`, label it as NIST P-256.

Do not label it as secp256k1.

---

## 9. Nonce attack and defense rules

Nonce attack page should make this point:

```text
ECDLP may be hard, but ECDSA can still fail if nonce k is reused, leaked, biased, or generated badly.
```

Allowed demos:

```text
reused nonce: two signatures use same k → recover k → recover d
known nonce: one signature with known k → recover d
partial nonce leakage: explanation only, no lattice implementation unless explicitly requested
```

Frame correctly:

```text
Correct ECDSA is not shown to be broken.
Nonce misuse is an implementation failure.
```

Defense page should include:

```text
threat model
nonce discipline
RFC6979-style deterministic nonce
CSPRNG
constant-time
side-channel
test vector
audit
risk gate / fatal finding
toy vs prototype vs production
mature library
```

Risk score is educational only. Do not present it as a real security audit.

Critical findings should override simple additive scoring, for example:

```text
fixed/reused nonce
weak RNG in production
self-written ECDSA for production without review/audit
```

---

## 10. Safety constraints

Never implement or modify the project to:

```text
create real Bitcoin wallets
generate seed phrases for real use
import real wallet files
scan private keys
test ownership of real funds
recover real private keys
interact with the real Bitcoin network
broadcast transactions
steal funds
brute-force real secp256k1 keys
attack real users or real systems
```

All attack demonstrations must be limited to:

```text
toy curves
toy keys
locally generated temporary test keys
```

If a user asks for real-wallet or real-key attack behavior, refuse that part and redirect to safe educational toy examples.

---

## 11. Development workflow for Agent CLI

Before editing:

```text
1. Inspect the relevant files.
2. Identify the exact user request.
3. Make a small implementation plan.
4. Modify only necessary files.
5. Preserve existing working demos and tests.
```

After editing Python code:

```powershell
pytest -q
```

If `pytest` is unavailable:

```powershell
python -m pytest -q
```

After editing Streamlit UI:

```powershell
streamlit run app.py
```

After editing OpenSSL-related code:

```powershell
openssl version
```

If the current environment cannot run a command, state clearly:

```text
I could not run this command in the current environment.
```

Never claim tests passed unless they actually ran.

---

## 12. Code style

Use clear, small functions.

Prefer readable educational code over clever code.

Use type hints when practical.

Use dataclasses for simple data containers.

Add docstrings for cryptographic or algorithmic functions.

For educational cryptographic functions, docstrings should mention:

```text
what the function demonstrates
what assumptions it makes
why it is not production-safe
```

Avoid:

```text
large hidden side effects
silent failure
unclear global state
over-engineering
heavy dependencies for simple tasks
```

Prefer:

```text
explicit parameters
explicit validation
clear error messages
small helpers
deterministic behavior in tests
```

---

## 13. Test requirements

Maintain and extend tests.

Important test cases:

```text
modular inverse works
invalid inverse raises clear error
point addition works
point doubling works
scalar multiplication works
point at infinity behaves correctly
ECDSA sign/verify succeeds
tampered message fails
wrong public key fails
invalid nonce is handled
valid Bitcoin-like spend succeeds
tampered transaction fails
wrong-key transaction fails
Mallory-signed transaction fails
public-key-hash mismatch fails
missing UTXO fails
double spend fails
reused nonce recovers k and d on toy curve
known nonce recovers d on toy curve
ECDLP brute force recovers toy private key
BSGS recovers toy private key if implemented
Pollard rho tests are deterministic and non-flaky if implemented
Shamir result matches naive result
```

Tests must not depend on:

```text
real Bitcoin network
real wallet files
real private keys
external web APIs
non-deterministic online state
```

---

## 14. Documentation requirements

Docs should be consistent with the app storyline.

Recommended docs:

```text
README.md
PROJECT_PLAN.md
PROJECT_SCOPE_AND_REFERENCES.md
docs/APP_USAGE_GUIDE.md
docs/ECDSA_NONCE_ATTACK_AND_DEFENSE.md
AGENTS.md
```

Documentation should include:

```text
what the project does
what it does not do
how to install
how to run tests
how to run Streamlit
what each page demonstrates
limitations and safety warnings
references
```

Do not maintain multiple long conflicting instruction files.

If adding `GEMINI.md`, keep it short:

```markdown
# Gemini CLI instructions

Read and follow AGENTS.md first.
```

---

## 15. Report and slide guidance

Report should follow this structure:

```text
1. Introduction
2. Public-key cryptography background
3. ECC and ECDLP
4. ECDSA
5. Bitcoin UTXO case study
6. Nonce attack and defense
7. Implementation, testing, OpenSSL demo
8. Conclusion and limitations
```

Slides should be shorter:

```text
1. Title
2. Problem and project map
3. Public-key crypto → ECC
4. Q = dG
5. ECDLP
6. ECDSA
7. Bitcoin UTXO case study
8. Transaction lab failures
9. Nonce attack
10. Defense checklist
11. Shamir + OpenSSL
12. Conclusion
```

Avoid slide/report drift into:

```text
Bitcoin price
generic blockchain introduction
Schnorr/Taproot deep dive
full Bitcoin Script
overclaiming benchmark
real key attack
```

---

## 16. Modern Bitcoin crypto notes

It is acceptable to mention:

```text
BIP340 Schnorr signatures
Taproot
BIP341
BIP342
MuSig2
BIP327
libsecp256k1
```

But frame them as modern context, not the implementation target.

This project does not implement Schnorr, Taproot, Tapscript, or MuSig2.

If documentation mentions them, keep it clear:

```text
Bitcoin has modern signature/spending mechanisms beyond ECDSA.
This project focuses on ECC/ECDSA because that is the course topic and current implementation scope.
```

---

## 17. Dependency policy

Keep dependencies minimal.

Acceptable common dependencies:

```text
pytest
streamlit
plotly
pandas
```

Do not add heavy packages unless clearly necessary.

Do not add production cryptographic libraries just to replace toy code unless explicitly requested.

OpenSSL may be used through command line for Page 2 and Page 9 demos.

---

## 18. File cleanup policy

Do not commit generated or sensitive files:

```text
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
*.pem
*.key
*.bin
.env
results/
sig.bin
message.txt
message_tampered.txt
```

Do not commit local assistant context:

```text
docs/context/
docs/papers/
GEMINI.md if it contains long private context
PROJECT_PROMPTS.md
```

If files are already tracked, `.gitignore` alone will not remove them. Use:

```powershell
git rm --cached <path>
```

Then commit the removal from tracking.

---

## 19. When expanding the project

Before adding a new feature, ask:

```text
Does this support the main chain?
```

Main chain:

```text
public-key crypto
→ ECC
→ ECDLP
→ ECDSA
→ Bitcoin UTXO case study
→ nonce attack
→ defense
→ optimization
→ OpenSSL
```

Good additions:

```text
better Page 2 benchmark explanation
cleaner ECDLP helper module
more robust transaction lab test cases
better nonce defense notes
clearer report/slides mapping
more precise OpenSSL warnings
```

Risky additions:

```text
full Bitcoin Script
full sighash
Schnorr implementation
MuSig2 implementation
lattice attack implementation
wallet UI
network broadcasting
real key import
```

Only add risky features if explicitly requested and if they remain safe and educational.

---

## 20. Final quality target

The final project should make this chain obvious:

```text
Public-key crypto solves key distribution/authentication problems.
ECC is one public-key approach using elliptic curve groups.
Private key d creates public key Q = dG.
ECDLP protects d from Q.
ECDSA uses d to sign and Q to verify.
Bitcoin uses signatures to prove spending authority over UTXOs.
Tampering, wrong keys, missing UTXOs, and double spends fail in the toy model.
Nonce misuse can leak private key without solving ECDLP.
Defense requires nonce discipline, RFC6979-style/CSPRNG, constant-time, side-channel awareness, test vectors, audits, and mature libraries.
Shamir's trick optimizes verification.
OpenSSL secp256k1 connects toy math to real cryptographic tooling.
```

If a change does not support this chain, reconsider whether it belongs in the project.
