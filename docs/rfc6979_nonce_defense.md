# Nonce Defense Notes (RFC6979-style) cho ECDSA

## Mục tiêu tài liệu
Tài liệu này giải thích vì sao `k` (nonce) trong ECDSA là điểm sống còn về an toàn triển khai, và vì sao demo `nonce reuse` trong repo là một lỗi triển khai, không phải bằng chứng rằng ECDSA đúng chuẩn bị "phá".

Phạm vi ở đây là **giáo dục**:
- Không phải hướng dẫn triển khai production.
- Không phải mô tả đầy đủ mọi biến thể tấn công side-channel.
- Không thay thế chuẩn RFC/FIPS hay review bảo mật chuyên sâu.

## 1) Vì sao nonce `k` phải vừa duy nhất vừa bí mật
Trong ECDSA, mỗi chữ ký dùng một giá trị nonce `k` mới.  
`k` cần thỏa hai yêu cầu:

1. **Duy nhất theo từng chữ ký**: không được tái sử dụng cho hai message khác nhau.
2. **Bí mật/khó đoán**: attacker không được biết trước hoặc suy ra chính xác `k`.

Lý do: công thức ký dùng trực tiếp `k` cùng private key `d`. Khi `k` lặp lại hoặc rò rỉ thông tin, các phương trình chữ ký tạo ra đủ ràng buộc để suy ra `d`.

## 2) Vì sao reuse nonce làm lộ private key
Với hai chữ ký ECDSA khác message nhưng dùng cùng `k`, attacker có thể kết hợp hai phương trình chữ ký để:

1. Khôi phục `k`.
2. Từ `k`, khôi phục `d` (private key).

Đây là tấn công toán học trực tiếp từ công thức ECDSA, không cần brute-force secp256k1.  
Kết luận đúng là: **lỗi triển khai nonce** làm hỏng hệ thống chữ ký.

## 3) Vì sao nonce thiên lệch hoặc rò rỉ một phần cũng nguy hiểm
Nguy cơ không chỉ ở reuse hoàn toàn. Nếu `k`:

- có bias (không phân phối đều),
- bị rò vài bit,
- hoặc sinh từ RNG yếu/predictable,

thì attacker có thể tích lũy nhiều chữ ký và áp dụng kỹ thuật thống kê/lattice để suy ra `d` trong một số điều kiện thực tế.

Vì vậy, "không reuse" là điều kiện cần, nhưng chưa đủ nếu nguồn nonce vẫn yếu.

## 4) Vì sao không thể nói "ECDSA bị broken"
Nói chính xác:

- **ECDSA đúng chuẩn không bị broken bởi chính công thức của nó** trong mô hình an toàn tương ứng.
- Hệ thống ECDSA thường vỡ vì **implementation failure**: nonce reuse, RNG yếu, side-channel, hoặc code tự viết thiếu kỷ luật bảo mật.

Do đó, thông điệp kỹ thuật đúng là:
> Good cryptography = toán tốt + triển khai đúng.

## 5) Hướng phòng thủ khuyến nghị
1. **Never reuse `k`** giữa hai chữ ký.
2. **Dùng RNG an toàn** nếu chọn ký kiểu randomized.
3. **Ưu tiên deterministic ECDSA theo hướng RFC6979** để giảm phụ thuộc vào entropy runtime.
4. **Dùng thư viện constant-time, đã review kỹ** thay vì tự ráp primitive.
5. **Không tự viết ECDSA production từ đầu** trừ khi có năng lực audit và quy trình kiểm chứng nghiêm ngặt.

Lưu ý: deterministic nonce theo RFC6979 giúp giảm rủi ro từ RNG lỗi, nhưng **không tự động giải quyết mọi rủi ro triển khai** (ví dụ side-channel).

## 6) Liên hệ với demo reused nonce trong repo
Repo có demo tấn công reused nonce trên **toy parameters** để minh họa:

1. Hai chữ ký dùng chung nonce.
2. Khôi phục lại private key thành công.

Demo này chứng minh một điểm rất cụ thể:
- **Khi quản lý nonce sai, ECDSA có thể sụp đổ hoàn toàn.**

Demo này **không** chứng minh:
- có thể tấn công secp256k1 thực tế bằng brute force toy code,
- hay giảm bảo mật Bitcoin nói chung.

Trong storyline Q0-Q8 của repo, phần này là cầu nối từ:
- Q6: "nonce reuse làm lộ khóa"
- sang Q6.5: "kỷ luật triển khai để tránh lỗi hệ thống".

## Nguồn tham khảo
1. Thomas Pornin, *RFC 6979: Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature Algorithm (ECDSA)*, IETF, 2013.  
   https://datatracker.ietf.org/doc/html/rfc6979
2. Bitcoin Developer Documentation, *Transactions* (phần chữ ký giao dịch và xác thực chi tiêu).  
   https://developer.bitcoin.org/devguide/transactions.html
3. Joachim Breitner, Nadia Heninger, *Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies*, 2013.  
   https://www.readkong.com/page/biased-nonce-sense-lattice-attacks-against-weak-ecdsa-2687059
