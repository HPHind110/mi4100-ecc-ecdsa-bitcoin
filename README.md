# MI4100 ECC/ECDSA Bitcoin Project

## 1. Project identity
Dự án môn học **MI4100: Mật mã và độ phức tạp thuật toán**.

Chủ đề: **Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin**.

Phạm vi:
- Dự án giáo dục, mô phỏng bằng toy parameters và demo OpenSSL.
- Không phải ví Bitcoin thật.
- Không phải phần mềm wallet, mining, mạng ngang hàng, hay broadcast transaction.

## 2. Core thesis
Luận điểm cốt lõi:

**Bitcoin không mã hóa giao dịch bằng ECC/ECDSA. Bitcoin dùng chữ ký số để xác thực quyền chi tiêu (spending authority).**

Chuỗi ý tưởng:

```text
Bitcoin ownership problem
-> ownership as spending condition in UTXO
-> ECC (Q = dG)
-> ECDLP hardness
-> ECDSA sign/verify
-> transaction authentication
```

Diễn đạt chính xác:
- Trong Bitcoin thật, ownership nghĩa là **thỏa điều kiện chi tiêu** của UTXO (script/spending condition).
- Trong demo **P2PKH-like educational model**, ownership được đơn giản hóa thành:
  - `hash(pubkey)` khớp locking condition
  - chữ ký hợp lệ trên dữ liệu transaction demo

## 3. Question-driven storyline
| Question | Code demo | What it proves |
|---|---|---|
| Q0. Bitcoin cần giải bài toán gì? | Trang mở đầu trong `app.py` | Bài toán gốc là xác thực quyền chi tiêu trong môi trường không tin cậy |
| Q1. Ownership trong Bitcoin biểu diễn thế nào? | `src/bitcoin_tx.py` + trang Mini Bitcoin Transaction | Ownership trong mô hình UTXO là khả năng thỏa spending condition |
| Q2. Private key sinh public key thế nào? | `src/ecc.py`, `src/demo_params.py` | Quan hệ `Q = dG` trên nhóm điểm elliptic |
| Q3. Vì sao biết Q không suy ra d? | `src/ecdlp_attacks.py` (brute force/BSGS/Pollard rho experimental trên toy curve) | ECDLP có thể minh họa trên toy curve, nhưng không khả thi cho secp256k1 thật |
| Q4. ECDSA ký và xác minh thế nào? | `src/ecdsa_toy.py` | Private key ký, public key xác minh; sửa message thì verify fail |
| Q5. ECDSA đi vào transaction ra sao? | `src/bitcoin_tx.py`, `tests/test_bitcoin_tx.py` | Chữ ký gắn với UTXO cụ thể; tamper/wrong key/double spend/missing UTXO bị từ chối |
| Q6. ECDSA có luôn an toàn không? | `src/nonce_attack.py` | Reused nonce làm lộ private key là lỗi triển khai |
| Q6.5. Phòng thủ nonce ra sao? | `docs/rfc6979_nonce_defense.md` | Kỷ luật nonce/RNG/library quan trọng ngang toán học |
| Q7. Tối ưu verify thế nào? | `src/shamir.py`, `tests/test_shamir.py` | Shamir's trick tối ưu biểu thức `u1G + u2Q` |
| Q8. Liên hệ công cụ thật? | `openssl_demo/gen_keys.ps1`, `openssl_demo/sign_verify.ps1`, `openssl_demo/benchmark.ps1` | OpenSSL secp256k1 là tooling thật cho message/file signing, không phải full Bitcoin transaction signing |

## 4. How to install
Yêu cầu:
- Python 3.10+
- OpenSSL
- PowerShell (nếu chạy script `.ps1`)

Cài đặt:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 5. How to run tests
```powershell
pytest -q
```

Nếu `pytest` chưa có trong PATH:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 6. How to run Streamlit
```powershell
streamlit run app.py
```

Nếu `streamlit` chưa có trong PATH:

```powershell
python -m streamlit run app.py
```

## 7. How to run OpenSSL demo
```powershell
openssl version
.\openssl_demo\gen_keys.ps1
.\openssl_demo\sign_verify.ps1
.\openssl_demo\benchmark.ps1
```

Lưu ý:
- `sign_verify.ps1` minh họa ký/xác minh message hoặc file.
- Không phải quy trình full Bitcoin transaction signing.

## 8. Key demos
- **Toy ECC**: `src/ecc.py` + `src/demo_params.py`.
- **ECDLP toy attacks (if implemented)**: `src/ecdlp_attacks.py`.
  - brute force
  - baby-step giant-step
  - Pollard rho (experimental, toy-only, có thể fail graceful)
- **ECDSA sign/verify**: `src/ecdsa_toy.py`.
- **Mini Bitcoin transaction signing** (P2PKH-like educational model): `src/bitcoin_tx.py`.
- **Reused nonce attack**: `src/nonce_attack.py`.
- **Nonce defense notes**: `docs/rfc6979_nonce_defense.md`.
- **Shamir's trick**: `src/shamir.py`.
- **OpenSSL secp256k1 demo**: thư mục `openssl_demo/`.

Về benchmark:
- Kết quả benchmark phụ thuộc operation, key size, curve, implementation và máy chạy.
- `openssl speed ecdsap256` là benchmark cho **NIST P-256 / prime256v1**, không phải `secp256k1`.
- Nếu `openssl speed` trên máy không liệt kê `secp256k1` trực tiếp thì không được diễn giải kết quả đó như benchmark `secp256k1`.
- Demo `secp256k1` trong `gen_keys.ps1` và `sign_verify.ps1` được giữ tách biệt với benchmark `openssl speed`.
- Không kết luận tuyệt đối kiểu "ECDSA luôn nhanh hơn RSA trong mọi tình huống".
- RSA verification có thể rất nhanh tùy exponent và implementation.

## 9. Limitations
- Toy curve trong repo là mô hình học tập, **không an toàn** để dùng production.
- Tham số toy legacy `n = 21` là composite (điểm hạn chế thường gặp trong các demo cũ); repo hiện đã dùng shared demo params mới để học tập nhất quán.
- Mini transaction model là **P2PKH-like educational model**, không phải full Bitcoin consensus/script/sighash.
- OpenSSL message/file signing không phải full Bitcoin transaction signing.
- Reused nonce attack minh họa **implementation failure**, không chứng minh ECDSA đúng chuẩn bị "phá".
- ECDLP attacks trong repo là demo toy, không dùng để giảm bảo mật Bitcoin thật.

## 10. References
1. Satoshi Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*.  
   https://bitcoin.org/bitcoin.pdf
2. SECG, *SEC 2: Recommended Elliptic Curve Domain Parameters*.  
   https://www.secg.org/sec2-v2.pdf
3. Thomas Pornin, *RFC 6979: Deterministic Usage of DSA and ECDSA*.  
   https://datatracker.ietf.org/doc/html/rfc6979
4. Bitcoin Developer Documentation, *Transactions*.  
   https://developer.bitcoin.org/devguide/transactions.html
5. OpenSSL Documentation, ECDSA command/API references.  
   https://docs.openssl.org/
6. Joachim Breitner, Nadia Heninger, *Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies*.
