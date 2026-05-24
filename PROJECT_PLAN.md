# PROJECT_PLAN: Lộ trình triển khai dự án ECC/ECDSA trong Bitcoin

## 1. Mục tiêu học thuật

Dự án phục vụ môn **MI4100: Mật mã và độ phức tạp thuật toán** với chủ đề:

> **Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin**

Mục tiêu không phải là tạo ví Bitcoin hay sản phẩm blockchain. Mục tiêu là xây dựng một phòng lab có khả năng giải thích, mô phỏng và kiểm thử một chuỗi vấn đề mật mã học:

```text
Bitcoin cần xác thực quyền chi tiêu
→ quyền chi tiêu được biểu diễn qua UTXO/spending condition
→ ECC sinh public key từ private key: Q = dG
→ ECDLP bảo vệ private key khỏi public key
→ ECDSA tạo chữ ký số
→ node mô phỏng dùng chữ ký để kiểm tra quyền tiêu UTXO
→ lỗi nonce trong ECDSA có thể làm lộ private key
→ tối ưu verification và công cụ thực tế được đưa vào như phần mở rộng
```

Luận điểm trung tâm cần giữ nhất quán trong toàn bộ repo:

> **Bitcoin không dùng ECC/ECDSA để mã hóa giao dịch. Bitcoin dùng ECDSA để chứng minh quyền chi tiêu đối với UTXO.**

---

## 2. Nguyên tắc thiết kế

### 2.1. Bắt đầu từ bài toán Bitcoin, không bắt đầu từ công thức ECC

Nếu mở đầu bằng công thức đường cong elliptic, người học dễ xem project như một bài toán đại số rời rạc. Nhưng điểm sáng của đề tài nằm ở việc đưa lý thuyết mật mã vào một ứng dụng cụ thể.

Vì vậy, mạch trình bày phải bắt đầu từ câu hỏi:

```text
Trong môi trường không có ngân hàng trung gian, làm sao chứng minh ai có quyền tiêu một tài sản số?
```

Từ đó mới dẫn tới:

- UTXO và spending condition;
- chữ ký số;
- ECC và ECDLP;
- ECDSA;
- transaction authentication;
- thám mã và lỗi triển khai.

### 2.2. Phân biệt rõ toy model và Bitcoin thật

Repo dùng mô hình giáo dục kiểu **P2PKH-like**, không triển khai Bitcoin thật. Các thuật ngữ cần dùng nhất quán:

```text
mini Bitcoin transaction demo
P2PKH-like educational model
toy UTXO set
demo transaction hash
```

Không dùng các cụm gây hiểu nhầm:

```text
real Bitcoin transaction signing
real Bitcoin Script implementation
real sighash implementation
real Bitcoin consensus
wallet software
```

### 2.3. Mọi demo phải phục vụ câu chuyện chính

Một module chỉ nên tồn tại nếu nó hỗ trợ ít nhất một mắt xích trong chuỗi:

```text
ownership → UTXO → ECC → ECDLP → ECDSA → transaction verification → nonce failure → defense/optimization/tooling
```

Nếu một phần không giúp người học hiểu chuỗi này, cần cân nhắc đưa vào phụ lục hoặc loại bỏ.

---

## 3. Lộ trình câu hỏi Q0–Q8/Q9

### Q0. Bitcoin cần giải bài toán gì?

**Mục tiêu:** đặt bài toán gốc.

Bitcoin hoạt động trong môi trường không có cơ sở dữ liệu trung tâm kiểu ngân hàng. Vì vậy, hệ thống cần một cơ chế để mọi node có thể tự kiểm tra:

```text
Giao dịch này có được tạo bởi người có quyền tiêu UTXO hay không?
```

**Kết quả mong muốn:** người học hiểu rằng bài toán gốc không phải là “giấu nội dung giao dịch”, mà là “chứng minh quyền chi tiêu”.

---

### Q1. Quyền sở hữu trong Bitcoin được biểu diễn thế nào?

Trong Bitcoin thật, quyền sở hữu không phải là username/password. Nó là khả năng thỏa điều kiện chi tiêu của một output chưa bị tiêu.

Trong demo giáo dục:

```text
UTXO.locking_condition ≈ pubkey_hash
unlocking_data         ≈ signature + public key
verification           ≈ hash(public key) matches + ECDSA signature verifies
```

**Module liên quan:**

- `src/bitcoin_tx.py`
- trang “Quyền sở hữu trong Bitcoin” trong `app.py`
- trang “Phòng lab giao dịch Bitcoin mô phỏng” trong `app.py`

---

### Q2. Private key sinh public key như thế nào?

ECC được đưa vào sau khi người học hiểu vì sao cần chữ ký.

Quan hệ lõi:

```text
Q = dG
```

Trong đó:

- `d`: private key;
- `G`: điểm sinh;
- `Q`: public key;
- phép nhân `dG`: scalar multiplication trên nhóm điểm elliptic curve.

**Module liên quan:**

- `src/field.py`
- `src/ecc.py`
- `src/demo_params.py`

---

### Q3. Vì sao biết public key mà không suy ra private key?

Đây là phần nối ECC với độ phức tạp thuật toán.

Bài toán:

```text
Given G and Q = dG, find d.
```

Trên toy curve, có thể minh họa bằng:

- brute force discrete logarithm: `O(n)`;
- Baby-step Giant-step: `O(√n)` thời gian và `O(√n)` bộ nhớ;
- Pollard rho: `O(√n)` kỳ vọng, bộ nhớ thấp, nhưng mang tính xác suất và được đánh dấu experimental.

**Kết luận bắt buộc:** các thuật toán này có thể phá toy curve vì `n` rất nhỏ, nhưng không làm giảm an toàn thực tế của secp256k1 trong phạm vi máy tính cổ điển hiện nay.

**Module liên quan:**

- `src/ecdlp_attacks.py` nếu đã tách thuật toán khỏi app;
- trang ECDLP trong `app.py`.

---

### Q4. ECDSA ký và xác minh như thế nào?

Nội dung cần giải thích:

- private key `d` dùng để ký;
- public key `Q` dùng để verify;
- chữ ký ECDSA là cặp `(r, s)`;
- nonce `k` là giá trị bí mật dùng một lần;
- verification kiểm tra tính nhất quán qua biểu thức `u1G + u2Q`.

**Demo bắt buộc:**

```text
sign(message, private_key)
verify(message, signature, public_key) = True
verify(tampered_message, signature, public_key) = False
```

**Module liên quan:**

- `src/ecdsa_toy.py`
- trang ECDSA trong `app.py`

---

### Q5. ECDSA đi vào Bitcoin transaction như thế nào?

Đây là lớp kết nối quan trọng nhất của dự án.

Luồng mô phỏng cần có:

1. Alice có một UTXO trong toy UTXO set.
2. Alice tạo transaction trả Bob.
3. Transaction được serialize theo định dạng giáo dục, quyết định.
4. Alice ký dữ liệu transaction bằng private key.
5. Node mô phỏng kiểm tra:
   - UTXO có tồn tại không;
   - UTXO đã bị tiêu chưa;
   - `hash(public key)` có khớp locking condition không;
   - chữ ký ECDSA có hợp lệ với transaction không.
6. Nếu các kiểm tra đều đúng, transaction được áp dụng vào toy UTXO set.

**Ca thất bại bắt buộc:**

- sửa amount sau khi ký;
- đổi người nhận sau khi ký;
- dùng public key sai;
- Mallory ký bằng key khác;
- double spend;
- missing UTXO;
- public-key-hash mismatch.

**Module liên quan:**

- `src/bitcoin_tx.py`
- `tests/test_bitcoin_tx.py`
- trang “Phòng lab giao dịch Bitcoin mô phỏng” trong `app.py`

---

### Q6. ECDSA có chắc chắn an toàn không?

Không. ECDSA chỉ an toàn khi giả định toán học và yêu cầu triển khai đều được giữ đúng.

Demo trọng tâm:

```text
hai chữ ký khác nhau dùng cùng nonce k
→ khôi phục k
→ khôi phục private key d
```

Thông điệp cần nhấn mạnh:

```text
Correct ECDSA is not broken.
Nonce reuse is an implementation failure.
```

**Module liên quan:**

- `src/nonce_attack.py`
- trang reused nonce attack trong `app.py`

---

### Q6.5. Nếu nonce reuse nguy hiểm, phòng thủ thế nào?

Sau tấn công phải có phòng thủ để tránh kết luận lệch.

Nội dung:

- không reuse nonce `k`;
- dùng nguồn ngẫu nhiên đáng tin cậy nếu ký randomized;
- dùng deterministic nonce kiểu RFC6979;
- triển khai constant-time;
- dùng thư viện trưởng thành;
- không dùng toy code cho production.

**Module/tài liệu liên quan:**

- `docs/rfc6979_nonce_defense.md`
- trang “Ghi chú phòng thủ nonce” trong `app.py`

---

### Q7. Có thể tối ưu verification không?

Verification của ECDSA cần tính:

```text
u1G + u2Q
```

Shamir's trick giúp tính đồng thời hai scalar multiplications hiệu quả hơn cách naive.

**Vai trò:** bonus thuật toán/độ phức tạp, không phải trọng tâm chính.

**Module liên quan:**

- `src/shamir.py`
- `tests/test_shamir.py`
- trang Shamir trong `app.py`

---

### Q8/Q9. Toy demo liên hệ công cụ thật như thế nào?

OpenSSL được dùng để nối toy demo với công cụ mật mã thật.

Luồng:

- sinh key secp256k1;
- trích public key;
- ký message/file;
- verify thành công;
- sửa message/file thì verify thất bại;
- đo thời gian ký/verify với cảnh báo benchmark chỉ mang tính tham khảo.

**Cảnh báo bắt buộc:** OpenSSL demo không phải full Bitcoin transaction signing.

**Module liên quan:**

- `openssl_demo/`
- trang OpenSSL trong `app.py`

---

## 4. Trạng thái triển khai hiện tại

### 4.1. Đã có

- Toy finite-field arithmetic: `src/field.py`.
- Toy elliptic curve group: `src/ecc.py`.
- Shared toy parameters: `src/demo_params.py`.
- Toy ECDSA sign/verify: `src/ecdsa_toy.py`.
- Mini Bitcoin transaction/UTXO model: `src/bitcoin_tx.py`.
- Reused nonce attack: `src/nonce_attack.py`.
- ECDLP demonstrations: brute force, BSGS, Pollard rho toy-only/experimental.
- Shamir's trick: `src/shamir.py`.
- OpenSSL scripts: `openssl_demo/`.
- Streamlit app theo mạch Q0–Q9: `app.py`.
- Hướng dẫn sử dụng app: `docs/APP_USAGE_GUIDE.md`.
- Ghi chú phòng thủ nonce: `docs/rfc6979_nonce_defense.md`.

### 4.2. Cần hoàn thiện tiếp

- Đồng bộ README với trạng thái app mới nhất.
- Hoàn thiện báo cáo học thuật chính thức.
- Tạo slide thuyết trình bám theo mạch Q0–Q9.
- Chạy kiểm thử toàn bộ app thủ công theo các kịch bản chính.
- Dọn dependency nếu có package không dùng.
- Nếu thuật toán ECDLP còn nằm trong `app.py`, cân nhắc tách sang `src/ecdlp_attacks.py` để code sạch hơn.

---

## 5. Chiến lược kiểm thử

### 5.1. Test tự động

Chạy toàn bộ test:

```powershell
pytest -q
```

Nếu `pytest` chưa nằm trong PATH:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Các nhóm test cần có:

| Nhóm test | Mục tiêu |
|---|---|
| `test_field.py` | modular inverse, modular division, lỗi khi không có nghịch đảo |
| `test_ecc.py` | point addition, point doubling, scalar multiplication, point at infinity |
| `test_ecdsa.py` | sign/verify, tampered message fail, wrong key fail |
| `test_bitcoin_tx.py` | valid spend, tampered tx, wrong key, Mallory key, double spend, missing UTXO |
| `test_nonce_attack.py` | reused nonce recover `k` và `d` |
| `test_ecdlp_attacks.py` | brute force/BSGS recover toy private key; Pollard rho deterministic nếu có |
| `test_shamir.py` | Shamir result trùng naive result |

### 5.2. Test thủ công app

Phải chạy ít nhất các kịch bản:

1. **ECDSA message signing:** ký message, sửa message, verify fail.
2. **Valid transaction:** Alice có UTXO, Alice trả Bob, node accept, apply thành công.
3. **Tampered transaction:** sửa amount hoặc recipient sau khi ký, node reject.
4. **Wrong key:** Mallory ký hoặc thay public key, node reject.
5. **Double spend:** cùng UTXO tiêu lần đầu được, lần hai bị từ chối.
6. **Reused nonce:** recover được `k` và `d` trên toy curve.
7. **OpenSSL:** sinh key secp256k1, ký message, sửa message, verify fail.

Không tuyên bố pass nếu chưa chạy thật.

---

## 6. Phạm vi an toàn

Dự án không được làm các việc sau:

- tạo ví Bitcoin thật;
- sinh seed phrase thật;
- import wallet thật;
- quét private key;
- kiểm tra tài sản thật;
- tương tác mạng Bitcoin;
- broadcast transaction;
- triển khai mining, mempool, block validation, PoW;
- triển khai công cụ tấn công real secp256k1.

Mọi tấn công chỉ được giới hạn trong:

```text
toy curve
toy key
local temporary keys
```

---

## 7. Hướng mở rộng tương lai

### 7.1. Bổ sung ghi chú Bitcoin hiện đại

Có thể thêm `docs/modern_bitcoin_crypto_notes.md` để giải thích ngắn:

- Bitcoin truyền thống dùng ECDSA trên secp256k1;
- Taproot đưa Schnorr/BIP340 vào bối cảnh hiện đại;
- MuSig2/BIP327 liên quan multisignature hiện đại;
- các phần này là bối cảnh mở rộng, không thay thế trọng tâm ECDSA của repo.

### 7.2. Tách thuật toán ECDLP khỏi app

Nếu app tiếp tục phình to, nên đưa các hàm:

```text
brute_force_dlog_demo
baby_step_giant_step_demo
pollard_rho_dlog_demo
```

vào `src/ecdlp_attacks.py`, còn `app.py` chỉ giữ phần UI.

### 7.3. Viết báo cáo và slide

Báo cáo và slide nên bám mạch:

```text
Bitcoin ownership
→ UTXO spending condition
→ ECC: Q = dG
→ ECDLP hardness
→ ECDSA sign/verify
→ mini transaction authentication
→ nonce failure
→ defense
→ optimization/tooling
```

Không nên biến báo cáo thành:

- lịch sử Bitcoin quá dài;
- giới thiệu blockchain chung chung;
- thuần công thức ECC;
- thuần demo attack;
- so sánh benchmark thiếu kiểm soát.

---

## 8. Tiêu chí hoàn thành

Project được xem là đạt yêu cầu khi người xem có thể trả lời rõ ràng:

1. Bitcoin cần chữ ký số để làm gì?
2. UTXO là gì và tại sao chữ ký gắn với UTXO?
3. ECC tạo public key từ private key như thế nào?
4. ECDLP bảo vệ private key ra sao?
5. ECDSA ký và verify bằng công thức nào ở mức khái niệm?
6. Node mô phỏng kiểm tra giao dịch theo các bước nào?
7. Vì sao sửa transaction sau khi ký làm verify fail?
8. Vì sao dùng sai key không mở được UTXO?
9. Vì sao double spend bị reject?
10. Vì sao reused nonce làm lộ private key?
11. Cần phòng thủ nonce như thế nào?
12. Shamir's trick tối ưu phần nào?
13. OpenSSL demo liên hệ toy code với công cụ thật ra sao?

Câu kết luận cần hiện rõ trong mọi deliverable:

```text
ECC cung cấp cấu trúc toán học.
ECDLP cung cấp giả định độ khó.
ECDSA cung cấp cơ chế chữ ký.
Bitcoin dùng chữ ký để xác thực quyền chi tiêu UTXO.
Triển khai sai, đặc biệt là nonce sai, có thể phá hỏng toàn bộ an toàn.
```
