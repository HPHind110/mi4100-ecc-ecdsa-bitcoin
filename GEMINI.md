\# MI4100 ECC/ECDSA Bitcoin Project



\## Role of the assistant

You are helping build a course project for "Mật mã và độ phức tạp thuật toán" about:

"Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin".



Use Vietnamese explanations in comments/docs when appropriate. Code identifiers should be English.



\## Main thesis

The project does not propose a new cryptosystem. It models and simulates how ECC/ECDSA works, why ECC improves public-key cryptography efficiency compared with RSA/ElGamal, why ECDSA fits Bitcoin transaction authentication, and why incorrect implementation, especially nonce reuse, breaks security.



\## Required deliverables

1\. Python toy ECC over a small finite field.

2\. Python ECDSA sign/verify demo.

3\. Reused nonce attack demo recovering private key.

4\. Optional optimization: compare naive ECDSA verification with Shamir's trick.

5\. OpenSSL secp256k1 sign/verify demo.

6\. Benchmark RSA vs ECDSA using OpenSSL or Python timing.

7\. Report outline and slide outline.



\## Important sources in docs/context/extracted

\- MI4100\_LN06-Public-Key-Crypto\_NDHan.txt: public key crypto, RSA, ElGamal, signatures.

\- Elliptic Curve Cryptosystems.txt: Koblitz original ECC.

\- Elliptic Curve Cryptography in Practice.txt: secp256k1, ECDSA, Bitcoin, real deployment mistakes.

\- Biased Nonce Sense.txt: weak ECDSA nonces, repeated nonces, private key recovery.

\- Elliptic Curve Cryptography Engineering.txt: scalar multiplication, double-and-add, NAF, Shamir's trick, projective coordinates, side-channel issues.

\- Performance Analysis of Elliptic Curve Cryptography for SSL.txt: ECC vs RSA performance and key-size motivation.

\- Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities.txt: post-quantum risk discussion.



\## Architecture

src/

\- field.py: modular inverse and finite-field helpers.

\- ecc.py: Point class, curve validation, point addition, point doubling, scalar multiplication.

\- ecdsa\_toy.py: ECDSA keygen, sign, verify on toy curve.

\- nonce\_attack.py: reused nonce attack.

\- shamir.py: naive verification vs Shamir's trick operation count.

\- benchmark.py: timing and operation-count benchmark.



openssl\_demo/

\- gen\_keys.ps1

\- sign\_verify.ps1

\- benchmark.ps1



tests/

\- test\_field.py

\- test\_ecc.py

\- test\_ecdsa.py

\- test\_nonce\_attack.py



\## Safety constraints

Do not implement real wallet software.

Do not generate or scan real Bitcoin private keys.

Do not attempt to steal or recover real funds.

All attacks are educational on toy keys or locally generated test keys.

