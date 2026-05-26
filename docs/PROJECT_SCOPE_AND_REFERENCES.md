# Phạm vi dự án và tài liệu tham khảo

## 1. Mục đích của tài liệu

Tài liệu này là phụ lục cho project:

```text
Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin
```

Mục tiêu của file là:

- xác định rõ phạm vi chính của repo;
- đặt project vào bối cảnh mật mã Bitcoin hiện đại;
- giải thích vì sao project tập trung vào ECC/ECDSA thay vì Schnorr, Taproot hoặc MuSig2;
- gom các tài liệu tham khảo chính theo từng nhóm nội dung.

File này không phải phần demo chính. Phần demo chính vẫn nằm trong `app.py`.

---

## 2. Trục chính của project

Trục học tập của repo là:

```text
Mật mã khóa công khai
→ ECC
→ ECDLP
→ ECDSA
→ Bitcoin UTXO case study
→ nonce attack
→ phòng thủ triển khai
→ tối ưu verification
→ OpenSSL secp256k1
```

Trong đó:

| Thành phần | Vai trò |
|---|---|
| Mật mã khóa công khai | Bối cảnh vì sao cần public key, private key và chữ ký số |
| ECC | Nền tảng mật mã dựa trên nhóm điểm của đường cong elliptic |
| ECDLP | Bài toán khó làm nền cho độ an toàn của ECC |
| ECDSA | Thuật toán chữ ký số dựa trên ECC |
| Bitcoin case study | Minh họa ECDSA được dùng để chứng minh quyền chi tiêu UTXO |
| Nonce attack | Cho thấy triển khai sai ECDSA có thể làm lộ private key |
| Phòng thủ triển khai | Ghi chú về nonce discipline, RFC6979-style, CSPRNG, constant-time và side-channel |
| Shamir's trick | Tối ưu bước verification `u1G + u2Q` |
| OpenSSL secp256k1 | Đối chiếu toy demo với công cụ mật mã thật |

Luận điểm trung tâm:

```text
ECC là nền tảng.
ECDLP là bài toán khó.
ECDSA là ứng dụng chữ ký số.
Bitcoin là case study thực tế.
```

---

## 3. Phạm vi triển khai của repo

Repo này triển khai hoặc mô phỏng các nội dung sau:

| Nhóm | Nội dung trong repo |
|---|---|
| Toy finite field / ECC | Trường hữu hạn, điểm trên đường cong, cộng điểm, nhân điểm |
| Public key generation | Tạo public key bằng `Q = dG` |
| ECDLP demo | Brute force, Baby-step Giant-step, Pollard rho trên toy curve |
| ECDSA demo | Ký và kiểm tra chữ ký trên toy parameters |
| Bitcoin transaction lab | Ví Alice/Bob/Mallory, UTXO set, input/output, public key hash, chữ ký trong input |
| Nonce attack | Reused nonce, known nonce, ghi chú partial nonce leakage |
| Defense checklist | Nonce discipline, RFC6979-style, CSPRNG, constant-time, side-channel, audit |
| Verification optimization | Shamir's trick cho `u1G + u2Q` |
| OpenSSL lab | Sinh key `secp256k1`, ký message/file, verify message gốc và message bị sửa |

Repo này không triển khai đầy đủ Bitcoin thật. Cụ thể, repo không có:

- Bitcoin Script đầy đủ;
- transaction serialization thật theo Bitcoin Core;
- sighash thật;
- consensus rules;
- mempool;
- mining;
- network;
- broadcast transaction;
- ví Bitcoin thật;
- quản lý coin thật.

Các thành phần trong app chỉ phục vụ mục tiêu giáo dục.

---

## 4. Bitcoin truyền thống và ECDSA trên secp256k1

Trong Bitcoin truyền thống, chữ ký số được dùng để xác thực quyền chi tiêu giao dịch.

Ở mức khái niệm, flow có thể hiểu như sau:

```text
Người dùng giữ private key d.
Private key sinh public key Q = dG.
UTXO bị khóa bởi điều kiện liên quan đến public key hoặc public key hash.
Khi muốn tiêu UTXO, người dùng ký dữ liệu giao dịch bằng ECDSA.
Node dùng public key để kiểm tra chữ ký.
Nếu chữ ký và điều kiện khóa hợp lệ, giao dịch được chấp nhận.
```

Điểm quan trọng:

```text
Bitcoin không dùng ECDSA để mã hóa giao dịch.
Bitcoin dùng ECDSA để xác thực quyền chi tiêu.
```

Trong mô hình giáo dục của repo, phần Bitcoin được đơn giản hóa thành:

```text
UTXO bị khóa bởi public key hash.
Người tiêu cung cấp public key và ECDSA signature.
Node kiểm tra hash(public key) và verify chữ ký.
```

Mục tiêu là làm rõ vai trò của ECDSA trong việc chứng minh quyền chi tiêu, không phải mô phỏng toàn bộ Bitcoin protocol.

---

## 5. Bối cảnh Bitcoin hiện đại: Schnorr, Taproot và MuSig2

Bitcoin hiện đại không chỉ dừng ở ECDSA. Các chủ đề như Schnorr signatures, Taproot và MuSig2 là bối cảnh quan trọng khi nhìn vào hướng phát triển của Bitcoin.

Tuy nhiên, trong repo này, các nội dung đó chỉ đóng vai trò mở rộng. Chúng không phải trọng tâm triển khai.

### 5.1. Schnorr signatures và BIP340

BIP340 chuẩn hóa Schnorr signatures trên `secp256k1`.

Schnorr signatures khác ECDSA về cơ chế chữ ký, dù cùng làm việc trên `secp256k1`. Schnorr có nhiều tính chất thuận lợi cho thiết kế hiện đại, đặc biệt trong các bối cảnh như key aggregation, multisignature và Taproot.

Trong repo này, Schnorr chỉ nên được nhắc như một phần bối cảnh hiện đại của Bitcoin. Repo không triển khai Schnorr signing hoặc Schnorr verification.

### 5.2. Taproot

Taproot là nâng cấp quan trọng của Bitcoin, gắn với Schnorr signatures và cách biểu diễn điều kiện chi tiêu linh hoạt hơn.

Repo này không triển khai Taproot vì Taproot kéo theo nhiều nội dung ngoài phạm vi chính, như:

- key-path spending;
- script-path spending;
- Tapscript;
- Merkleized script trees;
- quy tắc validation riêng của Taproot.

Các nội dung này có giá trị tham khảo, nhưng không cần thiết cho mục tiêu giải thích ECC/ECDSA trong Bitcoin ở mức nhập môn.

### 5.3. MuSig2 và BIP327

BIP327 mô tả MuSig2, một giao thức multisignature tương thích với BIP340.

Ý tưởng chính của MuSig2 là nhiều signer phối hợp để tạo ra:

- một aggregate public key;
- một chữ ký Schnorr cuối cùng hợp lệ dưới aggregate public key đó.

MuSig2 là chủ đề hiện đại và có ý nghĩa thực tế, nhưng không phù hợp để triển khai trong repo này. Nếu đưa MuSig2 vào sâu, project sẽ phải mở rộng sang:

- Schnorr signatures;
- key aggregation;
- nonce coordination giữa nhiều signer;
- multisignature protocol;
- Taproot/key-path spending.

Các nội dung này vượt quá phạm vi của đề tài hiện tại.

---

## 6. Vì sao project vẫn tập trung vào ECDSA

### 6.1. Phù hợp trực tiếp với tên đề tài

Tên đề tài đã xác định rõ trọng tâm:

```text
Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin
```

Vì vậy, ECDSA không phải phần phụ. ECDSA là một trong các thành phần chính cần được giải thích từ toán học đến ứng dụng.

---

### 6.2. Mạch học từ ECC đến ECDSA rất liền

Mạch giải thích của project là:

```text
Private key d
→ public key Q = dG
→ ECDLP làm Q khó đảo về d
→ ECDSA dùng d để ký
→ public key Q dùng để verify
```

Mạch này phù hợp với mục tiêu giáo dục vì người học có thể nhìn thấy quan hệ giữa:

- private key;
- public key;
- bài toán khó ECDLP;
- chữ ký số;
- verification.

---

### 6.3. ECDSA phù hợp để minh họa lỗi nonce

Một bài học quan trọng của repo là:

```text
ECDLP khó không đảm bảo an toàn nếu ECDSA bị triển khai sai nonce.
```

Các demo reused nonce và known nonce cho thấy:

```text
Không cần phá ECDLP.
Không cần brute force private key.
Chỉ cần nonce k bị dùng sai hoặc bị lộ, private key có thể bị khôi phục.
```

Đây là bài học quan trọng khi chuyển từ lý thuyết mật mã sang triển khai thực tế.

---

### 6.4. ECDSA phù hợp với Bitcoin case study nhập môn

Để giải thích quyền chi tiêu UTXO theo hướng dễ hiểu, mô hình ECDSA là đủ trực quan:

```text
UTXO bị khóa bởi public key hash.
Người tiêu đưa public key và ECDSA signature.
Node kiểm tra public key hash và verify chữ ký.
```

Mô hình này không mô phỏng đầy đủ Bitcoin thật, nhưng đủ để làm rõ ý tưởng:

```text
Chữ ký số được dùng để chứng minh quyền chi tiêu.
```

---

### 6.5. Phù hợp với kiến trúc code hiện tại

Code hiện tại của repo xoay quanh:

```text
src/field.py
src/ecc.py
src/ecdsa_toy.py
src/bitcoin_tx.py
src/shamir.py
app.py
```

Các phần này phục vụ trực tiếp cho:

- toy ECC;
- toy ECDSA;
- ECDLP attacks;
- transaction lab;
- nonce attack;
- Shamir optimization;
- OpenSSL secp256k1 demo.

Nếu chuyển trọng tâm sang Schnorr, Taproot hoặc MuSig2, repo sẽ cần thay đổi đáng kể ở:

- mô hình chữ ký;
- cách sinh nonce;
- verification flow;
- transaction context;
- test strategy;
- giải thích giao thức.

Điều đó không cần thiết cho mục tiêu hiện tại.

---

## 7. Ghi chú về tài liệu tham khảo

Repo này không lưu trữ toàn bộ PDF bài báo hoặc toàn bộ văn bản chuẩn kỹ thuật. Các nguồn dưới đây được dùng làm tài liệu nền cho báo cáo và app.

Khi viết báo cáo chính, nên trích nguồn theo từng nhóm nội dung thay vì chỉ đặt một danh sách URL rời rạc.

---

## 8. Tài liệu tham khảo đề xuất

### 8.1. Nền tảng ECC

1. Neal Koblitz, **Elliptic Curve Cryptosystems**, Mathematics of Computation, 1987.  
   Gợi ý dùng cho phần: nguồn gốc ECC trong mật mã học.

2. Victor S. Miller, **Use of Elliptic Curves in Cryptography**, CRYPTO 1985.  
   Gợi ý dùng cho phần: nguồn gốc độc lập của ECC trong mật mã học.

3. Joppe W. Bos et al., **Elliptic Curve Cryptography in Practice**.  
   Gợi ý dùng cho phần: ECC trong triển khai thực tế.

4. Alessandro Cilardo et al., **Elliptic Curve Cryptography Engineering**.  
   Gợi ý dùng cho phần: khía cạnh engineering của ECC.

5. Vipul Gupta et al., **Performance Analysis of Elliptic Curve Cryptography for SSL**.  
   Gợi ý dùng cho phần: bối cảnh hiệu năng của ECC trong hệ thống thực tế.

---

### 8.2. ECDSA, nonce và lỗi triển khai

6. Thomas Pornin, **RFC 6979: Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature Algorithm (ECDSA)**, IETF, 2013.  
   https://datatracker.ietf.org/doc/html/rfc6979  
   Gợi ý dùng cho phần: deterministic nonce, giảm phụ thuộc vào nguồn random bên ngoài khi ký DSA/ECDSA.

7. Joachim Breitner and Nadia Heninger, **Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies**, 2013.  
   Gợi ý dùng cho phần: weak nonce, biased nonce, partial nonce leakage và lattice attack.

---

### 8.3. Bitcoin transaction và UTXO

8. Bitcoin Developer Documentation, **Transactions**.  
   https://developer.bitcoin.org/devguide/transactions.html  
   Gợi ý dùng cho phần: input/output, UTXO spending, pubkey script và signature script ở mức developer documentation.

9. Bitcoin Developer Documentation, **Transaction Reference**.  
   https://developer.bitcoin.org/reference/transactions.html  
   Gợi ý dùng cho phần: cấu trúc transaction ở mức tham khảo.

---

### 8.4. Bitcoin hiện đại: Schnorr, Taproot và MuSig2

10. BIP340, **Schnorr Signatures for secp256k1**.  
    https://bips.xyz/0340  
    Gợi ý dùng cho phần: Schnorr signatures trên `secp256k1` và phân biệt với ECDSA.

11. BIP341, **Taproot: SegWit version 1 spending rules**.  
    https://bips.xyz/0341  
    Gợi ý dùng cho phần: bối cảnh Taproot.

12. BIP342, **Validation of Taproot Scripts**.  
    https://bips.xyz/0342  
    Gợi ý dùng cho phần: bối cảnh Tapscript, nếu cần nhắc mở rộng.

13. BIP327, **MuSig2 for BIP340-compatible Multi-Signatures**.  
    https://bips.xyz/327  
    Gợi ý dùng cho phần: multisignature hiện đại tương thích BIP340.

---

### 8.5. Công cụ và benchmark

14. OpenSSL Documentation.  
    https://docs.openssl.org/  
    Gợi ý dùng cho phần: OpenSSL secp256k1 sign/verify.

15. OpenSSL `speed` manual.  
    https://docs.openssl.org/master/man1/openssl-speed/  
    Gợi ý dùng cho phần: benchmark RSA/DSA/ECDSA trong app.

---

## 9. Gợi ý trích dẫn trong báo cáo

### 9.1. Khi nói về nguồn gốc ECC

Ví dụ:

```text
ECC được đề xuất độc lập bởi Koblitz và Miller trong thập niên 1980.
```

Nguồn phù hợp:

```text
Koblitz 1987; Miller 1985
```

---

### 9.2. Khi nói về ECDSA nonce

Ví dụ:

```text
Nonce trong ECDSA phải không lặp lại, không dễ đoán và không bị rò rỉ; các lỗi nonce có thể dẫn tới khôi phục khóa riêng.
```

Nguồn phù hợp:

```text
RFC 6979; Breitner and Heninger 2013
```

---

### 9.3. Khi nói về Bitcoin transaction

Ví dụ:

```text
Bitcoin transaction gồm input và output; input chi tiêu output trước đó bằng dữ liệu thỏa điều kiện khóa của output đó.
```

Nguồn phù hợp:

```text
Bitcoin Developer Documentation
```

---

### 9.4. Khi nói về Schnorr/Taproot/MuSig2

Ví dụ:

```text
Bitcoin hiện đại bổ sung Schnorr signatures trên secp256k1 qua BIP340; Taproot và MuSig2 là các bối cảnh mở rộng quan trọng.
```

Nguồn phù hợp:

```text
BIP340; BIP341; BIP327
```

---

## 10. Tóm tắt phạm vi cuối cùng

Repo tập trung vào:

```text
ECC
ECDLP
ECDSA
Bitcoin UTXO case study
nonce attack
phòng thủ triển khai
Shamir optimization
OpenSSL secp256k1
```

Repo chỉ nhắc Schnorr, Taproot và MuSig2 như bối cảnh mở rộng.

Repo không triển khai:

```text
Schnorr
Taproot
Tapscript
MuSig2
Bitcoin transaction thật
Bitcoin Script đầy đủ
Bitcoin network
```

Cách đặt phạm vi này giúp project giữ đúng trọng tâm của đề tài, đồng thời vẫn cho người đọc thấy Bitcoin hiện đại đã phát triển thêm nhiều hướng ngoài ECDSA.
