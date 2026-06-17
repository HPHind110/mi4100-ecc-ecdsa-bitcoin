# MI4100: ECC, ECDSA và xác thực giao dịch trong Bitcoin

Dự án này là sản phẩm học tập cho môn **MI4100: Mật mã và độ phức tạp thuật toán**.

**Tên đề tài:**  
**Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin**

Repo này không nhằm xây dựng ví Bitcoin, blockchain mới hay phần mềm giao dịch thật. Mục tiêu của repo là xây dựng một **phòng lab giáo dục** để mô phỏng và giải thích mạch liên hệ:

```text
Mật mã khóa công khai
→ ECC
→ ECDLP
→ ECDSA
→ Bitcoin UTXO case study
→ nonce attack
→ phòng thủ triển khai
→ tối ưu verification
→ OpenSSL secp256k1
```

---

## 1. Luận điểm trung tâm

Trọng tâm của project không phải là “Bitcoin dùng ECC”, mà là:

```text
ECC là nền tảng.
ECDLP là bài toán khó.
ECDSA là ứng dụng chữ ký số.
Bitcoin là case study thực tế.
```

Bitcoin không dùng ECC/ECDSA để **mã hóa giao dịch**. Giao dịch Bitcoin về cơ bản là dữ liệu công khai trên blockchain.

Điều Bitcoin cần từ ECDSA là một cơ chế khác:

```text
Chứng minh quyền chi tiêu một UTXO mà không cần tiết lộ private key.
```

Trong mô hình giáo dục của repo, ta dùng flow đơn giản giống P2PKH:

```text
UTXO bị khóa bởi public key hash.
Người tiêu cung cấp public key + ECDSA signature.
Node kiểm tra public key hash và chữ ký.
Nếu hợp lệ, giao dịch được chấp nhận.
```

---

## 2. Dự án này giúp hiểu điều gì?

| Câu hỏi | Nội dung trong repo | Ý nghĩa |
|---|---|---|
| Vì sao cần mật mã khóa công khai? | Page 0–1 | Mật mã đối xứng nhanh nhưng gặp bài toán phân phối khóa; public-key crypto hỗ trợ trao đổi khóa, xác thực và chữ ký số. |
| RSA, ElGamal/DH và ECC khác nhau thế nào? | Page 2 | So sánh nền toán: factorization/RSA problem, DLP, ECDLP; benchmark RSA/DSA/ECDSA bằng OpenSSL. |
| ECC tạo public key như thế nào? | Page 3 | Private key `d` sinh public key `Q = dG` bằng phép nhân điểm trên elliptic curve. |
| Vì sao biết `Q` không suy ra được `d`? | Page 4 | ECDLP: thử brute force, Baby-step Giant-step và Pollard rho trên toy curve. |
| ECDSA ký và verify thế nào? | Page 5 | Private key ký, public key verify; sửa message làm chữ ký cũ không còn hợp lệ. |
| Bitcoin dùng ECDSA ở đâu? | Page 6 | Mô phỏng UTXO, locking/unlocking data, public key hash, signature trong input và node verification. |
| ECDSA có tự động an toàn không? | Page 7 | Reused nonce, known nonce và partial nonce leakage có thể làm lộ private key. |
| Phòng thủ triển khai thế nào? | Page 8 | Nonce discipline, RFC6979-style, CSPRNG, constant-time, side-channel, test vector, audit và thư viện trưởng thành. |
| Có thể tối ưu verify không? | Page 8 | Shamir's trick tối ưu phép tính `u1G + u2Q` trong ECDSA verification. |
| Toy demo liên hệ công cụ thật thế nào? | Page 9 | OpenSSL sinh key `secp256k1`, ký message/file và verify bằng công cụ thật. |

---

## 3. Cấu trúc app

Streamlit app trong `app.py` gồm 10 trang:

```text
0. Mở đầu
   Từ mật mã khóa công khai đến ECC/ECDSA và Bitcoin case study.

1. Từ khóa bí mật đến khóa công khai
   Key distribution problem, hybrid cryptosystem, one-way/trapdoor/hard problems.

2. RSA, ElGamal/DH và ECC
   So sánh các hệ public-key crypto và benchmark chạy thật bằng OpenSSL.

3. Nền tảng toán học ECC
   Trường hữu hạn, đường cong elliptic, điểm sinh G, private key d và public key Q = dG.

4. ECDLP
   Brute force, Baby-step Giant-step và Pollard rho trên toy curve.

5. Chữ ký số ECDSA
   Key generation, signing, verification, nonce k và sửa message sau khi ký.

6. Bitcoin case study
   UTXO, locking condition, unlocking data, public key hash, signature và node verification.

7. Nonce attack
   Reused nonce, known nonce và partial nonce leakage.

8. Phòng thủ và tối ưu
   Checklist phòng thủ triển khai ECDSA và Shamir's trick.

9. OpenSSL và kết luận
   Sinh key secp256k1, ký/verify bằng OpenSSL và tổng kết toàn bộ đề tài.
```

---

## 4. Cấu trúc repo

Cấu trúc khuyến nghị của repo:

```text
.
├── app.py
├── requirements.txt
├── README.md
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

Một số file có thể khác tùy phiên bản repo, nhưng ý nghĩa chính là:

| File / thư mục | Vai trò |
|---|---|
| `app.py` | Streamlit app chính, chứa toàn bộ demo tương tác |
| `src/field.py` | Số học modulo: nghịch đảo, chia modulo, kiểm tra số học hữu hạn |
| `src/ecc.py` | Điểm, đường cong, cộng điểm, nhân đôi, scalar multiplication |
| `src/demo_params.py` | Tham số toy curve dùng thống nhất trong demo |
| `src/ecdsa_toy.py` | Ký và kiểm tra chữ ký ECDSA trên toy parameters |
| `src/bitcoin_tx.py` | Mô hình transaction/UTXO giáo dục kiểu Bitcoin-like |
| `src/shamir.py` | So sánh cách tính trực tiếp `u1G + u2Q` và Shamir's trick |
| `tests/` | Bộ test cho các thành phần toán và mô phỏng |
| `docs/APP_USAGE_GUIDE.md` | Hướng dẫn sử dụng app chi tiết |
| `docs/ECDSA_NONCE_ATTACK_AND_DEFENSE.md` | Ghi chú về nonce attack và phòng thủ triển khai |
| `docs/PROJECT_SCOPE_AND_REFERENCES.md` | Phạm vi project, bối cảnh Bitcoin hiện đại và tài liệu tham khảo |
| `AGENTS.md` | Chỉ dẫn chính thức cho agent khi làm việc trên repository |
| `PROJECT_SCOPE_AND_REFERENCES.md` | File điều hướng ngắn ở root, trỏ về `docs/PROJECT_SCOPE_AND_REFERENCES.md` |

---

## 5. Cài đặt

Yêu cầu khuyến nghị:

- Python 3.10+
- Streamlit
- OpenSSL trong `PATH` nếu muốn chạy benchmark và OpenSSL lab
- PowerShell hoặc terminal tương đương trên Windows

Tạo môi trường ảo:

```powershell
python -m venv .venv
```

Kích hoạt môi trường ảo trên Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Cài dependencies:

```powershell
pip install -r requirements.txt
```

Nếu PowerShell chặn script activation, có thể dùng:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 6. Chạy Streamlit app

Chạy app:

```powershell
streamlit run app.py
```

Nếu `streamlit` chưa nằm trong PATH:

```powershell
python -m streamlit run app.py
```

Sau khi chạy, Streamlit sẽ mở app trên trình duyệt local.

---

## 7. Chạy test

Chạy toàn bộ test:

```powershell
pytest -q
```

Nếu `pytest` chưa nằm trong PATH:

```powershell
python -m pytest -q
```

Hoặc dùng Python trong virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Test trong repo chỉ dùng toy parameters hoặc key tạm cục bộ. Không test nào được phụ thuộc vào ví thật, private key thật, mạng Bitcoin thật hoặc transaction thật.

---

## 8. OpenSSL trong project

App dùng OpenSSL ở hai nơi:

| Vị trí | Vai trò |
|---|---|
| Page 2 | Benchmark RSA/DSA/ECDSA bằng `openssl speed` |
| Page 9 | Sinh key `secp256k1`, ký message/file và verify bằng OpenSSL |

Kiểm tra OpenSSL:

```powershell
openssl version
```

Lưu ý quan trọng:

- `openssl speed ecdsap256` là benchmark ECDSA trên **NIST P-256**, không phải `secp256k1`.
- Page 9 mới dùng `secp256k1` để ký/verify message/file.
- Ký message/file bằng OpenSSL **không phải** full Bitcoin transaction signing.
- Full Bitcoin transaction signing cần serialization, sighash rules, Script, consensus rules và UTXO set thật. Repo này không triển khai các phần đó.

---

## 9. Kịch bản thuyết trình khuyến nghị

Một flow thuyết trình hợp lý:

1. **Page 0:** Giới thiệu mạch public-key crypto → ECC → ECDSA → Bitcoin case study.
2. **Page 1:** Giải thích vì sao mật mã khóa công khai ra đời từ bài toán phân phối khóa.
3. **Page 2:** So sánh RSA, ElGamal/DH và ECC; chạy benchmark OpenSSL để thấy trade-off hiệu năng.
4. **Page 3:** Cho thấy private key `d` tạo public key `Q = dG` như thế nào.
5. **Page 4:** Đóng vai attacker thử tìm `d` từ `Q` bằng brute force, BSGS và Pollard rho trên toy curve.
6. **Page 5:** Tạo chữ ký ECDSA, trace quá trình ký, verify message gốc và sửa message để verify fail.
7. **Page 6:** Mô phỏng Alice tiêu UTXO, node kiểm tra public key hash và chữ ký; thử sửa transaction, sai key và double spend.
8. **Page 7:** Chạy reused nonce/known nonce attack để thấy private key có thể bị khôi phục nếu nonce sai.
9. **Page 8:** Chuyển sang secure engineering: nonce discipline, RFC6979-style, constant-time, side-channel, audit; sau đó demo Shamir's trick.
10. **Page 9:** Dùng OpenSSL secp256k1 để ký/verify bằng công cụ thật và tổng kết project.

Câu chốt nên giữ:

```text
ECDSA không phải để mã hóa giao dịch Bitcoin.
ECDSA dùng để chứng minh quyền chi tiêu.
ECC/ECDLP tạo nền toán.
Nonce và implementation quyết định hệ thống có an toàn trong thực tế hay không.
```

---

## 10. Giới hạn và cảnh báo an toàn

Repo này không làm các việc sau:

- tạo ví Bitcoin thật;
- quản lý seed phrase;
- import private key thật;
- quét hoặc thử khóa thật;
- kiểm tra quyền sở hữu tài sản thật;
- kết nối mạng Bitcoin;
- broadcast transaction;
- triển khai full Bitcoin Script;
- triển khai mempool, mining, block validation hoặc PoW;
- triển khai Schnorr, Taproot hoặc MuSig2;
- thay thế thư viện mật mã production.

Các demo tấn công trong repo chỉ áp dụng cho:

```text
toy curve
toy key
local temporary test keys
```

Không được diễn giải rằng:

```text
Toy curve đại diện cho bảo mật Bitcoin thật.
Pollard rho trong repo có thể phá secp256k1 thật.
Nonce reuse chứng minh ECDSA đúng chuẩn bị phá.
OpenSSL message signing là full Bitcoin transaction signing.
Benchmark là bằng chứng an toàn.
```

Diễn giải đúng:

```text
Toy curve giúp học toán.
OpenSSL giúp đối chiếu công cụ thật.
Nonce attack minh họa lỗi triển khai.
Bitcoin case study minh họa quyền chi tiêu UTXO ở mức giáo dục.
```

---

## 11. Tài liệu nên đọc thêm

Các tài liệu phụ trong repo:

| File | Nội dung |
|---|---|
| `AGENTS.md` | Chỉ dẫn chính thức cho agent khi inspect, sửa code, viết tài liệu và giữ giới hạn an toàn của project |
| `docs/PROJECT_SCOPE_AND_REFERENCES.md` | Phạm vi project, bối cảnh Schnorr/Taproot/MuSig2 và reference theo nhóm |
| `docs/APP_USAGE_GUIDE.md` | Hướng dẫn dùng từng page trong app |
| `docs/ECDSA_NONCE_ATTACK_AND_DEFENSE.md` | Giải thích reused nonce, known nonce, partial leakage và hướng phòng thủ |
| `PROJECT_SCOPE_AND_REFERENCES.md` | File điều hướng ngắn ở root, trỏ về tài liệu phạm vi trong `docs/` |

Các nguồn tham khảo chính:

1. Neal Koblitz, **Elliptic Curve Cryptosystems**, Mathematics of Computation, 1987.
2. Victor S. Miller, **Use of Elliptic Curves in Cryptography**, CRYPTO 1985.
3. Thomas Pornin, **RFC 6979: Deterministic Usage of DSA and ECDSA**, IETF, 2013.  
   https://datatracker.ietf.org/doc/html/rfc6979
4. Bitcoin Developer Documentation, **Transactions**.  
   https://developer.bitcoin.org/devguide/transactions.html
5. Bitcoin Developer Documentation, **Transaction Reference**.  
   https://developer.bitcoin.org/reference/transactions.html
6. BIP340, **Schnorr Signatures for secp256k1**.  
   https://bips.xyz/0340
7. BIP341, **Taproot: SegWit version 1 spending rules**.  
   https://bips.xyz/0341
8. BIP327, **MuSig2 for BIP340-compatible Multi-Signatures**.  
   https://bips.xyz/327
9. OpenSSL Documentation.  
   https://docs.openssl.org/
10. OpenSSL `speed` manual.  
    https://docs.openssl.org/master/man1/openssl-speed/
11. Joachim Breitner and Nadia Heninger, **Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies**, 2013.

---

## 12. Tóm tắt cuối

Repo này nên được hiểu là một phòng lab giáo dục cho đề tài:

```text
ECC/ECDSA trong Bitcoin
```

Không phải:

```text
ví Bitcoin thật
blockchain thật
crypto library production
công cụ tấn công Bitcoin thật
```

Mục tiêu quan trọng nhất là giúp người học nhìn thấy toàn bộ mạch:

```text
Vì sao cần public-key crypto?
ECC tạo public key như thế nào?
ECDLP bảo vệ private key ra sao?
ECDSA ký và verify thế nào?
Bitcoin dùng ECDSA để chứng minh quyền chi tiêu UTXO như thế nào?
Vì sao nonce sai có thể làm lộ private key?
Triển khai đúng cần phòng thủ gì?
Toy demo liên hệ công cụ thật OpenSSL ra sao?
```
