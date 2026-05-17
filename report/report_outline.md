# Đề cương Báo cáo: Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin

## 1. Tóm tắt đóng góp thành viên (1-2 trang)
*   **Thành viên 1 (Họ và tên - MSSV):**
    *   Tìm hiểu lý thuyết nền tảng về hệ mật mã khóa công khai, RSA, ElGamal [1].
    *   Triển khai mã nguồn lõi: thuật toán toán học trên trường hữu hạn (`src/field.py`) và thuật toán cơ bản của đường cong Elliptic (`src/ecc.py`).
    *   Soạn thảo phần Giới thiệu và Phương pháp luận (phần cơ sở toán học) trong báo cáo.
*   **Thành viên 2 (Họ và tên - MSSV):**
    *   Nghiên cứu về cơ chế chữ ký số ECDSA trong Bitcoin và tham số `secp256k1` [3].
    *   Triển khai mã nguồn mô phỏng thuật toán ECDSA trên đường cong nhỏ (toy curve) và thuật toán tối ưu hóa xác minh Shamir's Trick (`src/ecdsa_toy.py`, `src/shamir.py`).
    *   Xây dựng kịch bản benchmark so sánh hiệu năng RSA vs ECDSA bằng OpenSSL (`openssl_demo/`).
    *   Soạn thảo phần Kết quả và Bàn luận.
*   **Thành viên 3 (Họ và tên - MSSV):**
    *   Nghiên cứu các rủi ro bảo mật trong triển khai thực tế, đặc biệt là lỗi tái sử dụng nonce (Nonce Reuse) [4].
    *   Lập trình mã kịch bản tấn công khôi phục khóa bí mật khi nonce bị lộ hoặc tái sử dụng (`src/nonce_attack.py`).
    *   Xây dựng slide thuyết trình và tổng hợp Phụ lục, Tài liệu tham khảo.

## 2. Giới thiệu
*   **2.1. Đặt vấn đề:**
    *   Sự phát triển của mật mã khóa công khai: từ bài toán phân tích nhân số nguyên tố (RSA) và logarit rời rạc (ElGamal) đến bài toán logarit rời rạc trên đường cong Elliptic (ECDLP) [1][2].
    *   Ưu điểm của ECC: Cung cấp mức độ bảo mật tương đương RSA/ElGamal nhưng với kích thước khóa nhỏ hơn rất nhiều, tiết kiệm băng thông và năng lượng lưu trữ [6].
*   **2.2. Động lực của dự án:**
    *   Tại sao Bitcoin (và các nền tảng Blockchain) lại chọn ECC/ECDSA (cụ thể là đường cong `secp256k1`) thay vì RSA? [3]
    *   Tầm quan trọng của việc triển khai an toàn và rủi ro chí mạng từ các lỗi nhỏ (ví dụ: tái sử dụng số ngẫu nhiên nonce) [4].
*   **2.3. Mục tiêu và phạm vi:**
    *   Dự án không đề xuất hệ mật mới.
    *   Mục tiêu: Mô phỏng cơ chế cốt lõi của ECC/ECDSA, tối ưu hóa (Shamir's Trick), tấn công tái sử dụng nonce, và so sánh hiệu năng thực tế RSA/ECDSA qua OpenSSL.

## 3. Phương pháp luận
*   **3.1. Cơ sở toán học nền tảng:**
    *   Trường hữu hạn $F_p$ và các phép toán (Modulo, thuật toán Euclid mở rộng, nghịch đảo Modulo).
    *   Đường cong Elliptic: Phương trình Weierstrass $y^2 = x^3 + ax + b \pmod p$ [7].
    *   Phép toán trên điểm (Point Addition, Point Doubling) và nhân vô hướng (Scalar Multiplication - Double and Add) [5].
*   **3.2. Thuật toán Chữ ký số ECDSA:**
    *   Quá trình tạo khóa (Key Generation).
    *   Quá trình ký (Signing): Sự phụ thuộc bắt buộc vào số ngẫu nhiên $k$ (nonce).
    *   Quá trình xác minh (Verification) [3].
*   **3.3. Lỗ hổng tái sử dụng Nonce (Nonce Reuse Attack):**
    *   Toán học đằng sau cuộc tấn công: Nếu hai tin nhắn khác nhau $m_1, m_2$ được ký cùng một số $k$, hacker có thể tính được $k = (h_1 - h_2) / (s_1 - s_2) \pmod n$.
    *   Từ $k$, khôi phục được khóa bí mật $d = (s \cdot k - h) / r \pmod n$ [4].
*   **3.4. Tối ưu hóa xác minh bằng Shamir's Trick:**
    *   Thuật toán tính đồng thời $u_1G + u_2Q$ giúp giảm số lượng phép nhân đôi điểm (doublings) [5].

## 4. Kết quả và bàn luận
*   **4.1. Mô phỏng ECDSA trên Toy Curve (Môi trường Python):**
    *   Trình bày kết quả tạo khóa, ký và xác minh thành công trên đường cong mô phỏng $y^2 = x^3 + 7 \pmod{223}$.
    *   Chứng minh hệ thống từ chối chữ ký khi nội dung bị thay đổi (Tampering).
*   **4.2. Demo Khai thác Lỗ hổng Tái sử dụng Nonce:**
    *   Trình bày log output minh họa việc khôi phục chính xác khóa bí mật $d$ từ hai chữ ký sử dụng chung nonce $k$.
    *   *Bàn luận:* Tầm quan trọng của bộ sinh số ngẫu nhiên (CSPRNG) hoặc ECDSA tất định (Deterministic ECDSA - RFC 6979) trong các ví Bitcoin thực tế.
*   **4.3. Hiệu năng Tối ưu hóa Shamir's Trick:**
    *   Số liệu so sánh (Dựa trên benchmark code python): Thuật toán Shamir giảm được ~50% phép nhân đôi điểm so với cách tính naive rời rạc.
*   **4.4. Đánh giá Hiệu năng Thực tế (RSA vs ECDSA bằng OpenSSL):**
    *   Minh họa tính đúng đắn trên OpenSSL (secp256k1).
    *   Trình bày số liệu Benchmark từ `openssl speed`: So sánh `rsa2048`, `rsa3072` với `ecdsap256`.
    *   *Bàn luận:* Tốc độ tạo chữ ký (Sign) của ECDSA vượt trội so với RSA (nhanh hơn ~70 lần so với RSA 3072-bit), khẳng định lý do ECDSA phù hợp cho nền tảng phi tập trung như Bitcoin [6].
*   **4.5. Các nguy cơ trong tương lai (Post-Quantum):**
    *   Sự đe dọa của máy tính lượng tử (Thuật toán Shor) đối với ECC và hướng đi trong tương lai [8].

## 5. Tài liệu tham khảo
*   [1] NDHan, *MI4100_LN06-Public-Key-Crypto*, Bài giảng môn học, HUST.
*   [2] N. Koblitz, *Elliptic Curve Cryptosystems*, Mathematics of Computation, 1987.
*   [3] J. Bos et al., *Elliptic Curve Cryptography in Practice*, 2014.
*   [4] N. Heninger et al., *Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies*, 2013.
*   [5] *Elliptic Curve Cryptography Engineering*, Extract notes.
*   [6] *Performance Analysis of Elliptic Curve Cryptography for SSL*, Extract notes.
*   [7] *Use of Elliptic Curves in Cryptography*, Extract notes.
*   [8] *Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities: Resource Estimates and Mitigations*, Extract notes.

## 6. Phụ lục: Kế hoạch nhóm
*   **Tuần 1:** Nghiên cứu tài liệu (Slide lý thuyết, tài liệu về thuật toán). Phân chia công việc.
*   **Tuần 2:** Lập trình cơ sở toán học và kiến trúc lõi ECC trên Python (`field.py`, `ecc.py`).
*   **Tuần 3:** Mô phỏng chữ ký ECDSA (`ecdsa_toy.py`) và thực hiện Unit Test.
*   **Tuần 4:** Xây dựng mô phỏng tấn công Nonce Reuse (`nonce_attack.py`) và thuật toán tối ưu hóa (`shamir.py`).
*   **Tuần 5:** Nghiên cứu OpenSSL, chạy script thực tế, lấy số liệu Benchmark (`openssl_demo`).
*   **Tuần 6:** Tổng hợp số liệu, viết báo cáo (`report_outline.md`), làm slide trình bày và hoàn thiện dự án.
