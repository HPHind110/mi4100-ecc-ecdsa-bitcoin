\# Chat context summary



Project topic:

"Mật mã đường cong elliptic ECC và ứng dụng chữ ký số ECDSA trong Bitcoin".



Central thesis:

ECC/ECDSA is not just a mathematical curiosity. It is a practical evolution of public-key cryptography: from RSA factorization and ElGamal finite-field discrete logarithm to elliptic-curve discrete logarithm, achieving similar security with smaller keys. Bitcoin uses ECDSA on secp256k1 to authenticate spending rights. But implementation mistakes, especially nonce reuse or weak randomness, can reveal private keys.



Required report sections:

1\. 1–2 pages member contribution summary.

2\. Introduction.

3\. Methodology.

4\. Results and discussion.

5\. References.

6\. Appendix: group work plan.



Simulation plan:

\- Python toy ECC.

\- Python ECDSA sign/verify.

\- Reused nonce attack.

\- Shamir's trick optimization comparison.

\- OpenSSL secp256k1 sign/verify.

\- RSA/ECDSA benchmark.

