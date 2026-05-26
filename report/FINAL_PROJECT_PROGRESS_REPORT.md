# BÁO CÁO TỔNG HỢP KẾT QUẢ DỰ ÁN

# Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin

**Môn học:** MI4100 — Mật mã và độ phức tạp thuật toán  
**Tính chất dự án:** mô phỏng giáo dục, không phải ví Bitcoin thật, không phải phần mềm giao dịch thật, không phải thư viện mật mã production  
**Trạng thái:** tổng hợp những phần đã thiết kế, triển khai và hoàn thiện trong project đến thời điểm hiện tại

---

## Tóm tắt

Dự án xây dựng một phòng lab giáo dục để giải thích mối liên hệ giữa **mật mã khóa công khai**, **mật mã đường cong elliptic** (*Elliptic Curve Cryptography* — ECC), bài toán **logarit rời rạc trên đường cong elliptic** (*Elliptic Curve Discrete Logarithm Problem* — ECDLP), thuật toán chữ ký số **ECDSA** (*Elliptic Curve Digital Signature Algorithm*) và cơ chế xác thực quyền chi tiêu trong mô hình Bitcoin-like UTXO.

Luận điểm trung tâm của dự án là:

```text
Bitcoin không dùng ECC/ECDSA để mã hóa giao dịch.
Bitcoin dùng ECDSA để chứng minh quyền chi tiêu UTXO.
```

Dự án không bắt đầu từ Bitcoin như một câu chuyện blockchain chung chung, cũng không trình bày ECC như một tập công thức rời rạc. Mạch hiện tại của project được thiết kế theo hướng:

```text
Mật mã khóa công khai
→ RSA / ElGamal-DH / ECC
→ ECC: Q = dG
→ ECDLP
→ ECDSA
→ Bitcoin UTXO case study
→ nonce attack
→ phòng thủ triển khai
→ Shamir's trick
→ OpenSSL secp256k1
```

Đến thời điểm hiện tại, project đã có một Streamlit app tương tác gồm 10 page, mô phỏng được toàn bộ mạch học tập: từ bối cảnh mật mã khóa công khai, so sánh RSA/ElGamal/ECC, mô phỏng toán ECC trên toy curve, tấn công ECDLP trên toy curve, ký và kiểm tra chữ ký ECDSA, mô phỏng transaction Bitcoin-like, khai thác lỗi nonce trong ECDSA, checklist phòng thủ triển khai, tối ưu verification bằng Shamir's trick, và đối chiếu bằng OpenSSL trên `secp256k1`.

Kết luận chính rút ra từ dự án:

```text
ECC cung cấp cấu trúc toán học.
ECDLP cung cấp giả định độ khó.
ECDSA cung cấp cơ chế chữ ký số.
Bitcoin dùng chữ ký số để xác thực quyền chi tiêu UTXO.
An toàn thực tế không chỉ đến từ toán học, mà còn phụ thuộc vào triển khai đúng.
```

---

## Từ khóa

ECC, ECDSA, ECDLP, Bitcoin, UTXO, secp256k1, chữ ký số, public-key cryptography, nonce reuse, RFC6979, CSPRNG, constant-time, side-channel, Shamir's trick, OpenSSL.

---

# 1. Mục tiêu và phạm vi dự án

## 1.1. Mục tiêu học thuật

Dự án phục vụ việc học môn **Mật mã và độ phức tạp thuật toán** thông qua một case study cụ thể: ứng dụng chữ ký số ECDSA trong Bitcoin.

Các mục tiêu học thuật chính:

1. Hiểu vì sao mật mã khóa công khai ra đời.
2. Đặt ECC vào bản đồ các hệ mật mã khóa công khai cùng RSA và ElGamal/DH.
3. Hiểu quan hệ khóa trong ECC:

   ```text
   Q = dG
   ```

4. Hiểu ECDLP là bài toán khó bảo vệ private key.
5. Hiểu cơ chế ký và xác minh chữ ký ECDSA.
6. Hiểu ECDSA được dùng như thế nào trong mô hình Bitcoin-like UTXO.
7. Hiểu vì sao lỗi nonce có thể làm lộ private key.
8. Hiểu các nguyên tắc phòng thủ triển khai ECDSA.
9. Hiểu Shamir's trick như một tối ưu trong bước verification.
10. Biết cách liên hệ toy demo với công cụ thật như OpenSSL.

---

## 1.2. Phạm vi có triển khai

Dự án hiện tập trung vào các phần sau:

| Nhóm nội dung | Trạng thái | Ý nghĩa |
|---|---:|---|
| Mật mã khóa công khai | Đã đưa vào app | Giải thích key distribution, public key, private key, hybrid cryptosystem |
| So sánh RSA / ElGamal-DH / ECC | Đã đưa vào app | Đặt ECC vào bối cảnh public-key crypto |
| Benchmark RSA/DSA/ECDSA bằng OpenSSL | Đã đưa vào app | Minh họa trade-off sign/verify |
| Toy finite field và ECC | Đã triển khai | Mô phỏng trường hữu hạn, đường cong, cộng điểm, nhân điểm |
| `Q = dG` | Đã triển khai | Minh họa private key sinh public key |
| ECDLP attack demo | Đã triển khai | Brute force, BSGS, Pollard rho trên toy curve |
| ECDSA sign/verify | Đã triển khai | Ký message, verify message gốc, sửa message để kiểm tra chữ ký |
| Bitcoin transaction lab | Đã triển khai | Mô phỏng UTXO, public key hash, signature, node verification |
| Nonce attack | Đã triển khai | Reused nonce, known nonce, partial leakage note |
| Defense checklist | Đã triển khai | Risk checklist, threat model, critical gate, remediation notes |
| Shamir's trick | Đã triển khai | So sánh naive `u1G + u2Q` với Shamir optimization |
| OpenSSL secp256k1 | Đã triển khai | Sinh key, ký, verify, sửa message để verify fail |

---

## 1.3. Phạm vi không triển khai

Dự án không triển khai các phần sau:

- ví Bitcoin thật;
- seed phrase;
- import private key thật;
- kiểm tra tài sản thật;
- kết nối mạng Bitcoin;
- broadcast transaction;
- Bitcoin Script đầy đủ;
- sighash thật của Bitcoin;
- consensus rules;
- mempool;
- mining;
- block validation;
- Proof-of-Work;
- Schnorr signatures;
- Taproot;
- MuSig2;
- lattice attack chi tiết;
- thư viện mật mã production.

Các phần attack chỉ chạy trên:

```text
toy curve
toy key
local temporary keys
```

Dự án không được dùng để tấn công, quét hoặc khôi phục khóa thật.

---

# 2. Luận điểm trung tâm và mạch logic

## 2.1. Luận điểm trung tâm

Cách hiểu đúng:

```text
Bitcoin dùng chữ ký số để xác thực quyền chi tiêu.
Bitcoin không dùng ECDSA để mã hóa giao dịch.
```

Trong Bitcoin-like model:

```text
Wallet giữ private key.
Public key được tạo từ private key bằng Q = dG.
UTXO bị khóa bởi điều kiện liên quan đến public key hash.
Người muốn tiêu UTXO cung cấp public key và chữ ký.
Node kiểm tra public key hash và chữ ký.
Nếu hợp lệ, transaction được chấp nhận.
```

---

## 2.2. Mạch học tập cuối cùng của project

Sau nhiều lần chỉnh lại scope, project hiện đi theo mạch:

```text
0. Vì sao cần public-key crypto?
1. Từ symmetric crypto đến public-key crypto
2. RSA, ElGamal/DH và ECC
3. ECC: Q = dG
4. ECDLP: vì sao Q không lộ d
5. ECDSA: private key ký, public key verify
6. Bitcoin case study: chữ ký mở khóa UTXO
7. Nonce attack: triển khai sai làm lộ private key
8. Phòng thủ và tối ưu: secure engineering + Shamir's trick
9. OpenSSL secp256k1: đối chiếu toy demo với công cụ thật
```

Mạch này cân bằng ba lớp:

| Lớp | Nội dung |
|---|---|
| Lý thuyết mật mã | Public-key crypto, ECC, ECDLP, ECDSA |
| Thuật toán và độ phức tạp | Double-and-Add, brute force, BSGS, Pollard rho, Shamir's trick |
| Ứng dụng | Bitcoin UTXO, transaction authentication, OpenSSL secp256k1 |

---

# 3. Kiến trúc project

## 3.1. Cấu trúc tổng thể

Cấu trúc dự án được tổ chức theo các lớp:

```text
Lớp 1: Số học nền tảng
    field.py

Lớp 2: ECC toy
    ecc.py
    demo_params.py

Lớp 3: ECDSA toy
    ecdsa_toy.py

Lớp 4: Bitcoin-like transaction model
    bitcoin_tx.py

Lớp 5: Tối ưu verification
    shamir.py

Lớp 6: Giao diện học tập
    app.py

Lớp 7: Tài liệu
    README.md
    PROJECT_PLAN.md
    PROJECT_SCOPE_AND_REFERENCES.md
    APP_USAGE_GUIDE.md
    ECDSA_NONCE_ATTACK_AND_DEFENSE.md
    AGENTS.md
```

---

## 3.2. Vai trò các module chính

| File / module | Vai trò |
|---|---|
| `src/field.py` | Số học modulo: nghịch đảo modulo, chia modulo, Euclid mở rộng |
| `src/ecc.py` | Điểm, đường cong, cộng điểm, nhân đôi điểm, scalar multiplication |
| `src/demo_params.py` | Toy curve dùng chung cho app và test |
| `src/ecdsa_toy.py` | Ký và kiểm tra chữ ký ECDSA trên toy curve |
| `src/bitcoin_tx.py` | Mô hình transaction/UTXO giáo dục kiểu Bitcoin-like |
| `src/shamir.py` | So sánh naive `u1G + u2Q` và Shamir's trick |
| `app.py` | Streamlit app chính |
| `tests/` | Kiểm thử các module |
| `docs/` | Hướng dẫn sử dụng và ghi chú kỹ thuật |
| `README.md` | Giới thiệu nhanh project |
| `PROJECT_PLAN.md` | Kế hoạch triển khai |
| `PROJECT_SCOPE_AND_REFERENCES.md` | Phạm vi và tài liệu tham khảo |
| `AGENTS.md` | Hướng dẫn cho Agent CLI khi mở rộng project |

---

## 3.3. Tham số toy curve

Dự án dùng toy curve nhỏ để học:

```text
p = 17
a = 3
b = 5
G = (1, 3)
n = 23
```

Ý nghĩa:

- `p`: modulo của trường hữu hạn.
- `a`, `b`: hệ số đường cong.
- `G`: điểm sinh.
- `n`: order mô phỏng dùng trong ECDSA.

Cảnh báo bắt buộc:

```text
Toy curve chỉ dùng để học.
Toy curve không an toàn.
Toy curve không phải secp256k1.
Kết quả attack trên toy curve không phá được Bitcoin thật.
```

---

# 4. Những phần đã hoàn thiện trong app

## 4.1. Page 0 — Mở đầu

Page 0 hiện được thiết kế lại để không còn mở đầu theo kiểu Bitcoin-first.

Nội dung chính:

- vì sao cần mật mã khóa công khai;
- vì sao ECC đáng học;
- vì sao Bitcoin được chọn làm case study;
- bản đồ logic toàn bộ project;
- roadmap 10 page.

Dụng ý:

```text
Giúp người xem hiểu Bitcoin không phải điểm xuất phát.
Trọng tâm là ECC/ECDSA trong public-key crypto, Bitcoin là case study thực tế.
```

---

## 4.2. Page 1 — Từ khóa bí mật đến khóa công khai

Page 1 giải thích bối cảnh mật mã học:

- mật mã khóa bí mật;
- bài toán phân phối khóa;
- mật mã khóa công khai;
- hybrid cryptosystem;
- one-way function;
- trapdoor function;
- hard problems.

Demo tương tác:

```text
User chọn số người dùng N.
App so sánh số khóa đối xứng theo từng cặp với số cặp khóa public-key.
```

Dụng ý:

```text
Cho thấy public-key crypto ra đời để giải quyết bài toán phân phối khóa và xác thực trong hệ thống lớn.
```

---

## 4.3. Page 2 — RSA, ElGamal/DH và ECC

Page 2 đặt ECC vào bản đồ public-key cryptography.

Nội dung chính:

- RSA dựa trên factorization/RSA problem;
- Diffie-Hellman/ElGamal dựa trên DLP;
- ECC dựa trên ECDLP;
- so sánh chữ ký RSA, DSA-style và ECDSA;
- benchmark OpenSSL cho RSA/DSA/ECDSA.

Đã bổ sung phần đọc benchmark cẩn thận:

```text
RSA verify có thể rất nhanh.
ECDSA P-256 sign có thể rất nhanh.
ECDSA P-384 chậm hơn P-256 đáng kể.
Không được kết luận ECC luôn nhanh hơn RSA.
Benchmark đo hiệu năng, không chứng minh an toàn.
ecdsap256 trong OpenSSL speed là NIST P-256, không phải secp256k1.
```

Dụng ý:

```text
ECC không được trình bày như một công thức tự cô lập.
Nó là một họ public-key crypto đứng cạnh RSA và ElGamal/DH.
```

---

## 4.4. Page 3 — Nền tảng toán học ECC

Page 3 giải thích:

- trường hữu hạn `F_p`;
- đường cong elliptic;
- điểm sinh `G`;
- private key `d`;
- public key `Q`;
- phép nhân điểm `Q = dG`;
- double-and-add;
- trực giác hình học trên số thực;
- bản chất rời rạc trên trường hữu hạn.

Demo tương tác:

```text
User chọn d.
App tính Q = dG.
App trace double-and-add.
App vẽ đường cong thực để lấy trực giác.
App vẽ các điểm rời rạc trên F_p để đúng bản chất crypto.
```

Dụng ý:

```text
Tính Q từ d là nhanh.
Chiều ngược Q -> d sẽ được đưa sang Page 4 dưới tên ECDLP.
```

---

## 4.5. Page 4 — ECDLP

Page 4 mô phỏng vai attacker.

Attacker biết:

```text
curve
G
Q
```

Attacker không biết:

```text
d
```

Các thuật toán demo:

| Thuật toán | Ý tưởng | Độ phức tạp |
|---|---|---|
| Brute force | Thử từng `k` cho đến khi `kG = Q` | `O(n)` |
| Baby-step Giant-step | Gặp nhau ở giữa | `O(√n)` time, `O(√n)` memory |
| Pollard rho | Random-walk tìm collision | `O(√n)` expected time, low memory |

Dụng ý:

```text
Toy curve phá được vì n nhỏ.
Curve thật như secp256k1 không thể bị phá bằng demo này.
```

---

## 4.6. Page 5 — Chữ ký số ECDSA

Page 5 giải thích cơ chế ECDSA:

- key generation;
- signing;
- verification;
- hash message;
- nonce `k`;
- chữ ký `(r, s)`;
- verify bằng public key `Q`.

Demo tương tác:

```text
User chọn d, k và message.
App tạo chữ ký ECDSA.
App trace quá trình ký.
App verify message gốc.
User sửa message.
App kiểm tra chữ ký cũ với message đã sửa.
```

Đã bổ sung xử lý edge-case toy curve:

```text
Vì n quá nhỏ, có lúc message sửa vẫn verify True.
App cảnh báo đây là hạn chế của toy curve.
App có nút tìm message sửa chắc chắn bị từ chối.
```

Dụng ý:

```text
ECDSA chứng minh người ký có private key mà không cần tiết lộ private key.
Chữ ký gắn với dữ liệu cụ thể.
```

---

## 4.7. Page 6 — Bitcoin case study

Page 6 hiện là phần mô phỏng Bitcoin-like transaction/UTXO.

Nội dung chính:

- ví giữ private key;
- UTXO là output chưa bị tiêu;
- locking condition;
- unlocking data;
- public key hash;
- signature trong input;
- node verification;
- double spend.

Flow chính:

```text
Alice có UTXO.
Alice tạo transaction trả Bob.
Alice ký transaction.
Node kiểm tra UTXO + public key hash + ECDSA signature.
Nếu hợp lệ, transaction được apply vào UTXO set.
```

Các kịch bản đã có:

| Kịch bản | Kết quả mong muốn |
|---|---|
| Alice trả Bob hợp lệ | Accept |
| Sửa amount sau khi ký | Reject |
| Đổi receiver sau khi ký | Reject |
| Mallory ký bằng key khác | Reject |
| Thay public key bằng Mallory | Reject |
| Double spend | Reject lần tiêu sau |
| Chế độ tự do | User tự thử |

Dụng ý:

```text
ECDSA không bay lơ lửng.
Nó dùng để mở khóa một UTXO cụ thể trong một transaction cụ thể.
```

---

## 4.8. Page 7 — Nonce attack

Page 7 giải thích rằng ECDLP khó chưa đủ để bảo vệ hệ thống nếu ECDSA triển khai sai nonce.

Các mode đã có:

1. Reused nonce.
2. Known nonce.
3. Partial nonce leakage note.

Reused nonce demo:

```text
Hai message khác nhau được ký bằng cùng k.
Từ hai chữ ký, app khôi phục k.
Từ k, app khôi phục private key d.
```

Known nonce demo:

```text
Một chữ ký có nonce k bị lộ.
Từ chữ ký và k, app khôi phục private key d.
```

Partial nonce leakage:

```text
Giải thích lý thuyết về rò một phần nonce qua nhiều chữ ký.
Nhắc tới side-channel và lattice attack ở mức ghi chú.
Không triển khai lattice attack để tránh lệch phạm vi.
```

Dụng ý:

```text
Không cần phá ECDLP.
Sai nonce là đủ làm private key bay màu.
Đây là implementation failure, không phải ECDSA đúng chuẩn bị phá.
```

---

## 4.9. Page 8 — Phòng thủ và tối ưu

Page 8 gồm hai tab.

### Tab 1 — Phòng thủ triển khai

Đã bổ sung:

- threat model mini;
- nonce discipline;
- RFC6979-style;
- CSPRNG;
- constant-time;
- side-channel;
- partial nonce leakage;
- test vector;
- security audit;
- risk gate/fatal finding;
- toy/prototype/production context;
- mature library.

Checklist tương tác:

```text
User chọn cách sinh nonce.
User chọn có chống reuse hay không.
User chọn có constant-time/side-channel review hay không.
User chọn dùng thư viện hay tự viết.
User chọn context: toy, prototype, production.
App tính risk score minh họa.
App báo critical nếu có fatal finding.
App đưa danh sách việc cần sửa.
```

Dụng ý:

```text
Risk score chỉ là minh họa, không phải security audit thật.
Một số lỗi như reused nonce hoặc tự viết crypto production không audit phải bị xem là critical gate.
```

### Tab 2 — Shamir's trick

Nội dung:

- ECDSA verification cần tính:

  ```text
  P = u1G + u2Q
  ```

- Cách naive tính riêng `u1G`, `u2Q`, rồi cộng.
- Shamir's trick xử lý hai scalar cùng lúc.
- App so sánh số phép toán.

Dụng ý:

```text
Tab 1: làm đúng để an toàn.
Tab 2: làm khéo để hiệu quả.
```

---

## 4.10. Page 9 — OpenSSL và kết luận

Page 9 có hai vai trò:

1. Đối chiếu toy demo với công cụ thật.
2. Tổng kết toàn bộ đề tài.

Các tab chính:

| Tab | Nội dung |
|---|---|
| Sinh key thật | OpenSSL sinh key `secp256k1` |
| Ký nội dung | Ký message/file bằng private key |
| Sửa và verify | Verify message gốc pass, message sửa fail |
| Mini benchmark | Đo thời gian ký/verify trong lab hiện tại |
| Kết luận đề tài | Tổng kết public-key crypto, ECC, ECDLP, ECDSA, Bitcoin, nonce, defense |

Cảnh báo quan trọng:

```text
OpenSSL message/file signing không phải full Bitcoin transaction signing.
Page này không có Bitcoin Script, sighash, transaction serialization thật hoặc consensus.
```

Dụng ý:

```text
Toy demo giúp hiểu toán.
OpenSSL cho thấy ý tưởng ký/verify tồn tại trong công cụ mật mã thật.
```

---

# 5. Kết quả đạt được theo từng nhóm kiến thức

## 5.1. Mật mã khóa công khai

Đã giải thích được:

- khác biệt symmetric crypto và public-key crypto;
- bài toán phân phối khóa;
- hybrid cryptosystem;
- one-way function;
- trapdoor;
- hard problems;
- vị trí RSA, ElGamal/DH và ECC.

Kết quả:

```text
Người học hiểu vì sao cần public-key crypto trước khi đi vào ECC.
```

---

## 5.2. ECC

Đã mô phỏng được:

- trường hữu hạn;
- đường cong elliptic;
- điểm sinh;
- cộng điểm;
- nhân đôi điểm;
- scalar multiplication;
- double-and-add;
- `Q = dG`.

Kết quả:

```text
Người học thấy private key d tạo public key Q như thế nào.
```

---

## 5.3. ECDLP

Đã mô phỏng được:

- brute force discrete log;
- Baby-step Giant-step;
- Pollard rho ở mức demo;
- so sánh toy curve và curve thật.

Kết quả:

```text
Người học hiểu vì sao từ Q rất khó suy ra d trên tham số thật.
```

---

## 5.4. ECDSA

Đã mô phỏng được:

- key generation;
- signing;
- verification;
- trace công thức ký;
- trace công thức verify;
- tamper message.

Kết quả:

```text
Người học hiểu private key dùng để ký, public key dùng để verify.
```

---

## 5.5. Bitcoin UTXO case study

Đã mô phỏng được:

- ví Alice/Bob/Mallory;
- UTXO set;
- public key hash;
- locking/unlocking condition;
- signature trong input;
- node verification;
- transaction tampering;
- wrong key;
- double spend.

Kết quả:

```text
Người học hiểu ECDSA đi vào transaction Bitcoin-like ở bước nào.
```

---

## 5.6. Nonce attack

Đã mô phỏng được:

- reused nonce;
- known nonce;
- partial nonce leakage ở mức ghi chú.

Kết quả:

```text
Người học hiểu ECDSA có thể fail nếu nonce bị dùng sai, dù ECDLP không bị phá.
```

---

## 5.7. Defense engineering

Đã xây được checklist tương tác cho:

- nonce strategy;
- no-reuse policy;
- CSPRNG;
- constant-time;
- side-channel review;
- test vector;
- mature library;
- production context;
- audit;
- risk gate.

Kết quả:

```text
Người học hiểu an toàn mật mã không chỉ là công thức, mà còn là triển khai.
```

---

## 5.8. Optimization

Đã mô phỏng được:

```text
u1G + u2Q
```

bằng:

- cách naive;
- Shamir's trick.

Kết quả:

```text
Người học hiểu verification có thể được tối ưu ở mức thuật toán.
```

---

## 5.9. OpenSSL

Đã có lab OpenSSL:

- detect OpenSSL;
- sinh key `secp256k1`;
- ký message/file;
- verify;
- sửa message để verify fail;
- mini benchmark.

Kết quả:

```text
Người học thấy toy demo liên hệ với công cụ thật như thế nào.
```

---

# 6. Các tài liệu đã hoàn thiện hoặc viết lại

Trong quá trình hoàn thiện project, các tài liệu sau đã được viết lại hoặc tái cấu trúc.

| File | Vai trò |
|---|---|
| `README.md` | Giới thiệu nhanh project, cách chạy, phạm vi, cấu trúc repo |
| `PROJECT_PLAN.md` | Kế hoạch triển khai, mapping sang báo cáo và slide |
| `PROJECT_SCOPE_AND_REFERENCES.md` | Phạm vi project, bối cảnh Bitcoin hiện đại, reference |
| `AGENTS.md` | Hướng dẫn cho Agent CLI khi mở rộng project |
| `docs/APP_USAGE_GUIDE.md` | Hướng dẫn dùng app theo từng page |
| `docs/ECDSA_NONCE_ATTACK_AND_DEFENSE.md` | Ghi chú attack/defense nonce |
| `final report` | Báo cáo tổng hợp kết quả đến thời điểm hiện tại |

Các file này giúp repo không chỉ có code demo, mà còn có:

```text
hướng dẫn chạy
hướng dẫn thuyết trình
phạm vi rõ ràng
cảnh báo an toàn
định hướng mở rộng
```

---

# 7. Kết quả thực nghiệm và quan sát

## 7.1. Benchmark Page 2

Kết quả benchmark OpenSSL cần được diễn giải cẩn thận.

Những quan sát chính:

- RSA verify thường rất nhanh.
- RSA sign thường chậm hơn verify nhiều.
- ECDSA P-256 sign có thể rất nhanh.
- ECDSA P-384 chậm hơn P-256 đáng kể.
- DSA giúp nối về mặt lý thuyết với họ chữ ký discrete-log.
- Benchmark phụ thuộc vào máy, OpenSSL version, curve và implementation.
- `ecdsap256` là NIST P-256, không phải `secp256k1`.

Kết luận đúng:

```text
Benchmark cho thấy trade-off hiệu năng.
Benchmark không chứng minh hệ nào an toàn hơn.
ECC không phải lúc nào cũng nhanh hơn RSA ở mọi thao tác.
```

---

## 7.2. Toy curve và edge-case

Do toy curve rất nhỏ, một số hiện tượng có thể xảy ra:

- message sửa vẫn verify True trong vài trường hợp;
- Pollard rho có thể gặp collision suy biến;
- nonce không hợp lệ có thể tạo lỗi vì không có nghịch đảo modulo;
- `r = 0` hoặc `s = 0` có thể xảy ra.

Project đã xử lý theo hướng:

```text
không che giấu edge-case;
cảnh báo rõ đây là hạn chế của toy curve;
thêm nút hoặc logic hỗ trợ để chọn dữ liệu demo phù hợp.
```

Đây là cách xử lý trung thực và phù hợp với demo giáo dục.

---

## 7.3. Bitcoin transaction lab

Các kịch bản quan trọng đã được đưa vào lab:

1. Valid spend.
2. Tampered amount.
3. Tampered receiver.
4. Wrong signer.
5. Wrong public key.
6. Double spend.
7. Free mode.

Kết quả mong muốn:

```text
valid spend → accepted
tampering/wrong key/double spend → rejected
```

Dụng ý:

```text
Chữ ký ECDSA chỉ hợp lệ với đúng dữ liệu transaction đã ký và đúng public key liên quan đến locking condition.
```

---

## 7.4. Nonce attack

Các mô phỏng đã làm rõ:

```text
Hai chữ ký dùng cùng nonce k có thể khôi phục k và d.
Một chữ ký với known nonce k có thể khôi phục d.
Partial leakage có thể nguy hiểm qua nhiều chữ ký.
```

Điểm cần nhấn mạnh trong báo cáo/slides:

```text
Đây là lỗi triển khai.
Không phải ECDSA đúng chuẩn bị phá.
Không phải ECDLP bị phá.
```

---

# 8. Chiến lược kiểm thử

## 8.1. Test tự động cần duy trì

Các nhóm test nên được duy trì:

| Nhóm test | Nội dung |
|---|---|
| Field arithmetic | `mod_inv`, `mod_div`, lỗi không có nghịch đảo |
| ECC | point addition, point doubling, scalar multiplication |
| ECDSA | sign/verify, tampered message, wrong key |
| Bitcoin TX | valid spend, tamper, wrong key, double spend, missing UTXO |
| Nonce attack | reused nonce recover `k`, recover `d`, known nonce recover `d` |
| ECDLP | brute force, BSGS, Pollard rho nếu ổn định |
| Shamir | Shamir result bằng naive result |

Lệnh chạy:

```powershell
pytest -q
```

Nếu cần:

```powershell
python -m pytest -q
```

Không nên ghi trong báo cáo rằng test đã pass nếu chưa chạy thật ở máy hiện tại.

---

## 8.2. Test thủ công app

Các flow cần chạy thủ công trước khi nộp:

1. Page 1: tăng số người dùng và xem số khóa tăng.
2. Page 2: chạy benchmark OpenSSL và đọc kết quả.
3. Page 3: chọn `d`, xem `Q = dG`.
4. Page 4: chạy brute force/BSGS/Pollard rho.
5. Page 5: ký message, sửa message, verify fail.
6. Page 6: valid transaction Alice → Bob.
7. Page 6: sửa amount/receiver sau khi ký.
8. Page 6: Mallory ký sai key.
9. Page 6: double spend.
10. Page 7: reused nonce recover `k`, `d`.
11. Page 7: known nonce recover `d`.
12. Page 8: chọn cấu hình nguy hiểm để thấy critical finding.
13. Page 8: chạy Shamir's trick.
14. Page 9: sinh key OpenSSL, ký, verify pass, sửa message verify fail.

---

# 9. Mapping sang báo cáo chính thức

Báo cáo chính thức có thể dùng cấu trúc sau.

## Chương 1. Giới thiệu

Nội dung:

- bối cảnh public-key crypto;
- vì sao ECC đáng học;
- vì sao Bitcoin là case study phù hợp;
- mục tiêu và phạm vi.

App liên quan:

```text
Page 0, Page 1
```

---

## Chương 2. Cơ sở lý thuyết

Nội dung:

- symmetric vs public-key crypto;
- RSA, ElGamal/DH, ECC;
- finite field;
- elliptic curve;
- scalar multiplication;
- ECDLP;
- các thuật toán ECDLP toy.

App liên quan:

```text
Page 1, Page 2, Page 3, Page 4
```

---

## Chương 3. ECDSA

Nội dung:

- key generation;
- signing;
- verification;
- vai trò nonce;
- lỗi reused nonce và known nonce.

App liên quan:

```text
Page 5, Page 7
```

---

## Chương 4. Bitcoin case study

Nội dung:

- UTXO;
- locking condition;
- unlocking data;
- public key hash;
- signature trong input;
- node verification;
- tampering;
- wrong key;
- double spend.

App liên quan:

```text
Page 6
```

---

## Chương 5. Triển khai và kiểm thử

Nội dung:

- kiến trúc repo;
- các module `src/`;
- Streamlit app;
- test tự động;
- test thủ công;
- benchmark;
- OpenSSL lab;
- giới hạn.

App liên quan:

```text
Page 2, Page 8, Page 9
```

---

## Chương 6. Kết luận

Nội dung:

- ECC là nền tảng;
- ECDLP là bài toán khó;
- ECDSA là ứng dụng chữ ký;
- Bitcoin dùng chữ ký để xác thực quyền chi tiêu;
- triển khai sai nonce phá hỏng an toàn;
- giới hạn và hướng mở rộng.

App liên quan:

```text
Page 9
```

---

# 10. Mapping sang slide thuyết trình

Slide có thể đi theo cấu trúc:

| Slide | Nội dung |
|---:|---|
| 1 | Tên đề tài, môn học, thành viên |
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

Công thức nên đưa vào slide:

```text
Q = dG
ECDLP: given G and Q, find d
s = k^(-1)(h + rd) mod n
P = u1G + u2Q
```

Không nên nhồi quá nhiều công thức. Demo app mới là phần chứng minh trực quan.

---

# 11. Những điểm cần nhấn mạnh khi thuyết trình

## 11.1. Không nói Bitcoin mã hóa giao dịch bằng ECC

Nói đúng:

```text
Giao dịch Bitcoin là dữ liệu công khai.
ECDSA dùng để xác thực quyền chi tiêu, không dùng để mã hóa giao dịch.
```

---

## 11.2. Không nói toy curve đại diện cho Bitcoin thật

Nói đúng:

```text
Toy curve giúp nhìn thấy toán học.
secp256k1 thật có tham số lớn hơn rất nhiều.
```

---

## 11.3. Không nói nonce attack phá ECDSA đúng chuẩn

Nói đúng:

```text
Nonce attack là lỗi triển khai.
ECDSA đúng chuẩn yêu cầu nonce không lặp, không lộ, không dễ đoán.
```

---

## 11.4. Không nói OpenSSL signing là Bitcoin signing đầy đủ

Nói đúng:

```text
OpenSSL ký message/file bằng secp256k1.
Full Bitcoin transaction signing còn cần serialization, sighash, Script và consensus rules.
```

---

## 11.5. Không overclaim benchmark

Nói đúng:

```text
Benchmark phụ thuộc thao tác, curve, key size, implementation và máy chạy.
RSA verify có thể rất nhanh.
ECDSA P-256 sign có thể rất nhanh.
ECC đáng học không phải vì luôn thắng RSA ở mọi phép đo.
```

---

# 12. Giới hạn hiện tại của project

Dự án vẫn có các giới hạn:

1. Toy curve rất nhỏ, không có an toàn thật.
2. Python implementation không constant-time.
3. Transaction lab chỉ là mô hình giáo dục.
4. Không triển khai Bitcoin Script.
5. Không triển khai sighash thật.
6. Không triển khai Schnorr/Taproot/MuSig2.
7. Không triển khai lattice attack.
8. Pollard rho trên toy curve có thể có edge-case.
9. Benchmark chỉ mang tính tham khảo.
10. OpenSSL lab không phải full Bitcoin transaction signing.

Những giới hạn này cần được nói rõ trong báo cáo và slide để tránh hiểu nhầm.

---

# 13. Hướng mở rộng hợp lý

Các hướng mở rộng phù hợp:

| Hướng mở rộng | Lý do |
|---|---|
| Tách helper ECDLP khỏi `app.py` | Làm code sạch hơn |
| Thêm test cho Page 6 transaction lab | Tăng độ tin cậy |
| Làm slide bám theo 10 page | Dễ thuyết trình |
| Bổ sung phụ lục Schnorr/Taproot/MuSig2 | Cho thấy Bitcoin hiện đại nhưng không lệch trọng tâm |
| Cải thiện OpenSSL warning | Tránh nhầm message signing với Bitcoin signing |
| Thêm diagram architecture | Hữu ích cho báo cáo |

Các hướng chưa nên làm nếu không có yêu cầu rõ:

| Hướng | Lý do |
|---|---|
| Full Bitcoin Script | Quá rộng |
| Full sighash | Dễ lệch đề tài |
| Schnorr implementation | Khác ECDSA, cần scope riêng |
| MuSig2 implementation | Phức tạp, cần multisignature protocol |
| Lattice attack thật | Cần nền toán lattice |
| Wallet UI | Dễ gây hiểu nhầm là ví thật |
| Network/broadcast | Vượt phạm vi và có rủi ro |

---

# 14. Kết luận tổng hợp

Đến thời điểm hiện tại, project đã hoàn thiện được một mạch demo tương đối đầy đủ cho đề tài:

```text
Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin
```

Các kết quả chính:

```text
1. Đã xây được mạch public-key crypto → ECC → ECDSA → Bitcoin case study.
2. Đã mô phỏng được Q = dG trên toy curve.
3. Đã mô phỏng được ECDLP attack trên toy curve.
4. Đã mô phỏng được ECDSA sign/verify.
5. Đã xây được Bitcoin-like transaction lab với UTXO, signature, public key hash và node verification.
6. Đã mô phỏng được nonce attack.
7. Đã thêm phần phòng thủ triển khai và risk checklist tương tác.
8. Đã thêm Shamir's trick để nối với tối ưu thuật toán.
9. Đã thêm OpenSSL secp256k1 lab để đối chiếu với công cụ thật.
10. Đã viết lại các tài liệu chính phục vụ chạy project, mở rộng project, viết báo cáo và làm slide.
```

Câu kết luận cuối cùng:

```text
ECC cung cấp nền toán.
ECDLP cung cấp độ khó.
ECDSA cung cấp chữ ký số.
Bitcoin dùng chữ ký số để xác thực quyền chi tiêu UTXO.
Nhưng an toàn thực tế không chỉ đến từ toán học; triển khai sai, đặc biệt là sai nonce, có thể làm toàn bộ hệ thống sụp đổ.
```

---

# Phụ lục A. Checklist trước khi nộp

Trước khi nộp hoặc thuyết trình, nên kiểm tra:

```text
[ ] README.md đã đúng mạch mới
[ ] PROJECT_PLAN.md đã đúng mạch mới
[ ] PROJECT_SCOPE_AND_REFERENCES.md đã rõ phạm vi
[ ] AGENTS.md đã đúng cho Agent CLI
[ ] APP_USAGE_GUIDE.md khớp app.py hiện tại
[ ] ECDSA_NONCE_ATTACK_AND_DEFENSE.md khớp Page 7–8
[ ] Streamlit app chạy được
[ ] Page 2 benchmark có cảnh báo P-256 không phải secp256k1
[ ] Page 5 tampered message có xử lý edge-case toy curve
[ ] Page 6 transaction lab chạy được các scenario chính
[ ] Page 7 reused nonce/known nonce recover được key trên toy curve
[ ] Page 8 risk gate có critical finding
[ ] Page 9 OpenSSL ký/verify chạy được nếu máy có OpenSSL
[ ] pytest -q đã chạy nếu môi trường có đủ dependency
```

---

# Phụ lục B. Các lệnh thường dùng

## Chạy app

```powershell
streamlit run app.py
```

hoặc:

```powershell
python -m streamlit run app.py
```

## Chạy test

```powershell
pytest -q
```

hoặc:

```powershell
python -m pytest -q
```

## Kiểm tra OpenSSL

```powershell
openssl version
```

## Kiểm tra file đang bị Git track dù đã thêm vào `.gitignore`

```powershell
git status
git ls-files
```

Nếu cần bỏ tracking:

```powershell
git rm --cached <path>
```

---

# Phụ lục C. Cảnh báo an toàn bắt buộc

Khi trình bày project, cần nhắc rõ:

1. Toy curve không an toàn.
2. Toy ECDSA không phải production crypto.
3. App không phải ví Bitcoin.
4. Transaction lab không phải Bitcoin thật.
5. Không nhập private key thật vào app.
6. Không dùng code để ký giao dịch thật.
7. Không dùng ECDLP attack demo để thử phá `secp256k1`.
8. Reused nonce attack là lỗi triển khai, không phải ECDSA đúng chuẩn bị phá.
9. OpenSSL message/file signing không phải full Bitcoin transaction signing.
10. Benchmark chỉ đo hiệu năng trong môi trường cụ thể, không chứng minh an toàn.
