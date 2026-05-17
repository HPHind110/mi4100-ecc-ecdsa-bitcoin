# Mật mã đường cong elliptic ECC và ứng dụng chữ ký số ECDSA trong Bitcoin

## Tóm tắt

Dự án này tập trung vào nghiên cứu và mô phỏng Hệ mật mã đường cong Elliptic (ECC) và thuật toán chữ ký số ECDSA, vốn là nền tảng cốt lõi cho việc xác thực giao dịch trong mạng lưới Bitcoin. Xuất phát từ nhu cầu tìm kiếm một hệ mật hiệu quả hơn các phương pháp truyền thống như RSA hay ElGamal, dự án phân tích cách thức ECC đạt được mức độ bảo mật tương đương với kích thước khóa nhỏ hơn đáng kể, giúp tối ưu hóa tài nguyên cho hệ thống blockchain.

Người thực hiện đã triển khai một hệ thống mô phỏng toàn diện bằng ngôn ngữ Python, bao gồm các phép toán trên trường hữu hạn, cấu trúc đường cong Elliptic, và giao thức ký/xác minh ECDSA. Để minh họa các khía cạnh an toàn và hiệu năng, dự án thực hiện demo cuộc tấn công khôi phục khóa bí mật khi tái sử dụng số ngẫu nhiên (nonce reuse attack) và áp dụng thủ thuật Shamir (Shamir's trick) để tối ưu hóa tốc độ xác minh. Ngoài ra, việc sử dụng công cụ OpenSSL chuẩn công nghiệp trên đường cong `secp256k1` và thực hiện benchmark so sánh với RSA đã cung cấp cái nhìn thực tiễn về ưu thế vượt trội của ECC.

Kết quả thực nghiệm khẳng định rằng dù ECC mang lại hiệu quả cao về mặt toán học, tính an toàn của hệ thống phụ thuộc rất lớn vào việc triển khai thực tế, đặc biệt là quy trình quản lý nonce. Dự án đóng vai trò là một mô hình giáo dục giúp làm sáng tỏ các nguyên lý mật mã học đằng sau sự vận hành của tiền mã hóa hiện đại.

## 1. Giới thiệu

### 1.1. Bối cảnh
Mật mã khóa công khai (Public-key Cryptography) ra đời đã giải quyết triệt để bài toán phân phối khóa và xác thực trong môi trường mạng không tin cậy. Các hệ mật đầu tiên như RSA dựa trên độ khó của bài toán phân tích thừa số nguyên tố, trong khi ElGamal dựa trên bài toán logarit rời rạc (DLP) trong trường hữu hạn. Tuy nhiên, khi nhu cầu về độ bảo mật tăng lên, kích thước khóa của các hệ mật này phải mở rộng rất lớn, gây áp lực lên băng thông và khả năng xử lý.

ECC xuất hiện như một giải pháp thay đổi cấu trúc nhóm toán học từ trường hữu hạn sang nhóm các điểm trên đường cong Elliptic. Điều này tạo ra bài toán logarit rời rạc trên đường cong Elliptic (ECDLP) có độ phức tạp cao hơn nhiều lần. Trong bối cảnh Bitcoin, nơi mỗi giao dịch cần được xác thực nhanh chóng và lưu trữ vĩnh viễn trên sổ cái, ECDSA (biến thể chữ ký số của ECC) đã trở thành lựa chọn tối ưu nhờ khả năng tạo chữ ký nhỏ gọn nhưng cực kỳ an toàn.

### 1.2. Vấn đề của đề tài
Câu hỏi trung tâm mà dự án này giải quyết là: "Vì sao ECC/ECDSA phù hợp với Bitcoin hơn các hệ mật khóa công khai truyền thống như RSA hoặc ElGamal, và khi triển khai thực tế thì điểm yếu nằm ở đâu?"

### 1.3. Mục tiêu dự án
Dự án được thực hiện nhằm đạt được các mục tiêu cụ thể sau:
- Trình bày chi tiết cơ sở toán học của ECC trên trường hữu hạn.
- Mô phỏng các phép toán cốt lõi trên đường cong Elliptic (cộng điểm, nhân vô hướng).
- Triển khai quy trình sinh khóa, ký và xác minh ECDSA trên mô hình đường cong nhỏ (toy curve).
- Minh họa lỗ hổng bảo mật khi tái sử dụng nonce $k$ để khôi phục khóa bí mật.
- Tìm hiểu và triển khai thủ thuật Shamir để tối ưu hóa hiệu năng xác minh chữ ký.
- Sử dụng OpenSSL để thực nghiệm trên đường cong thực tế `secp256k1`.
- Thực hiện benchmark so sánh hiệu năng giữa RSA và ECDSA để rút ra nhận định thực tế.

### 1.4. Phạm vi và giới hạn
Báo cáo này tập trung vào khía cạnh giáo dục và minh họa nguyên lý. Vì vậy, dự án có các giới hạn sau:
- Không xây dựng phần mềm ví Bitcoin hoàn chỉnh hay tương tác với mạng lưới Bitcoin thật.
- Không tạo hoặc xử lý các khóa bí mật thực tế của người dùng trên blockchain.
- Các cuộc tấn công demo chỉ sử dụng khóa nhỏ hoặc khóa tự tạo cục bộ trong môi trường kiểm thử.
- Mã nguồn được thiết kế để dễ hiểu, không phải là thư viện mật mã dùng cho sản xuất (Production-ready).

## 2. Cơ sở lý thuyết

### 2.1. Mật mã khóa công khai
Hệ mật khóa công khai sử dụng một cặp khóa: khóa công khai (public key) để chia sẻ rộng rãi và khóa bí mật (private key) được giữ kín. Nguyên lý dựa trên các "hàm một chiều có cửa sập" (trapdoor one-way functions) - những phép toán dễ thực hiện theo một chiều nhưng cực kỳ khó đảo ngược nếu không biết thông tin bí mật. Chữ ký số là ứng dụng quan trọng nhất trong Bitcoin, cho phép người dùng chứng minh quyền sở hữu tài sản mà không cần tiết lộ khóa bí mật.

### 2.2. RSA và ElGamal như hai bước nền
- **RSA:** Dựa trên việc nhân hai số nguyên tố lớn là dễ, nhưng phân tích kết quả thành các thừa số nguyên tố ban đầu là cực khó.
- **ElGamal:** Chuyển sang bài toán logarit rời rạc: tính $g^a \pmod p$ là dễ, nhưng tìm $a$ khi biết kết quả là rất khó.
ECC kế thừa tư tưởng của ElGamal nhưng áp dụng trên một cấu trúc nhóm toán học phức tạp hơn, dẫn đến độ bảo mật cao hơn trên cùng một đơn vị dữ liệu.

### 2.3. Số học modulo và trường hữu hạn
Toàn bộ các phép toán trong dự án được thực hiện trên trường hữu hạn $F_p$. Các khái niệm then chốt bao gồm:
- **Nghịch đảo modulo:** Tìm $x$ sao cho $ax \equiv 1 \pmod p$, sử dụng thuật toán Euclid mở rộng.
- **Phép chia modulo:** Được thực hiện bằng cách nhân với nghịch đảo modulo của số chia.

**Liên hệ thực tế:** Logic này được hiện thực hóa qua hàm `mod_inv(a, p)` và `mod_div(a, b, p)` trong file `src/field.py` bằng thuật toán Euclid mở rộng (`egcd`).

### 2.4. Đường cong elliptic trên trường hữu hạn
Đường cong Elliptic được sử dụng có dạng phương trình Weierstrass:
$$E: y^2 = x^3 + ax + b \pmod p$$
Các điểm trên đường cong cùng với "điểm vô cực" $O$ tạo thành một nhóm Abel dưới phép cộng điểm.
- **Cộng hai điểm ($P+Q$):** Dựa trên hình học, là điểm đối xứng của giao điểm thứ ba giữa đường thẳng đi qua $P, Q$ và đường cong.
- **Nhân đôi điểm ($2P$):** Sử dụng tiếp tuyến tại điểm $P$.
- **Nhân vô hướng ($kP$):** Thực hiện cộng điểm $P$ liên tiếp $k$ lần. Trong dự án, thuật toán "Double-and-Add" được sử dụng để đạt độ phức tạp $O(\log k)$.

**Liên hệ thực tế:** Thuật toán nhân vô hướng tối ưu được lập trình chi tiết tại hàm `scalar_mul()` thuộc lớp `Curve` trong file `src/ecc.py`.

### 2.5. ECC và secp256k1 trong Bitcoin
Bitcoin sử dụng đường cong cụ thể mang tên `secp256k1` với các tham số $a=0, b=7$.
- **Khóa bí mật $d$:** Một số nguyên ngẫu nhiên 256-bit.
- **Khóa công khai $Q$:** Kết quả của phép nhân vô hướng $Q = dG$, với $G$ là điểm gốc (Generator point).
Địa chỉ Bitcoin thực chất là một bản băm (hash) của khóa công khai này.

### 2.6. ECDSA (Elliptic Curve Digital Signature Algorithm)
Quy trình ECDSA bao gồm ba giai đoạn:
1. **Tạo khóa:** Chọn $d$ ngẫu nhiên, tính $Q = dG$.
2. **Ký tin nhắn ($m$):**
   - Chọn số ngẫu nhiên $k$ (nonce).
   - Tính điểm $R = kG$, lấy hoành độ $r = x_R \pmod n$.
   - Tính $s = k^{-1}(H(m) + dr) \pmod n$.
   - Chữ ký là cặp $(r, s)$.
3. **Xác minh:**
   - Tính $w = s^{-1} \pmod n$.
   - Tính $u_1 = H(m) \cdot w \pmod n$ và $u_2 = r \cdot w \pmod n$.
   - Tính điểm $X = u_1G + u_2Q$.
   - Chấp nhận nếu $x_X \pmod n = r$.

**Giải thích trực giác:** Có thể coi chữ ký $(r, s)$ như một bộ khóa và ổ khóa tạm thời. Trong đó, $r$ giống như một "ổ khóa" được tạo ra từ số ngẫu nhiên $k$. Còn $s$ đóng vai trò là "chìa khóa" được đúc từ sự kết hợp giữa nội dung tin nhắn $H(m)$, khóa bí mật $d$ và ổ khóa $r$, tất cả được liên kết lại thông qua $k$. Việc xác minh thành công chứng minh rằng chỉ người sở hữu đúng khóa bí mật $d$ mới có thể tạo ra "chìa khóa" $s$ khớp với "ổ khóa" $r$ cho tin nhắn đó.

**Liên hệ thực tế:** Quy trình này được ánh xạ trực tiếp thành các hàm `sign(params, d, msg)` và `verify(params, Q, msg, sig)` tại file `src/ecdsa_toy.py`.

### 2.7. Nonce trong ECDSA
Số $k$ (nonce) phải là số ngẫu nhiên và tuyệt đối không được dùng lại. Nếu dùng chung $k$ cho hai tin nhắn khác nhau ($m_1, m_2$) với cùng khóa bí mật $d$, ta sẽ có hai chữ ký $(r, s_1)$ và $(r, s_2)$ có chung giá trị $r$.

**Chứng minh toán học:**
Từ công thức ký: $s = k^{-1}(h + d \cdot r) \pmod n$
$\Rightarrow k \cdot s = h + d \cdot r \pmod n$
Với hai chữ ký dùng chung $k$:
1. $k \cdot s_1 = h_1 + d \cdot r \pmod n$
2. $k \cdot s_2 = h_2 + d \cdot r \pmod n$
Trừ (1) cho (2), thành phần chứa khóa bí mật ($d \cdot r$) bị triệt tiêu:
$k(s_1 - s_2) = h_1 - h_2 \pmod n$
$\Rightarrow k = (h_1 - h_2)(s_1 - s_2)^{-1} \pmod n$
Khi đã tìm được $k$, khóa bí mật $d$ dễ dàng bị lộ: $d = (s_1 \cdot k - h_1)r^{-1} \pmod n$.

**Liên hệ thực tế:** Cuộc tấn công khôi phục khóa từ công thức này được tự động hóa tại hàm `recover_private_key_from_nonce()` trong file `src/nonce_attack.py`.

### 2.8. Shamir's trick
Trong bước xác minh, ta cần tính $u_1G + u_2Q$. Thủ thuật Shamir giúp tối ưu hóa bằng cách quét các bit của $u_1$ và $u_2$ cùng lúc, giảm đáng kể số phép nhân đôi điểm.

**Liên hệ thực tế:** Thuật toán tối ưu này được triển khai trong hàm `shamir_mul()` tại file `src/shamir.py`.

## 3. Phương pháp triển khai

### 3.1. Tổng quan kiến trúc dự án
Dự án được tổ chức theo mô hình module hóa để tách biệt logic toán học, ứng dụng và thực nghiệm:
```
F:\CAC_Project\
├───src\                    # Mã nguồn logic cốt lõi
│   ├───field.py            # Số học trường hữu hạn
│   ├───ecc.py              # Cấu trúc điểm và đường cong
│   ├───ecdsa_toy.py        # Mô phỏng ký/xác minh
│   ├───nonce_attack.py     # Demo tấn công bảo mật
│   └───shamir.py           # Tối ưu hóa hiệu năng
├───openssl_demo\           # Thực nghiệm công nghiệp
├───results\                # Dữ liệu benchmark thực tế
└───tests\                  # Hệ thống kiểm thử tự động
```

### 3.2. Module số học hữu hạn: src/field.py
Triển khai các hàm bổ trợ như `egcd` (Euclid mở rộng) để tìm nghịch đảo modulo và phép chia trong trường số nguyên. Đây là "lớp vật lý" cho mọi phép tính mật mã phía trên.

### 3.3. Module ECC: src/ecc.py
Định nghĩa lớp `Point` và `Curve`. Triển khai các quy tắc cộng điểm và nhân đôi điểm trên đường cong Elliptic. Đặc biệt, thuật toán nhân vô hướng được tối ưu hóa bằng phương pháp Double-and-Add.

### 3.4. Module ECDSA toy: src/ecdsa_toy.py
Hiện thực hóa quy trình ký và xác minh ECDSA. Để dễ quan sát, module này sử dụng một "Toy Curve" (đường cong nhỏ) với $p=223$ và $n=21$. Điều này cho phép kiểm chứng từng bước tính toán một cách trực quan.

### 3.5. Module tấn công reused nonce: src/nonce_attack.py
Triển khai công thức khôi phục khóa bí mật khi phát hiện hai chữ ký có cùng giá trị $r$ (chứng tỏ dùng chung $k$). Module này minh họa bài học thực tế về an toàn triển khai.

### 3.6. Module Shamir's trick: src/shamir.py
Xây dựng hai phương pháp xác minh: `naive_mul_add` và `shamir_mul`. Tích hợp bộ đếm phép toán (`add_count`, `double_count`) để so sánh hiệu quả của thủ thuật Shamir.

### 3.7. OpenSSL demo: openssl_demo/
Sử dụng các script PowerShell để gọi lệnh OpenSSL, thực hiện các thao tác:
- Sinh cặp khóa `secp256k1`.
- Ký file văn bản và xác minh chữ ký.
- Demo việc xác minh thất bại khi dữ liệu bị sửa đổi (`message_tampered.txt`).

### 3.8. Kiểm thử
Sử dụng `pytest` để kiểm tra tính đúng đắn của mọi module. Các bài test bao gồm việc xác minh nghịch đảo modulo, tính đúng đắn của phép cộng điểm, và đảm bảo quy trình ký/xác minh hoạt động chuẩn xác.

## 4. Kết quả thực nghiệm và khám phá

### 4.1. Kết quả mô phỏng số học hữu hạn
Hệ thống xử lý chính xác các phép toán modulo phức tạp. Các trường hợp không có nghịch đảo modulo được bắt lỗi kịp thời, đảm bảo tính ổn định cho các tầng phía trên.

### 4.2. Kết quả mô phỏng ECC
Phép nhân vô hướng trên Toy Curve cho ra các kết quả nhất quán. Thuật toán Double-and-Add giúp thực hiện phép nhân $kP$ chỉ trong $\approx \log_2 k$ bước, chứng minh tính hiệu quả so với phép cộng lặp.

### 4.3. Kết quả ECDSA sign/verify
Mô phỏng cho thấy:
- Chữ ký hợp lệ luôn được xác minh thành công.
- Chỉ cần thay đổi 1 byte trong tin nhắn hoặc chữ ký, hệ thống lập tức từ chối (Verify False).
Điều này khẳng định tính toàn vẹn và xác thực của giao dịch.

### 4.4. Kết quả reused nonce attack
Trong kịch bản thực nghiệm, khi dùng chung nonce $k=4$ cho hai tin nhắn khác nhau, module tấn công đã khôi phục chính xác khóa bí mật $d$.
**Kết quả thực tế thu được:**
```
Original Private Key (d): 2
Reused Nonce (k): 4
Recovered Nonce (k): 4
Recovered Private Key (d): 2
SUCCESS: Private key recovered successfully!
```

### 4.5. Kết quả Shamir's trick
Dựa trên kết quả chạy thực tế từ script `src/shamir.py` với các hệ số $u_1=13, u_2=19$:

| Phương pháp | Phép cộng điểm | Phép nhân đôi điểm |
| :--- | :---: | :---: |
| Naive (Rời rạc) | 5 | 9 |
| Shamir (Đồng thời) | 4 | 5 |

**Nhận xét:** Trong ví dụ này, Shamir's trick đã giảm được 1 phép cộng và đặc biệt là giảm tới **4 phép nhân đôi điểm** (tương đương giảm hơn 40% khối lượng tính toán nhân đôi). Với các đường cong thực tế có kích thước khóa 256-bit, sự tối ưu này sẽ giúp quá trình xác minh trên các node Bitcoin nhanh hơn đáng kể.

### 4.6. Kết quả OpenSSL secp256k1
Sử dụng OpenSSL 3.0, dự án đã thực hiện ký thành công trên đường cong thực tế của Bitcoin. Chữ ký được tạo ra tuân thủ chuẩn ASN.1/DER, tương thích với các công cụ mật mã tiêu chuẩn.

### 4.7. Kết quả benchmark RSA/ECDSA
Dựa trên kết quả chạy từ `openssl speed`, ta có bảng so sánh hiệu năng (số phép toán mỗi giây):

| Thuật toán | Ký (Sign/s) | Xác minh (Verify/s) |
| :--- | :---: | :---: |
| RSA 2048-bit | 1539.1 | 45198.2 |
| RSA 3072-bit | 452.9 | 22683.2 |
| **ECDSA 256-bit (NIST P-256)** | **33256.1** | **12769.3** |

**Phân tích:**
- Tốc độ ký của ECDSA 256-bit nhanh hơn RSA 3072-bit khoảng **73 lần**.
- Dù tốc độ xác minh của RSA rất nhanh nhờ số mũ công khai nhỏ, nhưng ECDSA mang lại sự cân bằng tốt hơn và tiết kiệm tài nguyên hơn cho việc tạo chữ ký trên thiết bị người dùng.

## 5. Bàn luận

### 5.1. Vì sao ECC là bước tiến hợp lý sau RSA/ElGamal?
Sự khác biệt nằm ở độ khó của bài toán nền tảng. Phân tích thừa số (RSA) bị đe dọa bởi các thuật toán như GNFS. ECDLP trên đường cong Elliptic chưa có thuật toán cổ điển nào hiệu quả hơn tìm kiếm theo cấp số nhân (ngoại trừ trên một số đường cong đặc biệt bị lỗi). Do đó, ECC đạt mức bảo mật cao với khóa 256-bit, trong khi RSA cần tới 3072-bit. Khóa nhỏ hơn đồng nghĩa với việc lưu trữ blockchain hiệu quả hơn.

### 5.2. Vì sao Bitcoin dùng ECDSA?
Bitcoin không cần mã hóa nội dung (vì giao dịch là công khai), nó chỉ cần xác thực. ECDSA cho phép bất kỳ node nào trong mạng lưới cũng có thể kiểm tra tính hợp lệ của một giao dịch bằng khóa công khai của người gửi mà không cần sự tin tưởng lẫn nhau. Tính nhỏ gọn của chữ ký ECDSA là yếu tố sống còn để mạng lưới Bitcoin có thể xử lý hàng ngàn giao dịch trong mỗi block.

### 5.3. Điều học được từ reused nonce
Đây là minh chứng rõ nhất cho câu nói: "Mật mã học khó ở khâu triển khai". Dù thuật toán ECDSA rất mạnh, nhưng nếu bộ sinh số ngẫu nhiên bị lỗi hoặc lập trình viên bất cẩn dùng lại nonce, toàn bộ hệ thống sụp đổ. Trong thực tế, Bitcoin đã chuyển sang dùng "Deterministic ECDSA" (RFC 6979), nơi nonce được tạo ra từ bản băm của tin nhắn và khóa bí mật, loại bỏ hoàn toàn rủi ro ngẫu nhiên.

### 5.4. Điều học được từ Shamir's trick
Tối ưu hóa thuật toán không chỉ là làm cho code chạy nhanh hơn, mà còn là hiểu sâu về cấu trúc của phép toán. Việc kết hợp các phép nhân vô hướng giúp giảm tải cho các node xác thực (miners/full nodes), nâng cao khả năng mở rộng của hệ thống.

### 5.5. Giới hạn của mô phỏng
Mô phỏng trong dự án này sử dụng Python, một ngôn ngữ không tối ưu cho hiệu năng mật mã. Ngoài ra, việc sử dụng "Toy Curve" chỉ mang tính minh họa; trong thực tế, các cuộc tấn công sẽ phức tạp hơn và đòi hỏi kiến thức về toán học lưới (lattice-based attacks).

## 6. Kết luận

Dự án đã thực hiện thành công việc nghiên cứu và mô phỏng hệ mật mã đường cong Elliptic (ECC) cùng ứng dụng của nó trong chữ ký số ECDSA của Bitcoin. Thông qua việc xây dựng mô hình từ những viên gạch toán học cơ bản nhất trên trường hữu hạn đến các thuật toán tối ưu và kịch bản tấn công thực tế, người thực hiện đã rút ra được những kết luận quan trọng.

Thứ nhất, ECC/ECDSA thực sự là một bước đột phá so với RSA về mặt hiệu quả, cung cấp khả năng bảo mật mạnh mẽ với kích thước khóa tối thiểu, đáp ứng hoàn hảo yêu cầu của các hệ thống phi tập trung như Bitcoin. Thứ hai, tính an toàn của một hệ mật không chỉ dựa trên độ khó toán học mà còn nằm ở sự tỉ mỉ trong quá trình triển khai thực tế; lỗi tái sử dụng nonce là một bài học đắt giá về tầm quan trọng của tính ngẫu nhiên. Cuối cùng, các kỹ thuật tối ưu như Shamir's trick cho thấy tiềm năng cải thiện hiệu năng hệ thống thông qua việc tổ chức phép toán thông minh.

Dự án này không chỉ giúp củng cố kiến thức lý thuyết về mật mã học mà còn rèn luyện kỹ năng lập trình và phân tích hệ thống. Đây là nền tảng vững chắc để tìm hiểu sâu hơn về các công nghệ bảo mật tiên tiến trong kỷ nguyên blockchain và điện toán lượng tử.

## 7. Tài liệu tham khảo

[1] Neal Koblitz, "Elliptic Curve Cryptosystems", Mathematics of Computation, 1987.
[2] Victor S. Miller, "Use of Elliptic Curves in Cryptography", CRYPTO 1985.
[3] Joppe W. Bos et al., "Elliptic Curve Cryptography in Practice", 2014.
[4] Joachim Breitner and Nadia Heninger, "Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies", 2013.
[5] Alessandro Cilardo et al., "Elliptic Curve Cryptography Engineering", 2006.
[6] Vipul Gupta et al., "Performance Analysis of Elliptic Curve Cryptography for SSL", 2002.
[7] Bitcoin Developer Documentation, "Elliptic Curve Digital Signature Algorithm (ECDSA)".
[8] OpenSSL Documentation, "ECDSA_sign and ECDSA_verify".
[9] Bài giảng MI4100: "Mật mã khóa công khai", Đại học Bách Khoa Hà Nội.

## Phụ lục A. Hướng dẫn chạy mô phỏng

Để khởi chạy các thành phần của dự án, người dùng thực hiện các bước sau trên PowerShell:

1. **Khởi tạo môi trường:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   $env:PYTHONPATH = "."
   ```

2. **Chạy kiểm thử toàn bộ:**
   ```powershell
   pytest tests/
   ```

3. **Chạy demo tấn công Nonce Reuse:**
   ```powershell
   python src/nonce_attack.py
   ```

4. **Chạy so sánh hiệu năng Shamir's trick:**
   ```powershell
   python src/shamir.py
   ```

5. **Chạy demo OpenSSL:**
   ```powershell
   cd openssl_demo
   .\gen_keys.ps1
   .\sign_verify.ps1
   .\benchmark.ps1
   ```

## Phụ lục B. Cấu trúc mã nguồn

- `src/field.py`: Chứa các hàm toán học về trường hữu hạn $F_p$ (GCD mở rộng, nghịch đảo modulo).
- `src/ecc.py`: Triển khai lớp `Point` và `Curve`, thực hiện phép cộng điểm và nhân vô hướng.
- `src/ecdsa_toy.py`: Triển khai quy trình ký và xác minh ECDSA trên đường cong mô phỏng.
- `src/nonce_attack.py`: Chứa logic tấn công khôi phục khóa từ lỗi nonce.
- `src/shamir.py`: Triển khai thuật toán tối ưu hóa Shamir's trick cho việc xác minh.
- `tests/`: Chứa các bộ unit test tương ứng cho từng module `src/`.
- `openssl_demo/`: Các kịch bản PowerShell thực hiện ký/xác minh và benchmark bằng thư viện OpenSSL.
