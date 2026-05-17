# MI4100: Dự án ECC/ECDSA & Ứng dụng trong Bitcoin

Dự án này là một phần của môn học **"Mật mã và độ phức tạp thuật toán" (MI4100)**. Mục tiêu của dự án là mô phỏng và giải thích cơ chế hoạt động của Mật mã đường cong Elliptic (ECC), thuật toán chữ ký số ECDSA, và tại sao nó được lựa chọn làm nền tảng xác thực cho Bitcoin.

## 📌 Luận điểm chính
1. **Hiệu quả:** ECC cung cấp mức độ bảo mật tương đương RSA nhưng với kích thước khóa nhỏ hơn nhiều, giúp tối ưu băng thông và bộ nhớ cho blockchain.
2. **An toàn:** Chữ ký ECDSA đảm bảo tính toàn vẹn và không thể phủ nhận cho các giao dịch Bitcoin.
3. **Lỗ hổng Nonce:** Minh họa rủi ro bảo mật nghiêm trọng khi triển khai sai cách (tái sử dụng nonce $k$), dẫn đến lộ khóa bí mật.
4. **Tối ưu hóa:** So sánh phương pháp xác minh truyền thống với thủ thuật Shamir (Shamir's trick).

## 📂 Cấu trúc thư mục
- `src/`: Mã nguồn Python triển khai toán học và ECC/ECDSA.
  - `field.py`: Toán học trên trường hữu hạn $F_p$.
  - `ecc.py`: Cốt lõi đường cong Elliptic (Cộng điểm, nhân vô hướng).
  - `ecdsa_toy.py`: Chữ ký ECDSA trên đường cong mô phỏng (Toy Curve).
  - `nonce_attack.py`: Demo tấn công khôi phục khóa bí mật khi lộ nonce.
  - `shamir.py`: Tối ưu hóa xác minh bằng Shamir's trick.
- `openssl_demo/`: Script PowerShell minh họa sử dụng OpenSSL với đường cong `secp256k1`.
- `tests/`: Các bộ kiểm thử unit test sử dụng `pytest`.
- `results/`: Kết quả benchmark hiệu năng.

## 🛠 Cài đặt môi trường
Yêu cầu: **Python 3.10+** và **OpenSSL**.

1. Cài đặt các thư viện phụ thuộc:
   ```powershell
   pip install -r requirements.txt
   ```
2. Cấu hình đường dẫn (để Python tìm thấy module `src`):
   ```powershell
   $env:PYTHONPATH = "."
   ```

## 🧪 Chạy Kiểm thử (Unit Tests)
Dự án sử dụng `pytest` để đảm bảo tính chính xác của các thuật toán:
```powershell
pytest tests/
```

## 🚀 Hướng dẫn chạy Demo

### 1. Python Toy ECC/ECDSA
Kiểm tra luồng tạo khóa, ký và xác minh trên đường cong nhỏ:
```powershell
python -c "from src.ecdsa_toy import *; from src.ecc import *; toy_curve = Curve(p=223, a=0, b=7); G = Point(47, 71); params = ECDSAParams(toy_curve, G, 21); d, Q = keygen(params); msg = b'hello'; r, s = sign(params, d, msg); print(f'Verified: {verify(params, Q, msg, (r, s))}')"
```

### 2. Tấn công tái sử dụng Nonce (Nonce Reuse Attack)
Demo khôi phục khóa bí mật Bitcoin giả định:
```powershell
python src/nonce_attack.py
```

### 3. Benchmark Shamir's Trick
So sánh tốc độ xác minh naive vs tối ưu hóa:
```powershell
python src/shamir.py
```

### 4. OpenSSL secp256k1 Sign/Verify
Sử dụng công cụ thực tế để ký/xác minh trên đường cong của Bitcoin:
```powershell
cd openssl_demo
.\gen_keys.ps1
.\sign_verify.ps1
```

### 5. OpenSSL Benchmark (RSA vs ECDSA)
So sánh hiệu năng thực tế giữa các hệ mật:
```powershell
cd openssl_demo
.\benchmark.ps1
```
Kết quả sẽ được lưu tại `results/openssl_benchmark.txt`.

## ⚠️ Cảnh báo quan trọng (Disclaimer)
- **Mục đích giáo dục:** Dự án này chỉ nhằm mục đích học thuật và mô phỏng. Không sử dụng mã nguồn này trong các hệ thống thực tế (Production).
- **An toàn tài sản:** Dự án **không** thực hiện quét blockchain, **không** tạo hoặc khôi phục các khóa bí mật Bitcoin thật. 
- **Bảo mật:** Các cuộc tấn công chỉ được thực hiện trên các khóa giả lập hoặc khóa tự tạo cục bộ để minh họa nguyên lý. Tuyệt đối không thử nghiệm trên tài sản thật.
