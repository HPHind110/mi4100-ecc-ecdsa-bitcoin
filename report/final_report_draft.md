# BÁO CÁO TỔNG HỢP DỰ ÁN

# Mật mã đường cong Elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin

**Môn học:** MI4100 — Mật mã và độ phức tạp thuật toán  
**Tính chất dự án:** mô phỏng giáo dục, không phải ví Bitcoin thật, không phải phần mềm giao dịch thật  
**Luận điểm trung tâm:** Bitcoin không dùng ECC/ECDSA để mã hóa giao dịch; Bitcoin dùng chữ ký số để xác thực quyền chi tiêu đối với UTXO.

---

## Tóm tắt

Dự án nghiên cứu và mô phỏng mối liên hệ giữa **mật mã đường cong elliptic** (*Elliptic Curve Cryptography* — ECC), bài toán **logarit rời rạc trên đường cong elliptic** (*Elliptic Curve Discrete Logarithm Problem* — ECDLP), thuật toán chữ ký số **ECDSA** (*Elliptic Curve Digital Signature Algorithm*) và cơ chế xác thực giao dịch trong Bitcoin.

Thay vì trình bày ECC như một tập công thức tách rời, dự án được xây dựng theo hướng đặt vấn đề từ ứng dụng: trong một hệ thống tiền điện tử không có ngân hàng trung tâm, làm thế nào để một người chứng minh mình có quyền tiêu một khoản tiền số mà không cần tiết lộ khóa bí mật? Bitcoin giải quyết phần xác thực quyền chi tiêu bằng chữ ký số. Trong mô hình P2PKH truyền thống, một UTXO được khóa bởi điều kiện liên quan đến mã băm của khóa công khai, còn người tiêu UTXO phải cung cấp khóa công khai và chữ ký hợp lệ để chứng minh quyền sở hữu.

Từ bài toán đó, dự án đi xuống các tầng mật mã phía dưới. ECC cung cấp quan hệ một chiều:

```text
Q = dG
```

trong đó `d` là khóa bí mật, `G` là điểm sinh trên đường cong elliptic, và `Q` là khóa công khai. Việc tính `Q` từ `d` là nhanh, nhưng việc tìm lại `d` từ `G` và `Q` là bài toán ECDLP, được xem là không khả thi với các tham số thực tế như `secp256k1`. ECDSA sử dụng cặp khóa `(d, Q)` để tạo và kiểm tra chữ ký. Bitcoin dùng chữ ký đó để xác thực quyền tiêu UTXO.

Dự án hiện thực các ý tưởng trên bằng Python và Streamlit. Hệ thống bao gồm: số học modulo, phép toán trên đường cong elliptic, sinh khóa, ký và xác minh ECDSA, mô phỏng mini Bitcoin transaction/UTXO, minh họa tấn công khi tái sử dụng nonce, ghi chú phòng thủ nonce, tối ưu hóa bước xác minh bằng Shamir's trick, và demo OpenSSL trên `secp256k1`.

Kết luận quan trọng của dự án là: **bảo mật mật mã không chỉ phụ thuộc vào độ khó toán học của bài toán nền, mà còn phụ thuộc mạnh vào việc triển khai đúng**. Với ECDSA, chỉ một lỗi như tái sử dụng nonce `k` có thể làm lộ hoàn toàn khóa bí mật, dù bản thân ECDLP trên đường cong thật vẫn rất khó.

---

## Từ khóa

ECC, ECDSA, ECDLP, Bitcoin, UTXO, secp256k1, chữ ký số, nonce reuse, Shamir's trick, mật mã khóa công khai, độ phức tạp thuật toán.

---

# 1. Giới thiệu

## 1.1. Bối cảnh

Mật mã khóa công khai ra đời để giải quyết những vấn đề mà mật mã khóa bí mật truyền thống không xử lý tốt trong môi trường mở. Với mật mã đối xứng, hai bên muốn liên lạc an toàn phải chia sẻ trước một khóa bí mật. Điều này tạo ra bài toán phân phối khóa: làm sao truyền khóa bí mật trong khi kênh truyền ban đầu chưa an toàn?

Mật mã khóa công khai thay đổi cách tiếp cận. Mỗi người có một cặp khóa:

- **Khóa bí mật** (*private key*): chỉ chủ sở hữu biết.
- **Khóa công khai** (*public key*): có thể công bố cho mọi người.

Trong hệ mã hóa công khai, khóa công khai có thể dùng để mã hóa hoặc thiết lập khóa phiên. Trong chữ ký số, khóa bí mật dùng để ký, còn khóa công khai dùng để xác minh. Nhờ đó, một người có thể chứng minh quyền sở hữu khóa bí mật mà không cần tiết lộ khóa đó.

Bitcoin là một ứng dụng điển hình của mật mã khóa công khai, nhưng điểm cần nhấn mạnh là: **Bitcoin không dùng ECC/ECDSA để che giấu nội dung giao dịch**. Giao dịch Bitcoin về cơ bản là dữ liệu công khai. Điều Bitcoin cần là một cơ chế để mọi node có thể kiểm tra:

```text
Người tạo giao dịch có quyền tiêu UTXO đang được tham chiếu hay không?
```

Trong mô hình UTXO, mỗi khoản tiền có thể tiêu được tồn tại dưới dạng một **Unspent Transaction Output**. Một giao dịch mới muốn tiêu UTXO cũ phải cung cấp dữ liệu thỏa mãn điều kiện khóa của UTXO đó. Với mô hình P2PKH truyền thống, dữ liệu mở khóa bao gồm khóa công khai và chữ ký số ECDSA hợp lệ.

Vì vậy, Bitcoin là một case study tự nhiên cho môn mật mã và độ phức tạp thuật toán: nó nối trực tiếp bài toán thực tế về quyền sở hữu tài sản số với các khái niệm mật mã như ECC, ECDLP, ECDSA, chữ ký số, độ khó tính toán và lỗi triển khai.

## 1.2. Vấn đề nghiên cứu

Dự án tập trung trả lời câu hỏi chính:

> ECC, ECDLP và ECDSA liên hệ với nhau như thế nào trong cơ chế xác thực quyền chi tiêu của Bitcoin, và những bài học mật mã/triển khai nào có thể rút ra từ trường hợp này?

Từ câu hỏi chính, báo cáo triển khai thành các câu hỏi nhỏ:

1. Bitcoin cần giải bài toán gì trong môi trường không có ngân hàng trung gian?
2. Quyền sở hữu trong Bitcoin được biểu diễn như thế nào qua mô hình UTXO?
3. ECC tạo khóa công khai từ khóa bí mật như thế nào?
4. Vì sao biết khóa công khai không suy ra được khóa bí mật?
5. ECDSA ký và xác minh chữ ký ra sao?
6. ECDSA đi vào transaction giống Bitcoin ở bước nào?
7. ECDSA có thể thất bại nếu triển khai sai nonce như thế nào?
8. Có thể tối ưu bước xác minh bằng kỹ thuật thuật toán nào?
9. Toy demo liên hệ với công cụ mật mã thật như OpenSSL ra sao?

## 1.3. Mục tiêu dự án

Dự án hướng tới các mục tiêu sau:

- Trình bày mạch ứng dụng: từ bài toán quyền chi tiêu trong Bitcoin đến chữ ký số ECDSA.
- Mô phỏng số học trường hữu hạn và phép toán trên đường cong elliptic.
- Giải thích quan hệ khóa `Q = dG` và bài toán ECDLP.
- Triển khai toy ECDSA để ký và xác minh thông điệp.
- Mô phỏng một mô hình giao dịch Bitcoin đơn giản dựa trên UTXO.
- Cho thấy chữ ký không “bay lơ lửng” trên một thông điệp bất kỳ, mà dùng để mở khóa một UTXO cụ thể.
- Minh họa tấn công reused nonce trong ECDSA và khôi phục private key.
- Trình bày các nguyên tắc phòng thủ nonce, bao gồm ý tưởng deterministic ECDSA theo RFC 6979.
- So sánh cách xác minh ngây thơ với Shamir's trick.
- Liên hệ toy demo với công cụ thật bằng OpenSSL trên `secp256k1`.

## 1.4. Phạm vi và giới hạn

Dự án là mô phỏng giáo dục, không phải phần mềm bảo mật dùng trong sản xuất.

Dự án **có**:

- Toy curve nhỏ để minh họa ECC/ECDSA.
- Mini Bitcoin transaction/UTXO model theo hướng P2PKH-like educational demo.
- Demo tấn công reused nonce trên dữ liệu giả lập.
- Demo OpenSSL ký/xác minh message hoặc file bằng `secp256k1`.
- Streamlit app để trình bày các bước theo storyline.

Dự án **không có**:

- Ví Bitcoin thật.
- Quản lý seed phrase hoặc private key thật.
- Kết nối mạng Bitcoin.
- Broadcast transaction.
- Full Bitcoin Script interpreter.
- Full sighash consensus logic.
- Mempool, mining, block validation hoặc Proof-of-Work.
- Bảo vệ side-channel đầy đủ như một thư viện production.

Các tấn công trong dự án chỉ được áp dụng trên toy curve, toy key hoặc khóa tạm sinh local. Không có thao tác quét, đoán, nhập hoặc khôi phục khóa thật của người dùng.

---

# 2. Cơ sở lý thuyết

## 2.1. Mật mã khóa công khai và chữ ký số

Trong mật mã khóa công khai, mỗi người dùng có một cặp khóa liên hệ toán học với nhau. Một hướng tính toán là dễ, hướng ngược lại là khó nếu không có bí mật.

Với chữ ký số, quy trình cơ bản gồm:

```text
private key  →  sign(message)  →  signature
public key   →  verify(message, signature)  →  true/false
```

Chữ ký số cung cấp ba ý nghĩa quan trọng:

1. **Xác thực**: chữ ký hợp lệ cho thấy người ký sở hữu khóa bí mật tương ứng.
2. **Toàn vẹn**: nếu dữ liệu bị sửa sau khi ký, chữ ký thường không còn hợp lệ.
3. **Không cần tiết lộ bí mật**: người xác minh dùng khóa công khai, không cần biết private key.

Trong Bitcoin, chữ ký số không nhằm che giấu giao dịch. Nó nhằm chứng minh rằng người tạo transaction có quyền tiêu UTXO đang được tham chiếu.

## 2.2. Mã hóa và ký số khác nhau như thế nào?

Một nhầm lẫn thường gặp là xem ECC/ECDSA trong Bitcoin như cơ chế “mã hóa giao dịch”. Đây là cách hiểu sai.

| Khái niệm | Mục tiêu | Liên hệ với Bitcoin |
|---|---|---|
| Mã hóa | Che nội dung để người ngoài không đọc được | Không phải vai trò chính của ECC/ECDSA trong Bitcoin |
| Hash | Tạo dấu vân tay dữ liệu | Dùng trong txid, address, Merkle tree, transaction digest |
| Chữ ký số | Chứng minh quyền ký và bảo vệ dữ liệu khỏi bị sửa | Vai trò trung tâm trong xác thực quyền tiêu UTXO |
| ECC | Cấu trúc toán học để tạo khóa và primitive mật mã | Cung cấp quan hệ `Q = dG` |
| ECDLP | Bài toán khó bảo vệ khóa bí mật | Là giả định độ khó đứng sau ECC |
| ECDSA | Thuật toán chữ ký số dựa trên ECC | Dùng trong Bitcoin truyền thống để ký transaction |

Tóm lại:

```text
ECC không phải ECDSA.
ECDLP không phải ECDSA.
Bitcoin không dùng ECDSA để mã hóa.
Bitcoin dùng ECDSA để chứng minh quyền chi tiêu.
```

## 2.3. RSA, ElGamal và ECC

Các hệ mật khóa công khai cổ điển dựa trên những bài toán khó khác nhau.

**RSA** dựa trên độ khó của bài toán phân tích thừa số nguyên tố. Nhân hai số nguyên tố lớn là dễ, nhưng phân tích tích của chúng trở lại hai thừa số ban đầu là khó nếu kích thước đủ lớn.

**ElGamal** dựa trên bài toán logarit rời rạc trong nhóm nhân modulo. Cho:

```text
y = g^a mod p
```

việc tính `y` từ `a` là dễ, nhưng tìm lại `a` từ `g`, `p`, `y` là khó với tham số phù hợp.

**ECC** thay nhóm nhân modulo bằng nhóm các điểm trên đường cong elliptic. Thay vì:

```text
y = g^a mod p
```

ta có:

```text
Q = dG
```

Trong đó:

- `G` là điểm sinh.
- `d` là khóa bí mật.
- `Q` là khóa công khai.

Bài toán tìm `d` từ `G` và `Q` được gọi là ECDLP. Ưu điểm lớn của ECC là đạt mức an toàn tương đương với kích thước khóa nhỏ hơn nhiều so với các hệ dựa trên số nguyên lớn truyền thống.

## 2.4. Trường hữu hạn và số học modulo

ECC trong mật mã không làm việc trên đường cong liên tục của số thực, mà làm việc trên trường hữu hạn. Trong dự án, trường hữu hạn được ký hiệu:

\[
\mathbb{F}_p
\]

với `p` là số nguyên tố.

Các phép toán cộng, trừ, nhân, chia đều được thực hiện theo modulo `p`.

Ví dụ:

\[
17 + 9 \equiv 3 \pmod{23}
\]

vì:

\[
17 + 9 = 26,\quad 26 \bmod 23 = 3
\]

Một phép toán quan trọng là **nghịch đảo modulo**. Với số `a`, nghịch đảo modulo của `a` theo `p` là số `x` sao cho:

\[
ax \equiv 1 \pmod p
\]

Trong mã nguồn, `src/field.py` triển khai:

```python
egcd(a, b)
mod_inv(a, p)
mod_div(a, b, p)
```

Đây là nền tảng của mọi phép toán ECC phía trên. Nếu nghịch đảo modulo sai, cộng điểm, nhân điểm và ECDSA đều sai theo.

## 2.5. Đường cong elliptic trên trường hữu hạn

Dạng Weierstrass ngắn thường dùng trong demo là:

\[
E: y^2 \equiv x^3 + ax + b \pmod p
\]

Tập điểm của đường cong bao gồm:

- Các điểm `(x, y)` thỏa mãn phương trình.
- Một điểm đặc biệt gọi là **điểm vô cực** `O`.

Tập điểm này cùng với phép cộng điểm tạo thành một nhóm Abel. Điều này cho phép ta định nghĩa:

- Cộng hai điểm `P + Q`.
- Nhân đôi điểm `2P`.
- Nhân vô hướng `kP`.

Trên số thực, phép cộng điểm có trực giác hình học: đường thẳng đi qua hai điểm cắt đường cong tại điểm thứ ba, rồi lấy đối xứng qua trục hoành. Trên trường hữu hạn, không còn hình ảnh đường cong mượt, nhưng công thức đại số vẫn có ý nghĩa và tạo thành phép toán nhóm.

## 2.6. Nhân vô hướng và Double-and-Add

Phép toán trung tâm của ECC là nhân vô hướng:

\[
Q = dG
\]

Hiểu đơn giản, `dG` là cộng `G` với chính nó `d` lần:

\[
dG = \underbrace{G + G + \cdots + G}_{d\ \text{lần}}
\]

Cộng lặp trực tiếp có độ phức tạp tuyến tính theo `d`, tức:

\[
O(d)
\]

Nhưng trong thực tế, ta dùng thuật toán **Double-and-Add**. Ý tưởng là biểu diễn `d` ở dạng nhị phân, rồi duyệt từng bit để kết hợp phép nhân đôi điểm và cộng điểm. Nhờ đó độ phức tạp theo số bit của `d`:

\[
O(\log d)
\]

Trong dự án, phép nhân vô hướng được triển khai trong `src/ecc.py`.

## 2.7. ECDLP: bài toán khó bảo vệ private key

Bài toán ECDLP được phát biểu như sau:

```text
Given G and Q = dG, find d.
```

Nếu biết `d`, tính `Q = dG` là nhanh. Nhưng nếu chỉ biết `G` và `Q`, tìm lại `d` là khó với tham số đủ lớn.

Trong toy curve nhỏ, có thể brute force:

```text
1G, 2G, 3G, ...
```

cho đến khi tìm được `kG = Q`. Nhưng với `secp256k1`, không gian khóa quá lớn. Ngay cả các thuật toán tốt hơn brute force như Baby-step Giant-step hoặc Pollard rho vẫn có độ phức tạp cỡ căn bậc hai kích thước nhóm, tức vẫn không khả thi với tham số 256-bit trong mô hình máy tính cổ điển.

Dự án mô phỏng ba mức:

| Thuật toán | Ý tưởng | Độ phức tạp |
|---|---|---|
| Brute force | Thử từng `k` | `O(n)` thời gian |
| Baby-step Giant-step | Gặp nhau ở giữa | `O(√n)` thời gian và `O(√n)` bộ nhớ |
| Pollard rho | Random-walk tìm collision | `O(√n)` kỳ vọng, bộ nhớ thấp |

Các thuật toán này chỉ dùng để minh họa ECDLP trên toy curve, không dùng để tấn công `secp256k1` thật.

## 2.8. secp256k1 trong Bitcoin

Bitcoin truyền thống sử dụng ECDSA trên đường cong `secp256k1`. Đường cong này có dạng:

\[
y^2 = x^3 + 7
\]

trên một trường hữu hạn nguyên tố rất lớn. Bộ tham số `secp256k1` được định nghĩa trong SEC 2, bao gồm trường hữu hạn, hệ số đường cong, điểm sinh `G`, bậc nhóm `n` và cofactor `h`.

Trong Bitcoin:

- Private key là số 256-bit.
- Public key được tính bằng `Q = dG`.
- Address truyền thống liên quan đến mã băm của public key.
- Transaction spending sử dụng chữ ký để chứng minh quyền tiêu.

Điểm cần nhớ: public key có thể được công khai, nhưng private key vẫn được bảo vệ bởi độ khó ECDLP.

## 2.9. ECDSA: sinh khóa, ký và xác minh

### 2.9.1. Sinh khóa

Chọn private key:

\[
d \in [1, n - 1]
\]

Tính public key:

\[
Q = dG
\]

### 2.9.2. Ký thông điệp

Với thông điệp `m`, tính giá trị băm:

\[
h = H(m)
\]

Chọn nonce bí mật dùng một lần:

\[
k \in [1, n - 1]
\]

Tính:

\[
R = kG
\]

Lấy:

\[
r = x_R \bmod n
\]

Tính:

\[
s = k^{-1}(h + dr) \bmod n
\]

Chữ ký là:

\[
(r, s)
\]

### 2.9.3. Xác minh chữ ký

Người xác minh biết thông điệp `m`, chữ ký `(r, s)` và public key `Q`.

Tính:

\[
h = H(m)
\]

\[
w = s^{-1} \bmod n
\]

\[
u_1 = hw \bmod n
\]

\[
u_2 = rw \bmod n
\]

Tính điểm:

\[
X = u_1G + u_2Q
\]

Chữ ký hợp lệ nếu:

\[
x_X \bmod n = r
\]

### 2.9.4. Trực giác

ECDSA có thể được hiểu như sau:

- `d` là bí mật dài hạn.
- `Q = dG` là định danh công khai.
- `k` là bí mật tạm thời cho mỗi chữ ký.
- `r` liên quan đến điểm `kG`.
- `s` trộn message hash, private key và nonce.

Người xác minh không biết `d` và không biết `k`, nhưng vẫn kiểm tra được sự nhất quán toán học giữa chữ ký, thông điệp và public key.

## 2.10. ECDSA trong transaction Bitcoin

Trong Bitcoin, chữ ký ECDSA không chỉ chứng minh “tôi biết private key”. Nó còn gắn với dữ liệu transaction cụ thể.

Với mô hình P2PKH truyền thống:

```text
locking condition  ≈  PubKeyHash
unlocking data     ≈  Signature + PublicKey
verification       ≈  hash(PublicKey) matches PubKeyHash
                       and signature verifies
```

Một output được khóa bởi điều kiện chi tiêu. Muốn tiêu output đó, input của transaction mới phải tham chiếu đúng output cũ bằng `txid` và `vout`, rồi cung cấp dữ liệu mở khóa. Bitcoin Developer Guide mô tả rằng P2PKH script điển hình dùng:

```text
OP_DUP OP_HASH160 <PubKeyHash> OP_EQUALVERIFY OP_CHECKSIG
```

Trong dự án, ta không triển khai đầy đủ Bitcoin Script. Thay vào đó, `src/bitcoin_tx.py` mô phỏng logic giáo dục:

```text
UTXO exists?
UTXO unspent?
hash(public_key) == locking_pubkey_hash?
ECDSA signature verifies over unsigned transaction data?
```

Nếu tất cả đúng, toy node chấp nhận transaction. Nếu một điều kiện sai, transaction bị từ chối.

## 2.11. Reused nonce attack trong ECDSA

Nonce `k` trong ECDSA là giá trị cực kỳ nhạy cảm. Nó phải:

- Bí mật.
- Khác nhau cho mỗi chữ ký.
- Không bị dự đoán.
- Không bị rò rỉ.

Nếu cùng một `k` được dùng để ký hai thông điệp khác nhau bằng cùng private key, ta có hai chữ ký:

\[
(r, s_1),\quad (r, s_2)
\]

với cùng `r`.

Từ công thức:

\[
s = k^{-1}(h + dr) \bmod n
\]

suy ra:

\[
ks = h + dr \bmod n
\]

Với hai thông điệp:

\[
ks_1 = h_1 + dr \bmod n
\]

\[
ks_2 = h_2 + dr \bmod n
\]

Trừ hai phương trình:

\[
k(s_1 - s_2) = h_1 - h_2 \bmod n
\]

Do đó:

\[
k = (h_1 - h_2)(s_1 - s_2)^{-1} \bmod n
\]

Sau khi có `k`, private key được khôi phục bằng:

\[
d = (s_1k - h_1)r^{-1} \bmod n
\]

Đây là điểm rất quan trọng: trong kịch bản này attacker không cần giải ECDLP. Private key bị lộ do lỗi triển khai nonce.

RFC 6979 đề xuất cách sinh nonce xác định cho DSA/ECDSA từ private key và message, nhằm giảm phụ thuộc vào bộ sinh số ngẫu nhiên bên ngoài.

## 2.12. Shamir's trick

Trong bước xác minh ECDSA, cần tính:

\[
X = u_1G + u_2Q
\]

Cách ngây thơ là tính riêng `u1G`, tính riêng `u2Q`, rồi cộng lại. Shamir's trick tối ưu bằng cách xử lý hai phép nhân vô hướng cùng lúc, quét bit của `u1` và `u2` song song.

Ý nghĩa:

- Giảm số phép nhân đôi điểm.
- Giảm chi phí tính `u1G + u2Q`.
- Phù hợp khi cần xác minh nhiều chữ ký.

Trong dự án, Shamir's trick là phần bonus thuật toán. Nó giúp nối nội dung mật mã với phân tích độ phức tạp và tối ưu hiệu năng.

---

# 3. Thiết kế và triển khai hệ thống

## 3.1. Triết lý thiết kế

Dự án không được thiết kế như một thư viện mật mã production. Nó được thiết kế như một **phòng lab học thuật**. Vì vậy, tiêu chí quan trọng nhất không phải là tốc độ cao nhất, mà là:

- Dễ đọc.
- Dễ kiểm chứng.
- Dễ trình bày.
- Có cảnh báo rõ về giới hạn bảo mật.
- Giữ đúng tuyến câu chuyện ECC → ECDLP → ECDSA → Bitcoin transaction authentication.

Mã nguồn được chia thành các lớp:

```text
số học modulo
→ ECC point arithmetic
→ ECDSA toy
→ ECDLP toy attacks
→ Bitcoin-like transaction model
→ nonce attack
→ Shamir optimization
→ Streamlit visualization
→ OpenSSL practical demo
```

## 3.2. Cấu trúc mã nguồn

Cấu trúc quan trọng của repo:

```text
src/
  field.py
  ecc.py
  demo_params.py
  ecdsa_toy.py
  bitcoin_tx.py
  ecdlp_attacks.py
  nonce_attack.py
  shamir.py

tests/
  test_field.py
  test_ecc.py
  test_ecdsa.py
  test_bitcoin_tx.py
  test_ecdlp_attacks.py
  test_nonce_attack.py
  test_shamir.py

openssl_demo/
  gen_keys.ps1
  sign_verify.ps1
  benchmark.ps1

docs/
  APP_USAGE_GUIDE.md
  rfc6979_nonce_defense.md

app.py
README.md
PROJECT_PLAN.md
```

## 3.3. Tham số toy curve

Dự án dùng toy curve nhỏ để minh họa:

\[
p = 17,\quad a = 3,\quad b = 5
\]

\[
G = (1,3),\quad n = 23
\]

Ưu điểm của bộ tham số này là `n = 23` là số nguyên tố, nên các phép nghịch đảo modulo trong ECDSA sạch hơn so với các demo cũ dùng order hợp số. Tuy nhiên, curve này cực nhỏ và hoàn toàn không có giá trị bảo mật. Nó chỉ dùng để học.

Các tham số này được gom trong `src/demo_params.py` để tránh hard-code rải rác trong nhiều file.

## 3.4. Module `field.py`

`field.py` phụ trách số học modulo:

- `egcd(a, b)`: thuật toán Euclid mở rộng.
- `mod_inv(a, p)`: nghịch đảo modulo.
- `mod_div(a, b, p)`: chia modulo bằng cách nhân với nghịch đảo.

Đây là tầng nền. Các hàm này phải xử lý rõ trường hợp không tồn tại nghịch đảo, thay vì trả kết quả sai âm thầm.

## 3.5. Module `ecc.py`

`ecc.py` triển khai:

- Lớp `Point`.
- Lớp `Curve`.
- Kiểm tra điểm thuộc curve.
- Cộng điểm.
- Nhân đôi điểm.
- Nhân vô hướng bằng Double-and-Add.
- Bộ đếm phép toán để phục vụ demo Shamir.

Module này biến lý thuyết nhóm điểm trên đường cong thành các thao tác cụ thể trong code.

## 3.6. Module `ecdsa_toy.py`

`ecdsa_toy.py` triển khai:

- `keygen`
- `hash_message_to_int`
- `sign`
- `verify`

Mục tiêu là minh họa ECDSA ở mức dễ kiểm tra. Toy curve nhỏ cho phép quan sát các giá trị `r`, `s`, `h`, `Q`, nhưng đồng thời có thể tạo ra edge case do không gian modulo quá nhỏ. Vì vậy app có cảnh báo và có nút tạo message sửa chắc chắn bị từ chối khi demo tamper.

## 3.7. Module `bitcoin_tx.py`

Đây là module quan trọng nhất để nối ECDSA với Bitcoin.

Module mô phỏng các cấu trúc:

- `TxOutput`
- `OutPoint`
- `TxInput`
- `Transaction`
- `UTXOSet`

Các helper chính:

- `serialize_pubkey_demo(Q)`
- `hash160_demo(data)`
- `pubkey_hash_demo(Q)`
- `serialize_unsigned_tx(tx)`
- `txid_demo(tx)`
- `sign_transaction_input(...)`
- `verify_transaction_input(...)`
- `demo_bitcoin_spending_flow()`

Module này không triển khai Bitcoin thật. Nó chỉ mô phỏng logic giáo dục:

```text
Alice có UTXO
Alice tạo transaction trả Bob
Alice ký unsigned transaction data
Node kiểm tra UTXO + pubkey hash + signature
```

Các ca bị từ chối:

- Sửa amount sau khi ký.
- Đổi người nhận sau khi ký.
- Dùng sai public key.
- Mallory ký bằng khóa khác.
- Tiêu cùng UTXO hai lần.
- UTXO không tồn tại.
- Public-key hash không khớp.

## 3.8. Module `ecdlp_attacks.py`

Module này minh họa các thuật toán tìm discrete log trên toy curve:

- Brute force.
- Baby-step Giant-step.
- Pollard rho toy-only experimental.

Mục tiêu không phải tấn công Bitcoin thật, mà để cho thấy:

```text
Toy curve nhỏ: tìm d được.
secp256k1 thật: không khả thi với các thuật toán cổ điển generic đã biết.
```

## 3.9. Module `nonce_attack.py`

Module này minh họa reused nonce attack:

```text
hai chữ ký dùng cùng k
→ recover k
→ recover d
```

Đây là phần quan trọng về bảo mật triển khai. Nó cho thấy không cần phá ECDLP nếu implementation làm sai nonce.

## 3.10. Module `shamir.py`

Module này so sánh:

```text
naive_mul_add(u1, G, u2, Q)
shamir_mul(u1, G, u2, Q)
```

Nó phục vụ câu hỏi tối ưu verification:

```text
Có thể tính u1G + u2Q hiệu quả hơn không?
```

## 3.11. Streamlit app

`app.py` là giao diện phòng lab, đi theo 10 trang:

| Trang | Nội dung |
|---|---|
| 0 | Bức tranh tổng quan |
| 1 | Quyền sở hữu trong Bitcoin |
| 2 | ECC: `Q = dG` |
| 3 | ECDLP |
| 4 | ECDSA ký/xác minh |
| 5 | Phòng lab giao dịch Bitcoin mô phỏng |
| 6 | Reused nonce attack |
| 7 | Phòng thủ nonce |
| 8 | Shamir's trick |
| 9 | OpenSSL secp256k1 |

Mỗi trang đều bắt đầu bằng ba mục:

```text
Câu hỏi
Ý tưởng
Demo chứng minh
```

Cách trình bày này giúp app không trở thành tập hợp demo rời rạc, mà thành một chuỗi lập luận.

## 3.12. OpenSSL demo

Thư mục `openssl_demo/` chứa script PowerShell:

- `gen_keys.ps1`: sinh cặp khóa `secp256k1`.
- `sign_verify.ps1`: ký và verify message/file.
- `benchmark.ps1`: benchmark RSA và ECDSA bằng OpenSSL.

Cần diễn giải cẩn thận:

- OpenSSL `dgst -sign/-verify` là ký/xác minh message hoặc file.
- Đây không phải full Bitcoin transaction signing.
- Benchmark `ecdsap256` là P-256/prime256v1, không phải `secp256k1`.
- Không kết luận tuyệt đối rằng ECDSA luôn nhanh hơn RSA trong mọi thao tác.

---

# 4. Kết quả thực nghiệm và phân tích

## 4.1. Kết quả số học modulo

Các test nền tảng kiểm tra:

- `egcd` trả về hệ số đúng.
- `mod_inv` tính đúng nghịch đảo khi tồn tại.
- `mod_inv` báo lỗi khi không tồn tại nghịch đảo.
- `mod_div` tương ứng với nhân nghịch đảo modulo.

Điều này xác nhận tầng field arithmetic đủ đúng để xây ECC phía trên.

## 4.2. Kết quả ECC

Các phép toán ECC được kiểm tra:

- Điểm thuộc curve.
- Điểm không thuộc curve.
- Cộng hai điểm.
- Nhân đôi điểm.
- Nhân vô hướng.

Double-and-Add cho thấy lợi thế thuật toán: thay vì cộng lặp tuyến tính, nó xử lý theo số bit của scalar.

## 4.3. Kết quả ECDLP demo

Với toy curve nhỏ, app có thể tìm `d` từ `Q = dG`.

- Brute force tìm bằng cách thử từng `k`.
- Baby-step Giant-step minh họa trade-off thời gian/bộ nhớ.
- Pollard rho minh họa random-walk và collision, nhưng được đánh dấu là nâng cao/experimental.

Ý nghĩa của phần này không phải “phá Bitcoin”, mà là làm rõ bản chất của ECDLP và độ phức tạp thuật toán.

## 4.4. Kết quả ECDSA sign/verify

Toy ECDSA cho thấy:

- Message gốc verify thành công.
- Message bị sửa thường verify thất bại.
- Sai public key không xác minh được chữ ký.
- Chữ ký gắn với dữ liệu đã ký.

Do toy curve quá nhỏ, đôi khi có edge case làm dữ liệu sửa vẫn verify thành công. App xử lý bằng cách cảnh báo và cho phép tự tạo dữ liệu sửa chắc chắn bị từ chối. Đây là cách trung thực với giới hạn của mô phỏng.

## 4.5. Kết quả mini Bitcoin transaction lab

Đây là kết quả quan trọng nhất về mặt ứng dụng.

Flow đúng:

```text
Tạo UTXO cho Alice
→ tạo transaction Alice trả Bob
→ Alice ký transaction
→ node toy model verify
→ transaction được áp dụng
→ UTXO cũ bị đánh dấu đã tiêu
→ output mới trở thành UTXO mới
```

Các ca thất bại:

| Kịch bản | Kết quả mong đợi | Ý nghĩa |
|---|---|---|
| Sửa amount sau khi ký | Reject | Chữ ký không còn khớp dữ liệu transaction |
| Đổi người nhận sau khi ký | Reject | Output mới khác dữ liệu đã ký |
| Thay public key bằng Mallory | Reject | PubKey hash không khớp locking condition |
| Mallory ký bằng key khác | Reject | Chữ ký không chứng minh quyền của Alice |
| Tiêu cùng UTXO hai lần | Reject lần hai | UTXO set chặn double spend |
| UTXO thiếu | Reject | Không thể tiêu output không tồn tại |

Phần này chứng minh đúng luận điểm: **ECDSA trong Bitcoin là cơ chế chứng minh quyền tiêu UTXO**.

## 4.6. Kết quả reused nonce attack

Khi hai chữ ký dùng cùng nonce `k`, dự án khôi phục được:

```text
recovered k = original k
recovered d = original d
```

Điều này xác nhận công thức tấn công. Bài học:

```text
ECDSA không chỉ cần ECDLP khó.
ECDSA còn cần nonce được sinh và bảo vệ đúng.
```

## 4.7. Kết quả Shamir's trick

Shamir's trick cho kết quả điểm giống phương pháp naive, nhưng thường giảm số phép toán trong biểu thức `u1G + u2Q`.

Ý nghĩa:

- Kết quả đúng về mặt toán học.
- Có cải thiện về operation count.
- Phù hợp để minh họa tối ưu thuật toán trong bước verification.

## 4.8. Kết quả OpenSSL

OpenSSL demo cho thấy:

- Sinh được cặp khóa `secp256k1`.
- Ký được message/file.
- Verify thành công với dữ liệu gốc.
- Verify thất bại nếu dữ liệu bị sửa.
- Đo thời gian ký/verify trên máy local.

Kết quả này nối toy implementation với tooling mật mã thật. Tuy nhiên, nó không thay thế full Bitcoin transaction signing.

## 4.9. Benchmark RSA/ECDSA

Benchmark cần được đọc cẩn thận.

Các kết quả kiểu `openssl speed` phụ thuộc:

- Máy chạy.
- Phiên bản OpenSSL.
- Curve.
- Kích thước khóa.
- Kiểu thao tác: sign hay verify.
- Cách tối ưu của implementation.

Nhận xét đúng:

- ECC thường có lợi thế kích thước khóa và chữ ký.
- ECDSA signing có thể nhanh hơn RSA signing ở một số cấu hình.
- RSA verification có thể rất nhanh do số mũ công khai nhỏ.
- Không được kết luận “ECDSA luôn nhanh hơn RSA”.
- Nếu benchmark dùng P-256 thì không được gọi là benchmark trực tiếp của `secp256k1`.

---

# 5. Bàn luận

## 5.1. Điểm mạnh của hướng tiếp cận

Điểm mạnh lớn nhất của dự án là không trình bày ECC như một chủ đề toán học cô lập. Dự án bắt đầu từ bài toán Bitcoin:

```text
Làm sao chứng minh quyền tiêu coin mà không cần ngân hàng?
```

Từ đó, các khái niệm được đưa vào đúng vai trò:

- UTXO: đối tượng cần được tiêu.
- Private key: quyền kiểm soát bí mật.
- Public key: định danh công khai.
- ECC: cách tạo public key từ private key.
- ECDLP: lý do public key không làm lộ private key.
- ECDSA: cách tạo bằng chứng quyền ký.
- Transaction verification: nơi chữ ký được kiểm tra.
- Nonce attack: nơi triển khai sai phá vỡ an toàn.

Mạch này phù hợp với môn học vì vừa có mật mã, vừa có độ phức tạp, vừa có thám mã, vừa có demo thực tế.

## 5.2. Vì sao ECC phù hợp với Bitcoin?

Bitcoin cần chữ ký số được lưu trữ và truyền đi trong số lượng lớn. Vì blockchain là dữ liệu công khai và được nhân bản trên nhiều node, kích thước khóa và chữ ký có ý nghĩa thực tế.

ECC có lợi thế:

- Khóa ngắn hơn ở mức an toàn tương đương.
- Public key và signature nhỏ gọn hơn RSA cùng mức an toàn.
- Phù hợp với hệ thống phân tán, nơi mọi node cần verify giao dịch.
- Có cấu trúc toán học đủ mạnh để xây dựng ECDSA.

Do đó, ECC/ECDSA là lựa chọn tự nhiên cho Bitcoin giai đoạn đầu.

## 5.3. Bitcoin cần chữ ký, không cần mã hóa giao dịch

Nếu coi Bitcoin là “tiền số công khai”, ta thấy rõ:

- Giao dịch cần được kiểm tra bởi mọi node.
- Mọi node phải thấy dữ liệu đủ để xác minh.
- Vì vậy, giao dịch không được thiết kế để bị che giấu bởi ECC.
- Điều cần bảo vệ là private key, không phải nội dung giao dịch.

Câu ngắn gọn:

```text
Bitcoin không hỏi “anh là ai?”.
Bitcoin hỏi “anh có tạo được chữ ký hợp lệ cho UTXO này không?”.
```

## 5.4. Ý nghĩa của mini transaction lab

Mini transaction lab là phần làm cho project khác một bài “ECDSA sign/verify” thông thường.

Nếu chỉ ký message `"Hello Bitcoin"`, người xem hiểu chữ ký số nhưng chưa thấy Bitcoin dùng nó ở đâu. Khi đưa vào UTXO model, chữ ký có ngữ cảnh:

```text
signature + public key unlock a specific UTXO
```

Điều này giúp kết nối trực tiếp:

```text
ECDSA formula
→ spending authority
→ node validation
→ double-spend rejection
```

Đây là cầu nối quan trọng nhất giữa lý thuyết môn học và ứng dụng Bitcoin.

## 5.5. Bài học từ reused nonce

Reused nonce attack cho thấy một nghịch lý quen thuộc trong mật mã:

```text
Bài toán nền có thể rất khó,
nhưng implementation sai có thể làm hệ thống sụp ngay.
```

Trong ECDSA, nonce `k` không phải chi tiết phụ. Nó tham gia trực tiếp vào công thức chữ ký. Nếu `k` bị lặp, private key có thể được tính ra bằng đại số modulo.

Bài học triển khai:

- Không tự viết ECDSA production từ đầu nếu không có chuyên môn.
- Dùng thư viện trưởng thành.
- Dùng nonce deterministic hoặc RNG chất lượng cao.
- Cẩn thận với side-channel và timing leak.

## 5.6. Vai trò của độ phức tạp thuật toán

Dự án có hai lớp độ phức tạp.

Thứ nhất là độ phức tạp phòng thủ:

- Double-and-Add giúp tính `dG` trong `O(log d)`.
- Shamir's trick giúp tối ưu `u1G + u2Q`.

Thứ hai là độ phức tạp tấn công:

- Brute force ECDLP: `O(n)`.
- BSGS/Pollard rho: `O(√n)`.
- Với `n` rất lớn như `secp256k1`, ngay cả `O(√n)` vẫn không khả thi trong thực tế cổ điển.

Điều này giúp project đúng chất “mật mã và độ phức tạp thuật toán”, không chỉ dừng ở demo UI.

## 5.7. Giới hạn của dự án

Dự án có các giới hạn cần nói rõ:

- Toy curve không an toàn.
- Python demo không constant-time.
- Mini transaction model không phải Bitcoin consensus thật.
- Không triển khai Bitcoin Script, SegWit, Taproot hoặc sighash đầy đủ.
- OpenSSL demo chỉ ký message/file, không ký transaction Bitcoin thật.
- Pollard rho trong app chỉ là demo nhỏ, có thể gặp collision suy biến.
- Benchmark không đủ để kết luận tuyệt đối về mọi hệ mật.

Những giới hạn này không làm giảm giá trị giáo dục của dự án. Ngược lại, nói rõ giới hạn giúp dự án đáng tin cậy hơn.

---

# 6. Hướng dẫn sử dụng hệ thống

## 6.1. Cài đặt môi trường

Trong PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu cần đặt `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "."
```

## 6.2. Chạy test

```powershell
pytest -q
```

Nếu `pytest` chưa có trong PATH:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 6.3. Chạy Streamlit app

```powershell
streamlit run app.py
```

hoặc:

```powershell
python -m streamlit run app.py
```

## 6.4. Cách đi qua app khi thuyết trình

Nên đi theo thứ tự:

1. Trang 0 — Bức tranh tổng quan.
2. Trang 1 — Quyền sở hữu trong Bitcoin.
3. Trang 2 — ECC: `Q = dG`.
4. Trang 3 — ECDLP và độ khó đảo ngược.
5. Trang 4 — ECDSA ký/xác minh.
6. Trang 5 — Mini Bitcoin Transaction Lab.
7. Trang 6 — Reused nonce attack.
8. Trang 7 — Nonce defense.
9. Trang 8 — Shamir's trick.
10. Trang 9 — OpenSSL secp256k1.

Nếu thời gian hạn chế, ưu tiên:

```text
Trang 0 → Trang 1 → Trang 5 → Trang 6 → Trang 9
```

Vì đây là các trang thể hiện rõ nhất mạch Bitcoin application.

## 6.5. Kịch bản demo chính

### Kịch bản 1: Giao dịch hợp lệ

1. Vào trang 5.
2. Tạo UTXO cho Alice.
3. Tạo giao dịch Alice → Bob.
4. Ký bằng Alice.
5. Node kiểm tra.
6. Gửi/áp dụng transaction.
7. Quan sát UTXO set cập nhật.

### Kịch bản 2: Sửa giao dịch sau khi ký

1. Tạo và ký transaction Alice → Bob.
2. Sang tab sửa phá.
3. Sửa số tiền hoặc đổi người nhận.
4. Node kiểm tra lại.
5. Giao dịch bị từ chối.

### Kịch bản 3: Mallory cố tiêu UTXO của Alice

1. Tạo UTXO cho Alice.
2. Tạo transaction chi tiêu UTXO đó.
3. Ký bằng Mallory.
4. Node verify.
5. Giao dịch bị từ chối vì khóa/chữ ký không khớp quyền của Alice.

### Kịch bản 4: Double spend

1. Gửi transaction hợp lệ lần đầu.
2. Thử gửi lại cùng transaction.
3. Lần hai bị từ chối vì UTXO đã bị tiêu.

### Kịch bản 5: Reused nonce attack

1. Vào trang 6.
2. Chọn private key `d`.
3. Chọn reused nonce `k`.
4. Nhập hai message khác nhau.
5. Chạy tấn công.
6. Quan sát recovered `k` và recovered `d`.

---

# 7. Kết luận

Dự án đã xây dựng được một mạch mô phỏng hoàn chỉnh từ bài toán thực tế của Bitcoin đến các thành phần mật mã nền tảng.

Thay vì chỉ nói “Bitcoin dùng ECC”, dự án làm rõ:

```text
Bitcoin cần xác thực quyền tiêu UTXO.
ECC tạo public key từ private key bằng Q = dG.
ECDLP bảo vệ private key khỏi public key.
ECDSA dùng private key để ký transaction data.
Node dùng public key để verify signature.
UTXO set ngăn double spend.
Nonce reuse làm lộ private key nếu triển khai sai.
```

Kết quả quan trọng nhất là project cho thấy mật mã trong Bitcoin không phải một khối kiến thức rời rạc. Nó là một chuỗi thiết kế có logic:

```text
bài toán ứng dụng
→ mô hình quyền sở hữu
→ primitive mật mã
→ bài toán khó
→ thuật toán chữ ký
→ kiểm chứng giao dịch
→ phân tích tấn công
→ bài học triển khai
```

Về mặt môn học, dự án đáp ứng cả hai trục:

- **Mật mã**: ECC, ECDSA, public key, chữ ký số, nonce.
- **Độ phức tạp thuật toán**: Double-and-Add, ECDLP, brute force, BSGS, Pollard rho, Shamir's trick.

Kết luận cuối cùng:

> ECC/ECDSA phù hợp với Bitcoin vì nó cung cấp cơ chế chữ ký số nhỏ gọn, hiệu quả và dựa trên bài toán khó. Nhưng một hệ mật mã mạnh không tự động tạo ra hệ thống an toàn. Trong mật mã học, lý thuyết đúng là điều kiện cần; triển khai đúng mới là điều kiện sống còn.

---

# 8. Tài liệu tham khảo

[1] Satoshi Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*.  
https://bitcoin.org/bitcoin.pdf

[2] Bitcoin Developer Documentation, *Transactions*.  
https://developer.bitcoin.org/devguide/transactions.html

[3] Standards for Efficient Cryptography Group, *SEC 2: Recommended Elliptic Curve Domain Parameters*, Version 2.0, 2010.  
https://www.secg.org/sec2-v2.pdf

[4] Neal Koblitz, “Elliptic Curve Cryptosystems”, *Mathematics of Computation*, 1987.

[5] Victor S. Miller, “Use of Elliptic Curves in Cryptography”, *CRYPTO*, 1985.

[6] Thomas Pornin, *RFC 6979: Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature Algorithm (ECDSA)*, IETF, 2013.  
https://datatracker.ietf.org/doc/html/rfc6979

[7] Joppe W. Bos, J. Alex Halderman, Nadia Heninger, Jonathan Moore, Michael Naehrig, Eric Wustrow, “Elliptic Curve Cryptography in Practice”, 2014.

[8] Joachim Breitner and Nadia Heninger, “Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies”, 2013.

[9] OpenSSL Documentation, `openssl-dgst`.  
https://docs.openssl.org/3.5/man1/openssl-dgst/

[10] Bài giảng MI4100, “Mật mã khóa công khai”, Đại học Bách Khoa Hà Nội.

---

# Phụ lục A. Liên hệ giữa câu hỏi nghiên cứu và module

| Câu hỏi | Module/App | Ý nghĩa |
|---|---|---|
| Q0. Bitcoin cần giải bài toán gì? | `app.py` trang 0 | Đặt bài toán ownership |
| Q1. Ownership biểu diễn thế nào? | `bitcoin_tx.py`, app trang 1/5 | UTXO spending condition |
| Q2. Private key sinh public key? | `ecc.py`, `demo_params.py` | `Q = dG` |
| Q3. Vì sao Q không lộ d? | `ecdlp_attacks.py`, app trang 3 | ECDLP và độ phức tạp |
| Q4. ECDSA ký/xác minh? | `ecdsa_toy.py`, app trang 4 | Chữ ký số |
| Q5. ECDSA vào transaction? | `bitcoin_tx.py`, app trang 5 | Ký transaction/UTXO |
| Q6. ECDSA sai nonce thì sao? | `nonce_attack.py`, app trang 6 | Recover private key |
| Q6.5. Phòng thủ nonce? | `rfc6979_nonce_defense.md`, app trang 7 | Defense/engineering |
| Q7. Tối ưu verify? | `shamir.py`, app trang 8 | Thuật toán tối ưu |
| Q8. Công cụ thật? | `openssl_demo/`, app trang 9 | OpenSSL secp256k1 |

---

# Phụ lục B. Các lệnh thường dùng

## B.1. Chạy test

```powershell
pytest -q
```

## B.2. Chạy app

```powershell
streamlit run app.py
```

## B.3. Chạy OpenSSL scripts

```powershell
openssl version
.\openssl_demo\gen_keys.ps1
.\openssl_demo\sign_verify.ps1
.\openssl_demo\benchmark.ps1
```

## B.4. Kiểm tra các file không nên commit

Không nên commit:

```text
.venv/
__pycache__/
*.pyc
*.pem
*.key
*.bin
.env
```

Các file key/signature sinh ra từ demo nên để trong thư mục tạm hoặc `results/` nếu cần lưu kết quả minh họa.

---

# Phụ lục C. Các cảnh báo bắt buộc khi trình bày

1. Toy curve không an toàn.
2. Mini transaction model không phải Bitcoin thật.
3. OpenSSL message/file signing không phải full Bitcoin transaction signing.
4. Reused nonce attack là lỗi triển khai, không chứng minh ECDSA chuẩn bị phá.
5. ECDLP toy attacks không dùng để tấn công `secp256k1`.
6. Dự án không tạo ví thật, không dùng private key thật, không broadcast transaction.
