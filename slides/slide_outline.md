# Outline Thuyết Trình: Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin

*Số lượng:* 13 slides
*Cấu trúc:* Bám sát yêu cầu đồ án môn học.

---

## Slide 1: Tiêu đề
- **Title:** Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin
- **Key message:** Giới thiệu đề tài và thành viên nhóm.
- **Nội dung chính:**
  - Tên môn học: Mật mã và độ phức tạp thuật toán.
  - Tên đề tài.
  - Thông tin sinh viên thực hiện & Giảng viên hướng dẫn.

## Slide 2: Bối cảnh và Chủ đề
- **Title:** Bối cảnh & Sự trỗi dậy của ECC
- **Key message:** Hệ thống phân tán như Blockchain đòi hỏi sự nhỏ gọn và tốc độ mà RSA khó đáp ứng.
- **Nội dung chính:**
  - Sự phát triển của các hệ thống mật mã khóa công khai (Public-Key Crypto).
  - Yêu cầu khắt khe của mạng lưới Bitcoin: Mọi node đều phải lưu trữ và xác minh hàng triệu giao dịch.
  - Lý do chọn ECC: Kích thước khóa nhỏ hơn rất nhiều nhưng cung cấp cùng một mức độ bảo mật.

## Slide 3: Bài toán và Giải pháp
- **Title:** Bài toán Xác thực Giao dịch & Giải pháp ECDSA
- **Key message:** ECDSA là chìa khóa để định danh và bảo vệ tài sản số trên Blockchain.
- **Nội dung chính:**
  - **Bài toán:** Làm sao chứng minh "Tôi là chủ sở hữu của số tiền này" mà không để lộ khóa bí mật? Làm sao ngăn chặn giả mạo giao dịch?
  - **Giải pháp:** Sử dụng thuật toán chữ ký số trên đường cong Elliptic (ECDSA).
    - Khóa công khai = Địa chỉ nhận tiền.
    - Khóa bí mật = Quyền chi tiêu.

## Slide 4: Phạm vi và Lý do triển khai sản phẩm
- **Title:** Phạm vi triển khai & Mục tiêu Mô phỏng
- **Key message:** Tập trung vào bản chất toán học và lỗ hổng triển khai thay vì xây dựng một ví Bitcoin thực tế.
- **Nội dung chính:**
  - **Lý do chỉ triển khai mô phỏng (Toy Model):**
    - Tránh rủi ro thao tác nhầm với real Bitcoin keys / funds (Safety constraints).
    - Các thư viện chuẩn đã ẩn giấu quá trình toán học (hộp đen). Việc tự code từ đầu giúp hiểu rõ cơ chế.
  - **Sản phẩm bao gồm:**
    - Code Python tự viết mô phỏng ECC/ECDSA trên trường hữu hạn nhỏ.
    - Demo các hình thức tấn công vào lỗi triển khai.
    - Script benchmark so sánh với OpenSSL.

## Slide 5: Cơ sở Toán học của ECC
- **Title:** Toán học đằng sau Elliptic Curve
- **Key message:** Phép nhân vô hướng (Scalar Multiplication) là trái tim của ECC.
- **Nội dung chính:**
  - Phương trình đường cong $y^2 = x^3 + ax + b$ trên trường hữu hạn $\mathbb{F}_p$.
  - Phép cộng điểm (Point Addition) & Phép nhân đôi điểm (Point Doubling).
  - Thuật toán Double-and-Add để tính $Q = kG$.
- **Hình ảnh:** Đồ thị minh họa phép cộng điểm trên đường cong Elliptic thực.

## Slide 6: Cơ chế hoạt động của ECDSA
- **Title:** ECDSA: Tạo khóa, Ký và Xác minh
- **Key message:** Biến đổi thông điệp và khóa bí mật thành cặp chữ ký $(r, s)$ thông qua một số ngẫu nhiên (Nonce).
- **Nội dung chính:**
  - **Keygen:** Chọn $d$ (Private), tính $Q = dG$ (Public).
  - **Sign:** Chọn nonce $k$ ngẫu nhiên. Tính $r$ từ tọa độ $x$ của $kG$. Tính $s = k^{-1}(H(m) + dr) \pmod n$.
  - **Verify:** Phục hồi lại điểm từ chữ ký $(r, s)$ và đối chiếu $r$. Tầm quan trọng của biểu thức $u_1G + u_2Q$.

## Slide 7: Demo & Mô phỏng Toy ECDSA
- **Title:** Trình bày Sản phẩm: Python Toy ECDSA
- **Key message:** Hiển thị mã nguồn minh họa các bước toán học cơ bản một cách tường minh.
- **Nội dung chính:**
  - Trình bày kiến trúc code: `field.py` (Toán học Modulo), `ecc.py` (Lớp Point và các phép toán).
  - Giải thích hàm `scalar_multiply()` (Double-and-add).
- **Demo/Hình ảnh:** Chụp màn hình Terminal chạy `ecdsa_toy.py` với các tham số nhỏ (ví dụ $p=97$), in ra quá trình ký và verify thành công.

## Slide 8: Kỹ thuật Tối ưu hóa (Shamir's Trick)
- **Title:** Tối ưu hóa: Shamir's Trick trong Verification
- **Key message:** Thuật toán xác minh ECDSA có thể được tăng tốc đáng kể nhờ tính toán song song.
- **Nội dung chính:**
  - Phân tích nút thắt: Hàm verify cần tính $u_1G + u_2Q$, nếu tính rời sẽ tốn 2 lần chạy vòng lặp nhân đôi điểm.
  - Áp dụng Shamir's Trick: Gộp chung vòng lặp duyệt bit, chỉ nhân đôi 1 lần cho cả 2 điểm, tra bảng tính sẵn $G+Q$.
- **Demo/Bảng:** Bảng/Biểu đồ so sánh số lượng phép tính (Operations count) giữa Naive Verify và Shamir's Trick từ `shamir.py`.

## Slide 9: Implementation Flaw - Lỗ hổng Nonce
- **Title:** Khi thực tiễn "phản bội" lý thuyết toán học
- **Key message:** ECDSA hoàn hảo về toán học nhưng cực kỳ dễ vỡ nếu tạo Nonce $k$ không ngẫu nhiên.
- **Nội dung chính:**
  - Phân tích lỗi triển khai nguy hiểm nhất: Dùng lại số ngẫu nhiên $k$ (Repeated Nonce).
  - Giải thích toán học: Nếu $k_1 = k_2$, thì $r_1 = r_2$. 
  - Kẻ tấn công có thể lấy hai chữ ký $(r, s_1)$ và $(r, s_2)$ trên hai tin nhắn $m_1, m_2$, giải hệ phương trình để tìm ra $k$, rồi suy ngược ra Private Key $d$.
  - Nhắc lại vụ hack thực tế: PlayStation 3, lỗi Android RNG (2013).

## Slide 10: Demo: Nonce Reuse Attack
- **Title:** Mô phỏng Tấn công khôi phục Private Key
- **Key message:** Chỉ cần 2 chữ ký chia sẻ chung Nonce, mất trắng toàn bộ tài sản.
- **Nội dung chính:**
  - Giả lập kịch bản: Nạn nhân ký 2 tin nhắn khác nhau bằng cùng 1 nonce $k$.
  - Kẻ tấn công bắt gói tin (interception), trích xuất chữ ký và nội dung.
- **Demo:** Chạy kịch bản `nonce_attack.py`. Show log terminal quá trình kẻ tấn công tính ra giá trị $d$ trùng khớp hoàn toàn với Private Key gốc.

## Slide 11: secp256k1 & OpenSSL
- **Title:** Triển khai thực tế: Curve secp256k1
- **Key message:** Chuyển từ Toy Model sang môi trường công nghiệp thực tế.
- **Nội dung chính:**
  - Giới thiệu chuẩn đường cong Koblitz `secp256k1` mà Satoshi Nakamoto lựa chọn cho Bitcoin.
  - Kích thước số nguyên tố khổng lồ $p = 2^{256} - 2^{32} - 977$.
  - Giới thiệu công cụ dòng lệnh OpenSSL để xử lý ECC trong thực tế.

## Slide 12: Demo & Benchmark: RSA vs ECDSA
- **Title:** Benchmark & So sánh Thực tế
- **Key message:** ECDSA đánh bại RSA về tốc độ ký và kích thước, đặc biệt phù hợp cho IoT và Blockchain.
- **Nội dung chính:**
  - Demo OpenSSL: Chạy đoạn mã `sign_verify.ps1` tạo khóa, ký tin nhắn và kiểm tra tính toàn vẹn (bao gồm demo sửa file `message_tampered.txt` để verify failed).
  - Benchmark: So sánh thời gian chạy và dung lượng khóa giữa RSA-3072 và ECDSA-secp256k1 (cùng mức độ bảo mật 128-bit).
- **Demo/Bảng:** Trích xuất kết quả từ `results/openssl_benchmark.txt` lên màn hình (Thời gian GenKey, Sign, Verify).

## Slide 13: Kết luận & Hỏi đáp
- **Title:** Tổng kết
- **Key message:** ECC là tương lai, nhưng đòi hỏi sự cẩn trọng tuyệt đối khi lập trình.
- **Nội dung chính:**
  - Nhấn mạnh sự ưu việt của ECC/ECDSA về tài nguyên và bảo mật (cơ sở cho Bitcoin).
  - Cảnh báo: Bảo mật của hệ thống mật mã thường không gãy ở toán học, mà gãy ở khâu lập trình (Implementation & Side-channel).
  - Lời khuyên: Sử dụng Deterministic ECDSA (RFC 6979) để tránh lỗi Nonce.
- **Lời cảm ơn & Q/A.**