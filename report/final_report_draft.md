# BÁO CÁO DỰ ÁN

# Mật mã đường cong Elliptic ECC và ứng dụng chữ ký số ECDSA trong Bitcoin

## Tóm tắt

Dự án tập trung nghiên cứu và mô phỏng **mật mã đường cong Elliptic** (*Elliptic Curve Cryptography* — ECC) cùng với thuật toán chữ ký số **ECDSA** (*Elliptic Curve Digital Signature Algorithm*). Đây là một trong những nền tảng mật mã quan trọng được sử dụng trong Bitcoin để xác thực quyền sở hữu và tính hợp lệ của giao dịch.

So với các hệ mật khóa công khai truyền thống như RSA hoặc ElGamal, ECC có ưu điểm nổi bật là đạt được mức bảo mật cao với kích thước khóa nhỏ hơn đáng kể. Điều này đặc biệt phù hợp với các hệ thống phân tán như blockchain, nơi chữ ký số cần được lưu trữ, truyền tải và xác minh với số lượng rất lớn.

Trong dự án này, hệ thống mô phỏng được xây dựng bằng Python, bao gồm các thành phần chính: số học trên trường hữu hạn, phép toán trên đường cong Elliptic, sinh khóa, ký số, xác minh chữ ký ECDSA, mô phỏng tấn công khi tái sử dụng nonce, và tối ưu hóa xác minh bằng Shamir's trick.

Ngoài mô phỏng trên đường cong nhỏ phục vụ mục đích học tập, dự án cũng sử dụng OpenSSL để thực nghiệm với các đường cong mật mã thực tế, đồng thời benchmark so sánh hiệu năng giữa RSA và ECDSA. Kết quả cho thấy ECC không chỉ hiệu quả về mặt lý thuyết mà còn có ý nghĩa thực tiễn lớn trong các hệ thống yêu cầu bảo mật, tốc độ và kích thước chữ ký nhỏ gọn.

Một kết luận quan trọng của dự án là: **bảo mật mật mã không chỉ phụ thuộc vào độ khó toán học của thuật toán, mà còn phụ thuộc rất lớn vào cách triển khai**. Đặc biệt, lỗi tái sử dụng nonce trong ECDSA có thể làm lộ hoàn toàn khóa bí mật.

---

## 1. Giới thiệu

### 1.1. Bối cảnh

Mật mã khóa công khai ra đời nhằm giải quyết hai vấn đề lớn trong môi trường mạng không tin cậy:

- Làm thế nào để hai bên có thể giao tiếp an toàn mà không cần chia sẻ trước khóa bí mật?
- Làm thế nào để một người có thể chứng minh danh tính hoặc quyền sở hữu mà không cần tiết lộ khóa bí mật?

Các hệ mật khóa công khai cổ điển như **RSA** và **ElGamal** đã đặt nền móng cho lĩnh vực này.

RSA dựa trên độ khó của bài toán phân tích một số nguyên lớn thành các thừa số nguyên tố. Trong khi đó, ElGamal dựa trên độ khó của bài toán logarit rời rạc trong trường hữu hạn.

Tuy nhiên, khi yêu cầu bảo mật ngày càng tăng, các hệ như RSA cần sử dụng kích thước khóa rất lớn. Điều này dẫn đến chi phí lưu trữ, truyền tải và tính toán cao hơn.

ECC xuất hiện như một hướng tiếp cận mới. Thay vì làm việc trực tiếp trên nhóm nhân modulo như ElGamal, ECC xây dựng hệ mật trên nhóm các điểm thuộc đường cong Elliptic trên trường hữu hạn. Nhờ cấu trúc toán học này, bài toán logarit rời rạc trên đường cong Elliptic — gọi là **ECDLP** (*Elliptic Curve Discrete Logarithm Problem*) — trở thành nền tảng bảo mật của ECC.

Trong Bitcoin, mỗi giao dịch cần được ký bởi chủ sở hữu khóa bí mật và được xác minh bởi các node trong mạng lưới. Vì vậy, Bitcoin cần một cơ chế chữ ký số vừa an toàn, vừa nhỏ gọn, vừa đủ nhanh để xử lý trên quy mô lớn. ECDSA trên đường cong `secp256k1` đáp ứng tốt yêu cầu này.

Đường cong `secp256k1` có dạng:

$$
y^2 = x^3 + 7
$$

trên một trường hữu hạn nguyên tố lớn. Đây là đường cong được định nghĩa trong bộ tham số SEC 2.

### 1.2. Vấn đề nghiên cứu

Dự án tập trung trả lời câu hỏi chính:

> Vì sao ECC/ECDSA phù hợp với Bitcoin hơn so với các hệ mật khóa công khai truyền thống như RSA hoặc ElGamal, và những rủi ro triển khai thực tế của ECDSA là gì?

Từ câu hỏi này, báo cáo đi vào ba hướng chính:

- Cơ sở toán học của ECC.
- Cách ECDSA tạo và xác minh chữ ký số.
- Các điểm yếu thực tế nếu triển khai sai, đặc biệt là lỗi tái sử dụng nonce.

### 1.3. Mục tiêu dự án

Dự án hướng tới các mục tiêu sau:

- Trình bày cơ sở toán học của ECC trên trường hữu hạn.
- Mô phỏng phép cộng điểm và nhân vô hướng trên đường cong Elliptic.
- Triển khai quy trình sinh khóa, ký và xác minh ECDSA trên đường cong nhỏ.
- Minh họa tấn công khôi phục khóa bí mật khi nonce bị tái sử dụng.
- Cài đặt Shamir's trick để tối ưu hóa bước xác minh chữ ký.
- Thực nghiệm với OpenSSL trên các đường cong mật mã thực tế.
- Benchmark so sánh hiệu năng giữa RSA và ECDSA.
- Rút ra nhận xét về ưu điểm, giới hạn và bài học triển khai của ECC/ECDSA.

### 1.4. Phạm vi dự án

Dự án mang tính học thuật và mô phỏng, không nhằm xây dựng một hệ thống mật mã dùng trong sản xuất.

Phạm vi bao gồm:

- Mô phỏng toán học ECC bằng Python.
- Cài đặt ECDSA trên toy curve để dễ quan sát.
- Demo tấn công reused nonce trên dữ liệu tự tạo.
- Thực nghiệm ký và xác minh bằng OpenSSL.
- Benchmark hiệu năng RSA/ECDSA ở mức cơ bản.

Dự án không bao gồm:

- Xây dựng ví Bitcoin hoàn chỉnh.
- Giao tiếp với mạng Bitcoin thật.
- Quản lý khóa bí mật thật của người dùng.
- Tạo thư viện mật mã dùng cho production.
- Chống các tấn công kênh kề như side-channel attack, timing attack hoặc fault attack.

---

## 2. Cơ sở lý thuyết

### 2.1. Mật mã khóa công khai

Mật mã khóa công khai sử dụng một cặp khóa:

- **Khóa công khai** (*public key*): được chia sẻ rộng rãi.
- **Khóa bí mật** (*private key*): chỉ chủ sở hữu được biết.

Ý tưởng cốt lõi của mật mã khóa công khai là sử dụng các hàm một chiều có cửa sập (*trapdoor one-way functions*). Đây là các phép toán dễ thực hiện theo một chiều, nhưng rất khó đảo ngược nếu không biết thông tin bí mật.

Trong chữ ký số, khóa bí mật được dùng để tạo chữ ký. Khóa công khai được dùng để xác minh chữ ký. Nhờ vậy, một người có thể chứng minh rằng mình sở hữu khóa bí mật mà không cần tiết lộ khóa đó.

Trong Bitcoin, điều này có ý nghĩa rất quan trọng. Người dùng không cần “đăng nhập” vào một hệ thống trung tâm. Thay vào đó, họ chứng minh quyền chi tiêu Bitcoin bằng cách tạo chữ ký hợp lệ cho giao dịch.

### 2.2. RSA và ElGamal

RSA và ElGamal là hai hệ mật quan trọng trước khi ECC trở nên phổ biến.

**RSA** dựa trên bài toán phân tích thừa số nguyên tố. Việc nhân hai số nguyên tố lớn là dễ, nhưng phân tích tích của chúng trở lại hai số nguyên tố ban đầu là rất khó nếu số đủ lớn.

**ElGamal** dựa trên bài toán logarit rời rạc. Cho một số $g$, một số mũ bí mật $a$, việc tính:

$$
g^a \pmod p
$$

là dễ. Nhưng nếu chỉ biết $g$, $p$, và $g^a \pmod p$, việc tìm lại $a$ là rất khó.

ECC có thể được xem là một bước phát triển tiếp theo của tư tưởng này. Thay vì sử dụng phép nhân modulo thông thường, ECC sử dụng phép cộng điểm trên đường cong Elliptic. Bài toán khó tương ứng là tìm số nguyên $d$ khi biết:

$$
Q = dG
$$

Trong đó:

- $G$ là điểm sinh.
- $d$ là khóa bí mật.
- $Q$ là khóa công khai.

Bài toán tìm $d$ từ $G$ và $Q$ được gọi là **Elliptic Curve Discrete Logarithm Problem** — ECDLP.

### 2.3. Trường hữu hạn và số học modulo

ECC trong thực tế không làm việc trên mặt phẳng số thực liên tục, mà làm việc trên trường hữu hạn. Trong dự án này, trường hữu hạn được ký hiệu là:

$$
\mathbb{F}_p
$$

với $p$ là một số nguyên tố.

Các phép toán cộng, trừ, nhân, chia đều được thực hiện theo modulo $p$.

Ví dụ:

$$
17 + 9 \equiv 3 \pmod{23}
$$

vì:

$$
17 + 9 = 26
$$

và:

$$
26 \bmod 23 = 3
$$

Một khái niệm quan trọng là **nghịch đảo modulo**. Với một số $a$, nghịch đảo modulo của $a$ theo $p$ là số $x$ sao cho:

$$
ax \equiv 1 \pmod p
$$

Trong dự án, hàm `mod_inv(a, p)` được dùng để tính nghịch đảo modulo bằng thuật toán Euclid mở rộng.

### 2.4. Đường cong Elliptic trên trường hữu hạn

Đường cong Elliptic trong dự án có dạng Weierstrass:

$$
E: y^2 = x^3 + ax + b \pmod p
$$

Tập các điểm $(x, y)$ thỏa mãn phương trình trên, kết hợp với một điểm đặc biệt gọi là **điểm vô cực** $O$, tạo thành một nhóm Abel dưới phép cộng điểm.

Các phép toán quan trọng gồm:

- Cộng hai điểm $P + Q$.
- Nhân đôi điểm $2P$.
- Nhân vô hướng $kP$.

Trong hình học trên số thực, phép cộng điểm có thể được hiểu như sau:

Nếu vẽ đường thẳng đi qua hai điểm $P$ và $Q$, đường thẳng này sẽ cắt đường cong tại điểm thứ ba. Lấy đối xứng điểm đó qua trục hoành, ta thu được điểm $P + Q$.

Trên trường hữu hạn, ta không còn hình ảnh đường cong mượt như trên số thực, nhưng công thức đại số vẫn giữ vai trò tương tự.

### 2.5. Nhân vô hướng và bài toán ECDLP

Phép nhân vô hướng là phép toán trung tâm của ECC:

$$
Q = dG
$$

Trong đó:

- $d$ là một số nguyên.
- $G$ là điểm sinh.
- $Q$ là kết quả của việc cộng $G$ với chính nó $d$ lần.

Nếu biết $d$ và $G$, việc tính $Q$ là dễ.

Nhưng nếu chỉ biết $G$ và $Q$, việc tìm lại $d$ là cực kỳ khó khi tham số đủ lớn.

Đây chính là nền tảng bảo mật của ECC.

Trong mã nguồn, phép nhân vô hướng được triển khai bằng thuật toán **Double-and-Add** trong hàm `scalar_mul()` thuộc file `src/ecc.py`.

Thay vì cộng $G$ lặp lại $d$ lần, Double-and-Add biểu diễn $d$ ở dạng nhị phân và xử lý từng bit. Nhờ đó, độ phức tạp giảm từ:

$$
O(d)
$$

xuống còn:

$$
O(\log d)
$$

### 2.6. Đường cong secp256k1 trong Bitcoin

Bitcoin sử dụng đường cong Elliptic `secp256k1`.

Đường cong này có dạng:

$$
y^2 = x^3 + 7
$$

trên một trường hữu hạn nguyên tố rất lớn. Theo chuẩn SEC 2, `secp256k1` được mô tả bằng bộ tham số gồm trường hữu hạn, hệ số đường cong, điểm sinh $G$, bậc nhóm $n$, và cofactor $h$.

Trong Bitcoin:

- Khóa bí mật $d$ là một số nguyên 256-bit.
- Khóa công khai $Q$ được tính bằng:

$$
Q = dG
$$

- Địa chỉ Bitcoin được tạo thông qua các bước băm và mã hóa từ khóa công khai.

Điểm quan trọng là: người dùng không cần tiết lộ khóa bí mật để chứng minh quyền sở hữu Bitcoin. Họ chỉ cần tạo chữ ký số hợp lệ cho giao dịch.

Tài liệu Bitcoin Developer Guide mô tả giao dịch Bitcoin sử dụng chữ ký `secp256k1` theo công thức ECDSA để kết hợp dữ liệu giao dịch với khóa bí mật, qua đó cho phép kiểm tra rằng người ký sở hữu khóa bí mật tương ứng với khóa công khai.

### 2.7. Thuật toán chữ ký số ECDSA

ECDSA gồm ba giai đoạn chính:

1. Sinh khóa.
2. Ký thông điệp.
3. Xác minh chữ ký.

#### 2.7.1. Sinh khóa

Chọn khóa bí mật:

$$
d \in [1, n - 1]
$$

Tính khóa công khai:

$$
Q = dG
$$

Trong đó:

- $G$ là điểm sinh của đường cong.
- $n$ là bậc của điểm sinh $G$.

#### 2.7.2. Ký thông điệp

Giả sử thông điệp là $m$. Trước hết, ta tính giá trị băm:

$$
h = H(m)
$$

Sau đó chọn nonce ngẫu nhiên:

$$
k \in [1, n - 1]
$$

Tính điểm:

$$
R = kG
$$

Lấy hoành độ của điểm $R$:

$$
r = x_R \pmod n
$$

Tiếp theo tính:

$$
s = k^{-1}(h + dr) \pmod n
$$

Chữ ký cuối cùng là cặp:

$$
(r, s)
$$

#### 2.7.3. Xác minh chữ ký

Người xác minh biết:

- Thông điệp $m$.
- Chữ ký $(r, s)$.
- Khóa công khai $Q$.

Tính giá trị băm:

$$
h = H(m)
$$

Tính nghịch đảo của $s$:

$$
w = s^{-1} \pmod n
$$

Tính hai hệ số:

$$
u_1 = hw \pmod n
$$

$$
u_2 = rw \pmod n
$$

Sau đó tính điểm:

$$
X = u_1G + u_2Q
$$

Chữ ký được chấp nhận nếu:

$$
x_X \pmod n = r
$$

#### 2.7.4. Trực giác của ECDSA

Có thể hiểu đơn giản như sau:

- Khóa bí mật $d$ là quyền sở hữu thật sự.
- Nonce $k$ là yếu tố ngẫu nhiên dùng một lần.
- Giá trị $r$ được tạo từ $kG$, giống như một “dấu vết công khai” của nonce.
- Giá trị $s$ liên kết thông điệp, khóa bí mật và nonce lại với nhau.

Nếu chữ ký hợp lệ, người xác minh tin rằng chữ ký đó chỉ có thể được tạo bởi người sở hữu khóa bí mật tương ứng.

Trong dự án, quy trình này được triển khai trong hai hàm:

```python
sign(params, d, msg)
verify(params, Q, msg, sig)
```

thuộc file:

```text
src/ecdsa_toy.py
```

### 2.8. Vai trò của nonce trong ECDSA

Nonce $k$ là yếu tố cực kỳ nhạy cảm trong ECDSA.

Điều kiện bắt buộc:

- $k$ phải bí mật.
- $k$ phải khác nhau cho mỗi chữ ký.
- $k$ không được bị dự đoán.
- $k$ không được tái sử dụng.

Nếu cùng một nonce $k$ được dùng để ký hai thông điệp khác nhau bằng cùng một khóa bí mật, khóa bí mật có thể bị khôi phục.

Giả sử có hai chữ ký:

$$
(r, s_1)
$$

và:

$$
(r, s_2)
$$

cùng dùng một nonce $k$.

Từ công thức ký:

$$
s = k^{-1}(h + dr) \pmod n
$$

suy ra:

$$
ks = h + dr \pmod n
$$

Với hai thông điệp khác nhau:

$$
ks_1 = h_1 + dr \pmod n
$$

$$
ks_2 = h_2 + dr \pmod n
$$

Trừ hai phương trình:

$$
k(s_1 - s_2) = h_1 - h_2 \pmod n
$$

Do đó:

$$
k = (h_1 - h_2)(s_1 - s_2)^{-1} \pmod n
$$

Sau khi tìm được $k$, khóa bí mật $d$ được tính bằng:

$$
d = (s_1k - h_1)r^{-1} \pmod n
$$

Đây là một lỗi triển khai nghiêm trọng. Dù bản thân ECDSA an toàn về mặt lý thuyết, chỉ một sai sót trong sinh nonce cũng có thể phá vỡ toàn bộ hệ thống.

RFC 6979 đề xuất cách sinh chữ ký DSA/ECDSA xác định. Theo hướng này, nonce được tạo theo cách deterministic từ khóa bí mật và thông điệp, giúp tránh việc phụ thuộc hoàn toàn vào bộ sinh số ngẫu nhiên bên ngoài.

### 2.9. Shamir's trick

Trong bước xác minh ECDSA, ta cần tính:

$$
X = u_1G + u_2Q
$$

Cách ngây thơ là tính riêng:

$$
u_1G
$$

và:

$$
u_2Q
$$

sau đó cộng hai kết quả.

Shamir's trick tối ưu bước này bằng cách xử lý hai phép nhân vô hướng cùng lúc. Thay vì quét bit của $u_1$ và $u_2$ riêng biệt, thuật toán quét đồng thời từng cặp bit.

Nhờ đó, số phép nhân đôi điểm có thể giảm đáng kể.

Trong dự án, Shamir's trick được triển khai trong file:

```text
src/shamir.py
```

với hai phương pháp để so sánh:

```python
naive_mul_add
shamir_mul
```

---

## 3. Phương pháp triển khai

### 3.1. Tổng quan kiến trúc dự án

Dự án được tổ chức theo hướng module hóa. Mỗi thành phần phụ trách một lớp logic riêng, từ số học cơ bản đến thuật toán chữ ký số và benchmark thực nghiệm.

Cấu trúc thư mục chính:

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
└── tests/
```

Ý nghĩa từng thư mục:

- `src/`: chứa mã nguồn lõi của dự án.
- `openssl_demo/`: chứa các script thực nghiệm với OpenSSL.
- `results/`: lưu kết quả benchmark.
- `tests/`: chứa unit test kiểm tra tính đúng đắn của chương trình.

### 3.2. Module `field.py`

File `field.py` phụ trách số học trên trường hữu hạn.

Các hàm chính gồm:

```python
egcd(a, b)
mod_inv(a, p)
mod_div(a, b, p)
```

Trong đó:

- `egcd()` dùng thuật toán Euclid mở rộng.
- `mod_inv()` tính nghịch đảo modulo.
- `mod_div()` thực hiện phép chia modulo thông qua nghịch đảo modulo.

Đây là tầng toán học cơ bản nhất của toàn bộ dự án. Nếu số học modulo sai, các phép toán ECC phía trên cũng sẽ sai.

### 3.3. Module `ecc.py`

File `ecc.py` triển khai hai lớp chính:

```python
Point
Curve
```

Lớp `Point` biểu diễn một điểm trên đường cong Elliptic.

Lớp `Curve` biểu diễn đường cong với các tham số:

```python
p, a, b
```

Các phép toán chính gồm:

- Kiểm tra một điểm có nằm trên đường cong hay không.
- Cộng hai điểm.
- Nhân đôi điểm.
- Nhân vô hướng bằng Double-and-Add.

Phép nhân vô hướng là phép toán quan trọng nhất vì nó được dùng trong cả sinh khóa, ký và xác minh chữ ký.

### 3.4. Module `ecdsa_toy.py`

File `ecdsa_toy.py` triển khai ECDSA trên một đường cong nhỏ.

Mục tiêu của toy curve không phải là bảo mật thật, mà là giúp quan sát thuật toán một cách dễ hiểu.

Module này gồm các chức năng:

- Sinh khóa bí mật và khóa công khai.
- Ký thông điệp.
- Xác minh chữ ký.
- Kiểm tra chữ ký sai khi thông điệp bị thay đổi.

Việc sử dụng toy curve giúp người học có thể kiểm tra từng phép toán bằng tay hoặc bằng log chương trình.

Lưu ý: toy curve hiện tại dùng các tham số nhỏ:

$$
p = 17,\quad a = 3,\quad b = 5
$$

với điểm sinh:

$$
G = (1, 3),\quad n = 23
$$

chỉ dùng cho mô phỏng giáo dục, không có giá trị bảo mật thực tế.

### 3.5. Module `nonce_attack.py`

File `nonce_attack.py` minh họa tấn công khôi phục khóa bí mật khi ECDSA tái sử dụng nonce.

Module này thực hiện các bước:

1. Tạo hai thông điệp khác nhau.
2. Ký hai thông điệp bằng cùng một khóa bí mật và cùng nonce $k$.
3. Thu được hai chữ ký có cùng giá trị $r$.
4. Áp dụng công thức toán học để khôi phục $k$.
5. Từ $k$, khôi phục khóa bí mật $d$.

Đây là phần quan trọng nhất về mặt bảo mật triển khai, vì nó cho thấy chỉ một lỗi nhỏ trong quá trình sinh nonce cũng có thể dẫn đến mất khóa bí mật.

### 3.6. Module `shamir.py`

File `shamir.py` so sánh hai cách tính:

$$
u_1G + u_2Q
$$

Cách thứ nhất là phương pháp ngây thơ:

```python
naive_mul_add
```

Cách thứ hai sử dụng Shamir's trick:

```python
shamir_mul
```

Module có bộ đếm số phép toán để so sánh:

- Số phép cộng điểm.
- Số phép nhân đôi điểm.

Kết quả cho thấy Shamir's trick có thể giảm số phép toán, đặc biệt là số phép nhân đôi điểm.

### 3.7. Thực nghiệm với OpenSSL

Phần `openssl_demo/` sử dụng các script PowerShell để gọi OpenSSL.

Các thao tác chính gồm:

- Sinh khóa ECC.
- Ký file văn bản.
- Xác minh chữ ký.
- Thử xác minh thất bại khi nội dung bị sửa.
- Benchmark RSA và ECDSA.

OpenSSL cung cấp các hàm ký và xác minh ECDSA. Trong đó, `ECDSA_verify()` dùng để kiểm tra chữ ký ECDSA trên giá trị băm của thông điệp bằng khóa công khai tương ứng.

---

## 4. Kết quả thực nghiệm

### 4.1. Kết quả số học trường hữu hạn

Các hàm trong `field.py` xử lý đúng các phép toán modulo cơ bản.

Một số kết quả kiểm thử:

- Tính đúng ước chung lớn nhất mở rộng.
- Tính đúng nghịch đảo modulo khi tồn tại.
- Báo lỗi khi nghịch đảo modulo không tồn tại.
- Thực hiện phép chia modulo thông qua phép nhân với nghịch đảo.

Điều này đảm bảo tầng toán học nền tảng hoạt động ổn định.

### 4.2. Kết quả mô phỏng ECC

Các phép toán trên đường cong Elliptic cho kết quả nhất quán.

Các chức năng đã được kiểm tra:

- Điểm hợp lệ thuộc đường cong.
- Điểm không hợp lệ bị loại.
- Cộng hai điểm.
- Nhân đôi điểm.
- Nhân vô hướng bằng Double-and-Add.

Kết quả cho thấy Double-and-Add giúp giảm đáng kể số bước tính toán so với cộng lặp trực tiếp.

### 4.3. Kết quả ký và xác minh ECDSA

Quy trình ký và xác minh hoạt động đúng trên toy curve.

Quan sát chính:

- Chữ ký hợp lệ được xác minh thành công.
- Nếu thay đổi thông điệp, chữ ký bị từ chối.
- Nếu thay đổi chữ ký, quá trình xác minh thất bại.
- Khóa công khai sai không thể xác minh chữ ký hợp lệ.

Kết quả này minh họa hai tính chất quan trọng của chữ ký số:

- **Tính xác thực**: chữ ký gắn với người sở hữu khóa bí mật.
- **Tính toàn vẹn**: nội dung bị sửa sẽ làm chữ ký không còn hợp lệ.

### 4.4. Kết quả tấn công reused nonce

Kịch bản thực nghiệm sử dụng cùng nonce:

$$
k = 4
$$

để ký hai thông điệp khác nhau.

Kết quả thu được:

```text
Original Private Key (d): 2
Reused Nonce (k): 4
Recovered Nonce (k): 4
Recovered Private Key (d): 2
SUCCESS: Private key recovered successfully!
```

Kết quả này xác nhận công thức tấn công là đúng. Khi cùng một nonce được dùng lại, khóa bí mật có thể bị khôi phục hoàn toàn.

Bài học rút ra:

> Trong ECDSA, nonce không phải chi tiết phụ. Nonce là một phần sống còn của bảo mật.

### 4.5. Kết quả Shamir's trick

Với ví dụ:

$$
u_1 = 13
$$

và:

$$
u_2 = 19
$$

kết quả so sánh như sau:

| Phương pháp | Số phép cộng điểm | Số phép nhân đôi điểm |
|---|---:|---:|
| Naive | 5 | 9 |
| Shamir's trick | 4 | 5 |

Nhận xét:

- Shamir's trick giảm 1 phép cộng điểm.
- Shamir's trick giảm 4 phép nhân đôi điểm.
- Số phép nhân đôi giảm từ 9 xuống 5, tức giảm hơn 40% trong ví dụ này.

Với các đường cong thực tế có kích thước 256-bit, tối ưu kiểu này có ý nghĩa lớn hơn nhiều so với toy example.

### 4.6. Kết quả thực nghiệm OpenSSL

Dự án đã sử dụng OpenSSL để thực hiện các thao tác:

- Sinh khóa ECC.
- Ký thông điệp.
- Xác minh chữ ký.
- Kiểm tra xác minh thất bại khi thông điệp bị sửa.

Kết quả cho thấy chữ ký hợp lệ được OpenSSL xác minh thành công. Khi nội dung thông điệp bị thay đổi, quá trình xác minh thất bại.

Điều này cho thấy mô phỏng Python trong dự án có sự tương ứng về mặt nguyên lý với các công cụ mật mã tiêu chuẩn.

### 4.7. Benchmark RSA và ECDSA

Kết quả benchmark từ `openssl speed`:

| Thuật toán | Ký mỗi giây | Xác minh mỗi giây |
|---|---:|---:|
| RSA 2048-bit | 1539.1 | 45198.2 |
| RSA 3072-bit | 452.9 | 22683.2 |
| ECDSA 256-bit, NIST P-256 | 33256.1 | 12769.3 |

Nhận xét:

- ECDSA 256-bit ký nhanh hơn RSA 3072-bit rất nhiều.
- RSA xác minh nhanh hơn ECDSA trong benchmark này, chủ yếu do RSA thường dùng số mũ công khai nhỏ.
- ECDSA có lợi thế lớn về kích thước khóa và kích thước chữ ký.
- Trong hệ thống như Bitcoin, chữ ký nhỏ gọn giúp giảm chi phí lưu trữ và truyền tải.

Lưu ý: benchmark trên sử dụng ECDSA P-256 để so sánh hiệu năng ECC 256-bit nói chung. Bitcoin sử dụng `secp256k1`, nên kết quả này không nên hiểu là benchmark trực tiếp của Bitcoin, mà là minh họa cho ưu thế hiệu năng của ECC so với RSA ở cùng mức bảo mật tương đương.

---

## 5. Bàn luận

### 5.1. Vì sao ECC là bước tiến sau RSA và ElGamal?

ECC là bước tiến hợp lý vì nó giữ lại tinh thần của mật mã khóa công khai nhưng thay đổi cấu trúc toán học nền tảng.

RSA dựa trên bài toán phân tích thừa số.

ElGamal dựa trên bài toán logarit rời rạc trong trường hữu hạn.

ECC dựa trên bài toán logarit rời rạc trên đường cong Elliptic.

Điểm mạnh của ECC là với kích thước khóa nhỏ hơn, nó vẫn đạt mức bảo mật cao. Điều này giúp giảm chi phí lưu trữ, truyền tải và xử lý.

Trong môi trường blockchain, nơi dữ liệu giao dịch được lưu trữ lâu dài và được nhân bản trên rất nhiều node, việc giảm kích thước chữ ký có ý nghĩa thực tế rất lớn.

### 5.2. Vì sao Bitcoin dùng ECDSA?

Bitcoin không cần mã hóa nội dung giao dịch, vì giao dịch trên blockchain là công khai.

Điều Bitcoin cần là:

- Xác minh người gửi có quyền chi tiêu.
- Đảm bảo giao dịch không bị sửa đổi.
- Cho phép mọi node kiểm tra chữ ký mà không cần tin tưởng bên thứ ba.

ECDSA đáp ứng đúng yêu cầu này.

Người dùng ký giao dịch bằng khóa bí mật. Các node xác minh chữ ký bằng khóa công khai. Nếu chữ ký hợp lệ, mạng lưới có cơ sở để tin rằng giao dịch được tạo bởi người sở hữu khóa bí mật tương ứng.

### 5.3. Bài học từ lỗi tái sử dụng nonce

Phần reused nonce attack là minh chứng rõ nhất cho câu nói:

> Mật mã học không chỉ khó ở thuật toán, mà còn khó ở triển khai.

ECDSA có thể an toàn về mặt toán học. Nhưng nếu nonce bị dùng lại, khóa bí mật có thể bị khôi phục trực tiếp bằng đại số modulo.

Điều này cho thấy:

- Bộ sinh số ngẫu nhiên phải đáng tin cậy.
- Nonce phải được quản lý cực kỳ nghiêm ngặt.
- Các triển khai hiện đại nên dùng cơ chế sinh nonce an toàn, ví dụ deterministic ECDSA theo RFC 6979.

### 5.4. Ý nghĩa của Shamir's trick

Shamir's trick cho thấy tối ưu thuật toán không chỉ nằm ở việc viết code nhanh hơn, mà nằm ở việc hiểu cấu trúc toán học của bài toán.

Thay vì tính hai phép nhân vô hướng riêng biệt, ta kết hợp chúng lại trong một quá trình quét bit chung.

Điều này giúp giảm số phép toán, đặc biệt là phép nhân đôi điểm — một thao tác xuất hiện rất nhiều trong ECC.

Trong các hệ thống cần xác minh nhiều chữ ký, những tối ưu như vậy có thể góp phần cải thiện hiệu năng tổng thể.

### 5.5. Giới hạn của dự án

Dự án có một số giới hạn:

- Toy curve không có giá trị bảo mật thật.
- Python không phù hợp để benchmark mật mã hiệu năng cao.
- Chưa xử lý các tấn công kênh kề như timing attack hoặc side-channel attack.
- Chưa triển khai đầy đủ chuẩn chữ ký Bitcoin.
- Chưa mô phỏng các cơ chế encoding chữ ký, transaction digest và script verification của Bitcoin ở mức đầy đủ.

Tuy nhiên, với mục tiêu giáo dục, dự án đã làm rõ được các nguyên lý cốt lõi của ECC và ECDSA.

---

## 6. Kết luận

Dự án đã nghiên cứu và mô phỏng thành công các thành phần cốt lõi của mật mã đường cong Elliptic và chữ ký số ECDSA.

Từ tầng thấp nhất là số học modulo, dự án xây dựng dần lên các phép toán trên đường cong Elliptic, sau đó triển khai sinh khóa, ký, xác minh chữ ký, tấn công reused nonce và tối ưu Shamir's trick.

Kết quả cho thấy ECC/ECDSA có nhiều ưu điểm quan trọng:

- Kích thước khóa nhỏ.
- Chữ ký gọn.
- Mức bảo mật cao.
- Phù hợp với các hệ thống phân tán như Bitcoin.

Tuy nhiên, dự án cũng chỉ ra rằng một thuật toán mạnh không tự động tạo ra một hệ thống an toàn. Nếu triển khai sai, đặc biệt ở bước sinh nonce, toàn bộ khóa bí mật có thể bị lộ.

Vì vậy, bài học lớn nhất của dự án là:

> Trong mật mã học, lý thuyết đúng mới chỉ là điều kiện cần. Triển khai đúng mới là điều kiện sống còn.

Dự án là nền tảng tốt để tiếp tục tìm hiểu sâu hơn về blockchain, chữ ký số, bảo mật hệ thống, ví tiền mã hóa, và các hướng mật mã hiện đại như Schnorr signature, threshold signature, zero-knowledge proof và mật mã hậu lượng tử.

---

## 7. Tài liệu tham khảo

[1] Neal Koblitz, “Elliptic Curve Cryptosystems”, *Mathematics of Computation*, 1987.

[2] Victor S. Miller, “Use of Elliptic Curves in Cryptography”, *CRYPTO*, 1985.

[3] Standards for Efficient Cryptography Group, “SEC 2: Recommended Elliptic Curve Domain Parameters”, Version 2.0, 2010.

[4] Thomas Pornin, “RFC 6979: Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature Algorithm (ECDSA)”, IETF, 2013.

[5] Joppe W. Bos et al., “Elliptic Curve Cryptography in Practice”, 2014.

[6] Joachim Breitner and Nadia Heninger, “Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies”, 2013.

[7] Bitcoin Developer Documentation, “Transactions: ECDSA and secp256k1 signatures”.

[8] OpenSSL Documentation, “ECDSA_sign and ECDSA_verify”.

[9] Vipul Gupta et al., “Performance Analysis of Elliptic Curve Cryptography for SSL”, 2002.

[10] Bài giảng MI4100, “Mật mã khóa công khai”, Đại học Bách Khoa Hà Nội.

---

# Phụ lục A. Hướng dẫn chạy mô phỏng

## A.1. Khởi tạo môi trường

Chạy các lệnh sau trong PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "."
```

## A.2. Chạy toàn bộ kiểm thử

```powershell
pytest tests/
```

## A.3. Chạy demo tấn công reused nonce

```powershell
python src/nonce_attack.py
```

## A.4. Chạy demo Shamir's trick

```powershell
python src/shamir.py
```

## A.5. Chạy demo OpenSSL

```powershell
cd openssl_demo
.\gen_keys.ps1
.\sign_verify.ps1
.\benchmark.ps1
```

---

# Phụ lục B. Cấu trúc mã nguồn

## B.1. `src/field.py`

Chứa các hàm số học trên trường hữu hạn:

- Euclid mở rộng.
- Nghịch đảo modulo.
- Phép chia modulo.

## B.2. `src/ecc.py`

Triển khai:

- Lớp `Point`.
- Lớp `Curve`.
- Cộng điểm.
- Nhân đôi điểm.
- Nhân vô hướng bằng Double-and-Add.

## B.3. `src/ecdsa_toy.py`

Triển khai ECDSA trên toy curve:

- Sinh khóa.
- Ký thông điệp.
- Xác minh chữ ký.

## B.4. `src/nonce_attack.py`

Triển khai mô phỏng tấn công khi nonce bị tái sử dụng:

- Khôi phục nonce.
- Khôi phục khóa bí mật.

## B.5. `src/shamir.py`

Triển khai và so sánh:

- Phương pháp tính ngây thơ `naive_mul_add`.
- Phương pháp tối ưu `shamir_mul`.

## B.6. `tests/`

Chứa các unit test kiểm tra:

- Số học modulo.
- Phép toán ECC.
- Quy trình ECDSA.
- Tấn công reused nonce.
- Shamir's trick.

## B.7. `openssl_demo/`

Chứa các script PowerShell phục vụ thực nghiệm:

- Sinh khóa.
- Ký và xác minh.
- Benchmark RSA/ECDSA.
