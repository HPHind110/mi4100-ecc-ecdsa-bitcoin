# Hướng dẫn sử dụng app mô phỏng ECC/ECDSA trong Bitcoin

> App này là **phòng lab giáo dục** cho project MI4100: *Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin*.
>
> Mục tiêu không phải xây ví Bitcoin, không phải ký giao dịch Bitcoin thật, không phải kết nối mạng Bitcoin. Mục tiêu là giúp người học hiểu mạch:
>
> ```text
> Bitcoin cần chứng minh quyền chi tiêu
> → UTXO bị khóa bởi điều kiện tiêu
> → ECC tạo khóa công khai Q = dG từ khóa bí mật d
> → ECDLP khiến việc tìm d từ Q trở nên khó
> → ECDSA tạo chữ ký số
> → node mô phỏng kiểm tra chữ ký để chấp nhận hoặc từ chối giao dịch
> → nonce sai có thể làm lộ private key
> → OpenSSL secp256k1 nối toy demo với công cụ mật mã thật
> ```

---

## 1. App này dùng để làm gì?

App được thiết kế để phục vụ 3 việc:

1. **Học lý thuyết theo câu chuyện rõ ràng**  
   Thay vì bắt đầu từ công thức elliptic curve, app bắt đầu từ câu hỏi:  
   *Trong một hệ thống không có ngân hàng trung gian, làm sao chứng minh ai có quyền tiêu coin?*

2. **Chạy demo tương tác**  
   Người dùng có thể tự chọn khóa bí mật, tạo public key, ký message, sửa message, tạo UTXO, ký transaction mô phỏng, thử double-spend, và xem node mô phỏng chấp nhận hay từ chối.

3. **Chuẩn bị thuyết trình/báo cáo**  
   App đã đi theo mạch Q0–Q9, có thể dùng gần như trực tiếp làm kịch bản demo trên lớp.

---

## 2. App này không dùng để làm gì?

App **không phải**:

- ví Bitcoin thật;
- phần mềm sinh ví;
- phần mềm ký giao dịch Bitcoin thật;
- Bitcoin node;
- Script interpreter thật;
- trình broadcast giao dịch;
- công cụ tìm private key;
- công cụ tấn công secp256k1 thật.

Tất cả khóa, UTXO, transaction và attack trong app đều là **mô phỏng giáo dục**.

---

## 3. Cách cài đặt và chạy app

### 3.1. Chuẩn bị môi trường

Từ thư mục gốc của repo, nên tạo virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Cài thư viện:

```powershell
pip install -r requirements.txt
```

Kiểm tra test:

```powershell
pytest -q
```

Chạy app:

```powershell
streamlit run app.py
```

Theo tài liệu Streamlit, lệnh `streamlit run your_script.py` sẽ chạy một local Streamlit server và thường tự mở app trong trình duyệt.

### 3.2. Chạy bằng Python module nếu cần

Nếu máy không nhận lệnh `streamlit`, thử:

```powershell
python -m streamlit run app.py
```

### 3.3. Phần OpenSSL

Trang 9 cần OpenSSL trong `PATH`.

Kiểm tra:

```powershell
openssl version
```

Nếu báo không tìm thấy OpenSSL, cần cài OpenSSL và thêm vào biến môi trường `PATH`.

---

## 4. Cách đi qua app theo đúng mạch

App có 10 trang:

| Trang | Tên trang | Vai trò trong câu chuyện |
|---:|---|---|
| 0 | Bức tranh tổng quan | Đặt bài toán: Bitcoin cần chứng minh quyền chi tiêu, không cần mã hóa transaction |
| 1 | Quyền sở hữu trong Bitcoin | Giải thích ownership qua UTXO và điều kiện mở khóa |
| 2 | ECC: `Q = dG` | Cho thấy private key sinh public key bằng scalar multiplication |
| 3 | ECDLP | Cho thấy vì sao biết public key `Q` không dễ suy ra private key `d` |
| 4 | ECDSA | Demo ký và kiểm tra chữ ký |
| 5 | Phòng lab giao dịch Bitcoin mô phỏng | Demo trung tâm: ECDSA mở khóa UTXO như thế nào |
| 6 | Tấn công reused nonce | Cho thấy ECDSA chết nếu nonce `k` bị dùng lại |
| 7 | Phòng thủ nonce | Tóm tắt cách tránh lỗi nonce khi triển khai |
| 8 | Thủ thuật Shamir | Bonus: tối ưu bước verify `u1G + u2Q` |
| 9 | OpenSSL secp256k1 | Nối toy demo với công cụ mật mã thật |

Nên đi theo thứ tự từ trang 0 đến trang 9. Đừng nhảy ngay vào OpenSSL hoặc nonce attack nếu người nghe chưa hiểu UTXO và ECDSA dùng để làm gì.

---

## 5. Hướng dẫn từng trang

### Trang 0 — Bức tranh tổng quan

**Câu hỏi chính:** Bitcoin cần giải bài toán gì trong môi trường không có ngân hàng trung gian?

**Ý tưởng:** Bitcoin không hỏi “mày đăng nhập tài khoản nào?”. Bitcoin hỏi:

> Mày có tạo được chữ ký hợp lệ để tiêu UTXO này không?

**Cách dùng:**

1. Đọc phần luận điểm trung tâm.
2. Mở bảng storyline.
3. Giải thích nhanh từng bước: quyền chi tiêu, UTXO, ECC, ECDLP, ECDSA, xác thực giao dịch, nonce attack, OpenSSL.

**Câu nên nói khi thuyết trình:**

> Project này không nói Bitcoin như một tài sản đầu tư. Project này xem Bitcoin như một case study của mật mã khóa công khai: chữ ký số biến private key thành bằng chứng quyền chi tiêu.

---

### Trang 1 — Quyền sở hữu trong Bitcoin

**Câu hỏi chính:** Quyền sở hữu trong Bitcoin được biểu diễn như thế nào?

**Ý tưởng:** Trong mô hình UTXO:

```text
Ownership ≈ khả năng thỏa điều kiện tiêu của một UTXO
```

Trong demo P2PKH-like:

```text
locking condition  ≈ public key hash
unlocking data     ≈ signature + public key
verification       ≈ hash(public key) khớp lock và signature hợp lệ
```

**Cách dùng:**

1. Đọc bảng các lớp: UTXO, điều kiện khóa, dữ liệu mở khóa, kiểm tra, lượt tiêu được chấp nhận.
2. Nhấn mạnh rằng ví không “chứa coin” theo nghĩa database ngân hàng.
3. Ví giữ private key; UTXO set mới biểu diễn các output còn tiêu được.

**Câu nên nói khi thuyết trình:**

> Một UTXO giống như một tờ tiền có ổ khóa. Người muốn tiêu phải đưa ra chìa khóa toán học: public key đúng và chữ ký đúng.

---

### Trang 2 — ECC: từ private key đến public key

**Câu hỏi chính:** Private key sinh ra public key như thế nào?

**Ý tưởng:** ECC dùng phép nhân vô hướng trên nhóm điểm elliptic curve:

```text
Q = dG
```

Trong đó:

- `d` là private key;
- `G` là điểm sinh;
- `Q` là public key.

**Cách dùng:**

1. Chọn một giá trị `d` bằng slider.
2. Quan sát app tính `Q = dG`.
3. Xem biểu đồ các điểm trên toy curve.
4. Chỉ ra điểm `G` và điểm `Q`.

**Điều cần nhấn mạnh:** Toy curve trong app rất nhỏ. Nó chỉ dùng để nhìn được các điểm và tính toán dễ hiểu. Nó không phải secp256k1 và không an toàn.

**Câu nên nói khi thuyết trình:**

> Tính xuôi `d → Q` thì nhanh. Nhưng bài toán ngược `Q → d` chính là ECDLP, được bàn ở trang tiếp theo.

---

### Trang 3 — ECDLP: vì sao public key không làm lộ private key?

**Câu hỏi chính:** Nếu attacker biết `G` và `Q = dG`, có tìm lại được `d` không?

**Ý tưởng:** Đây là bài toán ECDLP:

```text
Given G and Q = dG, find d.
```

Với toy curve nhỏ, ta tìm được `d`. Với secp256k1 thật, không khả thi bằng các thuật toán cổ điển hiện biết.

**Cách dùng brute force:**

1. Chọn private key mô phỏng `d`.
2. App tính public key `Q = dG`.
3. Xem bảng brute force: thử `0G`, `1G`, `2G`, ... đến khi `kG = Q`.

**Cách dùng Baby-step Giant-step:**

1. Tick “Hiện thêm Baby-step Giant-step”.
2. Quan sát app chia bài toán thành baby steps `jG` và giant steps `Q - i(mG)`.
3. Khi hai bên gặp nhau, app suy ra `d = i*m + j`.

**Cách dùng Pollard rho:**

1. Tick “Hiện thêm Pollard rho”.
2. Có thể tăng/giảm giới hạn số bước.
3. Nếu app tìm được collision hữu ích, nó khôi phục `d`.
4. Nếu app báo collision suy biến hoặc chưa thành công, đây là hành vi chấp nhận được vì Pollard rho mang tính xác suất.

**Câu nên nói khi thuyết trình:**

> Brute force là `O(n)`. Baby-step Giant-step giảm xuống `O(√n)` nhưng tốn bộ nhớ. Pollard rho cũng khoảng `O(√n)` kỳ vọng, bộ nhớ thấp hơn. Nhưng với secp256k1, `√n` vẫn khổng lồ.

**Cảnh báo:** Không dùng các thuật toán này để thử khóa Bitcoin thật. Đây chỉ là demo toy curve.

---

### Trang 4 — ECDSA: ký và kiểm tra chữ ký

**Câu hỏi chính:** ECDSA chứng minh quyền sở hữu private key như thế nào?

**Ý tưởng:**

- Private key dùng để ký.
- Public key dùng để verify.
- Người verify không cần biết private key.

**Cách dùng:**

1. Chọn khóa bí mật `d`.
2. App hiển thị public key `Q`.
3. Nhập message, ví dụ `Hello Bitcoin`.
4. Bấm “Tạo chữ ký”.
5. App tạo chữ ký `(r, s)`.
6. Kiểm tra message gốc: phải hợp lệ.
7. Sửa message ở ô “Thử sửa dữ liệu sau khi ký”.
8. Quan sát verify bị từ chối.

**Nếu message đã sửa vẫn verify True:** Vì toy curve rất nhỏ, đôi khi message khác nhau vẫn rơi vào edge case. Khi đó bấm “Tạo dữ liệu sửa chắc chắn bị từ chối”.

**Câu nên nói khi thuyết trình:**

> Chữ ký không chỉ chứng minh ai ký, mà còn gắn với dữ liệu đã ký. Nếu dữ liệu bị sửa sau khi ký, chữ ký cũ thường không còn hợp lệ.

---

## 6. Trang 5 — Phòng lab giao dịch Bitcoin mô phỏng

Đây là **trang demo trung tâm** của app.

**Câu hỏi chính:** ECDSA đi vào giao dịch giống Bitcoin như thế nào?

**Ý tưởng:** Một transaction muốn tiêu UTXO phải chứng minh:

```text
1. UTXO được tham chiếu có tồn tại
2. UTXO chưa bị tiêu
3. public key hash khớp điều kiện khóa
4. chữ ký ECDSA hợp lệ với transaction data
```

Nếu đủ điều kiện, node mô phỏng chấp nhận transaction. Nếu thiếu một điều kiện, node từ chối.

---

### Kịch bản 1 — Alice trả Bob thành công

**Mục tiêu:** chứng minh flow đúng.

#### Bước 1: Tạo UTXO cho Alice

1. Vào tab **1️⃣ Ví mô phỏng & tập UTXO**.
2. Ở mục “Tạo UTXO demo”:
   - chọn “Tạo cho”: `Alice`;
   - số tiền demo: `10`;
   - bấm “Tạo UTXO”.
3. Quan sát bảng UTXO xuất hiện một khoản thuộc về Alice.

#### Bước 2: Tạo giao dịch Alice → Bob

1. Vào tab **2️⃣ Tạo giao dịch**.
2. Chọn:
   - Người gửi: `Alice`;
   - UTXO đầu vào: UTXO vừa tạo;
   - Người nhận: `Bob`;
   - Số tiền demo: `10`.
3. Bấm “Tạo giao dịch chưa ký”.
4. App hiển thị JSON transaction mô phỏng.

#### Bước 3: Ký bằng Alice

1. Vào tab **3️⃣ Ký & kiểm tra**.
2. Chọn người ký: `Alice`.
3. Bấm “Ký giao dịch đang chọn”.
4. App thêm chữ ký và public key vào input.

#### Bước 4: Node kiểm tra

1. Bấm “Node kiểm tra giao dịch”.
2. Kết quả đúng là:

```text
Node mô phỏng CHẤP NHẬN giao dịch.
```

3. Xem bảng chi tiết:
   - UTXO tồn tại: True;
   - UTXO chưa bị tiêu: True;
   - pubkey hash khớp: True;
   - chữ ký hợp lệ: True;
   - overall: True.

#### Bước 5: Gửi / áp dụng transaction

1. Bấm “Gửi / áp dụng vào tập UTXO”.
2. App cập nhật UTXO set:
   - UTXO cũ của Alice bị tiêu;
   - UTXO mới thuộc về Bob được thêm vào.

**Ý nghĩa:**

```text
Alice dùng private key để ký transaction
→ node dùng public key để verify
→ nếu UTXO chưa tiêu và signature đúng, transaction được chấp nhận
```

---

### Kịch bản 2 — Sửa số tiền sau khi ký

**Mục tiêu:** chứng minh chữ ký gắn với dữ liệu transaction.

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab **4️⃣ Sửa phá / tấn công / tiêu hai lần**.
5. Bấm “Sửa số tiền sau khi ký”.
6. Bấm “Kiểm tra giao dịch đã bị sửa”.

**Kết quả đúng:** Node mô phỏng phải từ chối transaction.

**Ý nghĩa:** Nếu sửa amount sau khi ký, dữ liệu transaction đã thay đổi. Chữ ký cũ không còn khớp.

---

### Kịch bản 3 — Đổi người nhận sang Mallory sau khi ký

**Mục tiêu:** chứng minh không thể đổi recipient sau khi đã ký.

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab **4️⃣ Sửa phá / tấn công / tiêu hai lần**.
5. Bấm “Đổi người nhận sang Mallory”.
6. Bấm “Kiểm tra giao dịch đã bị sửa”.

**Kết quả đúng:** Node mô phỏng phải từ chối.

**Ý nghĩa:** Chữ ký của Alice là chữ ký trên transaction data ban đầu. Nếu output bị đổi sang Mallory, chữ ký cũ không còn hợp lệ.

---

### Kịch bản 4 — Mallory cố tiêu UTXO của Alice

**Mục tiêu:** chứng minh ký bằng key sai không mở được UTXO.

1. Tạo UTXO cho Alice.
2. Tạo transaction tiêu UTXO của Alice.
3. Vào tab **3️⃣ Ký & kiểm tra**.
4. Chọn người ký: `Mallory`.
5. Bấm “Ký giao dịch đang chọn”.
6. Bấm “Node kiểm tra giao dịch”.

**Kết quả đúng:** Node mô phỏng phải từ chối.

**Vì sao?** UTXO của Alice bị khóa bởi public key hash của Alice. Mallory ký bằng private key khác, nên public key/hash không khớp điều kiện khóa của UTXO.

---

### Kịch bản 5 — Thay public key mở khóa bằng của Mallory

**Mục tiêu:** chứng minh chữ ký và public key phải cùng đúng với locking condition.

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab **4️⃣ Sửa phá / tấn công / tiêu hai lần**.
5. Bấm “Thay khóa công khai mở khóa bằng của Mallory”.
6. Bấm “Kiểm tra giao dịch đã bị sửa”.

**Kết quả đúng:** Node mô phỏng phải từ chối.

**Ý nghĩa:** Dù transaction từng được Alice ký đúng, việc thay public key mở khóa làm pubkey hash không còn khớp locking condition.

---

### Kịch bản 6 — Tiêu cùng một UTXO hai lần

**Mục tiêu:** chứng minh vai trò của UTXO set trong chống double spend.

1. Tạo UTXO cho Alice.
2. Tạo transaction Alice → Bob.
3. Ký bằng Alice.
4. Vào tab **4️⃣ Sửa phá / tấn công / tiêu hai lần**.
5. Bấm “Thử tiêu hai lần giao dịch hiện tại”.

**Kết quả đúng:**

```text
Lần tiêu thứ nhất được chấp nhận, lần tiêu thứ hai bị từ chối.
```

**Nếu lần đầu đã bị từ chối:** Có thể transaction đã bị sửa, UTXO đã bị tiêu từ trước, người ký sai, public key bị thay hoặc lab state đang bẩn. Hãy bấm “Reset phòng lab giao dịch” rồi làm lại.

---

## 7. Trang 6 — Reused Nonce Attack

**Câu hỏi chính:** ECDSA có chắc chắn an toàn không?

**Ý tưởng:** ECDSA cần nonce `k` bí mật và dùng một lần. Nếu dùng lại cùng `k` cho hai message khác nhau, attacker có thể khôi phục `k` và private key `d`.

**Công thức trong app:**

```text
k' = (h1 - h2)(s1 - s2)^(-1) mod n
d' = (s1*k' - h1)r^(-1) mod n
```

**Cách dùng:**

1. Chọn khóa bí mật `d`.
2. Chọn reused nonce `k`.
3. Nhập hai thông điệp khác nhau.
4. Bấm “Chạy tấn công dùng lại nonce”.
5. App hiển thị `k ban đầu`, `k khôi phục`, `d ban đầu`, `d khôi phục`.

**Kết quả đúng:** Nếu không gặp edge case, app báo tấn công thành công.

**Câu nên nói khi thuyết trình:**

> ECDLP khó không cứu được mình nếu implementation sai. Không cần phá curve; reuse nonce là đủ lộ private key.

**Nếu attack không chạy được:** thử đổi message, `d` hoặc `k`.

---

## 8. Trang 7 — Phòng thủ nonce

Trang này trả lời câu hỏi: nếu nonce nguy hiểm như vậy, triển khai thật phải làm gì?

Nội dung chính:

1. không bao giờ dùng lại nonce `k`;
2. dùng nguồn ngẫu nhiên đáng tin cậy;
3. dùng nonce xác định kiểu RFC6979;
4. triển khai constant-time;
5. dùng thư viện mật mã đã được kiểm chứng.

**Câu nên nói khi thuyết trình:**

> Correct ECDSA không bị phá chỉ vì demo reused nonce. Bài học là: mật mã đúng công thức vẫn có thể chết vì implementation sai.

---

## 9. Trang 8 — Thủ thuật Shamir

**Câu hỏi chính:** Có thể tối ưu ECDSA verification không?

**Ý tưởng:** ECDSA verification cần tính:

```text
u1G + u2Q
```

Cách trực tiếp:

```text
u1G riêng
u2Q riêng
rồi cộng lại
```

Shamir’s trick tính đồng thời để giảm số phép toán.

**Cách dùng:**

1. Chọn `u1`.
2. Chọn `u2`.
3. Bấm “Chạy so sánh”.
4. Xem biểu đồ số phép cộng điểm và số phép nhân đôi điểm.
5. Kiểm tra hai kết quả có giống nhau không.

**Câu nên nói khi thuyết trình:**

> Đây là phần tối ưu thuật toán, không phải phần chứng minh quyền sở hữu. Nó cho thấy mật mã thực tế không chỉ có công thức, mà còn có engineering/performance.

---

## 10. Trang 9 — OpenSSL secp256k1

**Câu hỏi chính:** Toy demo có liên hệ gì với công cụ thật không?

**Ý tưởng:** Toy curve giúp hiểu toán. OpenSSL secp256k1 cho thấy ký và kiểm tra chữ ký bằng công cụ thật.

**Cảnh báo quan trọng:** Trang này **không ký transaction Bitcoin thật**. Nó chỉ ký một message/file bằng OpenSSL.

---

### Kịch bản 1 — Sinh khóa secp256k1

1. Vào tab **1️⃣ Sinh khóa**.
2. Bấm “Sinh cặp khóa secp256k1”.
3. App tạo private key tạm và public key tạm.
4. Các file nằm trong thư mục tạm của app.

Không commit các file `.pem`, `.key`, `.bin` lên GitHub.

---

### Kịch bản 2 — Ký nội dung gốc

1. Vào tab **2️⃣ Ký nội dung gốc**.
2. Nhập nội dung, ví dụ:

```text
Alice trả Bob 1 BTC mô phỏng
```

3. Bấm “Ký nội dung gốc bằng OpenSSL”.
4. App hiển thị một phần chữ ký dạng hex.

---

### Kịch bản 3 — Sửa nội dung và verify fail

1. Vào tab **3️⃣ Tự sửa và kiểm tra**.
2. Để nguyên nội dung và bấm kiểm tra: kết quả phải hợp lệ.
3. Bấm “Tạo bản bị sửa mẫu” hoặc tự sửa nội dung.
4. Bấm kiểm tra lại: kết quả phải bị từ chối.

**Ý nghĩa:** Chữ ký chỉ hợp lệ với đúng dữ liệu đã ký. Nếu sửa dữ liệu, chữ ký cũ không còn khớp.

---

### Kịch bản 4 — Đo thời gian

1. Vào tab **4️⃣ Đo thời gian**.
2. Chọn số lần chạy thử.
3. Bấm “Đo thời gian”.
4. App hiển thị thời gian ký trung bình, thời gian verify trung bình, số lần ký/verify mỗi giây.

**Cảnh báo benchmark:** Kết quả benchmark chỉ mang tính tham khảo. Nó phụ thuộc vào máy tính, hệ điều hành, phiên bản OpenSSL, số lần chạy và môi trường chạy.

Không kết luận kiểu “ECDSA luôn nhanh hơn RSA” chỉ từ demo này.

---

## 11. Kịch bản demo khuyến nghị khi thuyết trình

### Kịch bản ngắn 10–15 phút

1. **Trang 0:** nói thesis.
2. **Trang 1:** giải thích UTXO/ownership.
3. **Trang 2:** chọn `d`, tạo `Q = dG`.
4. **Trang 4:** ký message, sửa message, verify fail.
5. **Trang 5:** tạo UTXO Alice, Alice trả Bob, node accept.
6. **Trang 5:** sửa amount hoặc Mallory ký sai, node reject.
7. **Trang 6:** reused nonce attack recover private key.
8. **Trang 9:** OpenSSL secp256k1 ký/sửa/verify fail.

### Kịch bản đầy đủ

1. Trang 0 → 1: đặt bài toán Bitcoin ownership.
2. Trang 2: ECC sinh public key.
3. Trang 3: ECDLP và độ phức tạp thuật toán.
4. Trang 4: ECDSA sign/verify.
5. Trang 5: transaction lab.
6. Trang 6: nonce attack.
7. Trang 7: defense.
8. Trang 8: Shamir’s trick.
9. Trang 9: OpenSSL.

### Nếu chỉ được demo một trang

Chọn **Trang 5 — Phòng lab giao dịch Bitcoin mô phỏng**.

Vì đây là trang nối trực tiếp đề tài:

```text
ECC/ECDSA → Bitcoin transaction authentication
```

---

## 12. Troubleshooting

### 12.1. Không thấy OpenSSL

**Dấu hiệu:** Trang 9 báo `Không tìm thấy OpenSSL trong PATH`.

**Cách xử lý:**

1. Cài OpenSSL.
2. Thêm thư mục chứa `openssl.exe` vào PATH.
3. Mở terminal mới.
4. Chạy:

```powershell
openssl version
```

Nếu lệnh này chạy được, mở lại app.

---

### 12.2. Chưa tạo được transaction vì không có UTXO

**Dấu hiệu:** Trang 5 báo `Alice chưa có UTXO chưa bị tiêu`.

**Cách xử lý:**

1. Vào tab **Ví mô phỏng & tập UTXO**.
2. Tạo UTXO cho Alice.
3. Quay lại tab **Tạo giao dịch**.

---

### 12.3. Double spend lần đầu đã bị từ chối

**Nguyên nhân có thể:** transaction đã bị sửa, UTXO đã bị tiêu ở lần chạy trước, ký bằng người sai, public key bị thay hoặc state phòng lab đang lẫn nhiều thao tác.

**Cách xử lý:** Bấm “Reset phòng lab giao dịch” rồi làm lại từ đầu.

---

### 12.4. Sửa message nhưng verify vẫn True ở trang 4

**Nguyên nhân:** Toy curve quá nhỏ, giá trị hash bị rút gọn modulo `n` nhỏ, nên có thể gặp edge case.

**Cách xử lý:** Bấm “Tạo dữ liệu sửa chắc chắn bị từ chối” hoặc thử message khác.

---

### 12.5. Reused nonce attack không khôi phục đúng key

**Nguyên nhân có thể:** hai message giống nhau, hash modulo `n` trùng, `s1 - s2` không khả nghịch, `r` không khả nghịch hoặc toy curve gặp edge case.

**Cách xử lý:** Thử đổi message 1, message 2, `d` hoặc `k`.

---

### 12.6. Pollard rho không thành công

Pollard rho là thuật toán xác suất/random-walk. Với toy curve nhỏ, có thể gặp collision suy biến hoặc không tìm được collision hữu ích trong giới hạn bước.

**Cách xử lý:** tăng giới hạn số bước, đổi private key `d`, hoặc dùng Brute force/Baby-step Giant-step cho phần demo chính.

Khi thuyết trình, không nên phụ thuộc vào Pollard rho.

---

## 13. Những câu nên nói khi thuyết trình

### Câu mở đầu

> Bitcoin không cần biết danh tính ngoài đời của người gửi. Nó chỉ cần kiểm tra người đó có tạo được chữ ký hợp lệ để tiêu UTXO hay không.

### Khi nói về ECC

> ECC cung cấp cách tạo public key từ private key: `Q = dG`. Dễ tính xuôi, khó tính ngược.

### Khi nói về ECDLP

> Biết `Q` không đồng nghĩa biết `d`. Trên toy curve thì thử được, nhưng trên secp256k1 thì không khả thi bằng máy tính cổ điển hiện nay.

### Khi nói về ECDSA

> Private key ký. Public key verify. Người verify không cần biết private key.

### Khi nói về transaction lab

> Signature không bay lơ lửng. Nó mở khóa một UTXO cụ thể.

### Khi nói về nonce attack

> ECDSA không chết vì công thức sai. Nó chết khi implementation phá kỷ luật nonce.

### Khi nói về OpenSSL

> OpenSSL cho thấy đây không chỉ là toy code, nhưng ký file bằng OpenSSL vẫn không phải ký giao dịch Bitcoin đầy đủ.

---

## 14. Những câu không nên nói

Không nên nói:

```text
Bitcoin mã hóa giao dịch bằng ECC.
Private key chứa Bitcoin.
App này ký được giao dịch Bitcoin thật.
OpenSSL demo giống hệt Bitcoin signing.
Toy curve đại diện cho độ an toàn của secp256k1.
ECDSA đã bị phá vì reused nonce attack.
Pollard rho trong app có thể phá khóa Bitcoin thật.
ECDSA luôn nhanh hơn RSA.
```

Nên nói:

```text
Bitcoin dùng chữ ký số để xác thực quyền chi tiêu.
Private key cho khả năng ký.
Public key dùng để verify.
Toy curve dùng để học, không dùng cho bảo mật thật.
Mini transaction lab chỉ là P2PKH-like educational model.
Reused nonce là lỗi triển khai, không phải phá ECDSA đúng chuẩn.
OpenSSL secp256k1 demo là công cụ thật, nhưng không phải full Bitcoin transaction signing.
Benchmark phụ thuộc môi trường và chỉ mang tính tham khảo.
```

---

## 15. Checklist trước buổi demo

Trước khi thuyết trình, chạy:

```powershell
pytest -q
streamlit run app.py
```

Kiểm tra nhanh:

- [ ] Trang 2 chọn `d`, tạo được `Q`.
- [ ] Trang 3 brute force tìm được `d`.
- [ ] Trang 3 BSGS tìm được `d`.
- [ ] Trang 4 ký message gốc thành công.
- [ ] Trang 4 sửa message bị từ chối.
- [ ] Trang 5 tạo UTXO cho Alice.
- [ ] Trang 5 Alice trả Bob được chấp nhận.
- [ ] Trang 5 sửa amount bị từ chối.
- [ ] Trang 5 Mallory ký sai bị từ chối.
- [ ] Trang 5 double-spend bị từ chối ở lần thứ hai.
- [ ] Trang 6 reused nonce attack khôi phục được `k` và `d`.
- [ ] Trang 9 OpenSSL hoạt động hoặc đã chuẩn bị sẵn lời giải thích nếu máy không có OpenSSL.

---

## 16. Tài liệu tham khảo chính

- Streamlit Docs — Running your app: https://docs.streamlit.io/develop/concepts/architecture/run-your-app
- Bitcoin Developer Guide — Transactions: https://developer.bitcoin.org/devguide/transactions.html
- OpenSSL Docs — `openssl dgst`: https://docs.openssl.org/3.5/man1/openssl-dgst/
- RFC 6979 — Deterministic Usage of DSA and ECDSA: https://datatracker.ietf.org/doc/html/rfc6979

---

## 17. Kết luận

App nên được dùng như một bài lab theo đúng thứ tự:

```text
Bài toán Bitcoin ownership
→ UTXO
→ ECC Q = dG
→ ECDLP
→ ECDSA
→ Mini Bitcoin transaction signing
→ Nonce attack
→ Nonce defense
→ Shamir optimization
→ OpenSSL secp256k1
```

> **Bitcoin không dùng ECC/ECDSA để giấu giao dịch. Bitcoin dùng ECDSA để chứng minh quyền tiêu UTXO.**
