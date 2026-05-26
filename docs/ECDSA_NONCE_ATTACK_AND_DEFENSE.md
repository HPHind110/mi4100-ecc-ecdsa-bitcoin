# ECDSA Nonce Security: Tấn công và phòng thủ

## Mục tiêu tài liệu

Tài liệu này tổng hợp phần kiến thức về **tấn công nonce trong ECDSA** và **các nguyên tắc phòng thủ khi triển khai ECDSA** trong project mô phỏng ECC/ECDSA.

Trọng tâm của tài liệu là một thông điệp rất quan trọng:

```text
ECDLP khó không có nghĩa là hệ thống ECDSA tự động an toàn.
ECDSA chỉ an toàn khi toán học đúng và triển khai đúng.
```

Trong app, nội dung này liên hệ trực tiếp với:

```text
Page 7: Nonce attack
Page 8: Phòng thủ triển khai ECDSA
```

Tài liệu này dùng cho mục đích **giáo dục và thuyết trình**. Đây không phải hướng dẫn triển khai production, không thay thế RFC/FIPS, không thay thế security audit và không nên dùng để tự viết thư viện mật mã thật.

---

## 1. Vị trí của nonce trong ECDSA

Trong ECDSA, private key là `d`, public key là:

```text
Q = dG
```

Khi ký một message `m`, ta tính:

```text
h = H(m) mod n
R = kG
r = x(R) mod n
s = k⁻¹(h + r d) mod n
```

Trong đó:

| Ký hiệu | Ý nghĩa |
|---|---|
| `d` | private key, phải giữ bí mật |
| `Q` | public key, có thể công khai |
| `m` | message hoặc dữ liệu cần ký |
| `h` | hash của message sau khi rút gọn modulo `n` |
| `k` | nonce dùng một lần |
| `R` | điểm được tạo từ nonce, `R = kG` |
| `(r, s)` | chữ ký ECDSA |

Nonce `k` là thành phần cực kỳ nhạy cảm. Nó không phải “số phụ cho có”. Nó trực tiếp xuất hiện trong công thức ký cùng với private key `d`.

Vì vậy, `k` phải thỏa các yêu cầu sau:

```text
1. Không được lặp lại giữa hai chữ ký khác nhau.
2. Không được bị lộ.
3. Không được dễ đoán.
4. Không được sinh từ nguồn random yếu.
5. Không được rò rỉ một phần qua side-channel.
```

Nếu một trong các điều trên bị vi phạm, attacker có thể khôi phục private key mà không cần giải ECDLP.

---

## 2. ECDLP khó không cứu được nonce sai

Page ECDLP cho thấy: nếu attacker chỉ biết `G` và `Q = dG`, việc tìm lại `d` là rất khó với tham số thật.

Nhưng nonce attack đi theo hướng khác.

Attacker không cần giải:

```text
Q = dG
```

Thay vào đó, attacker khai thác công thức ký:

```text
s = k⁻¹(h + r d) mod n
```

Nếu `k` bị dùng sai, phương trình trên làm lộ đủ thông tin để suy ra `d`.

Đây là điểm cần nói thật rõ khi thuyết trình:

```text
Nonce attack không phải là phá ECDLP.
Nonce attack là khai thác lỗi triển khai ECDSA.
```

Nói ngắn gọn:

```text
ECDLP bảo vệ public key.
Nonce discipline bảo vệ quá trình signing.
```

Một hệ thống có thể chọn curve tốt, tham số mạnh, ECDLP rất khó, nhưng vẫn sụp đổ nếu nonce bị reuse hoặc bị lộ.

---

## 3. Tấn công 1: Reused nonce

### 3.1. Tình huống

Giả sử cùng một private key `d` dùng cùng một nonce `k` để ký hai message khác nhau:

```text
m1 -> chữ ký (r, s1)
m2 -> chữ ký (r, s2)
```

Vì cùng nonce `k`, điểm `R = kG` giống nhau, nên thành phần `r` cũng giống nhau.

Ta có:

```text
s1 = k⁻¹(h1 + r d) mod n
s2 = k⁻¹(h2 + r d) mod n
```

Trong đó:

```text
h1 = H(m1) mod n
h2 = H(m2) mod n
```

### 3.2. Khôi phục nonce k

Lấy hiệu hai phương trình:

```text
s1 - s2 = k⁻¹(h1 - h2) mod n
```

Suy ra:

```text
k = (h1 - h2)(s1 - s2)⁻¹ mod n
```

Nếu `s1 - s2` có nghịch đảo modulo `n`, attacker khôi phục được nonce `k`.

### 3.3. Khôi phục private key d

Từ công thức ký:

```text
s1 = k⁻¹(h1 + r d) mod n
```

Nhân hai vế với `k`:

```text
s1 k = h1 + r d mod n
```

Suy ra:

```text
d = (s1 k - h1) r⁻¹ mod n
```

Vậy chỉ cần hai chữ ký khác message nhưng reuse cùng nonce, attacker có thể khôi phục private key.

### 3.4. Bài học

Reused nonce là lỗi cực kỳ nghiêm trọng.

Không nên xem nó là “rủi ro tăng nhẹ”. Trong checklist phòng thủ, lỗi này phải bị đánh là **critical / fatal finding**.

```text
Reuse nonce trong ECDSA = có khả năng lộ private key.
```

---

## 4. Tấn công 2: Known nonce

### 4.1. Tình huống

Giả sử attacker biết nonce `k` của một chữ ký ECDSA.

Chỉ cần một chữ ký:

```text
(r, s)
```

và hash message:

```text
h = H(m) mod n
```

attacker có thể tính lại private key.

### 4.2. Công thức khôi phục private key

Từ:

```text
s = k⁻¹(h + r d) mod n
```

Suy ra:

```text
d = (s k - h) r⁻¹ mod n
```

Nghĩa là nếu nonce `k` bị lộ hoàn toàn, một chữ ký cũng đủ làm lộ private key.

### 4.3. Bài học

Nonce `k` không chỉ cần “không lặp lại”. Nó còn phải **bí mật**.

```text
Không reuse k là điều kiện cần.
Không để lộ k cũng là điều kiện bắt buộc.
```

---

## 5. Tấn công 3: Partial nonce leakage

### 5.1. Tình huống

Partial nonce leakage nghĩa là nonce `k` không bị lộ toàn bộ, nhưng attacker biết hoặc suy ra một phần thông tin về `k`.

Ví dụ:

```text
- vài bit cao/thấp của nonce bị lộ;
- nonce có bias, không phân phối đều;
- nonce sinh từ RNG yếu;
- thời gian chạy rò một phần thông tin về k;
- cache/power side-channel rò một phần quá trình tính kG.
```

Nếu attacker thu thập được nhiều chữ ký có nonce yếu hoặc rò một phần, họ có thể dùng các kỹ thuật nâng cao, thường liên quan đến lattice attack, để khôi phục private key trong một số điều kiện.

### 5.2. Vì sao không demo lattice attack trong project?

Project này tập trung vào:

```text
ECC -> ECDLP -> ECDSA -> Bitcoin case study -> nonce attack -> phòng thủ
```

Lattice attack là một hướng cryptanalysis nâng cao, cần thêm kiến thức về lattice reduction như LLL/BKZ. Nếu đưa vào demo chính, project sẽ dễ bị loãng khỏi trọng tâm.

Vì vậy, app chỉ cần nhấn mạnh:

```text
Nonce không cần lộ toàn bộ mới nguy hiểm.
Rò một phần nonce qua nhiều chữ ký cũng có thể là thảm họa.
```

### 5.3. Bài học

Phòng thủ ECDSA không chỉ là “đừng reuse nonce”. Cần kiểm soát cả:

```text
- chất lượng nguồn sinh nonce;
- side-channel;
- constant-time;
- implementation discipline;
- audit và test.
```

---

## 6. Các lỗi triển khai thường gặp

| Lỗi | Hậu quả |
|---|---|
| Dùng lại nonce `k` | Có thể khôi phục `k` và private key `d` từ hai chữ ký |
| Nonce bị lộ | Có thể khôi phục private key từ một chữ ký |
| Random yếu | Nonce có thể bị đoán, bị bias hoặc lặp lại |
| Không constant-time | Có thể rò bit bí mật qua timing side-channel |
| Side-channel không được xem xét | Có thể rò một phần nonce hoặc private key |
| Tự viết ECDSA production | Dễ sai edge-case, validate, randomness, encoding hoặc timing |
| Không có test vector | Khó phát hiện implementation sai |
| Không audit production crypto | Lỗi nghiêm trọng có thể tồn tại mà không bị phát hiện |

Một câu dễ nhớ:

```text
Crypto thường không chết vì công thức sai.
Crypto chết vì triển khai sai công thức.
```

---

## 7. Phòng thủ 1: Nonce discipline

Nonce discipline là kỷ luật quản lý nonce trong ECDSA.

Các nguyên tắc bắt buộc:

```text
1. Không reuse nonce.
2. Không để lộ nonce.
3. Không sinh nonce bằng random thường.
4. Không để nonce bị bias.
5. Không để nonce rò qua side-channel.
```

Trong app Page 8, nếu chọn cấu hình:

```text
Cố định hoặc có thể dùng lại k
```

thì phải báo critical ngay. Đây là lỗi chí mạng, không phải lỗi nhỏ.

---

## 8. Phòng thủ 2: RFC6979-style deterministic nonce

### 8.1. Ý tưởng

Một vấn đề lớn của ECDSA truyền thống là phụ thuộc vào chất lượng random khi sinh nonce.

Nếu random yếu, nonce yếu.

RFC6979-style deterministic nonce giảm rủi ro này bằng cách sinh nonce từ:

```text
private key d + message m
```

theo một quy trình xác định và an toàn.

Ý tưởng trực giác:

```text
Thay vì hỏi hệ điều hành: "cho tôi một số random thật tốt",
ta sinh nonce bằng một hàm xác định từ private key và message.
```

Điều này giúp giảm nguy cơ RNG lỗi hoặc thiếu entropy runtime.

### 8.2. RFC6979-style có giải quyết mọi thứ không?

Không.

RFC6979-style chủ yếu giảm rủi ro từ random yếu. Nó không tự động giải quyết:

```text
- side-channel;
- timing leak;
- code không constant-time;
- lỗi validate chữ ký;
- lỗi encode/decode;
- thư viện bị bug;
- private key bị lộ;
- malware;
- supply-chain attack.
```

Vì vậy, câu đúng là:

```text
RFC6979-style giúp giảm rủi ro RNG.
Nó không thay thế secure engineering.
```

---

## 9. Phòng thủ 3: CSPRNG tốt nếu dùng random nonce

Nếu không dùng deterministic nonce, mà dùng random nonce, nguồn random phải là **CSPRNG**.

CSPRNG là viết tắt của:

```text
Cryptographically Secure Pseudo-Random Number Generator
```

Không dùng random thường để sinh nonce hoặc khóa.

Ví dụ tư duy:

```text
Random thường: dùng cho game, mô phỏng, UI.
CSPRNG: dùng cho khóa, nonce, token, mật mã.
```

Nếu random nonce bị đoán, bị bias hoặc bị lặp, ECDSA có thể làm lộ private key.

---

## 10. Phòng thủ 4: Constant-time implementation

Constant-time nghĩa là thời gian chạy không phụ thuộc vào dữ liệu bí mật.

Trong ECDSA/ECC, các dữ liệu bí mật gồm:

```text
- private key d;
- nonce k;
- các bit của scalar trong scalar multiplication;
- một số giá trị trung gian khi ký.
```

Ví dụ nguy hiểm:

```text
Nếu bit của k là 1 thì code chạy lâu hơn.
Nếu bit của k là 0 thì code chạy nhanh hơn.
```

Attacker đo thời gian nhiều lần, rồi suy ra thông tin về nonce `k`. Nếu suy được đủ thông tin qua nhiều chữ ký, private key có thể bị đe dọa.

Các phần cần chú ý:

```text
- scalar multiplication: dG, kG;
- modular inversion;
- branch theo bit bí mật;
- memory access phụ thuộc secret;
- error handling rò thông tin;
- log/debug vô tình in dữ liệu nhạy cảm.
```

---

## 11. Phòng thủ 5: Side-channel awareness

Side-channel là kênh rò rỉ phụ, không nằm trong output chính của thuật toán.

Ví dụ:

```text
- timing;
- cache;
- power consumption;
- electromagnetic leakage;
- memory access pattern;
- exception behavior;
- log/debug output.
```

Trong mô hình toán học, ECDSA có thể an toàn. Nhưng trong hệ thật, attacker có thể không tấn công công thức, mà tấn công cách code chạy.

Vì vậy, với production crypto, cần review side-channel nghiêm túc.

---

## 12. Phòng thủ 6: Test vector và kiểm thử

Test vector là bộ input-output chuẩn dùng để kiểm tra implementation.

Ví dụ một test vector có thể gồm:

```text
private key d
public key Q
message m
nonce k
expected signature (r, s)
expected verify result
```

Test vector giúp phát hiện:

```text
- sai hash;
- sai modulo;
- sai nghịch đảo;
- sai xử lý r = 0 hoặc s = 0;
- sai validate public key;
- sai encode/decode chữ ký;
- sai verify edge-case.
```

Toy code trong project có thể chấp nhận đơn giản hóa. Nhưng production crypto mà không có test vector là rất nguy hiểm.

---

## 13. Phòng thủ 7: Dùng thư viện trưởng thành

Tự viết ECDSA để học là rất tốt.

Tự viết ECDSA để production là câu chuyện khác hẳn.

Với hệ thật, nên dùng thư viện mật mã trưởng thành:

```text
- được dùng rộng rãi;
- có test nghiêm túc;
- có review/audit;
- xử lý edge-case;
- có chú ý constant-time;
- có quy trình vá lỗi;
- có tài liệu rõ về threat model và giới hạn.
```

Trong project, toy implementation có giá trị học tập vì nó làm rõ toán học. Nhưng cần ghi rõ:

```text
Toy code không dùng cho ví thật, khóa thật, giao dịch thật hoặc hệ thống thật.
```

---

## 14. Risk gate và fatal finding

Trong app Page 8, risk score chỉ nên hiểu là **điểm minh họa**, không phải audit thật.

Tuy nhiên, có những lỗi không nên chỉ cộng điểm nhẹ. Chúng phải bị chặn bằng risk gate.

Ví dụ fatal finding:

```text
- nonce cố định hoặc có khả năng reuse;
- dùng random thường/seed yếu trong production;
- tự viết ECDSA production nhưng không audit;
- không có cơ chế chống reuse nonce trong hệ thật;
- bỏ qua side-channel trong môi trường production.
```

Với các lỗi này, app nên báo:

```text
Critical: lỗi chí mạng.
Phải sửa trước khi bàn tiếp.
```

Điều này phản ánh đúng bản chất mật mã: có lỗi là chết luôn, không phải cộng trừ điểm kiểu bài kiểm tra thường.

---

## 15. Toy demo, prototype và production

Cùng một hành động có mức rủi ro khác nhau tùy ngữ cảnh.

| Ngữ cảnh | Ý nghĩa | Mức chấp nhận đơn giản hóa |
|---|---|---|
| Toy demo | Code để học, minh họa công thức | Có thể đơn giản hóa nhiều, miễn là ghi rõ không dùng thật |
| Prototype nội bộ | Thử nghiệm ý tưởng | Vẫn phải tránh thói quen nguy hiểm như nonce yếu hoặc tự viết crypto sai |
| Production | Hệ thật, ví thật, tiền thật, dữ liệu thật | Cần thư viện trưởng thành, test, audit, constant-time, side-channel review |

Trong project này, code thuộc nhóm:

```text
Toy demo giáo dục.
```

Không được nâng nó thành production crypto.

---

## 16. Cách đọc Page 7 và Page 8 trong app

### Page 7: Nonce attack

Page 7 cho thấy ba tình huống:

```text
1. Reused nonce: dùng lại k cho hai chữ ký.
2. Known nonce: k của một chữ ký bị lộ.
3. Partial nonce leakage: k rò một phần qua nhiều chữ ký.
```

Bài học:

```text
ECDSA không cần bị phá về mặt toán học để private key bị lộ.
Chỉ cần triển khai sai nonce là đủ nguy hiểm.
```

### Page 8: Phòng thủ và tối ưu

Page 8 có hai phần:

```text
Tab 1: Phòng thủ triển khai ECDSA.
Tab 2: Shamir's trick để tối ưu verification.
```

Tab phòng thủ giúp người học kiểm tra:

```text
- cách sinh nonce;
- có chống reuse không;
- có constant-time không;
- có side-channel review không;
- dùng thư viện hay tự viết;
- toy/prototype/production;
- có audit không.
```

Tab Shamir’s trick không phải phòng thủ nonce attack. Nó chỉ tối ưu bước verify:

```text
P = u1G + u2Q
```

---

## 17. Shamir’s trick không phải phòng thủ nonce attack

Trong ECDSA verification, ta cần tính:

```text
P = u1G + u2Q
```

Cách trực tiếp:

```text
tính u1G riêng
tính u2Q riêng
cộng hai điểm lại
```

Shamir’s trick tính kết hợp hai phép nhân điểm để giảm số phép toán.

Điểm cần nhớ:

```text
Shamir’s trick là tối ưu hiệu năng.
Nó không làm ECDSA an toàn hơn trước reused nonce, known nonce hoặc partial nonce leakage.
```

Không được trình bày Shamir’s trick như một biện pháp phòng thủ nonce.

---

## 18. Kịch bản thuyết trình gợi ý

Có thể nói ngắn gọn như sau:

```text
Ở Page 4, em cho thấy ECDLP khó: biết Q = dG thì khó tìm d.

Nhưng ở Page 7, em cho thấy một hướng khác:
không cần giải ECDLP, chỉ cần nonce trong ECDSA bị dùng sai là private key có thể bị khôi phục.

Nếu dùng lại cùng nonce cho hai chữ ký, ta khôi phục được k rồi khôi phục d.
Nếu biết nonce của một chữ ký, ta khôi phục được d ngay.
Nếu nonce rò một phần qua nhiều chữ ký, hệ thống cũng có thể nguy hiểm.

Vì vậy Page 8 đưa ra các nguyên tắc phòng thủ:
không reuse nonce, ưu tiên RFC6979-style hoặc CSPRNG tốt,
constant-time, side-channel awareness, test vector, audit và thư viện trưởng thành.

Kết luận là: an toàn ECDSA không chỉ nằm ở ECDLP.
Nó còn nằm ở kỷ luật triển khai.
```

---

## 19. Checklist ngắn cần nhớ

Khi đánh giá một triển khai ECDSA, hãy hỏi:

```text
1. Nonce k có thể bị reuse không?
2. Nonce k có thể bị lộ không?
3. Nonce k có được sinh bằng RFC6979-style hoặc CSPRNG tốt không?
4. Code có constant-time ở phần xử lý bí mật không?
5. Có nguy cơ side-channel không?
6. Có dùng thư viện trưởng thành không?
7. Nếu tự viết, có phải chỉ dùng để học không?
8. Nếu production, có test vector và audit độc lập không?
9. Có phân biệt toy demo, prototype và production không?
10. Có đang nhầm tối ưu hiệu năng với phòng thủ bảo mật không?
```

---

## 20. Kết luận

ECDSA dựa trên nền tảng toán học mạnh, nhưng an toàn thực tế không chỉ đến từ công thức.

Kết luận đúng:

```text
ECC/ECDLP cung cấp nền tảng toán học.
ECDSA cung cấp cơ chế chữ ký số.
Nonce discipline bảo vệ private key trong quá trình signing.
Secure engineering bảo vệ hệ thống trước lỗi triển khai và side-channel.
```

Nói ngắn gọn:

```text
Good cryptography = good mathematics + disciplined implementation.
```

Trong project này, demo reused nonce, known nonce và checklist phòng thủ không nhằm chứng minh ECDSA “bị phá”. Chúng nhằm chứng minh rằng:

```text
ECDSA đúng chuẩn vẫn có thể sụp đổ nếu triển khai sai.
```

---

## 21. Tài liệu tham khảo nên đọc

1. RFC 6979 — Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature Algorithm (ECDSA).
2. FIPS 186 series — Digital Signature Standard.
3. SEC 1 — Elliptic Curve Cryptography.
4. Bitcoin Developer Documentation — Transactions.
5. Các bài viết/case study về ECDSA nonce reuse và biased nonce trong cryptocurrency.
