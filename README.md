# MI4100: ECC, ECDSA và xác thực giao dịch trong Bitcoin

Dự án này là sản phẩm học tập cho môn **MI4100: Mật mã và độ phức tạp thuật toán**.

**Chủ đề:** *Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin*.

Mục tiêu của repo không phải là xây dựng ví Bitcoin, blockchain mới hay phần mềm giao dịch thật. Repo này được thiết kế như một **phòng lab giáo dục** để giải thích, mô phỏng và kiểm chứng mối liên hệ:

```text
Bitcoin ownership problem
→ UTXO spending condition
→ ECC: Q = dG
→ ECDLP hardness
→ ECDSA digital signature
→ Bitcoin-like transaction authentication
```

---

## 1. Luận điểm trung tâm

Bitcoin không dùng ECC/ECDSA để **mã hóa giao dịch**. Giao dịch Bitcoin về bản chất là dữ liệu công khai trên blockchain.

Điểm Bitcoin cần từ ECC/ECDSA là một cơ chế khác:

> **Chứng minh quyền chi tiêu một UTXO mà không cần tiết lộ private key.**

Trong Bitcoin thật, quyền chi tiêu được xác định bởi điều kiện khóa của từng output, thường được biểu diễn bằng Script. Trong mô hình giáo dục của repo này, ta dùng một mô hình đơn giản kiểu **P2PKH-like**:

```text
locking condition  ≈ hash(public key)
unlocking data     ≈ signature + public key
verification       ≈ hash(public key) khớp và chữ ký ECDSA hợp lệ
```

Do đó, project không đặt trọng tâm vào việc “khoe công thức ECC”, mà đặt trọng tâm vào việc trả lời câu hỏi:

> **ECDSA nằm ở đâu trong quá trình một node kiểm tra giao dịch Bitcoin-like?**

---

## 2. Dự án này chứng minh điều gì?

| Câu hỏi | Thành phần trong repo | Ý nghĩa học tập |
|---|---|---|
| Q0. Bitcoin cần giải bài toán gì? | Trang “Bức tranh tổng quan” trong `app.py` | Đặt vấn đề xác thực quyền chi tiêu trong môi trường không có ngân hàng trung gian. |
| Q1. Quyền sở hữu trong Bitcoin được biểu diễn thế nào? | `src/bitcoin_tx.py`, trang “Quyền sở hữu” và “Phòng lab giao dịch” | Ownership được hiểu là khả năng thỏa spending condition của UTXO. |
| Q2. Private key sinh public key như thế nào? | `src/ecc.py`, `src/demo_params.py` | Mô phỏng quan hệ `Q = dG` trên nhóm điểm elliptic curve. |
| Q3. Vì sao biết public key không suy ra private key? | Demo ECDLP trong app | Minh họa brute force, Baby-step Giant-step và Pollard rho trên toy curve; giải thích vì sao secp256k1 thật không bị brute force. |
| Q4. ECDSA ký và xác minh như thế nào? | `src/ecdsa_toy.py` | Private key ký, public key xác minh; sửa dữ liệu thì chữ ký không còn hợp lệ. |
| Q5. ECDSA đi vào transaction như thế nào? | `src/bitcoin_tx.py`, `tests/test_bitcoin_tx.py` | Chữ ký gắn với một UTXO và một transaction cụ thể; tamper/wrong key/double spend bị từ chối. |
| Q6. ECDSA có tự động an toàn không? | `src/nonce_attack.py`, trang reused nonce attack | Dùng lại nonce `k` có thể làm lộ private key; đây là lỗi triển khai, không phải lỗi của ECDSA đúng chuẩn. |
| Q6.5. Phòng thủ nonce thế nào? | `docs/rfc6979_nonce_defense.md`, trang defense notes | Giải thích vai trò của RNG, deterministic nonce kiểu RFC6979, constant-time implementation và thư viện mật mã trưởng thành. |
| Q7. Có thể tối ưu verification không? | `src/shamir.py` | Shamir's trick tối ưu biểu thức `u1G + u2Q` trong bước verify ECDSA. |
| Q8. Toy demo liên hệ công cụ thật thế nào? | `openssl_demo/`, trang OpenSSL secp256k1 | OpenSSL dùng secp256k1 để ký/verify message hoặc file; không phải full Bitcoin transaction signing. |

---

## 3. Cấu trúc repo

```text
src/
  field.py             # số học modulo: egcd, mod_inv, mod_div
  ecc.py               # Point, Curve, cộng điểm, nhân đôi, scalar multiplication
  demo_params.py       # tham số toy curve dùng thống nhất trong demo/test
  ecdsa_toy.py         # ECDSA toy: keygen/sign/verify
  bitcoin_tx.py        # mini Bitcoin transaction + toy UTXO set
  nonce_attack.py      # reused nonce attack
  ecdlp_attacks.py     # brute force, BSGS, Pollard rho toy-only
  shamir.py            # naive u1G+u2Q và Shamir's trick

openssl_demo/
  gen_keys.ps1         # sinh key secp256k1 bằng OpenSSL
  sign_verify.ps1      # ký và verify message/file
  benchmark.ps1        # benchmark cẩn trọng, không overclaim

tests/
  test_field.py
  test_ecc.py
  test_ecdsa.py
  test_bitcoin_tx.py
  test_nonce_attack.py
  test_ecdlp_attacks.py
  test_shamir.py

docs/
  APP_USAGE_GUIDE.md           # hướng dẫn dùng app chi tiết
  rfc6979_nonce_defense.md     # ghi chú phòng thủ nonce

app.py                 # Streamlit app theo mạch Q0–Q8/Q9
PROJECT_PLAN.md        # kế hoạch triển khai và kiểm thử
README.md              # tài liệu nhập môn nhanh cho repo
```

---

## 4. Cài đặt

Yêu cầu khuyến nghị:

- Python 3.10+
- PowerShell nếu chạy các script `.ps1`
- OpenSSL nếu muốn chạy demo secp256k1 thật

Tạo môi trường ảo và cài dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 5. Chạy test

Chạy toàn bộ test:

```powershell
pytest -q
```

Nếu `pytest` chưa nằm trong PATH:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Test không được phụ thuộc vào mạng Bitcoin thật, ví thật hay private key thật. Mọi test phải chạy trên toy parameters hoặc key tạm sinh cục bộ.

---

## 6. Chạy Streamlit app

```powershell
streamlit run app.py
```

Nếu `streamlit` chưa nằm trong PATH:

```powershell
python -m streamlit run app.py
```

App đi theo mạch:

```text
0. Bức tranh tổng quan
1. Quyền sở hữu trong Bitcoin
2. ECC: Q = dG
3. ECDLP: Vì sao Q không làm lộ d?
4. ECDSA: Ký và kiểm tra chữ ký
5. Phòng lab giao dịch Bitcoin mô phỏng
6. Tấn công ECDSA khi dùng lại nonce
7. Ghi chú phòng thủ nonce
8. Thủ thuật Shamir
9. Demo OpenSSL secp256k1
```

Hướng dẫn chi tiết cách dùng app nằm tại:

[docs/APP_USAGE_GUIDE.md](docs/APP_USAGE_GUIDE.md)

---

## 7. Chạy OpenSSL demo

Kiểm tra OpenSSL:

```powershell
openssl version
```

Chạy các script demo:

```powershell
.\openssl_demo\gen_keys.ps1
.\openssl_demo\sign_verify.ps1
.\openssl_demo\benchmark.ps1
```

Lưu ý quan trọng:

- `gen_keys.ps1` và `sign_verify.ps1` minh họa key/sign/verify bằng secp256k1.
- Đây là ký message/file bằng OpenSSL, **không phải ký giao dịch Bitcoin đầy đủ**.
- Full Bitcoin transaction signing cần serialization, sighash rules, Script, consensus rules và UTXO set thật; repo này không triển khai các thành phần đó.

---

## 8. Kịch bản demo khuyến nghị

Khi thuyết trình, nên đi theo thứ tự sau:

1. **Trang 0–1:** Bitcoin cần chứng minh quyền chi tiêu, không phải mã hóa giao dịch.
2. **Trang 2:** Private key `d` sinh public key `Q = dG`.
3. **Trang 3:** Attacker muốn tìm `d` từ `Q` phải giải ECDLP; toy curve phá được vì nhỏ, secp256k1 thật thì không.
4. **Trang 4:** ECDSA ký và verify message; sửa dữ liệu thì chữ ký cũ fail.
5. **Trang 5:** Mini Bitcoin transaction lab: Alice có UTXO, ký giao dịch trả Bob, node verify, tamper/wrong key/double spend bị từ chối.
6. **Trang 6–7:** Reused nonce làm lộ private key; sau đó nói về phòng thủ nonce.
7. **Trang 8:** Shamir's trick là phần tối ưu verification.
8. **Trang 9:** OpenSSL secp256k1 nối toy demo với công cụ mật mã thật.

Thông điệp cần giữ xuyên suốt:

```text
Signature không bay lơ lửng.
Nó dùng để mở khóa một UTXO cụ thể trong một transaction cụ thể.
```

---

## 9. Giới hạn và cảnh báo an toàn

Repo này **không** làm các việc sau:

- tạo ví Bitcoin thật;
- quản lý seed phrase;
- import wallet thật;
- quét private key thật;
- kiểm tra quyền sở hữu tài sản thật;
- kết nối mạng Bitcoin;
- broadcast transaction;
- triển khai full Script interpreter;
- triển khai mempool, mining, block validation hay PoW.

Các demo tấn công chỉ áp dụng cho:

```text
toy curve
toy key
local temporary test keys
```

Không được diễn giải rằng:

- “Bitcoin mã hóa giao dịch bằng ECC”;
- “toy curve đại diện cho bảo mật Bitcoin thật”;
- “OpenSSL message signing là full Bitcoin transaction signing”;
- “nonce reuse chứng minh ECDSA đúng chuẩn bị phá”;
- “Pollard rho trong repo có thể phá secp256k1 thật”.

---

## 10. Tài liệu tham khảo chính

- Satoshi Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*: https://bitcoin.org/bitcoin.pdf
- Bitcoin Developer Documentation, *Transactions*: https://developer.bitcoin.org/devguide/transactions.html
- SECG, *SEC 2: Recommended Elliptic Curve Domain Parameters*: https://www.secg.org/sec2-v2.pdf
- Thomas Pornin, *RFC 6979: Deterministic Usage of DSA and ECDSA*: https://datatracker.ietf.org/doc/html/rfc6979
- OpenSSL Documentation, `openssl-dgst`: https://docs.openssl.org/3.5/man1/openssl-dgst/
- Joachim Breitner, Nadia Heninger, *Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies*.
