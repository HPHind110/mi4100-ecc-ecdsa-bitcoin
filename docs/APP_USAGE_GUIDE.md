# Hướng dẫn sử dụng app mô phỏng ECC/ECDSA trong Bitcoin

Tài liệu này hướng dẫn cách chạy và sử dụng app Streamlit trong file `app.py`.

App là một **phòng lab giáo dục** cho đề tài:

```text
Mật mã đường cong elliptic (ECC)
→ ECDLP
→ chữ ký số ECDSA
→ Bitcoin như case study dùng ECDSA để chứng minh quyền chi tiêu UTXO
→ lỗi nonce
→ phòng thủ triển khai
→ tối ưu verification
→ đối chiếu OpenSSL secp256k1
```

Luận điểm chính của app:

```text
ECC là nền tảng.
ECDLP là bài toán khó.
ECDSA là ứng dụng chữ ký số.
Bitcoin là case study thực tế.
```

App **không phải ví Bitcoin thật**, không tạo khóa thật để dùng ngoài đời, không ký giao dịch Bitcoin thật và không được dùng cho production crypto.

---

## 1. App này dùng để làm gì?

App dùng để học và trình bày mạch kiến thức sau:

```text
Mật mã khóa bí mật
→ bài toán phân phối khóa
→ mật mã khóa công khai
→ RSA / ElGamal-DH / ECC
→ ECC tạo public key bằng Q = dG
→ ECDLP khiến việc tìm d từ Q trở nên khó
→ ECDSA dùng private key để ký, public key để verify
→ Bitcoin dùng ECDSA để mở khóa UTXO
→ nonce sai có thể làm lộ private key
→ triển khai thật cần nonce discipline, constant-time, side-channel awareness
→ Shamir's trick tối ưu bước verify
→ OpenSSL secp256k1 cho thấy luồng ký/verify bằng công cụ thật
```

App phù hợp cho 3 mục tiêu:

1. **Học lý thuyết theo mạch câu chuyện**  
   Không bắt đầu ngay bằng công thức khô khốc, mà đi từ câu hỏi: vì sao cần public-key cryptography, vì sao ECC đáng học, rồi mới sang Bitcoin.

2. **Chạy demo tương tác**  
   Người dùng có thể tự chọn số người dùng, private key, nonce, message, thuật toán benchmark, UTXO, người gửi, người nhận, kiểu tấn công nonce, cách phòng thủ và tham số Shamir.

3. **Dùng làm kịch bản thuyết trình**  
   App chia thành 10 page, có intro, thuật ngữ, bảng, chart, trace từng bước và summary cuối page.

---

## 2. App này không dùng để làm gì?

App **không phải**:

- ví Bitcoin thật;
- phần mềm sinh private key thật để lưu tài sản;
- phần mềm ký giao dịch Bitcoin thật;
- Bitcoin full node;
- Bitcoin Script interpreter thật;
- công cụ broadcast giao dịch lên mạng Bitcoin;
- công cụ tấn công khóa Bitcoin thật;
- thư viện crypto production.

Toàn bộ khóa, curve nhỏ, UTXO, transaction, chữ ký, benchmark, attack và checklist trong app đều phục vụ mục tiêu **giáo dục**.

Không dùng output của app cho ví thật, tiền thật, khóa thật hoặc giao dịch thật.

---

## 3. Cài đặt và chạy app

### 3.1. Tạo môi trường Python

Từ thư mục gốc của repo:

```powershell
python -m venv .venv
```

Kích hoạt môi trường trên Windows PowerShell:

```powershell
.\.venv\Scripts\activate
```

Nếu dùng Linux/macOS:

```bash
source .venv/bin/activate
```

---

### 3.2. Cài thư viện

```powershell
pip install -r requirements.txt
```

App dùng các thư viện chính:

```text
streamlit
pandas
plotly
pytest
```

Nếu gặp lỗi `ModuleNotFoundError`, cài lại:

```powershell
pip install -r requirements.txt
```

---

### 3.3. Chạy test

```powershell
pytest -q
```

Lệnh này chạy test của project. Nếu test pass, phần code nền tương đối ổn để chạy demo.

---

### 3.4. Chạy app Streamlit

```powershell
streamlit run app.py
```

Nếu terminal không nhận lệnh `streamlit`, dùng:

```powershell
python -m streamlit run app.py
```

Sau khi chạy, Streamlit thường tự mở trình duyệt. Nếu không tự mở, copy link trong terminal, thường là:

```text
http://localhost:8501
```

---

## 4. Yêu cầu thêm nếu muốn dùng OpenSSL

Page 2 và Page 9 có phần dùng OpenSSL.

- Page 2 dùng OpenSSL để benchmark `rsa2048`, `rsa3072`, `dsa2048`, `ecdsap256`, `ecdsap384`.
- Page 9 dùng OpenSSL để sinh key `secp256k1`, ký message và verify chữ ký.

Muốn dùng đầy đủ hai page này, máy cần có OpenSSL trong `PATH`.

Kiểm tra nhanh:

```powershell
openssl version
```

Nếu app báo không tìm thấy OpenSSL, vẫn dùng được các page toy demo khác. Chỉ phần benchmark/OpenSSL lab sẽ không chạy.

Lưu ý quan trọng:

```text
ecdsap256 trong openssl speed là NIST P-256.
Nó không phải secp256k1 của Bitcoin.
```

Page 9 mới là phần dùng `secp256k1` để ký/verify bằng OpenSSL.

---

## 5. Điều hướng và reset trạng thái

App dùng sidebar để chuyển page.

Trong sidebar có nút:

```text
🔄 Reset toàn bộ trạng thái mô phỏng
```

Nút này xóa toàn bộ `st.session_state`, bao gồm:

- page hiện tại;
- benchmark cũ;
- ECDSA signature đang lưu;
- transaction lab;
- OpenSSL lab;
- file tạm OpenSSL.

Dùng reset toàn bộ khi:

- app giữ dữ liệu cũ;
- page chạy ra kết quả không giống kịch bản;
- transaction lab bị sửa phá quá nhiều;
- OpenSSL lab còn key/message/signature cũ;
- muốn thuyết trình lại từ đầu.

Riêng Page 6 có nút:

```text
🧹 Reset phòng lab giao dịch
```

Nút này chỉ reset transaction lab Bitcoin mô phỏng.

---

## 6. Tổng quan 10 page

| Page | Tên page | Vai trò |
|---:|---|---|
| 0 | Mở đầu | Đặt bản đồ: public-key crypto → ECC → ECDSA → Bitcoin case study |
| 1 | Từ khóa bí mật đến khóa công khai | Giải thích key distribution, hybrid cryptosystem, one-way/trapdoor/hard problems |
| 2 | RSA, ElGamal/DH và ECC | So sánh nền toán và benchmark chạy thật bằng OpenSSL |
| 3 | Nền tảng toán học ECC | Trường hữu hạn, đường cong elliptic, điểm sinh, `Q = dG`, double-and-add |
| 4 | ECDLP | Brute force, Baby-step Giant-step, Pollard rho |
| 5 | Chữ ký số ECDSA | Key generation, signing, verification, nonce `k`, sửa message sau khi ký |
| 6 | Bitcoin case study | ECDSA mở khóa UTXO mô phỏng, transaction lab, sửa phá, double spend |
| 7 | Nonce attack | Reused nonce, known nonce, partial nonce leakage |
| 8 | Phòng thủ và tối ưu | Nonce discipline, RFC6979-style, constant-time, side-channel, Shamir's trick |
| 9 | OpenSSL và kết luận | OpenSSL secp256k1 thật + tổng kết toàn bộ đề tài |

Nên đi theo thứ tự từ Page 0 đến Page 9.

Nếu thời gian thuyết trình ngắn, có thể ưu tiên:

```text
Page 0 → Page 1 → Page 2 → Page 3 → Page 4 → Page 5 → Page 6 → Page 7
```

Page 8 và Page 9 dùng để nâng chất lượng phần triển khai/thực tế.

---

# 7. Hướng dẫn từng page

---

## Page 0 — Mở đầu: Vì sao cần ECC/ECDSA?

### Mục tiêu

Page 0 trả lời 3 câu hỏi:

```text
Vì sao cần mật mã khóa công khai?
Vì sao ECC đáng học?
Vì sao chọn Bitcoin làm case study?
```

Luận điểm chính:

```text
Đề tài này không bắt đầu từ Bitcoin.
Trọng tâm là ECC và ECDSA trong mật mã khóa công khai.
Bitcoin là case study thực tế cho ECDSA.
```

### Cách dùng

1. Đọc phần intro 3 cột:
   - câu hỏi;
   - ý tưởng;
   - demo chứng minh.

2. Đọc box luận điểm trung tâm.

3. Mở phần thuật ngữ nếu cần:
   - mật mã khóa bí mật;
   - mật mã khóa công khai;
   - bài toán khó;
   - ECC;
   - ECDLP;
   - ECDSA.

4. Xem sơ đồ logic:

```text
Mật mã khóa bí mật
→ bài toán phân phối khóa
→ mật mã khóa công khai
→ RSA / ElGamal-DH / ECC
→ ECDLP
→ ECDSA
→ Bitcoin case study
```

5. Xem bảng 3 câu hỏi dẫn dắt.

6. Xem bảng lộ trình 10 page.

### Câu nên nói khi thuyết trình

```text
Bitcoin không phải điểm xuất phát của đề tài.
Em dùng Bitcoin như một case study để thấy ECDSA giải quyết bài toán chứng minh quyền chi tiêu trong một hệ thống không cần ngân hàng trung gian.
```

---

## Page 1 — Từ khóa bí mật đến khóa công khai

### Mục tiêu

Page 1 trả lời câu hỏi:

```text
Vì sao public-key cryptography ra đời?
```

Ý chính:

```text
Mật mã khóa bí mật rất nhanh,
nhưng gặp bài toán phân phối khóa khi số người dùng tăng lên.
```

### Kiến thức cần nắm

#### Mật mã khóa bí mật

Hai bên dùng chung một khóa để mã hóa/giải mã. Mạnh ở tốc độ, nhưng khó chia sẻ khóa an toàn khi hệ thống có nhiều người.

#### Bài toán phân phối khóa

Nếu có `N` người và mỗi cặp cần một khóa bí mật riêng, số khóa cần quản lý là:

```text
N(N - 1) / 2
```

Khi `N` lớn, số khóa tăng rất nhanh.

#### Mật mã khóa công khai

Mỗi người có:

```text
private key: giữ bí mật
public key : công khai
```

Số cặp khóa cần quản lý là:

```text
N
```

#### Hybrid cryptosystem

Trong thực tế, public-key crypto thường không mã hóa toàn bộ dữ liệu lớn. Mạch thường gặp:

```text
public-key crypto dùng để trao đổi khóa hoặc xác thực
symmetric crypto dùng để mã hóa dữ liệu chính
```

#### One-way / trapdoor / hard problem

- RSA thường gắn với trapdoor one-way function.
- ECC nên hiểu là quan hệ một chiều khó đảo: biết `d` thì tính `Q = dG` nhanh, nhưng biết `Q` thì tìm `d` rất khó.

### Cách dùng

1. Dùng slider chọn số người dùng `N`.
2. Quan sát 3 metric:
   - số người dùng;
   - số khóa đối xứng theo từng cặp;
   - số cặp khóa công khai.
3. Xem bảng so sánh hai mô hình.
4. Xem line chart số khóa tăng theo `N`.
5. Đọc bảng symmetric / public-key / hybrid.
6. Đọc bảng RSA / Diffie-Hellman-ElGamal / ECC ở mức bài toán khó.

### Câu nên nói khi thuyết trình

```text
Public-key crypto không thay thế hoàn toàn symmetric crypto.
Nó giải quyết phần bắt tay, trao đổi khóa, xác thực và chữ ký số.
Trong hệ thật, hai mô hình thường kết hợp theo kiểu hybrid.
```

---

## Page 2 — RSA, ElGamal/DH và ECC

### Mục tiêu

Page 2 trả lời câu hỏi:

```text
ECC đứng ở đâu trong bản đồ mật mã khóa công khai?
```

Page này có 3 tab:

| Tab | Vai trò |
|---|---|
| Bản đồ public-key systems | So sánh RSA, Diffie-Hellman/ElGamal và ECC |
| So sánh chữ ký số | So sánh RSA signature, DSA/ElGamal-style và ECDSA |
| Benchmark chạy thật | Chạy OpenSSL speed để đo sign/verify |

---

### Tab 1 — Bản đồ public-key systems

Các hệ chính:

| Hệ | Public key | Private key | Bài toán khó | Ứng dụng |
|---|---|---|---|---|
| RSA | `(n, e)` | `d` | factorization / RSA problem | mã hóa, chữ ký số |
| Diffie-Hellman / ElGamal | `y = g^x mod p` | `x` | discrete logarithm | trao đổi khóa, mã hóa, chữ ký họ DLP |
| ECC | `Q = dG` | `d` | ECDLP | ECDH, ECDSA, EdDSA |

Ý quan trọng:

```text
ECC không phải một thứ nằm ngoài public-key crypto.
Nó là một cách xây public-key crypto bằng nhóm điểm elliptic curve.
```

---

### Tab 2 — So sánh chữ ký số

Cần nắm:

| Chữ ký | Nền tảng | Signing | Verification |
|---|---|---|---|
| RSA signature | RSA problem | dùng private exponent | dùng public exponent |
| DSA / ElGamal-style | DLP | dùng nonce `k` | kiểm tra quan hệ discrete log |
| ECDSA | ECDLP | dùng nonce `k`, điểm `R = kG` | tính `P = u1G + u2Q` |

Ý cần nhấn mạnh:

```text
ECDSA không từ trên trời rơi xuống.
Nó là chữ ký kiểu DSA trên nhóm điểm elliptic curve.
```

---

### Tab 3 — Benchmark chạy thật

Tab này gọi OpenSSL để benchmark:

```text
rsa2048
rsa3072
dsa2048
ecdsap256
ecdsap384
```

Cách dùng:

1. Chọn thuật toán cần benchmark.
2. Chọn số giây benchmark mỗi thuật toán.
3. Bấm:

```text
🚀 Chạy OpenSSL benchmark
```

4. Xem bảng kết quả.
5. Xem chart `Sign/s` và `Verify/s`.
6. Xem phần giải thích kết quả.

### Cách đọc benchmark

Không được kết luận đơn giản:

```text
ECC luôn nhanh hơn RSA.
```

Cách hiểu đúng:

```text
Một thuật toán có thể ký rất nhanh nhưng verify không nhanh nhất.
Một thuật toán khác có thể verify rất nhanh nhưng ký chậm hơn.
```

Các kết luận thường thấy:

- RSA verify thường rất nhanh.
- RSA sign chậm hơn verify rất nhiều.
- ECDSA P-256 có thể sign rất nhanh.
- ECDSA P-384 chậm hơn P-256 rõ rệt.
- Benchmark đo hiệu năng, không chứng minh an toàn.
- Không so sánh số bit thô giữa RSA và ECC.
- `ecdsap256` là NIST P-256, không phải secp256k1.

### Câu nên nói khi thuyết trình

```text
ECC đáng học không phải vì nó thắng RSA ở mọi phép đo.
Điểm mạnh của ECC là trade-off giữa kích thước khóa, hiệu năng và mức an toàn.
ECDSA là một ứng dụng chữ ký số quan trọng của trade-off đó.
```

---

## Page 3 — Nền tảng toán học ECC: Q = dG

### Mục tiêu

Page 3 trả lời câu hỏi:

```text
ECC tạo public key từ private key như thế nào?
```

Công thức trung tâm:

```text
Q = dG
```

Trong đó:

| Ký hiệu | Ý nghĩa |
|---|---|
| `d` | private key, một số bí mật |
| `G` | điểm sinh cố định |
| `Q` | public key, một điểm trên đường cong |
| `dG` | phép nhân điểm, tức cộng điểm theo quy tắc elliptic curve |

### Cách dùng

1. Đọc warning về toy curve.
2. Mở thuật ngữ nếu cần:
   - trường hữu hạn `F_p`;
   - đường cong elliptic;
   - điểm sinh `G`;
   - private key `d`;
   - public key `Q`;
   - phép nhân điểm;
   - ECDLP.
3. Xem phương trình toy curve:

```text
y² ≡ x³ + ax + b mod p
```

4. Đọc box case study nhỏ về secp256k1.
5. Dùng slider chọn private key `d`.
6. Quan sát app tính:

```text
Q = dG
```

7. Mở expander:

```text
🔎 Xem quá trình double-and-add tạo Q
```

8. Xem bảng trace double-and-add.
9. Xem hai tab trực quan:
   - đường cong trên số thực;
   - điểm rời rạc trên `F_p`.

### Điểm cần nhấn mạnh

`dG` **không phải** nhân từng tọa độ của `G` với `d`.

Nó là phép cộng điểm lặp lại:

```text
dG = G + G + ... + G
```

Nhưng thay vì cộng từng lần, ta dùng double-and-add để tính nhanh.

### Câu nên nói khi thuyết trình

```text
Page này cho thấy chiều dễ: từ d tính ra Q.
Page sau sẽ thử chiều ngược: biết Q rồi tìm lại d.
Đó chính là ECDLP.
```

---

## Page 4 — ECDLP: vì sao Q không làm lộ d?

### Mục tiêu

Page 4 trả lời câu hỏi:

```text
Nếu attacker biết G và Q = dG, có tìm lại được d không?
```

Đây là bài toán ECDLP:

```text
Given G and Q = dG, find d.
```

### Cách dùng

1. Chọn private key bí mật mô phỏng `d`.
2. App tính public key `Q = dG`.
3. Xem bảng attacker biết gì:
   - đường cong;
   - điểm sinh `G`;
   - public key `Q`;
   - không biết private key `d`.
4. Chọn thuật toán hiển thị:
   - brute force luôn có;
   - Baby-step Giant-step tùy chọn;
   - Pollard rho tùy chọn.
5. Xem bảng so sánh kết quả.
6. Mở tab chi tiết từng thuật toán.

### Ba thuật toán trong page

| Thuật toán | Ý tưởng | Độ phức tạp |
|---|---|---|
| Brute force | Thử từng `k`, kiểm tra `kG = Q` | `O(n)` thời gian |
| Baby-step Giant-step | Viết `d = i*m + j`, cho hai phía gặp nhau | `O(√n)` thời gian, `O(√n)` bộ nhớ |
| Pollard rho | Random-walk tìm collision | `O(√n)` kỳ vọng, ít bộ nhớ |

### Lưu ý về Pollard rho

Pollard rho có tính xác suất. Trên toy curve nhỏ, có thể gặp collision suy biến hoặc chưa tìm được kết quả trong số bước giới hạn.

Điều đó không làm sai ý tưởng. Đây chỉ là hạn chế của mô phỏng nhỏ.

### Câu nên nói khi thuyết trình

```text
Toy curve nhỏ nên ta phá được để nhìn thấy ECDLP.
Curve thật có order rất lớn, nên brute force hay thuật toán O(√n) vẫn không khả thi trong thực tế.
```

---

## Page 5 — Chữ ký số ECDSA

### Mục tiêu

Page 5 trả lời câu hỏi:

```text
Làm sao chứng minh mình có private key mà không tiết lộ private key?
```

Ý tưởng:

```text
private key d dùng để ký
public key Q dùng để verify
người verify không cần biết d
```

### Công thức ký

```text
h = H(m) mod n
R = kG
r = x(R) mod n
s = k⁻¹(h + rd) mod n
```

### Công thức verify

```text
w = s⁻¹ mod n
u1 = hw mod n
u2 = rw mod n
P = u1G + u2Q
valid ⇔ x(P) mod n = r
```

### Cách dùng

1. Chọn private key `d`.
2. Chọn nonce mô phỏng `k`.
3. Quan sát public key `Q = dG`.
4. Nhập message cần ký.
5. Bấm:

```text
🖊️ Tạo chữ ký ECDSA
```

6. Xem chữ ký `(r, s)`.
7. Mở phần trace signing để xem từng bước:
   - hash dữ liệu;
   - tính `R = kG`;
   - tính `r`;
   - tính nghịch đảo `k`;
   - tính `h + rd`;
   - tính `s`.
8. Verify message gốc bằng public key.
9. Sửa message sau khi ký.
10. Verify message đã sửa.

### Nếu message sửa vẫn verify True

Vì toy curve có `n` rất nhỏ, đôi khi message khác vẫn vô tình thỏa điều kiện verify.

Khi gặp vậy, bấm:

```text
🎯 Tìm message sửa chắc chắn bị từ chối
```

Đây là hạn chế của toy curve, không phải hành vi mong muốn trong hệ thật.

### Câu nên nói khi thuyết trình

```text
ECDSA ký dữ liệu cụ thể, không ký một ý định mơ hồ.
Nếu dữ liệu đổi sau khi ký, chữ ký cũ phải bị từ chối.
Trong Bitcoin case study, dữ liệu được ký là dữ liệu giao dịch.
```

---

## Page 6 — Bitcoin case study: ECDSA mở khóa UTXO

Page 6 là demo trung tâm về Bitcoin case study.

### Mục tiêu

Page 6 trả lời câu hỏi:

```text
ECDSA đi vào Bitcoin như thế nào?
```

Trong mô hình giống P2PKH:

```text
UTXO bị khóa bởi public key hash
người tiêu cung cấp public key + ECDSA signature
node kiểm tra public key hash và chữ ký
```

### Điều kiện để transaction được chấp nhận

Một giao dịch được chấp nhận khi:

```text
1. UTXO được tham chiếu có tồn tại.
2. UTXO còn chưa bị tiêu.
3. Public key hash khớp locking condition.
4. Chữ ký ECDSA hợp lệ với dữ liệu giao dịch.
```

Nếu một điều kiện sai, node mô phỏng từ chối giao dịch.

---

### Cấu trúc Page 6

Page 6 có 4 tab:

| Tab | Vai trò |
|---|---|
| 1️⃣ Ví mô phỏng & tập UTXO | Xem ví Alice/Bob/Mallory, tạo UTXO demo, reset lab |
| 2️⃣ Tạo giao dịch | Chọn sender, UTXO input, receiver, amount |
| 3️⃣ Ký & kiểm tra | Ký transaction, node verify, gửi/apply vào UTXO set |
| 4️⃣ Sửa phá / tấn công / tiêu hai lần | Mallory ký sai, sửa amount, đổi receiver, thay public key, double spend |

Page 6 có selectbox:

```text
🎬 Kịch bản hướng dẫn
```

Các kịch bản:

```text
Kịch bản đúng: Alice trả Bob
Sửa số tiền sau khi ký
Đổi người nhận sang Mallory sau khi ký
Mallory cố tiêu UTXO của Alice
Thay public key mở khóa bằng của Mallory
Tiêu cùng một UTXO hai lần
Chế độ tự do
```

Khi chọn kịch bản, app hiện bảng:

```text
Tab cần vào
Thao tác
Kết quả mong đợi
Kết luận cần rút ra
```

---

### Kịch bản 1 — Alice trả Bob thành công

Mục tiêu:

```text
Alice có UTXO
→ Alice tạo transaction trả Bob
→ Alice ký bằng private key của Alice
→ node verify thành công
→ UTXO cũ của Alice bị tiêu
→ UTXO mới của Bob xuất hiện
```

Các bước:

1. Tab 1: tạo UTXO cho Alice, ví dụ amount = 10.
2. Tab 2: chọn sender Alice, chọn UTXO của Alice, receiver Bob, amount = 10.
3. Tab 3: chọn người ký Alice, bấm ký giao dịch.
4. Tab 3: bấm node kiểm tra giao dịch.
5. Tab 3: bấm gửi / áp dụng vào tập UTXO.

Kết quả đúng:

```text
Node mô phỏng CHẤP NHẬN giao dịch.
UTXO cũ bị tiêu.
UTXO mới thuộc về Bob.
```

---

### Kịch bản 2 — Sửa số tiền sau khi ký

Mục tiêu:

```text
Cho thấy chữ ký gắn với dữ liệu transaction cụ thể.
Sửa amount sau khi ký làm chữ ký cũ mất hiệu lực.
```

Các bước:

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Tab 4: nhập số tiền mới sau khi ký.
5. Bấm áp dụng số tiền mới.
6. Bấm kiểm tra giao dịch đã bị sửa.

Kết quả đúng:

```text
Node từ chối giao dịch.
```

---

### Kịch bản 3 — Đổi người nhận sang Mallory sau khi ký

Mục tiêu:

```text
Attacker không thể đổi receiver sau khi transaction đã được ký.
```

Các bước:

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Tab 4: bấm đổi người nhận sang Mallory.
5. Bấm kiểm tra giao dịch đã bị sửa.

Kết quả đúng:

```text
Node từ chối giao dịch.
```

Lý do: dữ liệu transaction thay đổi, chữ ký cũ không còn khớp.

---

### Kịch bản 4 — Mallory cố tiêu UTXO của Alice

Mục tiêu:

```text
Mallory không thể dùng private key của mình để tiêu UTXO bị khóa bởi public key hash của Alice.
```

Các bước:

1. Tạo UTXO cho Alice.
2. Tạo transaction tiêu UTXO của Alice.
3. Tab 3: chọn người ký Mallory.
4. Bấm ký giao dịch.
5. Bấm node kiểm tra giao dịch.

Kết quả đúng:

```text
Node từ chối giao dịch.
```

Lý do: Mallory ký được bằng khóa của Mallory, nhưng public key hash của Mallory không khớp locking condition của UTXO Alice.

---

### Kịch bản 5 — Thay public key mở khóa bằng của Mallory

Mục tiêu:

```text
Không thể thay public key trong unlocking data một cách tùy tiện.
```

Các bước:

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Tab 4: bấm thay khóa công khai mở khóa bằng của Mallory.
5. Bấm kiểm tra giao dịch đã bị sửa.

Kết quả đúng:

```text
Node từ chối giao dịch.
```

Lý do: unlocking data không còn khớp locking condition của UTXO Alice.

---

### Kịch bản 6 — Tiêu cùng một UTXO hai lần

Mục tiêu:

```text
Cho thấy vai trò của UTXO set trong chống double spend.
```

Các bước:

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Tab 4: bấm thử tiêu hai lần giao dịch hiện tại.

Kết quả đúng:

```text
Lần đầu được chấp nhận.
Lần hai bị từ chối.
```

Lý do: sau lần tiêu đầu, UTXO không còn ở trạng thái unspent.

### Câu nên nói khi thuyết trình

```text
Bitcoin case study cho thấy ECDSA không đứng riêng lẻ.
Nó nằm trong cơ chế mở khóa UTXO: public key phải khớp public key hash, và chữ ký phải hợp lệ với dữ liệu transaction.
```

---

## Page 7 — Nonce attack: khi ECDSA triển khai sai

### Mục tiêu

Page 7 trả lời câu hỏi:

```text
ECDLP khó có đủ để bảo vệ private key không?
```

Câu trả lời:

```text
Không đủ.
Nếu ECDSA triển khai sai nonce k, attacker có thể khôi phục private key mà không cần giải ECDLP.
```

Page này có 3 mode:

| Mode | Ý nghĩa |
|---|---|
| Reused nonce | Dùng lại cùng `k` cho hai chữ ký |
| Known nonce | Nonce `k` của một chữ ký bị lộ |
| Partial nonce leakage | Nonce chỉ rò một phần, chỉ ghi chú lý thuyết |

### Cách dùng chung

1. Chọn private key nạn nhân `d`.
2. Chọn nonce mô phỏng `k`.
3. Nhập message 1.
4. Nhập message 2 nếu chạy reused nonce.
5. Chọn kiểu tấn công.
6. Bấm:

```text
⚡ Chạy mô phỏng tấn công
```

---

### Mode 1 — Reused nonce

Nếu cùng một nonce `k` dùng để ký hai message khác nhau:

```text
s1 = k⁻¹(h1 + rd) mod n
s2 = k⁻¹(h2 + rd) mod n
```

Lấy hiệu hai phương trình:

```text
s1 - s2 = k⁻¹(h1 - h2) mod n
```

Khôi phục nonce:

```text
k' = (h1 - h2)(s1 - s2)⁻¹ mod n
```

Sau đó khôi phục private key:

```text
d' = (s1k' - h1)r⁻¹ mod n
```

Kết quả đúng:

```text
k khôi phục = k ban đầu
d khôi phục = d ban đầu
```

---

### Mode 2 — Known nonce

Với một chữ ký:

```text
s = k⁻¹(h + rd) mod n
```

Nếu attacker biết `k`, suy ra:

```text
d' = (sk - h)r⁻¹ mod n
```

Chỉ một chữ ký cũng có thể đủ để khôi phục private key.

---

### Mode 3 — Partial nonce leakage

Partial leakage nghĩa là nonce `k` không lộ toàn bộ, nhưng rò một phần qua nhiều chữ ký.

Nguồn rò rỉ có thể là:

```text
RNG yếu hoặc bị bias
timing side-channel
cache / power side-channel
implementation bug
```

App không demo lattice attack vì đó là chủ đề cryptanalysis nâng cao.

Thông điệp cần nhớ:

```text
Không chỉ reuse nonce mới nguy hiểm.
Nonce bị rò một phần qua nhiều chữ ký cũng có thể nguy hiểm.
```

### Câu nên nói khi thuyết trình

```text
Page 4 cho thấy phá ECDLP là khó.
Page 7 cho thấy một đường khác: không cần phá ECDLP, chỉ cần ECDSA dùng nonce sai là private key có thể bay màu.
```

---

## Page 8 — Phòng thủ và tối ưu

### Mục tiêu

Page 8 trả lời hai câu hỏi:

```text
Muốn dùng ECDSA thật thì cần kỷ luật triển khai gì?
Có tối ưu nào cho bước verify không?
```

Page này có 2 tab:

| Tab | Vai trò |
|---|---|
| Phòng thủ triển khai | Mini security review tương tác cho ECDSA implementation |
| Shamir's trick | Demo tối ưu phép tính `u1G + u2Q` trong ECDSA verification |

---

### Tab 1 — Phòng thủ triển khai

Tab này nối trực tiếp với Page 7.

Page 7 nói:

```text
nonce sai → private key bị lộ
```

Page 8 hỏi tiếp:

```text
Làm sao thiết kế/triển khai để tránh lỗi kiểu đó?
```

#### Threat model mini

App nhắc 3 nhóm mối đe dọa:

| Mối đe dọa | Liên quan | Phòng thủ |
|---|---|---|
| Attacker thấy nhiều chữ ký | reused nonce, biased nonce, partial leakage | RFC6979/CSPRNG tốt, không reuse nonce |
| Attacker đo thời gian chạy | timing side-channel | constant-time implementation |
| Attacker khai thác lỗi tự viết crypto | sai edge-case, sai validate, sai randomness | thư viện trưởng thành, test vector, audit |

#### Checklist rủi ro triển khai

Người dùng chọn:

```text
Cách sinh nonce k
Có cơ chế đảm bảo không reuse nonce không
Có test vector / kiểm thử chữ ký không
Có constant-time không
Có xem xét side-channel không
Dùng thư viện trưởng thành hay tự viết
Mục tiêu sử dụng: toy / prototype / production
Có audit độc lập không
```

App tính:

```text
Điểm rủi ro minh họa
Đánh giá: thấp / trung bình / cao / cực cao / critical
Lỗi chí mạng cần sửa ngay
Việc nên sửa trước
Lý do app đánh giá như vậy
```

#### Cách hiểu risk score

Điểm rủi ro trong app là **minh họa**, không phải security audit thật.

Nó giúp người học hiểu:

- nonce cố định hoặc reuse nonce là lỗi chí mạng;
- random thường hoặc seed yếu rất nguy hiểm;
- production cần tiêu chuẩn cao hơn toy demo;
- tự viết crypto production là rủi ro cực cao;
- không constant-time có thể rò thông tin qua timing;
- thiếu test vector dễ làm implementation sai mà không biết;
- production nên có audit/review độc lập.

App có cơ chế **fatal finding**. Một số lỗi không chỉ cộng điểm mà bị báo critical ngay, ví dụ:

```text
Cố định hoặc có thể reuse nonce
Random yếu trong production
Tự viết ECDSA production không audit
```

### Tab 2 — Shamir's trick

Trong ECDSA verification, cần tính:

```text
P = u1G + u2Q
```

Cách trực tiếp:

```text
tính u1G riêng
tính u2Q riêng
cộng hai điểm lại
```

Shamir's trick xử lý hai phép nhân điểm cùng lúc để giảm số phép toán điểm.

Cách dùng:

1. Chọn private key mô phỏng để tạo `Q = dG`.
2. Nhập hệ số `u1`.
3. Nhập hệ số `u2`.
4. Bấm:

```text
📊 So sánh cách trực tiếp và Shamir's trick
```

5. Xem bảng kết quả:
   - kết quả điểm `P`;
   - số phép cộng điểm;
   - số phép nhân đôi điểm;
   - tổng phép toán đếm được.
6. Xem biểu đồ so sánh.

Điểm quan trọng:

```text
Shamir's trick là tối ưu hiệu năng.
Nó không chống nonce attack.
```

### Câu nên nói khi thuyết trình

```text
Page 8 cho thấy ECDSA không dừng ở công thức.
Dùng thật cần secure engineering để không lộ khóa, và algorithmic optimization để verify hiệu quả.
```

---

## Page 9 — OpenSSL secp256k1 và kết luận

### Mục tiêu

Page 9 có hai vai trò:

```text
1. Đối chiếu toy demo với công cụ thật OpenSSL secp256k1.
2. Tổng kết toàn bộ đề tài.
```

Page này không ký giao dịch Bitcoin thật. Nó chỉ ký message/file bằng OpenSSL.

Không có:

```text
Bitcoin Script
sighash thật
transaction serialization thật
consensus/network
broadcast transaction
```

---

### Cấu trúc Page 9

Page 9 có 5 tab:

| Tab | Vai trò |
|---|---|
| 1️⃣ Sinh key thật | Sinh private/public key secp256k1 bằng OpenSSL |
| 2️⃣ Ký nội dung | Ký message gốc bằng private key |
| 3️⃣ Sửa và verify | Dùng chữ ký cũ verify message gốc hoặc message bị sửa |
| 4️⃣ Mini benchmark | Đo thời gian ký/verify trong lab hiện tại |
| 5️⃣ Kết luận đề tài | Tổng kết ECC, ECDLP, ECDSA, Bitcoin, nonce, engineering |

---

### Tab 1 — Sinh key thật

Bấm:

```text
🔑 Sinh cặp khóa secp256k1
```

App dùng OpenSSL để tạo:

```text
private key
public key
```

Các file nằm trong thư mục tạm của app.

---

### Tab 2 — Ký nội dung

1. Nhập nội dung gốc.
2. Bấm:

```text
✍️ Ký nội dung gốc bằng OpenSSL
```

App tạo chữ ký cho đúng nội dung đó.

---

### Tab 3 — Sửa và verify

Có 3 thao tác:

```text
✅ Verify nội dung hiện tại
🧪 Tạo bản bị sửa mẫu
↩️ Khôi phục giống gốc
```

Kết quả đúng:

```text
Nội dung giống gốc → verify pass
Nội dung bị sửa    → verify fail
```

Ý nghĩa:

```text
Chữ ký gắn với dữ liệu cụ thể.
Sửa dữ liệu sau khi ký làm chữ ký cũ mất hiệu lực.
```

Liên hệ Page 6: nếu attacker sửa số tiền hoặc người nhận sau khi transaction đã ký, node phải từ chối.

---

### Tab 4 — Mini benchmark

Tab này đo nhanh thao tác ký/verify trong OpenSSL lab hiện tại.

Cách dùng:

1. Sinh key ở tab 1.
2. Ký message ở tab 2.
3. Chọn số lần chạy thử.
4. Bấm:

```text
📊 Đo thời gian ký/verify
```

Lưu ý: đây chỉ là mini benchmark cho lab hiện tại. Muốn so sánh RSA/ECDSA nhiều hệ thì xem Page 2.

---

### Tab 5 — Kết luận đề tài

Các mảnh ghép cần chốt:

| Mảnh ghép | Kết luận |
|---|---|
| Public-key cryptography | Ra đời để giải quyết trao đổi khóa, xác thực và chữ ký số |
| ECC | Nhánh public-key crypto dựa trên nhóm điểm elliptic curve |
| ECDLP | Bài toán khó: biết `G` và `Q = dG` thì khó tìm lại `d` |
| ECDSA | Chữ ký số trên ECC: private key ký, public key verify |
| Bitcoin | Case study dùng ECDSA để chứng minh quyền tiêu UTXO |
| Nonce attack | ECDLP khó không cứu được nếu nonce bị reuse/lộ/rò |
| Secure engineering | Cần nonce discipline, CSPRNG/RFC6979-style, constant-time, thư viện trưởng thành |
| OpenSSL | Đối chiếu toy demo với công cụ thật |

Câu chốt:

```text
ECC cung cấp nền tảng khóa công khai hiệu quả dựa trên ECDLP;
ECDSA biến nền tảng đó thành cơ chế chữ ký số;
Bitcoin dùng ECDSA như một case study để chứng minh quyền chi tiêu UTXO;
và an toàn thực tế không chỉ đến từ toán học, mà còn đến từ triển khai đúng.
```

---

# 8. Kịch bản thuyết trình gợi ý

## Bản đầy đủ

```text
Page 0: Nêu thesis ECC-first, Bitcoin là case study.
Page 1: Vì sao cần public-key crypto.
Page 2: Đặt ECC cạnh RSA/ElGamal và benchmark trade-off.
Page 3: Giải thích Q = dG bằng toy curve.
Page 4: Minh họa ECDLP bằng brute force/BSGS/Pollard rho.
Page 5: Giải thích ECDSA sign/verify.
Page 6: Mô phỏng Bitcoin UTXO case study.
Page 7: Chứng minh nonce sai làm lộ private key.
Page 8: Phòng thủ triển khai và Shamir optimization.
Page 9: OpenSSL secp256k1 + kết luận.
```

## Bản ngắn 10–15 phút

```text
Page 0 → Page 2 → Page 3 → Page 4 → Page 5 → Page 6 → Page 7 → Page 9
```

Nếu thiếu thời gian, Page 1 và Page 8 có thể nói nhanh, không demo hết.

## Bản tập trung Bitcoin case study

```text
Page 0 → Page 3 → Page 5 → Page 6 → Page 7 → Page 9
```

Dùng khi giảng viên quan tâm trực tiếp đến ECDSA trong Bitcoin.

---

# 9. Lỗi thường gặp và cách xử lý

## 9.1. App giữ trạng thái cũ

Dấu hiệu:

- chữ ký cũ vẫn còn;
- transaction đã bị sửa nhiều lần;
- UTXO set không như kịch bản;
- OpenSSL lab dùng message/key cũ.

Cách xử lý:

```text
Bấm Reset toàn bộ trạng thái mô phỏng ở sidebar.
```

Hoặc riêng Page 6:

```text
Bấm Reset phòng lab giao dịch ở tab 1.
```

---

## 9.2. OpenSSL không tìm thấy

Dấu hiệu:

```text
Không tìm thấy OpenSSL trong PATH
```

Cách xử lý:

1. Kiểm tra:

```powershell
openssl version
```

2. Nếu không chạy được, cài OpenSSL và thêm vào `PATH`.
3. Chạy lại Streamlit.

---

## 9.3. Benchmark không parse được

Có thể do:

- OpenSSL version khác;
- thuật toán không được hỗ trợ;
- output format khác;
- lệnh bị lỗi.

Cách xử lý:

```text
Mở expander “Xem output thô từ OpenSSL”.
Bỏ thuật toán gây lỗi, ví dụ dsa2048 nếu máy không hỗ trợ.
Chạy lại với rsa2048, rsa3072, ecdsap256 trước.
```

---

## 9.4. Toy curve có kết quả lạ

Dấu hiệu:

- message sửa vẫn verify `True`;
- nonce nào đó không tạo được chữ ký;
- attack nonce gặp mẫu số không khả nghịch;
- Pollard rho chưa thành công.

Nguyên nhân:

```text
Toy curve rất nhỏ, order n nhỏ, nên dễ gặp edge-case.
```

Cách xử lý:

```text
Đổi message.
Đổi nonce k.
Bấm nút tìm message sửa chắc chắn bị từ chối.
Dùng auto fallback nonce nếu app có báo tự chọn nonce hợp lệ.
```

Thông điệp cần nhớ:

```text
Toy curve dùng để học.
Không đại diện cho độ an toàn thật của secp256k1.
```

---

## 9.5. Page 6 không có UTXO để tạo giao dịch

Dấu hiệu:

```text
Alice/Bob/Mallory chưa có UTXO chưa bị tiêu.
```

Cách xử lý:

1. Vào Page 6 tab 1.
2. Chọn người nhận UTXO.
3. Nhập số tiền demo.
4. Bấm:

```text
➕ Tạo UTXO
```

Sau đó quay lại tab 2 để tạo giao dịch.

---

## 9.6. Mallory ký được nhưng node vẫn từ chối

Đây là kết quả đúng.

Mallory có thể tạo chữ ký bằng private key của Mallory. Nhưng nếu UTXO bị khóa bởi public key hash của Alice, public key của Mallory không khớp locking condition.

Nói gọn:

```text
Ký được không có nghĩa là tiêu được.
Phải ký bằng khóa khớp điều kiện khóa của UTXO.
```

---

## 9.7. Verify OpenSSL fail sau khi sửa message

Đây là kết quả đúng.

Chữ ký được tạo cho message gốc. Khi message bị sửa, chữ ký cũ không còn hợp lệ.

---

# 10. Các câu chốt quan trọng

## Câu chốt toàn đề tài

```text
ECC là nền tảng public-key crypto dựa trên ECDLP.
ECDSA là chữ ký số xây trên ECC.
Bitcoin là case study dùng ECDSA để chứng minh quyền chi tiêu UTXO.
An toàn thật cần cả toán học đúng và triển khai đúng.
```

## Câu chốt Page 2

```text
ECC không thắng RSA ở mọi phép đo.
Điểm mạnh của ECC là trade-off tốt giữa kích thước khóa, hiệu năng và mức an toàn.
```

## Câu chốt Page 3–4

```text
Tính Q từ d rất nhanh.
Tìm d từ Q là ECDLP, rất khó với tham số thật.
```

## Câu chốt Page 5

```text
ECDSA cho phép private key ký, public key verify, không cần tiết lộ private key.
```

## Câu chốt Page 6

```text
Trong Bitcoin case study, ECDSA là dữ liệu mở khóa giúp chứng minh quyền tiêu một UTXO cụ thể.
```

## Câu chốt Page 7

```text
Không cần phá ECDLP; chỉ cần nonce sai là private key có thể lộ.
```

## Câu chốt Page 8

```text
Secure engineering không phải phần phụ. Với ECDSA, nonce discipline, constant-time, side-channel awareness và thư viện trưởng thành là sống còn.
```

## Câu chốt Page 9

```text
Toy demo giúp hiểu toán; OpenSSL cho thấy luồng ký/verify bằng công cụ thật. Nhưng ký message bằng OpenSSL không phải ký giao dịch Bitcoin đầy đủ.
```

---

# 11. Ghi nhớ cuối cùng

App này nên được hiểu như một **bản đồ học tập có tương tác**, không phải phần mềm mật mã thật.

Khi thuyết trình, nên nhấn mạnh ba lớp:

```text
1. Lớp toán học: ECC, ECDLP, Q = dG.
2. Lớp chữ ký: ECDSA signing và verification.
3. Lớp ứng dụng: Bitcoin UTXO case study và secure implementation.
```

```text
ECDSA an toàn không chỉ vì ECDLP khó, mà còn vì nonce và implementation phải đúng kỷ luật.
```
