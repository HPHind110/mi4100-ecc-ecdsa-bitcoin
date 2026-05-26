# PROJECT_IMPLEMENTATION_PLAN.md

# Kế hoạch triển khai project ECC/ECDSA trong Bitcoin

## 1. Mục đích của tài liệu

Tài liệu này mô tả cách triển khai project:

```text
Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin
```

File này dùng để làm rõ:

- project được xây theo logic nào;
- mỗi module trong code phục vụ phần kiến thức nào;
- app demo đi theo mạch nào;
- test cần kiểm tra những gì;
- báo cáo và slide nên bám theo cấu trúc nào.

Tài liệu này không phải báo cáo học thuật hoàn chỉnh. Nó là bản kế hoạch triển khai và bản đồ kiến trúc để từ đó viết báo cáo, làm slide và kiểm thử project.

---

## 2. Mục tiêu của project

Project có ba mục tiêu chính.

### 2.1. Mục tiêu học thuật

Giải thích được mạch từ mật mã khóa công khai đến ECDSA trong Bitcoin:

```text
Mật mã khóa công khai
→ ECC
→ ECDLP
→ ECDSA
→ Bitcoin UTXO case study
```

Trong đó:

- ECC cung cấp nền tảng toán học.
- ECDLP là bài toán khó đứng sau ECC.
- ECDSA là thuật toán chữ ký số dựa trên ECC.
- Bitcoin là case study dùng ECDSA để xác thực quyền chi tiêu UTXO.

---

### 2.2. Mục tiêu mô phỏng

Xây dựng một Streamlit app có thể cho người học tự thao tác:

- so sánh public-key cryptography;
- quan sát `Q = dG`;
- thử tấn công ECDLP trên toy curve;
- ký và verify ECDSA;
- mô phỏng transaction kiểu Bitcoin-like;
- thử sửa transaction, dùng sai key, double spend;
- thử nonce attack;
- xem checklist phòng thủ triển khai;
- đối chiếu với OpenSSL `secp256k1`.

---

### 2.3. Mục tiêu triển khai phần mềm

Repo cần có cấu trúc đủ rõ để phục vụ cả demo và kiểm thử:

```text
app.py          → giao diện học tập và mô phỏng tương tác
src/            → logic toán học và mô hình toy
tests/          → kiểm thử tự động
docs/           → hướng dẫn sử dụng và ghi chú kỹ thuật
README.md       → giới thiệu nhanh project
PROJECT_PLAN.md → kế hoạch triển khai
```

Code không hướng tới production crypto. Tất cả phần toy crypto chỉ phục vụ giáo dục.

---

## 3. Luận điểm trung tâm

Luận điểm cần giữ xuyên suốt project:

```text
Bitcoin không dùng ECDSA để mã hóa giao dịch.
Bitcoin dùng ECDSA để chứng minh quyền chi tiêu UTXO.
```

Mạch giải thích nên được hiểu như sau:

```text
Người dùng giữ private key d.
Từ d tạo public key Q = dG.
Do ECDLP khó, từ Q rất khó suy ra d.
Người dùng dùng d để ký dữ liệu giao dịch bằng ECDSA.
Node dùng Q để verify chữ ký.
Nếu chữ ký hợp lệ và điều kiện khóa UTXO khớp, giao dịch được chấp nhận.
```

Điểm quan trọng:

```text
An toàn không chỉ đến từ ECDLP.
An toàn còn phụ thuộc vào nonce k, cách triển khai, constant-time, CSPRNG và thư viện được kiểm chứng.
```

---

## 4. Phạm vi project

### 4.1. Project có làm

Project triển khai hoặc mô phỏng các phần sau:

| Nhóm nội dung | Có trong project | Vai trò |
|---|---|---|
| Mật mã khóa công khai | Có | Đặt bối cảnh cho RSA, ElGamal/DH, ECC |
| ECC toy curve | Có | Minh họa trường hữu hạn, đường cong, cộng điểm, nhân điểm |
| Public key generation | Có | Minh họa `Q = dG` |
| ECDLP demo | Có | Minh họa độ khó đi ngược từ `Q` về `d` |
| ECDSA toy | Có | Minh họa sign/verify |
| Bitcoin-like UTXO lab | Có | Minh họa ECDSA mở khóa UTXO |
| Nonce attack | Có | Minh họa lỗi reused/known nonce làm lộ private key |
| Defense checklist | Có | Minh họa nguyên tắc phòng thủ khi triển khai ECDSA |
| Shamir's trick | Có | Minh họa tối ưu verification |
| OpenSSL secp256k1 | Có | Đối chiếu toy demo với công cụ thật |

---

### 4.2. Project không làm

Project không triển khai:

- ví Bitcoin thật;
- seed phrase;
- import private key thật;
- Bitcoin Script đầy đủ;
- sighash thật;
- transaction serialization thật của Bitcoin;
- consensus rules;
- mempool;
- mining;
- network;
- broadcast transaction;
- Schnorr signatures;
- Taproot;
- MuSig2;
- crypto library production.

Các demo attack chỉ chạy trên:

```text
toy curve
toy key
local temporary keys
```

Không được dùng project để thử khóa thật, ví thật hoặc giao dịch thật.

---

## 5. Kiến trúc triển khai tổng thể

Kiến trúc project gồm bốn lớp.

```text
Lớp 1: Toán học nền tảng
    field.py
    ecc.py
    demo_params.py

Lớp 2: Mật mã toy
    ecdsa_toy.py
    shamir.py

Lớp 3: Mô hình ứng dụng Bitcoin-like
    bitcoin_tx.py

Lớp 4: Giao diện và demo
    app.py
```

Ngoài ra có:

```text
tests/  → kiểm thử tự động
docs/   → hướng dẫn và phụ lục
```

---

## 6. Thiết kế module

### 6.1. `src/field.py`

Vai trò:

```text
Cung cấp số học modulo cho toàn bộ project.
```

Các chức năng chính nên có:

- tính `gcd`;
- tìm nghịch đảo modulo;
- chia modulo;
- xử lý trường hợp không tồn tại nghịch đảo.

Kiến thức phục vụ:

```text
Trường hữu hạn F_p
Phép chia modulo
Nghịch đảo modulo trong ECDSA
```

Test cần có:

- nghịch đảo tồn tại;
- nghịch đảo không tồn tại;
- chia modulo đúng;
- lỗi được xử lý rõ.

---

### 6.2. `src/ecc.py`

Vai trò:

```text
Mô phỏng nhóm điểm trên elliptic curve.
```

Các chức năng chính:

- biểu diễn điểm `Point`;
- biểu diễn đường cong `Curve`;
- kiểm tra điểm nằm trên curve;
- cộng điểm;
- nhân đôi điểm;
- scalar multiplication `kP`;
- điểm vô cực;
- bộ đếm phép toán nếu cần cho Shamir's trick.

Kiến thức phục vụ:

```text
ECC
Cộng điểm
Nhân điểm
Q = dG
ECDLP
ECDSA
```

Test cần có:

- cộng hai điểm;
- nhân đôi điểm;
- cộng với điểm vô cực;
- scalar multiplication;
- kết quả vẫn nằm trên curve.

---

### 6.3. `src/demo_params.py`

Vai trò:

```text
Định nghĩa toy curve thống nhất cho toàn bộ demo và test.
```

File này nên chứa:

- `p`;
- `a`;
- `b`;
- điểm sinh `G`;
- order mô phỏng `n`;
- hàm trả về tham số dùng chung.

Lý do cần file riêng:

```text
Tránh mỗi module tự định nghĩa tham số khác nhau.
Giúp test và app dùng cùng một curve.
Giảm lỗi lệch tham số.
```

---

### 6.4. `src/ecdsa_toy.py`

Vai trò:

```text
Mô phỏng ECDSA trên toy curve.
```

Các chức năng chính:

- hash message về số modulo `n`;
- ký message;
- verify chữ ký;
- xử lý các edge-case như `r = 0`, `s = 0`, nonce không có nghịch đảo.

Kiến thức phục vụ:

```text
ECDSA signing
ECDSA verification
Vai trò của nonce k
Message integrity
```

Test cần có:

- ký xong verify đúng;
- sửa message thì verify fail;
- dùng sai public key thì verify fail;
- nonce không hợp lệ bị xử lý.

---

### 6.5. `src/bitcoin_tx.py`

Vai trò:

```text
Mô phỏng transaction và UTXO set kiểu Bitcoin-like.
```

Các khái niệm cần có:

- `OutPoint`;
- `TxInput`;
- `TxOutput`;
- `Transaction`;
- `UTXOSet`;
- public key hash;
- serialize unsigned transaction;
- sign transaction input;
- verify transaction input.

Luồng mô phỏng:

```text
Alice có UTXO.
Alice tạo transaction trả Bob.
Alice ký transaction bằng private key.
Node kiểm tra UTXO, public key hash và chữ ký.
Nếu hợp lệ, UTXO cũ bị tiêu và output mới được tạo.
```

Test cần có:

- transaction hợp lệ được chấp nhận;
- sửa amount sau khi ký bị từ chối;
- đổi receiver sau khi ký bị từ chối;
- Mallory ký bằng key khác bị từ chối;
- thay public key bị từ chối;
- double spend bị từ chối;
- missing UTXO bị từ chối.

---

### 6.6. `src/shamir.py`

Vai trò:

```text
So sánh cách tính trực tiếp u1G + u2Q với Shamir's trick.
```

Các chức năng chính:

- `naive_mul_add(curve, u1, G, u2, Q)`;
- `shamir_mul(curve, u1, G, u2, Q)`.

Mục tiêu:

```text
Hai cách phải cho cùng kết quả P.
Shamir's trick có thể giảm số phép toán điểm trong verification.
```

Test cần có:

- kết quả Shamir bằng kết quả naive;
- chạy được với nhiều cặp `u1`, `u2`;
- xử lý các trường hợp nhỏ.

---

### 6.7. `app.py`

Vai trò:

```text
Giao diện chính để người học thao tác với toàn bộ project.
```

`app.py` có thể chứa nhiều UI helper, nhưng phần logic toán/mật mã nên ưu tiên nằm trong `src/`.

Nếu `app.py` quá lớn, có thể tách dần:

```text
src/ecdlp_attacks.py
src/benchmark_utils.py
src/openssl_utils.py
```

Tuy nhiên, không nên tách quá sớm nếu project vẫn đang trong giai đoạn demo môn học. Ưu tiên ổn định luồng demo trước.

---

## 7. Thiết kế các page trong app

### Page 0. Mở đầu

Mục tiêu:

```text
Đặt bản đồ toàn bộ project.
```

Nội dung cần có:

- vì sao cần public-key crypto;
- vì sao ECC đáng học;
- vì sao Bitcoin được chọn làm case study;
- roadmap 10 page.

Dụng ý:

```text
Giúp người xem hiểu project không bắt đầu từ Bitcoin.
Project bắt đầu từ public-key crypto, rồi đi đến ECC, ECDSA và Bitcoin case study.
```

---

### Page 1. Từ khóa bí mật đến khóa công khai

Mục tiêu:

```text
Giải thích vì sao public-key cryptography ra đời.
```

Nội dung:

- symmetric cryptography;
- bài toán phân phối khóa;
- public-key cryptography;
- hybrid cryptosystem;
- one-way function;
- trapdoor;
- hard problems.

Demo tương tác:

```text
Cho N người dùng.
So sánh số khóa đối xứng cần quản lý với số cặp khóa public-key.
```

Dụng ý:

```text
Từ vấn đề phân phối khóa dẫn tới public-key crypto.
Từ public-key crypto dẫn tới RSA, ElGamal/DH và ECC.
```

---

### Page 2. RSA, ElGamal/DH và ECC

Mục tiêu:

```text
Đặt ECC vào bản đồ các hệ khóa công khai.
```

Nội dung:

- RSA;
- Diffie-Hellman / ElGamal;
- ECC;
- DSA-style signatures;
- ECDSA;
- benchmark OpenSSL.

Demo tương tác:

```text
Chạy openssl speed cho RSA/DSA/ECDSA.
Hiển thị bảng sign/s và verify/s.
Giải thích trade-off: RSA verify rất nhanh, ECDSA P-256 sign rất nhanh, benchmark không phải bằng chứng an toàn.
```

Dụng ý:

```text
Không kết luận ECC luôn nhanh hơn RSA.
Kết luận đúng là các hệ có trade-off khác nhau.
ECC đáng học vì hiệu quả, khóa ngắn, nền toán ECDLP và ứng dụng ECDSA.
```

---

### Page 3. Nền tảng toán học ECC

Mục tiêu:

```text
Giải thích Q = dG.
```

Nội dung:

- trường hữu hạn `F_p`;
- đường cong elliptic;
- điểm sinh `G`;
- private key `d`;
- public key `Q`;
- scalar multiplication;
- double-and-add.

Demo tương tác:

```text
User chọn d.
App tính Q = dG.
App trace double-and-add.
App vẽ đường cong thực để lấy trực giác và vẽ điểm rời rạc trên F_p để đúng bản chất crypto.
```

Dụng ý:

```text
Tính xuôi Q = dG là nhanh.
Chiều ngược Q -> d sẽ là ECDLP ở Page 4.
```

---

### Page 4. ECDLP

Mục tiêu:

```text
Cho người học thấy vì sao public key Q không làm lộ private key d.
```

Nội dung:

- bài toán ECDLP;
- attacker biết `G`, `Q`, curve;
- attacker không biết `d`;
- brute force;
- Baby-step Giant-step;
- Pollard rho;
- toy curve vs curve thật.

Demo tương tác:

```text
User chọn d.
App tạo Q.
Attacker thử tìm d bằng các thuật toán.
```

Dụng ý:

```text
Toy curve phá được vì n nhỏ.
Curve thật an toàn vì n rất lớn.
```

---

### Page 5. Chữ ký số ECDSA

Mục tiêu:

```text
Giải thích cách ký và verify bằng ECDSA.
```

Nội dung:

- key generation `Q = dG`;
- hash message;
- nonce `k`;
- signing formula;
- verification formula;
- vai trò của public key.

Demo tương tác:

```text
User chọn d, k, message.
App tạo chữ ký (r, s).
App trace signing.
App verify message gốc.
User sửa message để thấy verify fail.
```

Dụng ý:

```text
Private key dùng để ký.
Public key dùng để verify.
Chữ ký gắn với dữ liệu cụ thể.
```

---

### Page 6. Bitcoin case study

Mục tiêu:

```text
Giải thích ECDSA đi vào mô hình Bitcoin-like như thế nào.
```

Nội dung:

- wallet;
- UTXO;
- locking condition;
- unlocking data;
- public key hash;
- signature trong input;
- node verification;
- double spend.

Demo tương tác:

```text
Alice có UTXO.
Alice tạo transaction trả Bob.
Alice ký transaction.
Node verify.
Apply vào UTXO set.
Thử sửa amount, đổi receiver, Mallory ký, thay public key, double spend.
```

Dụng ý:

```text
ECDSA không bay lơ lửng.
ECDSA được dùng để mở khóa một UTXO cụ thể trong một transaction cụ thể.
```

---

### Page 7. Nonce attack

Mục tiêu:

```text
Chứng minh triển khai sai ECDSA có thể làm lộ private key.
```

Nội dung:

- reused nonce;
- known nonce;
- partial nonce leakage;
- side-channel;
- lattice attack ở mức ghi chú.

Demo tương tác:

```text
User chọn d, k, message.
App tạo hai chữ ký dùng cùng nonce.
App khôi phục k và d.
Hoặc app mô phỏng known nonce attack từ một chữ ký.
```

Dụng ý:

```text
Không cần phá ECDLP.
Chỉ cần nonce sai là ECDSA có thể sụp đổ.
```

---

### Page 8. Phòng thủ và tối ưu

Mục tiêu:

```text
Nối lý thuyết ECDSA với secure engineering và optimization.
```

Tab 1: Phòng thủ triển khai

Nội dung:

- threat model;
- nonce discipline;
- RFC6979-style;
- CSPRNG;
- constant-time;
- side-channel;
- test vector;
- audit;
- toy/prototype/production;
- risk gate/fatal finding.

Demo tương tác:

```text
User chọn cách sinh nonce, cách triển khai, context sử dụng.
App đánh giá risk score minh họa.
App báo lỗi critical nếu có fatal finding.
```

Tab 2: Shamir's trick

Nội dung:

- ECDSA verification cần tính `P = u1G + u2Q`;
- cách naive tính riêng `u1G` và `u2Q`;
- Shamir's trick tính kết hợp;
- so sánh số phép toán.

Dụng ý:

```text
Tab 1: làm đúng để an toàn.
Tab 2: làm khéo để hiệu quả.
```

---

### Page 9. OpenSSL và kết luận

Mục tiêu:

```text
Đối chiếu toy demo với công cụ thật và tổng kết project.
```

Nội dung:

- sinh key `secp256k1`;
- ký message/file;
- verify message gốc;
- sửa message để verify fail;
- mini benchmark;
- kết luận toàn bộ project.

Dụng ý:

```text
Toy demo giúp hiểu toán.
OpenSSL cho thấy ký/verify tồn tại trong công cụ mật mã thật.
Nhưng OpenSSL message signing không phải full Bitcoin transaction signing.
```

---

## 8. Kế hoạch triển khai theo giai đoạn

### Giai đoạn 1. Xây nền toán học

Mục tiêu:

```text
Có đủ field arithmetic và ECC group operations.
```

Công việc:

- viết `field.py`;
- viết `ecc.py`;
- định nghĩa toy curve trong `demo_params.py`;
- viết test cho modular inverse, point addition, scalar multiplication.

Kết quả đầu ra:

```text
Có thể tính kG trên toy curve.
Có thể kiểm tra điểm thuộc curve.
Có thể dùng chung curve cho toàn bộ project.
```

---

### Giai đoạn 2. Xây ECDSA toy

Mục tiêu:

```text
Có thể ký và verify message trên toy curve.
```

Công việc:

- viết `ecdsa_toy.py`;
- implement `hash_message_to_int`;
- implement `sign`;
- implement `verify`;
- xử lý edge-case của toy curve;
- viết test sign/verify.

Kết quả đầu ra:

```text
sign(message, d) tạo (r, s).
verify(message, (r, s), Q) trả True.
Tampered message hoặc wrong key trả False.
```

---

### Giai đoạn 3. Xây ECDLP demo

Mục tiêu:

```text
Cho người học thấy chiều Q -> d khó hơn chiều d -> Q.
```

Công việc:

- implement brute force discrete log;
- implement Baby-step Giant-step;
- implement Pollard rho ở mức demo;
- tạo bảng so sánh độ phức tạp;
- tích hợp vào Page 4.

Kết quả đầu ra:

```text
Toy private key có thể được recover.
Người học hiểu vì sao toy curve không đại diện cho curve thật.
```

---

### Giai đoạn 4. Xây Bitcoin-like transaction lab

Mục tiêu:

```text
Mô phỏng ECDSA mở khóa UTXO.
```

Công việc:

- thiết kế `OutPoint`, `TxInput`, `TxOutput`, `Transaction`;
- thiết kế `UTXOSet`;
- tạo public key hash;
- serialize unsigned transaction theo format giáo dục;
- ký input;
- verify input;
- apply transaction vào UTXO set;
- viết test các case hợp lệ/thất bại.

Kết quả đầu ra:

```text
Alice tiêu UTXO hợp lệ được chấp nhận.
Tamper, wrong key, hash mismatch, double spend bị từ chối.
```

---

### Giai đoạn 5. Xây nonce attack

Mục tiêu:

```text
Minh họa lỗi triển khai nonce làm lộ private key.
```

Công việc:

- reused nonce attack;
- known nonce attack;
- partial nonce leakage ở mức ghi chú;
- xử lý edge-case toy curve;
- viết test recover `k` và `d`.

Kết quả đầu ra:

```text
Hai chữ ký dùng cùng k có thể recover k và d.
Một chữ ký với known k có thể recover d.
Người học hiểu đây là implementation failure, không phải ECDSA đúng chuẩn bị phá.
```

---

### Giai đoạn 6. Xây phòng thủ và tối ưu

Mục tiêu:

```text
Sau attack phải có phần defense và optimization.
```

Công việc:

- viết checklist phòng thủ triển khai;
- thêm threat model mini;
- thêm risk score minh họa;
- thêm risk gate/fatal finding;
- giải thích RFC6979-style, CSPRNG, constant-time, side-channel, test vector, audit;
- implement Shamir's trick;
- viết test Shamir bằng naive result.

Kết quả đầu ra:

```text
Page 8 cho thấy secure engineering quan trọng như thế nào.
Shamir's trick minh họa tối ưu verification, không phải phòng thủ nonce attack.
```

---

### Giai đoạn 7. Xây OpenSSL lab

Mục tiêu:

```text
Đối chiếu toy demo với công cụ thật.
```

Công việc:

- kiểm tra OpenSSL trong PATH;
- sinh key `secp256k1`;
- ký message/file;
- verify message gốc;
- sửa message và verify fail;
- mini benchmark;
- ghi rõ giới hạn của OpenSSL demo.

Kết quả đầu ra:

```text
Người học thấy ECDSA secp256k1 chạy được bằng công cụ thật.
Không nhầm với full Bitcoin transaction signing.
```

---

### Giai đoạn 8. Hoàn thiện tài liệu

Mục tiêu:

```text
Repo đủ rõ để người khác đọc, chạy, hiểu và thuyết trình.
```

Công việc:

- viết lại `README.md`;
- viết `APP_USAGE_GUIDE.md`;
- viết `ECDSA_NONCE_ATTACK_AND_DEFENSE.md`;
- viết `PROJECT_SCOPE_AND_REFERENCES.md`;
- viết/hoàn thiện `PROJECT_PLAN.md`;
- chuẩn bị báo cáo;
- chuẩn bị slide.

Kết quả đầu ra:

```text
Người đọc hiểu project làm gì, không làm gì, chạy thế nào và thuyết trình theo mạch nào.
```

---

## 9. Chiến lược kiểm thử

### 9.1. Test tự động

Chạy toàn bộ test:

```powershell
pytest -q
```

Nếu `pytest` chưa nằm trong PATH:

```powershell
python -m pytest -q
```

Nhóm test cần có:

| Nhóm test | Mục tiêu |
|---|---|
| Field arithmetic | Modular inverse, modular division, lỗi không có nghịch đảo |
| ECC | Point addition, point doubling, scalar multiplication, point at infinity |
| ECDSA | Sign/verify, tampered message fail, wrong key fail |
| Bitcoin transaction | Valid spend, tampered tx, wrong key, double spend, missing UTXO |
| Nonce attack | Reused nonce recover `k`, recover `d`; known nonce recover `d` |
| ECDLP | Brute force/BSGS recover toy private key; Pollard rho nếu ổn định |
| Shamir | Shamir result trùng naive result |

---

### 9.2. Test thủ công app

Cần chạy thủ công các flow chính:

1. Page 1: thay đổi số người dùng và quan sát số khóa.
2. Page 2: chạy benchmark OpenSSL, đọc sign/s và verify/s.
3. Page 3: chọn `d`, quan sát `Q = dG`, xem double-and-add.
4. Page 4: chạy brute force, BSGS, Pollard rho nếu bật.
5. Page 5: ký message, sửa message, verify fail.
6. Page 6: Alice trả Bob hợp lệ, node accept.
7. Page 6: sửa amount hoặc receiver sau khi ký, node reject.
8. Page 6: Mallory ký hoặc thay public key, node reject.
9. Page 6: double spend, node reject.
10. Page 7: reused nonce recover `k` và `d`.
11. Page 7: known nonce recover `d`.
12. Page 8: chọn cấu hình nguy hiểm để thấy critical finding.
13. Page 8: chạy Shamir's trick và so sánh với naive.
14. Page 9: sinh key OpenSSL, ký message, verify message gốc pass, sửa message fail.

Không nên tuyên bố hoàn thành nếu chưa chạy các flow này.

---

## 10. Mapping từ project sang báo cáo

Báo cáo nên đi theo cấu trúc sau.

### Chương 1. Giới thiệu

Nội dung:

- bối cảnh mật mã khóa công khai;
- vì sao ECC quan trọng;
- vì sao ECDSA liên quan Bitcoin;
- phạm vi project.

Liên hệ app:

```text
Page 0, Page 1
```

---

### Chương 2. Cơ sở lý thuyết

Nội dung:

- symmetric vs public-key crypto;
- RSA, ElGamal/DH, ECC;
- trường hữu hạn;
- elliptic curve;
- scalar multiplication;
- ECDLP.

Liên hệ app:

```text
Page 1, Page 2, Page 3, Page 4
```

---

### Chương 3. ECDSA

Nội dung:

- key generation;
- signing;
- verification;
- vai trò nonce;
- lỗi reused nonce và known nonce.

Liên hệ app:

```text
Page 5, Page 7
```

---

### Chương 4. Bitcoin case study

Nội dung:

- UTXO;
- locking condition;
- unlocking data;
- public key hash;
- signature trong input;
- node verification;
- tampering và double spend.

Liên hệ app:

```text
Page 6
```

---

### Chương 5. Triển khai và kiểm thử

Nội dung:

- kiến trúc repo;
- module `src/`;
- app Streamlit;
- test tự động;
- test thủ công;
- OpenSSL demo;
- benchmark;
- giới hạn của project.

Liên hệ app:

```text
Page 2, Page 8, Page 9
```

---

### Chương 6. Kết luận

Nội dung:

- ECC là nền tảng public-key crypto;
- ECDLP là giả định độ khó;
- ECDSA là ứng dụng chữ ký số;
- Bitcoin dùng ECDSA để xác thực quyền chi tiêu;
- an toàn cần cả toán học và triển khai đúng;
- giới hạn và hướng mở rộng.

Liên hệ app:

```text
Page 9
```

---

## 11. Mapping từ project sang slide

Slide nên ngắn hơn báo cáo. Một cấu trúc phù hợp:

| Slide | Nội dung |
|---|---|
| 1 | Tên đề tài, thành viên, môn học |
| 2 | Vấn đề: vì sao cần public-key crypto và chữ ký số |
| 3 | Bản đồ project: public-key → ECC → ECDSA → Bitcoin |
| 4 | ECC: `Q = dG` |
| 5 | ECDLP: vì sao public key không lộ private key |
| 6 | ECDSA: signing và verification |
| 7 | Bitcoin case study: UTXO và quyền chi tiêu |
| 8 | Transaction lab: valid spend, tamper, wrong key, double spend |
| 9 | Nonce attack: reused nonce/known nonce |
| 10 | Phòng thủ: RFC6979-style, CSPRNG, constant-time, side-channel |
| 11 | Shamir's trick và OpenSSL |
| 12 | Kết luận và giới hạn |

Slide không nên quá sa vào công thức. Công thức chỉ cần đủ để bảo vệ logic:

```text
Q = dG
ECDLP: given G, Q find d
s = k^(-1)(h + rd) mod n
P = u1G + u2Q
```

---

## 12. Tiêu chí hoàn thành project

Project được xem là hoàn thành khi đạt các tiêu chí sau.

### 12.1. Về kiến thức

Người xem trả lời được:

1. Vì sao cần public-key crypto?
2. ECC khác RSA và ElGamal/DH ở đâu?
3. `Q = dG` có ý nghĩa gì?
4. ECDLP bảo vệ private key như thế nào?
5. ECDSA ký và verify bằng ý tưởng nào?
6. Bitcoin dùng chữ ký để làm gì?
7. UTXO là gì?
8. Vì sao sửa transaction sau khi ký bị từ chối?
9. Vì sao wrong key không tiêu được UTXO?
10. Vì sao double spend bị reject?
11. Vì sao nonce reuse làm lộ private key?
12. Phòng thủ nonce cần gì?
13. Shamir's trick tối ưu phần nào?
14. OpenSSL demo liên hệ toy code với công cụ thật ra sao?

---

### 12.2. Về code

Repo cần:

- chạy được Streamlit app;
- chạy được test;
- không dùng key thật;
- không phụ thuộc mạng Bitcoin;
- không để secret/generated artifact trong repo;
- tài liệu đủ rõ để người khác chạy lại.

---

### 12.3. Về báo cáo và slide

Báo cáo và slide cần giữ đúng phạm vi:

```text
ECC/ECDSA trong Bitcoin
```

Không lệch sang:

- lịch sử Bitcoin quá dài;
- blockchain chung chung;
- Schnorr/Taproot quá sâu;
- benchmark overclaim;
- full Bitcoin transaction signing;
- tấn công secp256k1 thật.

---

## 13. Hướng mở rộng

Các hướng mở rộng có thể nhắc nhưng không cần triển khai:

| Hướng mở rộng | Lý do chỉ nên nhắc |
|---|---|
| Schnorr / BIP340 | Quan trọng trong Bitcoin hiện đại nhưng khác ECDSA |
| Taproot / BIP341 | Liên quan script/spending rules hiện đại, vượt phạm vi demo |
| MuSig2 / BIP327 | Cần multisignature protocol và nonce coordination |
| Lattice attack chi tiết | Cần nền toán lattice, dễ lệch khỏi project |
| Full Bitcoin sighash | Cần transaction serialization và consensus detail |
| Hardware side-channel | Rất sâu về implementation/security engineering |

Các phần này có thể nằm trong phụ lục hoặc mục hướng phát triển tương lai, không nên đưa vào mạch demo chính.

---

## 14. Kết luận triển khai

Project nên được hiểu là một phòng lab giáo dục có cấu trúc:

```text
Hiểu vì sao cần public-key crypto.
Đặt ECC cạnh RSA và ElGamal/DH.
Hiểu toán ECC qua Q = dG.
Thấy ECDLP là chiều khó.
Dùng ECDSA để ký và verify.
Đưa ECDSA vào Bitcoin UTXO case study.
Thấy nonce sai làm lộ private key.
Biết các nguyên tắc phòng thủ triển khai.
Nhìn một tối ưu verification bằng Shamir's trick.
Đối chiếu với OpenSSL secp256k1.
```

Câu kết luận cuối cùng:

```text
ECC cung cấp cấu trúc toán học.
ECDLP cung cấp giả định độ khó.
ECDSA cung cấp cơ chế chữ ký số.
Bitcoin dùng chữ ký để xác thực quyền chi tiêu UTXO.
Triển khai sai, đặc biệt là nonce sai, có thể phá hỏng toàn bộ an toàn.
```
