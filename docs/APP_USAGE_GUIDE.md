# Hướng dẫn sử dụng app mô phỏng ECC/ECDSA trong Bitcoin

Tài liệu này hướng dẫn cách chạy và sử dụng app Streamlit trong file `app.py`.

App này là một **phòng lab giáo dục** cho project MI4100 về:

```text
ECC → ECDLP → ECDSA → UTXO → giao dịch Bitcoin mô phỏng → lỗi nonce → phòng thủ → tối ưu → OpenSSL secp256k1
```

Mục tiêu chính của app không phải là xây ví Bitcoin thật, mà là giúp người học nhìn thấy **chữ ký số ECDSA được dùng để chứng minh quyền chi tiêu UTXO như thế nào**.

---

## 1. App này dùng để làm gì?

App dùng để học và demo mạch sau:

```text
Bitcoin không có ngân hàng trung gian
→ cần cách chứng minh quyền chi tiêu
→ quyền chi tiêu được biểu diễn bằng UTXO
→ UTXO bị khóa bởi điều kiện khóa
→ người muốn tiêu phải đưa dữ liệu mở khóa
→ private key d tạo public key Q = dG
→ ECDLP làm cho việc tìm d từ Q trở nên khó
→ ECDSA dùng d để tạo chữ ký
→ node dùng public key Q để kiểm tra chữ ký
→ transaction hợp lệ thì UTXO được tiêu
→ transaction sai thì bị từ chối
```

App phù hợp cho 3 mục tiêu:

1. **Học lý thuyết theo mạch câu chuyện**

   Thay vì bắt đầu ngay bằng công thức elliptic curve, app bắt đầu từ câu hỏi thực tế:

   ```text
   Trong một hệ thống không có ngân hàng trung gian, làm sao chứng minh ai có quyền tiêu coin?
   ```

2. **Chạy demo tương tác**

   Người dùng có thể tự chọn private key, nonce, message, UTXO, người gửi, người nhận, số tiền mô phỏng, rồi quan sát app ký, verify, sửa phá và kiểm tra lại.

3. **Dùng làm kịch bản thuyết trình**

   App được chia thành 10 page, đi từ tổng quan đến demo chi tiết. Có thể dùng gần như trực tiếp để trình bày trên lớp.

---

## 2. App này không dùng để làm gì?

App **không phải**:

- ví Bitcoin thật;
- phần mềm sinh private key thật;
- phần mềm ký giao dịch Bitcoin thật;
- Bitcoin full node;
- Bitcoin Script interpreter thật;
- công cụ broadcast giao dịch lên mạng Bitcoin;
- công cụ tấn công khóa Bitcoin;
- phần mềm production crypto.

Toàn bộ private key, public key, UTXO, transaction, chữ ký và attack trong app đều là **mô phỏng giáo dục**.

Không dùng output của app cho ví thật, tiền thật, khóa thật hoặc giao dịch thật.

---

## 3. Cài đặt và chạy app

### 3.1. Tạo môi trường Python

Từ thư mục gốc của repo, chạy:

```powershell
python -m venv .venv
```

Kích hoạt môi trường:

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

Nếu thiếu thư viện, app sẽ báo lỗi `ModuleNotFoundError`. Khi đó cài lại bằng:

```powershell
pip install -r requirements.txt
```

---

### 3.3. Chạy test

```powershell
pytest -q
```

Lệnh này chạy các test của project. Nếu test pass, code nền tảng tương đối ổn để chạy demo.

---

### 3.4. Chạy app Streamlit

```powershell
streamlit run app.py
```

Nếu terminal không nhận lệnh `streamlit`, dùng:

```powershell
python -m streamlit run app.py
```

Sau khi chạy, Streamlit thường tự mở trình duyệt. Nếu không tự mở, copy đường link hiện trong terminal, thường là:

```text
http://localhost:8501
```

---

## 4. Lưu ý khi dùng app

### 4.1. Reset trạng thái

App dùng `st.session_state`, nên dữ liệu demo có thể được giữ lại giữa các thao tác.

Trong sidebar có nút:

```text
🔄 Reset toàn bộ trạng thái mô phỏng
```

Dùng nút này khi:

- app đang giữ chữ ký cũ;
- UTXO set bị bẩn;
- transaction đã bị sửa nhiều lần;
- OpenSSL lab còn file tạm cũ;
- kết quả không giống kịch bản mong muốn.

Riêng page 5 có thêm nút:

```text
🧹 Reset phòng lab giao dịch
```

Nút này chỉ reset phần transaction lab.

---

### 4.2. Toy curve khác secp256k1 thật

Các page 2 đến page 8 chủ yếu dùng **đường cong mô phỏng nhỏ**.

Vì đường cong nhỏ nên có một số hiện tượng lạ:

- message bị sửa nhưng đôi khi chữ ký vẫn verify `True`;
- một số nonce tạo ra chữ ký không hợp lệ;
- một số phép tính rơi vào edge case;
- attack có thể bị chặn vì mẫu số không có nghịch đảo modulo.

Đây là hạn chế của toy curve, không phải hành vi bình thường của secp256k1 thật.

Thông điệp cần nhớ:

```text
Toy curve dùng để học và nhìn rõ phép tính.
secp256k1 thật dùng tham số rất lớn để đạt độ an toàn thực tế.
```

---

### 4.3. OpenSSL chỉ là bonus

Page 9 dùng OpenSSL và secp256k1 thật để ký một đoạn nội dung/file đơn giản.

Nhưng page 9 **không ký giao dịch Bitcoin thật**.

Nó không có:

- Bitcoin Script;
- UTXO thật;
- sighash thật;
- consensus rule;
- network;
- broadcast transaction.

Page 9 chỉ giúp nối ý tưởng từ toy code sang công cụ mật mã thật.

---

## 5. Tổng quan 10 page trong app

| Page | Tên page | Vai trò |
|---:|---|---|
| 0 | Bức tranh tổng quan | Đặt toàn bộ thesis pipeline của project |
| 1 | Quyền sở hữu trong Bitcoin | Giải thích ownership qua UTXO và điều kiện tiêu |
| 2 | ECC: `Q = dG` | Cho thấy private key sinh public key bằng phép nhân điểm |
| 3 | ECDLP | Giải thích vì sao biết `Q` khó suy ra `d` |
| 4 | ECDSA | Demo ký và kiểm tra chữ ký |
| 5 | Phòng lab giao dịch Bitcoin mô phỏng | Demo trung tâm: ECDSA mở khóa UTXO |
| 6 | Tấn công ECDSA khi dùng lại nonce | Demo reused nonce, known nonce và note partial leakage |
| 7 | Phòng thủ nonce | Tóm tắt cách triển khai ECDSA an toàn hơn |
| 8 | Thủ thuật Shamir | Bonus tối ưu bước verify `u1G + u2Q` |
| 9 | Bonus: OpenSSL secp256k1 | Đối chiếu toy demo với công cụ thật |

Nên đi theo thứ tự từ page 0 đến page 9.

Nếu thời gian thuyết trình ngắn, nên ưu tiên:

```text
Page 0 → Page 1 → Page 2 → Page 3 → Page 4 → Page 5 → Page 6 → Page 7
```

Page 8 và page 9 là bonus.

---

# 6. Hướng dẫn từng page

---

## Page 0 — Bức tranh tổng quan

### Mục tiêu

Page 0 trả lời câu hỏi:

```text
Bitcoin cần giải bài toán gì trong môi trường không có ngân hàng trung gian?
```

Luận điểm chính:

```text
Bitcoin không dùng ECC/ECDSA để mã hóa giao dịch.
Bitcoin dùng chữ ký số để xác thực quyền chi tiêu.
```

### Cách dùng

1. Đọc phần intro 3 cột:
   - câu hỏi;
   - ý tưởng;
   - demo chứng minh.

2. Đọc box luận điểm trung tâm.

3. Mở phần dịch thuật ngữ nếu cần:
   - UTXO;
   - quyền chi tiêu;
   - ECDSA;
   - ECDLP.

4. Xem bảng storyline từ bước 0 đến bước 9.

### Ý nghĩa của page này

Page 0 là bản đồ tổng quan. Người học chưa cần hiểu công thức ngay, chỉ cần nắm mạch:

```text
quyền chi tiêu → UTXO → ECC → ECDLP → ECDSA → verify transaction
```

### Câu nên nói khi thuyết trình

```text
Project này không xem Bitcoin như một tài sản đầu tư.
Project này xem Bitcoin như một case study của mật mã khóa công khai:
làm sao dùng chữ ký số để chứng minh quyền chi tiêu mà không cần lộ private key.
```

---

## Page 1 — Quyền sở hữu trong Bitcoin

### Mục tiêu

Page 1 trả lời câu hỏi:

```text
Quyền sở hữu trong Bitcoin được biểu diễn thế nào?
```

Trong mô hình UTXO, ownership không phải là dòng số dư trong tài khoản ngân hàng.

Nói đúng hơn:

```text
Ownership ≈ khả năng thỏa điều kiện tiêu của một UTXO cụ thể
```

### Các khái niệm chính

| Khái niệm | Ý nghĩa |
|---|---|
| UTXO | Một output chưa bị tiêu |
| Locking condition | Điều kiện khóa UTXO |
| Unlocking data | Dữ liệu dùng để mở khóa UTXO |
| Public key hash | Mã băm của public key |
| Signature | Chữ ký chứng minh người ký có private key tương ứng |

Trong demo, app dùng mô hình giống P2PKH:

```text
UTXO bị khóa bởi public key hash
→ người tiêu đưa public key + signature
→ node kiểm tra hash(public key) có khớp không
→ node kiểm tra chữ ký có hợp lệ không
```

### Cách dùng

1. Đọc bảng các lớp:
   - UTXO;
   - điều kiện khóa;
   - dữ liệu mở khóa;
   - kiểm tra;
   - lượt tiêu được chấp nhận.

2. Nhấn mạnh sự khác biệt giữa ví và UTXO set:

```text
Ví giữ private key.
UTXO set biểu diễn các khoản còn tiêu được.
```

### Câu nên nói khi thuyết trình

```text
Một UTXO giống như một tờ tiền có ổ khóa.
Ai muốn tiêu tờ tiền đó phải đưa ra đúng chìa khóa toán học:
public key đúng và chữ ký đúng.
```

---

## Page 2 — ECC: từ private key đến public key

### Mục tiêu

Page 2 trả lời câu hỏi:

```text
Private key tạo public key như thế nào?
```

Công thức trung tâm:

```text
Q = dG
```

Trong đó:

| Ký hiệu | Ý nghĩa |
|---|---|
| `d` | private key, một số nguyên bí mật |
| `G` | điểm sinh cố định trên elliptic curve |
| `Q` | public key, một điểm trên elliptic curve |
| `dG` | phép nhân điểm, tức cộng `G` với chính nó theo quy tắc elliptic curve |

### Cách dùng

1. Đọc warning về toy curve.
2. Mở phần thuật ngữ nếu cần.
3. Xem phương trình toy curve:

```text
y² ≡ x³ + ax + b (mod p)
```

4. Đọc box liên hệ secp256k1:

```text
Bitcoin dùng dạng y² = x³ + 7 mod p
```

5. Dùng slider để chọn private key mô phỏng `d`.

6. Quan sát app tính:

```text
Q = dG
```

7. Mở expander:

```text
🔎 Xem quá trình double-and-add tạo Q
```

8. Xem bảng từng bước double-and-add.

9. Chuyển giữa 2 tab trực quan:
   - trực giác hình học trên số thực;
   - điểm rời rạc trên trường hữu hạn `F_p`.

### Điểm cần nhấn mạnh

`dG` không phải là nhân từng tọa độ của điểm `G` với số `d`.

Nó là phép nhân vô hướng trong nhóm điểm elliptic curve:

```text
dG = G + G + ... + G
```

Tuy nhiên app không cộng lặp chậm kiểu ngây thơ, mà minh họa double-and-add:

```text
biểu diễn d dưới dạng nhị phân
→ dùng thao tác double
→ dùng thao tác add khi bit bằng 1
```

### Câu nên nói khi thuyết trình

```text
Tính xuôi từ d ra Q rất nhanh.
Nhưng đi ngược từ Q về d chính là ECDLP, và đó là lý do public key có thể công khai.
```

---

## Page 3 — ECDLP: vì sao public key không làm lộ private key?

### Mục tiêu

Page 3 trả lời câu hỏi:

```text
Nếu attacker biết G và Q = dG, có tìm lại được d không?
```

Đây là bài toán ECDLP:

```text
Given G and Q = dG, find d.
```

### Các kiểu tấn công trong page 3

Page 3 cho attacker thử tìm `d` bằng 3 cách trên toy curve:

| Thuật toán | Ý tưởng | Độ phức tạp |
|---|---|---|
| Brute force | Thử từng `k` đến khi `kG = Q` | `O(n)` thời gian |
| Baby-step Giant-step | Chia `d = i*m + j`, cho hai phía gặp nhau | `O(√n)` thời gian, `O(√n)` bộ nhớ |
| Pollard rho | Random-walk tìm collision | `O(√n)` kỳ vọng, ít bộ nhớ |

### Cách dùng brute force

1. Chọn private key mô phỏng `d`.
2. App tính public key `Q = dG`.
3. Xem bảng brute force:
   - `k thử`;
   - `kG`;
   - có trùng với `Q` không.

Khi bảng xuất hiện dòng `kG = Q`, app tìm được `d`.

### Cách dùng Baby-step Giant-step

1. Tick:

```text
Hiện thêm Baby-step Giant-step
```

2. Xem bảng so sánh nhanh.
3. Vào tab Baby-step Giant-step.
4. Quan sát:
   - bảng baby steps `jG`;
   - bảng giant steps `Q - i(mG)`;
   - giá trị `i`, `j` khi hai phía gặp nhau.

Ý tưởng:

```text
d = i*m + j
Q = dG = i(mG) + jG
Q - i(mG) = jG
```

### Cách dùng Pollard rho

1. Tick:

```text
Hiện thêm Pollard rho
```

2. Chọn giới hạn số bước.
3. Xem bảng tortoise/hare.
4. Nếu có collision hữu ích, app khôi phục `d`.

Lưu ý: Pollard rho có thể chưa thành công trong một số lần chạy vì đây là demo nhỏ và có tính xác suất.

### Câu nên nói khi thuyết trình

```text
Page này minh họa tấn công trực diện vào toán học nền tảng.
Với toy curve nhỏ thì phá được.
Với secp256k1 thật, kể cả thuật toán O(√n) vẫn quá lớn để thực hiện bằng máy tính cổ điển hiện nay.
```

---

## Page 4 — ECDSA: ký và kiểm tra chữ ký

### Mục tiêu

Page 4 trả lời câu hỏi:

```text
ECDSA chứng minh quyền sở hữu private key như thế nào?
```

Ý tưởng:

```text
private key d dùng để ký
public key Q dùng để verify
người verify không cần biết d
```

### Công thức ký

ECDSA signing dùng:

```text
h = H(m) mod n
R = kG
r = x(R) mod n
s = k⁻¹(h + rd) mod n
```

Trong đó:

| Ký hiệu | Ý nghĩa |
|---|---|
| `m` | dữ liệu cần ký |
| `h` | hash của dữ liệu sau khi rút gọn modulo `n` |
| `d` | private key |
| `k` | nonce dùng một lần |
| `R` | điểm sinh từ nonce |
| `(r, s)` | chữ ký ECDSA |

### Công thức verify

ECDSA verification dùng:

```text
w = s⁻¹ mod n
u1 = hw mod n
u2 = rw mod n
P = u1G + u2Q
valid ⇔ x(P) mod n = r
```

### Cách dùng

1. Chọn:

```text
🔑 Khóa bí mật d
```

2. Chọn:

```text
🎲 Nonce mô phỏng k
```

3. Quan sát public key tương ứng:

```text
Q = dG
```

4. Nhập dữ liệu cần ký, ví dụ:

```text
Hello Bitcoin
```

5. Bấm:

```text
🖊️ Tạo chữ ký
```

6. App tạo chữ ký:

```text
(r, s)
```

7. Mở expander:

```text
🖊️ Xem các bước tạo chữ ký với số cụ thể
```

8. Xem bảng các bước:
   - hash dữ liệu;
   - tính `R = kG`;
   - tính `r`;
   - tính `k⁻¹`;
   - tính `h + rd`;
   - tính `s`.

9. Xem phần kiểm tra chữ ký với dữ liệu gốc.

10. Mở expander:

```text
🧮 Xem các bước kiểm tra chữ ký với số cụ thể
```

11. Sửa dữ liệu trong ô:

```text
🧪 Thử sửa dữ liệu sau khi ký
```

12. Quan sát verify với dữ liệu đã sửa.

### Nếu dữ liệu đã sửa vẫn verify True

Vì app dùng toy curve rất nhỏ, `n` nhỏ, nên đôi khi message khác nhau vẫn vô tình thỏa điều kiện:

```text
x(P) mod n = r
```

Đây là edge case của mô phỏng nhỏ.

Khi gặp trường hợp này, bấm:

```text
🎯 Tạo dữ liệu sửa chắc chắn bị từ chối
```

App sẽ tự tìm một dữ liệu sửa khác khiến verify trả về `False`.

### Câu nên nói khi thuyết trình

```text
Chữ ký số gắn với dữ liệu cụ thể.
Nếu dữ liệu bị sửa sau khi ký, chữ ký cũ thường không còn hợp lệ.
Trong Bitcoin, dữ liệu được ký không phải một câu văn, mà là dữ liệu giao dịch cần được ủy quyền.
```

---

# 7. Page 5 — Phòng lab giao dịch Bitcoin mô phỏng

Page 5 là **demo trung tâm** của app.

### Mục tiêu

Page 5 trả lời câu hỏi:

```text
ECDSA đi vào giao dịch giống Bitcoin như thế nào?
```

Trong demo, một transaction muốn tiêu UTXO phải vượt qua các điều kiện:

```text
1. UTXO được tham chiếu có tồn tại
2. UTXO còn chưa bị tiêu
3. public key hash khớp điều kiện khóa
4. chữ ký ECDSA hợp lệ với dữ liệu giao dịch
```

Nếu tất cả đúng, node mô phỏng chấp nhận transaction.

Nếu một điều kiện sai, node mô phỏng từ chối transaction.

---

## 7.1. Cấu trúc page 5

Page 5 có 4 tab:

| Tab | Tên | Vai trò |
|---:|---|---|
| 1 | Ví mô phỏng & tập UTXO | Xem ví Alice/Bob/Mallory và tạo UTXO |
| 2 | Tạo giao dịch | Chọn sender, UTXO input, receiver, amount |
| 3 | Ký & kiểm tra | Ký transaction và cho node verify |
| 4 | Sửa phá / tấn công / tiêu hai lần | Sửa transaction sau khi ký, thử Mallory, thử double spend |

Page 5 cũng có selectbox:

```text
🎬 Kịch bản hướng dẫn
```

Các kịch bản gồm:

```text
Kịch bản đúng: Alice trả Bob
Sửa số tiền sau khi ký
Mallory cố tiêu UTXO của Alice
Tiêu cùng một UTXO hai lần
Chế độ tự do
```

Khi chọn kịch bản, app hiện checklist gợi ý các bước cần làm.

---

## 7.2. Kịch bản 1 — Alice trả Bob thành công

### Mục tiêu

Chứng minh flow hợp lệ:

```text
Alice có UTXO
→ Alice tạo transaction trả Bob
→ Alice ký bằng private key của mình
→ node verify thành công
→ UTXO cũ bị tiêu
→ UTXO mới thuộc về Bob
```

### Bước 1: Tạo UTXO cho Alice

Vào tab:

```text
1️⃣ Ví mô phỏng & tập UTXO
```

Ở phần tạo UTXO:

```text
Tạo cho: Alice
Số tiền demo: 10
```

Bấm:

```text
➕ Tạo UTXO
```

Kết quả: bảng UTXO xuất hiện một khoản thuộc về Alice.

---

### Bước 2: Tạo transaction Alice → Bob

Vào tab:

```text
2️⃣ Tạo giao dịch
```

Chọn:

```text
Người gửi: Alice
Chọn UTXO đầu vào: UTXO của Alice
Người nhận: Bob
Số tiền demo: 10
```

Bấm:

```text
Tạo giao dịch chưa ký
```

App sẽ hiển thị transaction mô phỏng ở dạng JSON.

---

### Bước 3: Ký transaction bằng Alice

Vào tab:

```text
3️⃣ Ký & kiểm tra
```

Chọn:

```text
Người ký: Alice
```

Bấm:

```text
✍️ Ký giao dịch đang chọn
```

Lúc này input của transaction sẽ có:

```text
chữ ký = (r, s)
khóa công khai = Q của Alice
```

---

### Bước 4: Node kiểm tra transaction

Bấm:

```text
🧪 Node kiểm tra giao dịch
```

Kết quả đúng:

```text
✅ Node mô phỏng CHẤP NHẬN giao dịch.
```

Bảng kiểm tra nên có:

| Bước kiểm tra | Kết quả đúng |
|---|---|
| UTXO được tham chiếu có tồn tại không | True |
| UTXO còn chưa bị tiêu không | True |
| Mã băm khóa công khai có khớp điều kiện khóa không | True |
| Chữ ký ECDSA có hợp lệ không | True |
| Kết luận cuối cùng | True |

---

### Bước 5: Áp dụng transaction vào UTXO set

Bấm:

```text
📣 Gửi / áp dụng vào tập UTXO
```

Kết quả:

```text
UTXO cũ của Alice bị tiêu
UTXO mới thuộc về Bob được thêm vào
```

### Câu nên nói khi thuyết trình

```text
Đây là mô hình cốt lõi:
Alice không cần gửi private key cho node.
Alice chỉ gửi signature + public key.
Node dùng public key để kiểm tra chữ ký và kiểm tra public key hash có khớp UTXO hay không.
```

---

## 7.3. Kịch bản 2 — Sửa số tiền sau khi ký

### Mục tiêu

Chứng minh chữ ký gắn với dữ liệu transaction.

Nếu transaction đã được ký rồi mà sửa amount, chữ ký cũ phải bị invalid.

### Cách làm

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab:

```text
4️⃣ Sửa phá / tấn công / tiêu hai lần
```

5. Nhập số tiền mới ở ô:

```text
🔧 Nhập số tiền mới sau khi ký
```

Ví dụ transaction ban đầu amount `10`, sửa thành `15`.

6. Bấm:

```text
🔧 Áp dụng số tiền mới
```

7. Bấm:

```text
🧪 Kiểm tra giao dịch đã bị sửa
```

### Kết quả đúng

Node mô phỏng phải từ chối.

Lý do:

```text
Chữ ký được tạo trên dữ liệu transaction ban đầu.
Sau khi đổi amount, dữ liệu transaction thay đổi.
Chữ ký cũ không còn khớp.
```

### Câu nên nói khi thuyết trình

```text
Chữ ký không chỉ chứng minh “Alice đồng ý gửi tiền”.
Nó gắn với nội dung transaction cụ thể.
Đổi số tiền sau khi ký làm chữ ký cũ mất giá trị.
```

---

## 7.4. Kịch bản 3 — Đổi người nhận sang Mallory sau khi ký

### Mục tiêu

Chứng minh attacker không thể đổi receiver sau khi transaction đã ký.

### Cách làm

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab:

```text
4️⃣ Sửa phá / tấn công / tiêu hai lần
```

5. Bấm:

```text
🔧 Đổi người nhận sang Mallory
```

6. Bấm:

```text
🧪 Kiểm tra giao dịch đã bị sửa
```

### Kết quả đúng

Node mô phỏng từ chối.

Lý do:

```text
Output đã bị sửa.
Dữ liệu transaction không còn là dữ liệu Alice đã ký.
```

---

## 7.5. Kịch bản 4 — Mallory cố tiêu UTXO của Alice

### Mục tiêu

Chứng minh không thể ký bằng private key sai để tiêu UTXO của người khác.

### Cách làm kiểu 1: Ký giao dịch nháp bằng Mallory

1. Tạo UTXO cho Alice.
2. Tạo transaction tiêu UTXO của Alice.
3. Vào tab:

```text
3️⃣ Ký & kiểm tra
```

4. Chọn:

```text
Người ký: Mallory
```

5. Bấm:

```text
✍️ Ký giao dịch đang chọn
```

6. Bấm:

```text
🧪 Node kiểm tra giao dịch
```

### Cách làm kiểu 2: Dùng nút trong tab phá

1. Sau khi có transaction nháp hoặc transaction đã ký, vào tab:

```text
4️⃣ Sửa phá / tấn công / tiêu hai lần
```

2. Bấm:

```text
🦹 Ký giao dịch nháp bằng Mallory
```

3. Kiểm tra lại bằng node mô phỏng.

### Kết quả đúng

Node từ chối.

Lý do:

```text
UTXO của Alice bị khóa bởi hash public key của Alice.
Mallory ký bằng private key khác.
Public key/hash của Mallory không khớp locking condition của UTXO Alice.
```

---

## 7.6. Kịch bản 5 — Thay public key mở khóa bằng của Mallory

### Mục tiêu

Chứng minh chữ ký và public key không thể bị thay tùy tiện.

### Cách làm

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab:

```text
4️⃣ Sửa phá / tấn công / tiêu hai lần
```

5. Bấm:

```text
🦹 Thay khóa công khai mở khóa bằng của Mallory
```

6. Bấm:

```text
🧪 Kiểm tra giao dịch đã bị sửa
```

### Kết quả đúng

Node từ chối.

Có hai lý do trực giác:

```text
public key hash không khớp locking condition của UTXO Alice
hoặc chữ ký không còn kiểm tra đúng với public key đã bị thay
```

---

## 7.7. Kịch bản 6 — Tiêu cùng một UTXO hai lần

### Mục tiêu

Chứng minh vai trò của UTXO set trong chống double-spend.

### Cách làm

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab:

```text
4️⃣ Sửa phá / tấn công / tiêu hai lần
```

5. Bấm:

```text
♻️ Thử tiêu hai lần giao dịch hiện tại
```

### Kết quả đúng

```text
Lần đầu: được chấp nhận
Lần hai: bị từ chối
```

Lý do:

```text
Lần đầu transaction tiêu UTXO thành công.
Sau đó UTXO bị đánh dấu là đã tiêu.
Lần hai dùng lại cùng UTXO nên node từ chối.
```

### Nếu kết quả không như mong muốn

Bấm:

```text
🧹 Reset phòng lab giao dịch
```

Rồi làm lại từ đầu.

---

# 8. Page 6 — Tấn công ECDSA khi dùng lại nonce

### Mục tiêu

Page 6 trả lời câu hỏi:

```text
ECDSA có chắc chắn an toàn không?
```

Câu trả lời đúng là:

```text
ECDSA an toàn nếu toán học đúng và triển khai đúng.
Nhưng nếu nonce k bị dùng sai, private key có thể bị lộ.
```

Page 6 không phá ECDLP. Nó minh họa lỗi implementation.

---

## 8.1. Các kiểu tấn công trong page 6

Page 6 có 3 mode:

```text
Reused nonce: dùng lại k cho hai chữ ký
Known nonce: nonce k bị lộ trong một chữ ký
Partial nonce leakage: ghi chú lý thuyết
```

---

## 8.2. Reused nonce attack

### Ý tưởng

Nếu hai message khác nhau dùng cùng nonce `k`, ta có:

```text
s1 = k⁻¹(h1 + r d) mod n
s2 = k⁻¹(h2 + r d) mod n
```

Lấy hiệu:

```text
s1 - s2 = k⁻¹(h1 - h2) mod n
```

Suy ra:

```text
k' = (h1 - h2)(s1 - s2)⁻¹ mod n
```

Sau khi có `k`, suy ra private key:

```text
d' = (s1 k' - h1)r⁻¹ mod n
```

### Cách dùng

1. Chọn private key mô phỏng:

```text
🔑 Khóa bí mật d
```

2. Chọn nonce:

```text
🎲 Nonce k
```

3. Nhập hai thông điệp khác nhau:

```text
Thông điệp 1
Thông điệp 2
```

4. Chọn mode:

```text
Reused nonce: dùng lại k cho hai chữ ký
```

5. Bấm:

```text
⚡ Chạy mô phỏng tấn công
```

6. Xem bảng hai chữ ký dùng cùng nonce.
7. Xem bảng khôi phục `k` và `d`.

### Kết quả đúng

Nếu không gặp edge case, app báo:

```text
🎯 Tấn công thành công: đã khôi phục nonce và khóa bí mật.
```

---

## 8.3. Known nonce attack

### Ý tưởng

Nếu attacker biết nonce `k` của **một chữ ký**, private key cũng có thể bị khôi phục.

Từ công thức:

```text
s = k⁻¹(h + r d) mod n
```

Suy ra:

```text
d' = (s k - h)r⁻¹ mod n
```

### Cách dùng

1. Chọn `d`.
2. Chọn `k`.
3. Nhập thông điệp 1.
4. Chọn mode:

```text
Known nonce: nonce k bị lộ trong một chữ ký
```

5. Bấm:

```text
⚡ Chạy mô phỏng tấn công
```

6. Xem bảng chữ ký có nonce bị lộ.
7. Xem bảng khôi phục private key.

### Kết quả đúng

Nếu không gặp edge case, app báo:

```text
🎯 Tấn công thành công: chỉ cần biết nonce k của một chữ ký là khôi phục được private key.
```

---

## 8.4. Partial nonce leakage

### Ý tưởng

Partial nonce leakage là trường hợp nonce không bị lộ hoàn toàn, nhưng bị rò một phần qua nhiều chữ ký.

Ví dụ:

```text
rò vài bit của k
random generator bị lệch
side-channel làm lộ thông tin về k
```

Trong thực tế, dạng này có thể dẫn tới các tấn công nâng cao như lattice attack.

### Cách dùng

1. Chọn mode:

```text
Partial nonce leakage: ghi chú lý thuyết
```

2. Bấm:

```text
⚡ Chạy mô phỏng tấn công
```

3. App hiển thị bảng so sánh:
   - reused nonce;
   - known nonce;
   - partial nonce leakage.

### Vì sao app không demo lattice attack?

Vì lattice attack là chủ đề nâng cao, dễ làm loãng project.

Project này tập trung vào:

```text
ECC/ECDSA trong Bitcoin
```

nên page 6 chỉ cần demo reused nonce và known nonce là đủ.

---

## 8.5. Nếu app báo lỗi nonce

Một số lỗi có thể xuất hiện:

```text
Provided k has no modular inverse mod n
```

hoặc:

```text
Không tạo được chữ ký với k = ...
```

Điều cần hiểu:

```text
Lỗi này liên quan đến nonce k hoặc edge case của toy curve.
Nó không phải do private key d.
```

Trong toy curve nhỏ, một số giá trị có thể làm chữ ký rơi vào trường hợp không hợp lệ.

App có cơ chế tự thử tìm nonce hợp lệ khác. Nếu vẫn lỗi:

- đổi `k`;
- đổi message;
- bấm reset app;
- restart Streamlit nếu session bị bẩn.

### Câu nên nói khi thuyết trình

```text
ECDLP khó không cứu được mình nếu ECDSA bị triển khai sai.
Không cần phá elliptic curve; chỉ cần nonce bị dùng sai là private key có thể bay màu.
```

---

# 9. Page 7 — Phòng thủ nonce trong ECDSA

### Mục tiêu

Page 7 trả lời câu hỏi:

```text
Nếu nonce reuse nguy hiểm, phòng thủ thế nào?
```

Luận điểm chính:

```text
ECDSA chỉ an toàn khi toán học đúng và implementation đúng.
```

### Nội dung chính

Page 7 có bảng các cách phòng thủ:

| Cách phòng thủ | Ý nghĩa |
|---|---|
| Không bao giờ dùng lại nonce `k` | Mỗi chữ ký phải có nonce riêng |
| Dùng nguồn ngẫu nhiên đáng tin cậy | RNG yếu có thể làm nonce đoán được |
| Sinh nonce xác định kiểu RFC6979 | Giảm phụ thuộc vào random bên ngoài |
| Triển khai constant-time | Giảm rò rỉ qua thời gian chạy/kênh phụ |
| Dùng thư viện mật mã đã kiểm chứng | Không tự viết crypto production từ demo |

### Câu nên nói khi thuyết trình

```text
Mật mã không chỉ là công thức.
Mật mã an toàn cần cả công thức đúng, random đúng, code đúng và thư viện đúng.
```

---

# 10. Page 8 — Thủ thuật Shamir

### Mục tiêu

Page 8 trả lời câu hỏi:

```text
Có thể tối ưu bước kiểm tra chữ ký ECDSA không?
```

Trong ECDSA verify, cần tính:

```text
P = u1G + u2Q
```

Cách trực tiếp:

```text
tính u1G riêng
tính u2Q riêng
rồi cộng lại
```

Shamir’s trick tính hai phép nhân điểm đồng thời để giảm số phép toán.

### Cách dùng

1. Nhập `u1`.
2. Nhập `u2`.
3. App cố định:

```text
Q = 5G
```

4. Bấm:

```text
📊 Chạy so sánh
```

5. Xem biểu đồ:
   - số phép cộng điểm;
   - số phép nhân đôi điểm;
   - cách trực tiếp;
   - cách Shamir.

6. Xem kết quả hai cách có giống nhau không.

### Ý nghĩa

Page 8 không phải trọng tâm Bitcoin ownership. Đây là phần bonus để cho thấy:

```text
crypto thực tế không chỉ có công thức đúng,
mà còn cần tối ưu thuật toán và hiệu năng.
```

### Câu nên nói khi thuyết trình

```text
ECDSA verification có biểu thức u1G + u2Q.
Shamir's trick giúp tính biểu thức này hiệu quả hơn bằng cách xử lý hai phép nhân điểm cùng lúc.
```

---

# 11. Page 9 — Bonus: OpenSSL secp256k1

### Mục tiêu

Page 9 trả lời câu hỏi:

```text
Toy demo liên hệ công cụ thật thế nào?
```

Toy curve giúp hiểu từng bước. OpenSSL secp256k1 cho thấy việc ký và kiểm tra chữ ký cũng tồn tại trong công cụ mật mã thật.

### Điều kiện cần

Máy cần có OpenSSL trong `PATH`.

Kiểm tra bằng:

```powershell
openssl version
```

Nếu không có OpenSSL, page 9 sẽ báo:

```text
Không tìm thấy OpenSSL trong PATH
```

Khi đó cần cài OpenSSL và thêm vào biến môi trường `PATH`.

---

## 11.1. Tab 1 — Sinh khóa

### Cách dùng

1. Vào tab:

```text
1️⃣ Sinh khóa
```

2. Bấm:

```text
🔑 Sinh cặp khóa secp256k1
```

3. App tạo:
   - private key tạm;
   - public key tạm.

4. Có thể mở expander để xem vị trí file tạm.

### Lưu ý

Các file key nằm trong thư mục tạm của app.

Không commit các file như:

```text
*.pem
*.key
*.bin
```

lên GitHub.

---

## 11.2. Tab 2 — Ký nội dung gốc

### Cách dùng

1. Vào tab:

```text
2️⃣ Ký nội dung gốc
```

2. Nhập nội dung, ví dụ:

```text
Alice trả Bob 1 BTC mô phỏng
```

3. Bấm:

```text
✍️ Ký nội dung gốc bằng OpenSSL
```

4. App hiển thị phần đầu chữ ký dạng hex.

### Ý nghĩa

Chữ ký này chỉ hợp lệ với đúng nội dung đã ký.

---

## 11.3. Tab 3 — Tự sửa và kiểm tra

### Cách dùng

1. Vào tab:

```text
3️⃣ Tự sửa và kiểm tra
```

2. Cột trái là nội dung gốc đã ký.
3. Cột phải là nội dung đem đi kiểm tra.

Có 3 nút:

```text
✅ Kiểm tra với nội dung hiện tại
🧪 Tạo bản bị sửa mẫu
↩️ Khôi phục giống nội dung gốc
```

### Kịch bản đúng

Nếu nội dung kiểm tra giống nội dung gốc:

```text
chữ ký được chấp nhận
```

Nếu sửa nội dung:

```text
chữ ký bị từ chối
```

### Liên hệ với Bitcoin

Nếu ai đó sửa số tiền hoặc người nhận sau khi transaction đã ký, chữ ký cũ sẽ không còn khớp với dữ liệu giao dịch nữa.

Đây là cùng ý tưởng với page 5, nhưng page 9 dùng OpenSSL và secp256k1 thật để minh họa tính toàn vẹn của chữ ký.

---

## 11.4. Tab 4 — Đo thời gian

### Cách dùng

1. Vào tab:

```text
4️⃣ Đo thời gian
```

2. Chọn số lần chạy thử.
3. Bấm:

```text
📊 Đo thời gian
```

4. App hiển thị:
   - thời gian ký trung bình;
   - thời gian verify trung bình;
   - số lần ký mỗi giây;
   - số lần verify mỗi giây;
   - biểu đồ so sánh.

### Lưu ý

Kết quả phụ thuộc vào:

- máy đang dùng;
- phiên bản OpenSSL;
- môi trường chạy;
- số lần benchmark.

Không dùng benchmark này để kết luận hiệu năng hệ thống thật.

---

# 12. Kịch bản thuyết trình gợi ý

Nếu có khoảng 10 đến 15 phút, nên đi như sau:

```text
Page 0: Nêu thesis pipeline
Page 1: Giải thích UTXO ownership
Page 2: Demo Q = dG
Page 3: Demo ECDLP trên toy curve
Page 4: Demo ECDSA ký/verify message
Page 5: Demo transaction lab Alice trả Bob
Page 6: Demo reused nonce attack
Page 7: Chốt phòng thủ nonce
```

Nếu còn thời gian:

```text
Page 8: Shamir's trick
Page 9: OpenSSL secp256k1
```

---

## 12.1. Kịch bản demo ngắn nhất

Dùng khi thời gian rất ít.

### Bước 1: Page 0

Nói:

```text
Bitcoin cần chứng minh quyền chi tiêu, không cần chứng minh danh tính.
```

### Bước 2: Page 2

Chọn `d`, cho thấy:

```text
Q = dG
```

Nói:

```text
Private key tạo public key.
```

### Bước 3: Page 3

Cho brute force tìm `d` trên toy curve.

Nói:

```text
Toy curve nhỏ nên phá được.
secp256k1 thật thì không.
```

### Bước 4: Page 4

Ký `Hello Bitcoin`, sửa message, verify fail.

Nói:

```text
Chữ ký gắn với dữ liệu.
```

### Bước 5: Page 5

Tạo UTXO cho Alice, tạo transaction Alice → Bob, ký, verify.

Nói:

```text
Đây là cách chữ ký mở khóa UTXO.
```

### Bước 6: Page 6

Chạy reused nonce attack.

Nói:

```text
ECDLP khó không cứu được nếu nonce bị dùng lại.
```

---

# 13. Các lỗi thường gặp

## 13.1. Không chạy được Streamlit

Lỗi thường gặp:

```text
streamlit: The term 'streamlit' is not recognized
```

Cách sửa:

```powershell
python -m streamlit run app.py
```

Nếu vẫn lỗi:

```powershell
pip install streamlit
```

---

## 13.2. Thiếu thư viện

Lỗi:

```text
ModuleNotFoundError
```

Cách sửa:

```powershell
pip install -r requirements.txt
```

---

## 13.3. Page 9 không tìm thấy OpenSSL

Lỗi:

```text
Không tìm thấy OpenSSL trong PATH
```

Cách sửa:

```powershell
openssl version
```

Nếu terminal cũng không nhận `openssl`, cần cài OpenSSL và thêm vào `PATH`.

---

## 13.4. Message sửa nhưng vẫn verify True ở page 4

Nguyên nhân:

```text
Toy curve quá nhỏ.
n nhỏ nên một số message khác nhau có thể vô tình thỏa điều kiện verify.
```

Cách xử lý:

```text
Bấm "Tạo dữ liệu sửa chắc chắn bị từ chối"
```

hoặc đổi message khác.

---

## 13.5. Nonce attack báo edge case

Nguyên nhân có thể là:

- hai message giống nhau;
- hash modulo `n` bị trùng;
- `s1 - s2` không có nghịch đảo;
- `r` không có nghịch đảo;
- toy curve quá nhỏ;
- session state đang giữ giá trị cũ.

Cách xử lý:

1. đổi message;
2. đổi nonce `k`;
3. đổi private key `d`;
4. bấm reset;
5. restart Streamlit.

---

## 13.6. Giao dịch page 5 bị từ chối dù làm đúng

Kiểm tra các điểm sau:

1. UTXO đã được tạo chưa?
2. UTXO còn chưa bị tiêu không?
3. Transaction đã được ký chưa?
4. Có ký bằng đúng owner không?
5. Có sửa amount hoặc receiver sau khi ký không?
6. Có thay public key thành Mallory không?
7. Có dùng lại transaction đã apply rồi không?

Nếu không chắc, bấm:

```text
🧹 Reset phòng lab giao dịch
```

rồi làm lại kịch bản Alice trả Bob.

---

# 14. Thông điệp chính cần nhớ

App muốn người học nhớ 5 ý:

1. **Bitcoin không cần biết danh tính người dùng.**

   Bitcoin cần kiểm tra quyền chi tiêu một UTXO cụ thể.

2. **Private key tạo public key bằng ECC.**

   ```text
   Q = dG
   ```

3. **Public key không làm lộ private key vì ECDLP khó.**

   Toy curve phá được, secp256k1 thật thì không khả thi trong thực tế cổ điển.

4. **ECDSA dùng private key để ký và public key để verify.**

   Người verify không cần biết private key.

5. **Implementation sai có thể làm lộ private key.**

   Reused nonce hoặc known nonce có thể làm ECDSA bay màu dù toán học nền tảng vẫn mạnh.

---

# 15. Một câu chốt cho báo cáo

Có thể dùng câu này để kết thúc phần demo:

```text
Dự án cho thấy Bitcoin không dùng ECC/ECDSA để che giấu giao dịch, mà dùng chữ ký số để chứng minh quyền chi tiêu UTXO. ECC tạo ra quan hệ Q = dG dễ tính xuôi nhưng khó đảo ngược; ECDSA biến private key thành chữ ký có thể kiểm tra bằng public key; còn UTXO set giúp node biết output nào còn được tiêu. Tuy nhiên, bảo mật không chỉ nằm ở toán học: nếu nonce trong ECDSA bị dùng sai, private key có thể bị khôi phục ngay cả khi ECDLP vẫn rất khó.
```
