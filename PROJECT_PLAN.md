# Lộ trình triển khai dự án theo Q0–Q8

## 1. Luận điểm dự án

Dự án phục vụ môn học **MI4100: Mật mã và độ phức tạp thuật toán** với chủ đề:

> Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin

Luận điểm trung tâm cần được giữ nhất quán trong toàn bộ mã nguồn, tài liệu, báo cáo và giao diện là:

> Bitcoin không dùng ECC/ECDSA để mã hóa giao dịch. Bitcoin dùng ECDSA để chứng minh **quyền chi tiêu** đối với UTXO.

Chuỗi ý tưởng cốt lõi của dự án là:

```text
Bitcoin cần quyền sở hữu không cần ngân hàng
→ quyền sở hữu được biểu diễn như khả năng thỏa điều kiện chi tiêu của UTXO
→ trong P2PKH-like educational demo, điều đó được đơn giản hóa thành tạo chữ ký hợp lệ
→ ECC cho quan hệ Q = dG
→ ECDLP làm cho việc suy ra d từ Q là khó
→ ECDSA dùng d để ký và dùng Q để xác minh
→ node toy model chỉ chấp nhận giao dịch khi chữ ký hợp lệ và UTXO chưa bị tiêu
→ sửa dữ liệu, dùng sai khóa, thiếu UTXO, double spend đều thất bại
→ reuse nonce làm lộ private key
→ triển khai đúng mới bảo vệ được ECDSA
→ Shamir's trick là phần tối ưu hóa verification
→ OpenSSL secp256k1 nối toy math với công cụ mật mã thật
```

## 2. Vì sao dự án bắt đầu từ quyền sở hữu Bitcoin, không phải từ công thức ECC

Nếu bắt đầu trực tiếp từ công thức đường cong elliptic, sinh viên dễ nhìn dự án như một bài tập đại số rời rạc hơn là một lời giải cho bài toán của Bitcoin. Điều dự án cần trả lời trước tiên không phải là “đường cong elliptic là gì?” mà là:

```text
Bitcoin đang cần giải bài toán nào trong môi trường không tin cậy?
```

Câu trả lời là:

```text
Bitcoin cần cơ chế chứng minh quyền chi tiêu mà không cần ngân hàng trung tâm.
```

Từ đó mới suy ra mạch logic đúng:

1. Quyền sở hữu trong Bitcoin không phải username/password, cũng không phải một ô số dư trong cơ sở dữ liệu tập trung.
2. Trong mô hình UTXO, “sở hữu” nghĩa là có khả năng thỏa điều kiện chi tiêu của một đầu ra chưa tiêu.
3. Trong **P2PKH-like educational demo**, điều kiện đó được đơn giản hóa thành:
   - `hash(pubkey)` khớp khóa của UTXO
   - chữ ký trên dữ liệu transaction demo xác minh thành công
4. Chỉ sau khi người học hiểu “chữ ký dùng để làm gì”, dự án mới đi xuống tầng toán học:
   - ECC giải thích `Q = dG`
   - ECDLP giải thích vì sao biết `Q` chưa đủ để có `d`
   - ECDSA giải thích cơ chế ký/xác minh

Vì vậy, dự án phải được kể theo hướng **vấn đề Bitcoin trước, công cụ mật mã sau**. ECC là nền tảng toán học; ECDSA là cơ chế chữ ký; Bitcoin là ngữ cảnh ứng dụng làm cho các thành phần đó có ý nghĩa.

## 3. Lộ trình Q0–Q8

### Q0. Bitcoin cần giải bài toán gì?

Mục tiêu của phần mở đầu là đặt bài toán:

```text
Trong môi trường không có ngân hàng hay cơ sở dữ liệu trung tâm, làm sao chứng minh ai có quyền tiêu một tài sản số?
```

Kết quả mong muốn:
- Người đọc hiểu Bitcoin cần **proof of spending authority**.
- Dự án không mở đầu bằng công thức ECC hay benchmark.
- App/README/report phải thống nhất thông điệp này.

### Q1. Quyền sở hữu trong Bitcoin được biểu diễn thế nào?

Phần này phải chuyển khái niệm “ownership” sang mô hình UTXO:

```text
Ownership = ability to satisfy the spending condition of a UTXO
```

Trong phạm vi demo:
- Dùng **P2PKH-like educational model**, không tuyên bố là full Bitcoin Script.
- Giải thích:
  - locking condition ≈ `pubkey_hash`
  - unlocking data ≈ `signature + public key`
  - verification = `hash(public key)` khớp và chữ ký hợp lệ

Phần này được hiện thực chính qua:
- `src/bitcoin_tx.py`
- demo transaction trong `app.py`
- test từ chối `wrong key`, `missing UTXO`, `double spend`, `pubkey hash mismatch`

### Q2. Private key sinh ra public key như thế nào?

Phần này giới thiệu ECC như tầng toán học phía dưới:

```text
Q = dG
```

Yêu cầu triển khai:
- có mô hình `Curve`, `Point`
- có cộng điểm
- có doubling
- có scalar multiplication bằng double-and-add

Phần này phải dùng **toy curve** để trực quan:

```text
p = 17
a = 3
b = 5
G = (1, 3)
n = 23
```

Và phải ghi rõ:
- đây không phải `secp256k1`
- đây không an toàn
- chỉ dùng để học toán và kiểm thử

### Q3. Vì sao biết public key mà không suy ra private key?

Phần này giới thiệu ECDLP:

```text
Given G and Q = dG, find d
```

Mục tiêu giáo dục:
- Cho thấy toy curve đủ nhỏ để brute force discrete log.
- Giải thích vì sao cùng ý tưởng đó không áp dụng được cho `secp256k1` thật.

Yêu cầu triển khai:
- `brute_force_dlog(curve, G, Q, max_k)` là bắt buộc
- `baby_step_giant_step_dlog(...)` là mở rộng nên có
- `pollard_rho_dlog(...)` chỉ là **toy-only experimental**

Kết luận bắt buộc:
- brute force là `O(n)`
- BSGS là `O(sqrt(n))` thời gian và bộ nhớ
- Pollard rho có kỳ vọng `O(sqrt(n))` với bộ nhớ thấp
- với `secp256k1`, `sqrt(n)` vẫn là không khả thi

### Q4. ECDSA ký và xác minh như thế nào?

Đây là phần chuyển từ “black box signature” sang cơ chế bên trong của ECDSA.

Nội dung cần giải thích:
- `r, s` là hai thành phần của chữ ký
- `k` là nonce cho từng chữ ký
- ký dùng private key `d`
- xác minh dùng public key `Q`
- verification kiểm tra tính nhất quán qua biểu thức `u1G + u2Q`

Yêu cầu demo:
- `sign(message, private_key)`
- `verify(message, signature, public_key) == True`
- sửa message thì verify fail
- sai public key thì verify fail

Yêu cầu kiểm tra đầu vào:
- `d = 0` hoặc `d >= n` phải bị từ chối
- `k = 0`, `r = 0`, `s = 0` hoặc nonce không khả nghịch modulo `n` phải bị xử lý rõ ràng
- public key không hợp lệ hoặc điểm không thuộc đường cong không được bỏ qua âm thầm

### Q5. ECDSA đi vào Bitcoin transaction như thế nào?

Đây là lớp kết nối quan trọng nhất giữa mật mã và Bitcoin.

Phần này phải chứng minh rằng chữ ký không tồn tại độc lập; nó dùng để mở khóa một UTXO cụ thể trong một giao dịch cụ thể.

Lộ trình triển khai:
1. Alice sở hữu một UTXO trong toy UTXO set.
2. Alice tạo transaction chi tiêu UTXO đó cho Bob.
3. Transaction được serialize theo định dạng quyết định, phục vụ giáo dục.
4. Dữ liệu unsigned transaction được băm.
5. Alice ký bản băm bằng private key.
6. Node toy model xác minh chữ ký bằng public key và kiểm tra UTXO chưa tiêu.
7. Nếu hợp lệ thì chấp nhận chi tiêu; nếu không thì từ chối.

Các cấu trúc dữ liệu cần có:
- `TxOutput`
- `OutPoint`
- `TxInput`
- `Transaction`
- `UTXOSet`

Các helper chính:
- `serialize_pubkey_demo(Q)`
- `hash160_demo(data)`
- `pubkey_hash_demo(Q)`
- `serialize_unsigned_tx(tx)`
- `txid_demo(tx)`
- `sign_transaction_input(...)`
- `verify_transaction_input(...)`
- `demo_bitcoin_spending_flow()`

Các ca thất bại bắt buộc:
- valid spend → accepted
- tampered output amount → rejected
- tampered recipient → rejected
- wrong public key → rejected
- Mallory ký bằng khóa khác → rejected
- double spend → rejected
- missing UTXO → rejected
- public-key-hash mismatch → rejected

Phần này phải dùng wording trung thực:
- mini Bitcoin transaction demo
- P2PKH-like educational model
- toy UTXO set
- không phải real Bitcoin serialization/script/sighash/consensus

### Q6. ECDSA có chắc chắn an toàn không?

Phần này phải cho thấy:

```text
ECDSA không “tự nhiên” an toàn nếu triển khai sai.
```

Demo trọng tâm:
- hai chữ ký dùng chung nonce `k`
- khôi phục `k`
- khôi phục private key `d`

Thông điệp bắt buộc:
- ECDSA không bị “phá” chỉ vì công thức sai
- reuse nonce là **implementation failure**
- toán tốt không cứu được triển khai sai

### Q6.5. Nếu nonce reuse nguy hiểm, phòng thủ thế nào?

Ngay sau phần tấn công cần có phần phòng thủ để tránh thông điệp lệch.

Nội dung nên có:
- không bao giờ reuse nonce `k`
- nếu dùng randomized signing thì phải có RNG tốt
- deterministic ECDSA kiểu RFC6979 giúp giảm phụ thuộc vào RNG
- constant-time implementation vẫn quan trọng
- production phải dùng thư viện trưởng thành như OpenSSL hoặc libsecp256k1
- không nên tự viết production ECDSA từ toy code

Phần này chủ yếu là giải thích, không cần quảng bá toy code như giải pháp production.

### Q7. Có thể tối ưu verification không?

Phần này là bonus theo đúng tinh thần môn học về thuật toán và độ phức tạp.

Nội dung:
- verification trong ECDSA có biểu thức `u1G + u2Q`
- Shamir's trick giúp tính đồng thời hai phép nhân vô hướng hiệu quả hơn
- so sánh với cách naive `u1*G + u2*Q`

Yêu cầu:
- không để phần tối ưu hóa lấn át câu chuyện ownership, transaction signing và nonce failure
- kiểm thử phải chứng minh kết quả Shamir trùng với cách naive

### Q8. Toy demo có liên hệ công cụ thật không?

Phần cuối cùng nối toy math với tooling thực tế:
- OpenSSL sinh khóa `secp256k1`
- trích xuất public key
- ký message/file
- verify thành công
- sửa message/file thì verify fail

Benchmark phải được trình bày cẩn thận:
- benchmark bằng `openssl speed` là benchmark của OpenSSL, không phải mô phỏng Bitcoin
- nếu dùng `ecdsap256` thì phải ghi rõ đó là **NIST P-256 / prime256v1**
- nếu `openssl speed` không benchmark trực tiếp `secp256k1` thì phải nói thẳng điều đó
- không được kết luận “ECDSA luôn nhanh hơn RSA”
- phải nêu rằng benchmark phụ thuộc operation, key size, curve, implementation và machine
- phải nêu rằng RSA verification có thể nhanh tùy exponent và implementation

Kết luận của Q8:
- OpenSSL secp256k1 là công cụ mật mã thật cho message/file signing
- nhưng không phải full Bitcoin transaction signing

## 4. Các module đã được triển khai

### Nền tảng toán học và ECC
- `src/field.py`
  - `egcd`, `mod_inv`, `mod_div`
  - nền tảng cho nghịch đảo modulo và phép chia trên trường hữu hạn
- `src/ecc.py`
  - `Point`, `Curve`
  - point addition, point doubling, scalar multiplication

### Tham số demo và ECDSA toy
- `src/demo_params.py`
  - gom tham số toy curve dùng chung toàn dự án
- `src/ecdsa_toy.py`
  - `keygen`, `sign`, `verify`, `hash_message_to_int`
  - mô phỏng chữ ký số ECDSA trên toy curve

### Tầng Bitcoin giáo dục
- `src/bitcoin_tx.py`
  - mô hình mini transaction/UTXO kiểu P2PKH-like educational demo
  - kiểm tra spending authority bằng `signature + public key`

### Tầng tấn công và phân tích
- `src/nonce_attack.py`
  - demo recovered nonce và recovered private key khi reuse nonce
- `src/ecdlp_attacks.py`
  - brute force discrete log
  - Baby-step Giant-step
  - Pollard rho ở trạng thái toy-only experimental
- `src/shamir.py`
  - tính `u1G + u2Q` theo cách naive và theo Shamir's trick

### Tầng OpenSSL
- `openssl_demo/gen_keys.ps1`
  - sinh key `secp256k1`
- `openssl_demo/sign_verify.ps1`
  - ký và verify message/file
- `openssl_demo/benchmark.ps1`
  - benchmark RSA và ECDSA bằng `openssl speed`
  - đã tách rõ benchmark P-256 khỏi secp256k1 sign/verify demo

### Tài liệu và giao diện
- `app.py`
  - Streamlit app theo storyline Q0–Q8
- `README.md`
  - tóm tắt dự án, cách chạy và caveat chính
- `docs/rfc6979_nonce_defense.md`
  - ghi chú phòng thủ nonce

## 5. Module còn thiếu / module mới được bổ sung

### Module mới đã bổ sung so với cấu trúc tối thiểu ban đầu
- `src/bitcoin_tx.py`
  - bổ sung lớp kết nối giữa ECDSA và UTXO spending authority
- `src/ecdlp_attacks.py`
  - bổ sung lớp minh họa ECDLP trên toy curve
- `src/demo_params.py`
  - gom tham số toy curve để tránh lệch giữa các module
- `docs/rfc6979_nonce_defense.md`
  - bổ sung phần Q6.5 về phòng thủ triển khai
- `tests/test_bitcoin_tx.py`
  - test cho spending flow và các ca thất bại
- `tests/test_ecdlp_attacks.py`
  - test cho brute force/BSGS và phần experimental khi phù hợp

### Thành phần vẫn có thể bổ sung thêm
- `docs/storyline_q0_q8.md`
  - tài liệu kể chuyện ngắn gọn theo đúng Q0–Q8 để dùng chung cho báo cáo/slides/app
- `docs/modern_bitcoin_crypto_notes.md`
  - ghi chú tách riêng phần mở rộng hiện đại như Schnorr, Taproot, MuSig2
- ghi chú riêng cho benchmark methodology
  - giúp tránh diễn giải quá mức từ `openssl speed`

## 6. Phạm vi an toàn

Phạm vi của dự án là **giáo dục và nghiên cứu học thuật**, không phải triển khai thực chiến.

Những giới hạn bắt buộc:
- không tạo ví Bitcoin thật
- không import wallet thật
- không quét private key thật
- không thử sở hữu quỹ thật
- không tương tác với mạng Bitcoin thật
- không broadcast transaction
- không triển khai full script interpreter, mempool, mining, block validation hay PoW

Các demo tấn công chỉ được áp dụng cho:
- toy curve
- toy key
- khóa tạm sinh cục bộ cho test/demo

Các tuyên bố phải tránh:
- “Bitcoin mã hóa giao dịch bằng ECC”
- “toy curve đại diện cho bảo mật Bitcoin thật”
- “OpenSSL sign file = full Bitcoin signing”
- “nonce reuse chứng minh ECDSA bản thân nó bị phá”

## 7. Chiến lược kiểm thử

Chiến lược test phải bám theo cả hai lớp:
- đúng toán học
- đúng câu chuyện Bitcoin spending authority

### Test nền tảng toán học
- `test_field.py`
  - modular inverse đúng
  - trường hợp không có nghịch đảo phải raise lỗi rõ ràng
- `test_ecc.py`
  - point addition đúng
  - scalar multiplication đúng
  - xử lý điểm vô cực và dữ liệu không hợp lệ khi cần

### Test ECDSA toy
- `test_ecdsa.py`
  - sign/verify thành công
  - message bị sửa thì verify fail
  - sai public key thì fail
  - trường hợp fixed `k` hoạt động đúng trong phạm vi test giáo dục

### Test mini Bitcoin transaction
- `test_bitcoin_tx.py`
  - valid spend thành công
  - tampered transaction thất bại
  - wrong key thất bại
  - Mallory-signed attempt thất bại
  - double spend thất bại
  - missing UTXO thất bại
  - public-key-hash mismatch thất bại

### Test reused nonce attack
- `test_nonce_attack.py`
  - khôi phục nonce thành công
  - khôi phục private key thành công
  - nhấn mạnh đây là demo implementation failure

### Test tối ưu hóa và ECDLP
- `test_shamir.py`
  - kết quả Shamir trùng với naive
- `test_ecdlp_attacks.py`
  - brute force khôi phục toy private key
  - BSGS khôi phục toy private key nếu được bật
  - Pollard rho chỉ nên test theo cách deterministic, không flaky

### Nguyên tắc chạy test
- mặc định chạy `pytest -q`
- nếu môi trường global không resolve đúng package `src`, có thể chạy qua virtualenv của repo:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

- không tuyên bố test pass nếu chưa chạy thật
- test không được phụ thuộc mạng Bitcoin thật

## 8. Hướng mở rộng tương lai

### Baby-step Giant-step

Giữ như hướng mở rộng quan trọng cho Q3:
- dùng để so sánh với brute force
- nhấn mạnh đánh đổi `time-memory`
- chỉ chạy trên toy curve

### Pollard rho toy-only experimental

Giữ như phần mở rộng có kiểm soát:
- phải ghi rõ experimental
- chỉ áp dụng trên toy curve
- có thể fail graceful trên các cạnh đặc biệt của nhóm nhỏ
- không quảng bá như công cụ tấn công secp256k1

### BIP340 Schnorr / Taproot context

Có thể thêm phần bối cảnh hiện đại:
- Bitcoin hiện đại đã có Taproot và Schnorr signatures
- đây là phần mở rộng lịch sử kỹ thuật, không thay thế trọng tâm ECDSA của dự án
- chỉ nên dùng để trả lời “Bitcoin hiện nay còn dùng gì ngoài ECDSA?”

### MuSig2 context

Có thể bổ sung một mục ngắn về:
- multisignature hiện đại
- aggregate signing
- MuSig2 và bối cảnh BIP327

Phần này chỉ nên là context:
- không triển khai full protocol nếu không có yêu cầu riêng
- không làm lệch trục chính của dự án khỏi ECC/ECDSA trong Bitcoin

### Không mở rộng sang wallet/network/broadcasting

Các hướng sau **không** thuộc roadmap tương lai của repo này:
- ví Bitcoin thật
- quản lý seed phrase
- kết nối node
- phát giao dịch lên mạng
- quét blockchain thật
- full consensus engine

Giới hạn này giúp dự án giữ đúng mục tiêu môn học:

```text
giải thích cơ chế quyền chi tiêu bằng ECC/ECDSA trong Bitcoin,
không biến thành sản phẩm blockchain.
```
