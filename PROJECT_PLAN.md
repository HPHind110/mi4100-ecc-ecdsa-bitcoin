# Kế hoạch và Kiến trúc Dự án (Retrospective Project Plan)

Dự án này tập trung vào việc nghiên cứu, mô phỏng và phân tích Hệ mật mã đường cong Elliptic (ECC) và ứng dụng chữ ký số ECDSA trong mạng lưới Bitcoin. Đây là bản tổng kết kiến trúc và logic triển khai sau khi dự án đã hoàn thiện.

## 1. Tóm tắt mục tiêu dự án
Dự án được xây dựng nhằm mục đích giáo dục cho môn học "Mật mã và độ phức tạp thuật toán". Mục tiêu chính là làm sáng tỏ cơ chế toán học của ECC và quy trình ký/xác minh của ECDSA. Thông qua việc lập trình mô phỏng trên Python, dự án giải thích cách thức Bitcoin bảo vệ quyền sở hữu tài sản. Đồng thời, dự án đi sâu vào phân tích hiệu năng so với RSA và cảnh báo về các rủi ro bảo mật thực tế như lỗi tái sử dụng nonce. Kết quả cuối cùng bao gồm cả mã nguồn mô phỏng, kịch bản sử dụng công cụ chuẩn OpenSSL và các số liệu benchmark thực tế.

## 2. Luận điểm chính
Mật mã đường cong Elliptic (ECC) và thuật toán ECDSA đại diện cho một bước tiến quan trọng trong mật mã học khóa công khai. So với các hệ mật truyền thống như RSA hay ElGamal, ECC đạt được mức độ bảo mật tương đương với kích thước khóa nhỏ hơn đáng kể (ví dụ: ECC 256-bit tương đương RSA 3072-bit). Điều này đặc biệt phù hợp với Bitcoin, nơi băng thông mạng và không gian lưu trữ blockchain là tài nguyên quý giá. Tuy nhiên, an toàn thực tế của ECDSA không chỉ nằm ở toán học mà còn phụ thuộc cực kỳ chặt chẽ vào việc triển khai, đặc biệt là tính ngẫu nhiên của số nonce $k$; chỉ một sai sót nhỏ trong việc quản lý nonce cũng có thể dẫn đến việc lộ hoàn toàn khóa bí mật.

## 3. Mô tả kiến trúc module

### A. Toán học trường hữu hạn (Finite Field)
*   **Mục tiêu:** Cung cấp các phép toán số học cơ bản cần thiết cho ECC.
*   **Input/Output:** Số nguyên $a, b, p$; Output là kết quả phép cộng, nhân, nghịch đảo modulo.
*   **File liên quan:** `src/field.py`, `tests/test_field.py`.
*   **Ý nghĩa:** Là nền tảng thấp nhất của toàn bộ hệ thống; không có nghịch đảo modulo thì không thể thực hiện phép chia trên đường cong.

### B. Cốt lõi ECC (Toy ECC)
*   **Mục tiêu:** Định nghĩa cấu trúc điểm và các phép toán hình học trên đường cong Elliptic.
*   **Input/Output:** Các đối tượng `Point` và `Curve`; Output là điểm mới sau khi cộng hoặc nhân vô hướng.
*   **File liên quan:** `src/ecc.py`, `tests/test_ecc.py`.
*   **Ý nghĩa:** Mô phỏng bài toán Logarit rời rạc trên đường cong Elliptic (ECDLP) - trái tim của bảo mật ECC.

### C. Chữ ký số ECDSA (Toy ECDSA)
*   **Mục tiêu:** Triển khai quy trình ký và xác minh tin nhắn.
*   **Input/Output:** Khóa bí mật, tin nhắn, tham số đường cong; Output là cặp chữ ký $(r, s)$ hoặc kết quả Boolean (True/False).
*   **File liên quan:** `src/ecdsa_toy.py`, `tests/test_ecdsa.py`.
*   **Ý nghĩa:** Giải thích cách thức một giao dịch Bitcoin được xác thực quyền sở hữu từ phía người dùng.

### D. Tấn công tái sử dụng Nonce (Reused Nonce Attack)
*   **Mục tiêu:** Chứng minh lỗ hổng chí mạng khi dùng chung nonce $k$ cho hai chữ ký khác nhau.
*   **Input/Output:** Hai cặp chữ ký $(r, s_1), (r, s_2)$ và hai bản băm tin nhắn $h_1, h_2$; Output là khóa bí mật $d$ bị khôi phục.
*   **File liên quan:** `src/nonce_attack.py`, `tests/test_nonce_attack.py`.
*   **Ý nghĩa:** Cảnh báo về an toàn triển khai; là nội dung quan trọng trong phần thảo luận về bảo mật của báo cáo.

### E. Tối ưu hóa Shamir's Trick
*   **Mục tiêu:** Tăng tốc độ xác minh chữ ký bằng cách tính đồng thời $u_1G + u_2Q$.
*   **Input/Output:** Các hệ số $u_1, u_2$ và các điểm $G, Q$; Output là điểm kết quả với số phép toán ít hơn.
*   **File liên quan:** `src/shamir.py`, `tests/test_shamir.py`.
*   **Ý nghĩa:** Minh họa khía cạnh "độ phức tạp thuật toán" và cách tối ưu hóa hiệu năng trong thực tế.

### F. Demo thực tế & Benchmark (OpenSSL)
*   **Mục tiêu:** Kết nối lý thuyết với thực tế bằng công cụ công nghiệp.
*   **Input/Output:** Các lệnh OpenSSL trên đường cong `secp256k1`.
*   **File liên quan:** `openssl_demo/*.ps1`, `results/openssl_benchmark.txt`.
*   **Ý nghĩa:** Cung cấp số liệu thực nghiệm so sánh RSA vs ECDSA để củng cố luận điểm về hiệu suất.

## 4. Thứ tự triển khai thực tế
1.  **Nền tảng toán học:** Xây dựng `field.py` để đảm bảo các phép toán modulo ổn định.
2.  **Hình học đường cong:** Triển khai `ecc.py` (cộng điểm, nhân vô hướng double-and-add).
3.  **Giao thức chữ ký:** Triển khai `ecdsa_toy.py` dựa trên các phép toán ECC đã có.
4.  **Kiểm chứng an toàn:** Xây dựng `nonce_attack.py` để demo lỗ hổng bảo mật.
5.  **Cải tiến hiệu năng:** Triển khai `shamir.py` để tối ưu hóa quá trình xác minh.
6.  **Thực nghiệm công nghiệp:** Chạy OpenSSL benchmark để lấy số liệu thực tế so sánh với RSA.

## 5. Phạm vi an toàn (Safety Scope)
*   **Mục đích duy nhất:** Giáo dục và nghiên cứu học thuật.
*   **Không phải Production Crypto:** Các module Python (`toy ecc`) không được thiết kế để chống lại tấn công kênh kề (side-channel attacks) hay sử dụng cho ví tiền mã hóa thực tế.
*   **Không tương tác Blockchain:** Dự án không quét dữ liệu trên mạng lưới Bitcoin thực, không tạo địa chỉ ví thật hay khôi phục khóa thật từ mạng lưới.
*   **Dữ liệu thử nghiệm:** Mọi bản demo tấn công chỉ thực hiện trên các khóa nhỏ (toy keys) hoặc khóa thử nghiệm được tạo cục bộ trong môi trường test.
