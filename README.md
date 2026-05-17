# MI4100: ECC/ECDSA và ứng dụng chữ ký số trong Bitcoin

Dự án này được thực hiện trong khuôn khổ môn học **Mật mã và độ phức tạp thuật toán (MI4100)**.

Mục tiêu của dự án là mô phỏng và giải thích cơ chế hoạt động của **mật mã đường cong Elliptic** (*Elliptic Curve Cryptography* — ECC), thuật toán chữ ký số **ECDSA** (*Elliptic Curve Digital Signature Algorithm*), và lý do ECDSA được sử dụng trong Bitcoin để xác thực giao dịch.

Dự án bao gồm hai phần chính:

- Mô phỏng ECC/ECDSA bằng Python trên một đường cong nhỏ phục vụ mục đích học tập.
- Thực nghiệm với OpenSSL để ký, xác minh và benchmark hiệu năng giữa RSA và ECDSA.

---

## 1. Ý tưởng chính

Bitcoin không cần mã hóa nội dung giao dịch, vì giao dịch trên blockchain là công khai. Điều Bitcoin cần là một cơ chế để chứng minh rằng người gửi thực sự sở hữu khóa bí mật tương ứng với khóa công khai.

ECDSA giải quyết bài toán này bằng chữ ký số.

Người dùng ký giao dịch bằng khóa bí mật. Các node trong mạng lưới xác minh chữ ký bằng khóa công khai. Nếu chữ ký hợp lệ, giao dịch được xem là do đúng chủ sở hữu tạo ra.

Về mặt toán học, ECC dựa trên phép nhân vô hướng trên đường cong Elliptic:

$$
Q = dG
$$

Trong đó:

- $d$ là khóa bí mật.
- $G$ là điểm sinh trên đường cong.
- $Q$ là khóa công khai.

Việc tính $Q$ từ $d$ và $G$ là dễ. Nhưng việc tìm lại $d$ khi chỉ biết $Q$ và $G$ là rất khó nếu tham số đủ lớn. Đây là nền tảng bảo mật của ECC.

---

## 2. Luận điểm chính của dự án

Dự án tập trung vào bốn luận điểm chính:

### 2.1. ECC hiệu quả hơn RSA về kích thước khóa

ECC có thể đạt mức bảo mật cao với kích thước khóa nhỏ hơn nhiều so với RSA. Điều này giúp giảm chi phí lưu trữ, truyền tải và xử lý dữ liệu.

Trong các hệ thống như blockchain, nơi chữ ký được lưu trữ lâu dài và được xác minh bởi nhiều node, kích thước khóa và chữ ký nhỏ là một lợi thế lớn.

### 2.2. ECDSA phù hợp với bài toán xác thực giao dịch Bitcoin

Bitcoin sử dụng chữ ký số để xác minh quyền chi tiêu. Người dùng không cần tiết lộ khóa bí mật, nhưng vẫn có thể chứng minh rằng họ là chủ sở hữu hợp lệ của khóa công khai.

### 2.3. Nonce là điểm cực kỳ nhạy cảm trong ECDSA

Khi ký ECDSA, mỗi chữ ký cần một nonce $k$.

Nếu cùng một nonce $k$ bị tái sử dụng cho hai thông điệp khác nhau, khóa bí mật có thể bị khôi phục.

Từ công thức ký:

$$
s = k^{-1}(h + dr) \pmod n
$$

nếu hai chữ ký dùng cùng nonce, ta có thể suy ra:

$$
k = (h_1 - h_2)(s_1 - s_2)^{-1} \pmod n
$$

Sau đó khóa bí mật được tính bằng:

$$
d = (s_1k - h_1)r^{-1} \pmod n
$$

Đây là minh chứng cho việc: thuật toán mạnh chưa đủ, triển khai sai vẫn có thể làm toàn bộ hệ thống mất an toàn.

### 2.4. Shamir's trick giúp tối ưu xác minh chữ ký

Trong bước xác minh ECDSA, ta cần tính:

$$
X = u_1G + u_2Q
$$

Cách thông thường là tính riêng $u_1G$ và $u_2Q$, sau đó cộng hai kết quả.

Shamir's trick tối ưu bước này bằng cách xử lý hai phép nhân vô hướng đồng thời, từ đó giảm số phép toán trên đường cong Elliptic.

---

## 3. Cấu trúc thư mục

```text
CAC_Project/
├── src/
│   ├── field.py
│   ├── ecc.py
│   ├── ecdsa_toy.py
│   ├── nonce_attack.py
│   └── shamir.py
│
├── openssl_demo/
│   ├── gen_keys.ps1
│   ├── sign_verify.ps1
│   └── benchmark.ps1
│
├── results/
│
├── tests/
│
├── requirements.txt
└── README.md
```

Ý nghĩa các thư mục và file chính:

| Thành phần | Vai trò |
|---|---|
| `src/field.py` | Cài đặt số học trên trường hữu hạn $\mathbb{F}_p$ |
| `src/ecc.py` | Cài đặt điểm, đường cong Elliptic, cộng điểm và nhân vô hướng |
| `src/ecdsa_toy.py` | Mô phỏng sinh khóa, ký và xác minh ECDSA |
| `src/nonce_attack.py` | Demo tấn công khi tái sử dụng nonce |
| `src/shamir.py` | So sánh xác minh naive với Shamir's trick |
| `openssl_demo/` | Script PowerShell để chạy OpenSSL |
| `tests/` | Unit test bằng `pytest` |
| `results/` | Lưu kết quả benchmark |

---

## 4. Yêu cầu môi trường

Dự án cần các công cụ sau:

- Python 3.10+
- `pip`
- `pytest`
- OpenSSL
- PowerShell trên Windows

Kiểm tra Python:

```powershell
python --version
```

Kiểm tra OpenSSL:

```powershell
openssl version
```

---

## 5. Cài đặt

### 5.1. Tạo môi trường ảo

```powershell
python -m venv .venv
```

Kích hoạt môi trường ảo:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5.2. Cài thư viện phụ thuộc

```powershell
pip install -r requirements.txt
```

### 5.3. Cấu hình `PYTHONPATH`

Để Python tìm thấy module trong thư mục `src/`, chạy:

```powershell
$env:PYTHONPATH = "."
```

---

## 6. Chạy kiểm thử

Dự án sử dụng `pytest` để kiểm tra tính đúng đắn của các module.

Chạy toàn bộ test:

```powershell
pytest tests/
```

Nếu muốn chạy ngắn gọn hơn:

```powershell
pytest -q
```

Các test kiểm tra:

- Số học modulo.
- Phép cộng điểm trên đường cong Elliptic.
- Phép nhân vô hướng.
- Ký và xác minh ECDSA.
- Tấn công reused nonce.
- Shamir's trick.

---

## 7. Hướng dẫn chạy demo

### 7.1. Demo ECDSA trên toy curve

Chạy lệnh sau để kiểm tra luồng sinh khóa, ký và xác minh:

```powershell
python -c "from src.ecdsa_toy import *; from src.ecc import *; toy_curve = Curve(p=223, a=0, b=7); G = Point(47, 71); params = ECDSAParams(toy_curve, G, 21); d, Q = keygen(params); msg = b'hello'; r, s = sign(params, d, msg); print(f'Private key: {d}'); print(f'Public key: {Q}'); print(f'Signature: {(r, s)}'); print(f'Verified: {verify(params, Q, msg, (r, s))}')"
```

Kết quả mong đợi:

```text
Verified: True
```

Điều này cho thấy chữ ký được tạo ra hợp lệ và có thể được xác minh bằng khóa công khai.

---

### 7.2. Demo tấn công tái sử dụng nonce

Chạy:

```powershell
python src/nonce_attack.py
```

---

### 7.3. Demo Shamir's trick

Chạy:

```powershell
python src/shamir.py
```

---

### 7.4. Demo OpenSSL với secp256k1

Chuyển vào thư mục `openssl_demo`:

```powershell
cd openssl_demo
```

Sinh khóa:

```powershell
.\gen_keys.ps1
```

Ký và xác minh chữ ký:

```powershell
.\sign_verify.ps1
```

Script này minh họa quy trình:

1. Sinh khóa ECC.
2. Ký một file văn bản.
3. Xác minh chữ ký.
4. Sửa nội dung file.
5. Kiểm tra xác minh thất bại sau khi nội dung bị thay đổi.

---

### 7.5. Benchmark RSA và ECDSA bằng OpenSSL

Từ thư mục `openssl_demo`, chạy:

```powershell
.\benchmark.ps1
```

Kết quả benchmark sẽ được lưu tại:

```text
results/openssl_benchmark.txt
```

---

### 7.6. Chạy Web Visualization (Streamlit)

Dự án cung cấp một giao diện web trực quan (Streamlit) để minh họa các kết quả toán học và mô phỏng tấn công. Để khởi chạy:

```powershell
streamlit run app.py
```

Ứng dụng sẽ tự động mở trên trình duyệt (thường ở địa chỉ `http://localhost:8501`), bao gồm các phần:
- ECC Toy Curve
- ECDSA Sign/Verify
- Tấn công Reused Nonce
- Tối ưu hóa Shamir's Trick
- Tóm tắt kết quả OpenSSL Benchmark

---

## 8. Kết quả chính

Dự án đạt được các kết quả sau:

- Cài đặt được số học trường hữu hạn $\mathbb{F}_p$.
- Cài đặt được phép cộng điểm và nhân vô hướng trên đường cong Elliptic.
- Mô phỏng được quá trình sinh khóa, ký và xác minh ECDSA.
- Demo được lỗi reused nonce làm lộ khóa bí mật.
- Cài đặt được Shamir's trick để tối ưu xác minh.
- Thực nghiệm được ký và xác minh bằng OpenSSL.
- Benchmark được hiệu năng giữa RSA và ECDSA.

---

## 9. Giới hạn của dự án

Dự án có một số giới hạn quan trọng:

- Toy curve chỉ dùng để học tập, không có giá trị bảo mật thực tế.
- Mã Python trong dự án ưu tiên tính dễ hiểu, không tối ưu hiệu năng.
- Không dùng mã nguồn này trong hệ thống production.
- Chưa xử lý side-channel attack, timing attack hoặc fault attack.
- Chưa triển khai đầy đủ quy trình tạo giao dịch Bitcoin thật.
- Không tương tác với blockchain thật.
- Không tạo, quét hoặc khôi phục khóa Bitcoin thật.

---

## 10. Cảnh báo bảo mật

Dự án này chỉ phục vụ mục đích học tập.

Không sử dụng mã nguồn trong dự án để:

- Quản lý tài sản thật.
- Tạo ví Bitcoin thật.
- Ký giao dịch thật.
- Quét khóa riêng tư.
- Thử tấn công hệ thống hoặc tài sản của người khác.

Các cuộc tấn công trong dự án chỉ được thực hiện trên dữ liệu giả lập hoặc khóa tự tạo cục bộ.

---

## 11. Tài liệu tham khảo

[1] Neal Koblitz, “Elliptic Curve Cryptosystems”, *Mathematics of Computation*, 1987.

[2] Victor S. Miller, “Use of Elliptic Curves in Cryptography”, *CRYPTO*, 1985.

[3] Standards for Efficient Cryptography Group, “SEC 2: Recommended Elliptic Curve Domain Parameters”, Version 2.0, 2010.  
https://www.secg.org/sec2-v2.pdf

[4] Thomas Pornin, “RFC 6979: Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature Algorithm (ECDSA)”, IETF, 2013.  
https://datatracker.ietf.org/doc/html/rfc6979

[5] Bitcoin Developer Documentation, “Transactions”.  
https://developer.bitcoin.org/devguide/transactions.html

[6] OpenSSL Documentation, “ECDSA_sign and ECDSA_verify”.  
https://docs.openssl.org/3.4/man3/ECDSA_sign/

[7] GitHub Docs, “Writing mathematical expressions”.  
https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions

---

## 12. Ghi chú

Dự án được xây dựng với mục tiêu chính là giúp người học hiểu được:

- Vì sao ECC quan trọng.
- ECDSA hoạt động như thế nào.
- Bitcoin dùng chữ ký số để xác thực giao dịch ra sao.
- Vì sao triển khai mật mã cần cực kỳ cẩn thận.

Thông điệp quan trọng nhất của dự án:

> Thuật toán mật mã mạnh không đảm bảo hệ thống an toàn nếu quá trình triển khai sai.
