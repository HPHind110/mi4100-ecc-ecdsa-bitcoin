# Ghi chú bối cảnh mật mã Bitcoin hiện đại

## Mục đích của tài liệu này

Tài liệu này chỉ đóng vai trò **bối cảnh mở rộng**. Trọng tâm chính của repo vẫn là:

```text
ECC/ECDSA trong Bitcoin
→ quyền chi tiêu theo mô hình UTXO
→ ký/xác minh
→ reused nonce attack
→ mini transaction demo
```

Repo này **không** chuyển trọng tâm sang Schnorr, Taproot hay MuSig2, và **không** triển khai các cơ chế đó.

## 1. Bitcoin truyền thống dùng ECDSA trên secp256k1

Trong phần lớn lịch sử của Bitcoin, chữ ký dùng để xác thực giao dịch là **ECDSA trên đường cong secp256k1**. Ở mức khái niệm, Bitcoin cần cơ chế để chứng minh ai có quyền chi tiêu một UTXO; trong các dạng chi tiêu quen thuộc như P2PKH, điều đó gắn với việc cung cấp chữ ký hợp lệ và dữ liệu khóa công khai phù hợp với điều kiện khóa của đầu ra trước đó. Bitcoin Developer Documentation mô tả transaction như cấu trúc gồm input và output, trong đó input chi tiêu một output trước đó bằng cách cung cấp dữ liệu thỏa điều kiện của pubkey script. BIP340 cũng nêu rõ Bitcoin truyền thống đã dùng **ECDSA signatures over the secp256k1 curve with SHA256 hashes for authenticating transactions**. [Sources: Bitcoin Developer Documentation, BIP340]

## 2. BIP340 giới thiệu Schnorr signatures trên secp256k1

BIP340 chuẩn hóa **Schnorr signatures for secp256k1**. Đây là bước phát triển hiện đại của chữ ký Bitcoin trên cùng đường cong `secp256k1`, nhưng với cơ chế chữ ký khác ECDSA. Theo BIP340, chuẩn này định nghĩa chữ ký Schnorr 64-byte trên `secp256k1` và được thiết kế như một chuẩn riêng, không phải chỉ là “ECDSA đổi nhãn”. Nó cũng tạo nền tảng tốt hơn cho các kỹ thuật như multisignature và threshold-style constructions ở tầng giao thức. [Source: BIP340]

## 3. Taproot/Schnorr là bối cảnh hiện đại, không phải mục tiêu chính của repo

Trong bối cảnh Bitcoin hiện đại, Schnorr và Taproot là các chủ đề quan trọng cần biết để đặt dự án vào dòng tiến hóa kỹ thuật của Bitcoin. Tuy nhiên, repo này **không lấy Taproot/Schnorr làm mục tiêu triển khai chính** vì các lý do sau:

- Chủ đề môn học của repo là **ECC và ECDSA trong Bitcoin**, không phải triển khai Schnorr/Taproot.
- Phần code hiện tại đã được tổ chức quanh toy ECC, toy ECDSA, reused nonce attack, mini UTXO signing flow và OpenSSL secp256k1 demo.
- Nếu đổi trọng tâm sang Schnorr, mạch giải thích hiện tại từ `Q = dG` đến `ECDSA transaction authentication` sẽ bị lệch khỏi luận điểm trung tâm của dự án.

Vì vậy, Schnorr/Taproot chỉ nên được nhắc như:

```text
bối cảnh hiện đại của Bitcoin
```

chứ không phải:

```text
đối tượng triển khai chính của repo này
```

## 4. MuSig2/BIP327 là chuẩn multisignature hiện đại tương thích với BIP340

BIP327 mô tả **MuSig2 for BIP340-compatible Multi-Signatures**. Ý tưởng cốt lõi là nhiều người ký có thể phối hợp để tạo ra:

- một aggregate public key tương thích BIP340
- một chữ ký Schnorr cuối cùng hợp lệ dưới aggregate public key đó

Theo BIP327, chuẩn này tương thích với public key và signature kiểu BIP340, và đặc biệt có ý nghĩa trong bối cảnh Taproot/key-path spending hiện đại. Tuy nhiên, BIP327 cũng không phải là phần mà repo này sẽ triển khai. Repo chỉ cần nhắc tới MuSig2 như một tiêu chuẩn multisignature hiện đại để người đọc thấy rằng hệ sinh thái Bitcoin đã phát triển vượt ra ngoài mô hình một chữ ký ECDSA đơn giản trong các ví dụ nhập môn. [Source: BIP327]

## 5. Vì sao repo này vẫn tập trung vào ECDSA

Repo tiếp tục lấy ECDSA làm trọng tâm vì các lý do thực dụng và học thuật sau.

### 5.1. Phù hợp trực tiếp với chủ đề môn học

Tên và trọng tâm của đồ án là:

```text
Mật mã đường cong elliptic (ECC) và ứng dụng chữ ký số ECDSA trong Bitcoin
```

Do đó, ECDSA không phải phần phụ; nó là trọng tâm phải được giải thích rõ ràng từ toán học đến ứng dụng Bitcoin.

### 5.2. Dễ kết nối với reused nonce attack

Một trong các bài học quan trọng nhất của repo là:

```text
ECDSA không bị phá vì toán sai;
ECDSA thất bại nếu triển khai sai, đặc biệt khi reuse nonce k
```

Thông điệp này nối rất tốt giữa:
- lý thuyết chữ ký số
- an toàn triển khai
- bài học thực tế trong hệ mật mã ứng dụng

Phần reused nonce attack là một trong những demo giáo dục mạnh nhất của repo hiện tại, và nó gắn tự nhiên với ECDSA hơn là với việc chuyển sang một lộ trình Schnorr mới.

### 5.3. Phù hợp với câu chuyện xác thực giao dịch Bitcoin truyền thống

Để giải thích transaction authentication theo hướng nhập môn, ECDSA vẫn là điểm xuất phát rất tự nhiên:

- private key tạo public key qua `Q = dG`
- public key tham gia xác minh chữ ký
- chữ ký gắn với quyền chi tiêu trong mô hình UTXO/P2PKH-like educational demo

Điều này giúp dự án kể một câu chuyện liền mạch từ:

```text
Bitcoin ownership problem
→ UTXO spending authority
→ ECC
→ ECDLP
→ ECDSA
→ transaction authentication
```

### 5.4. Phù hợp với kiến trúc code hiện tại

Kiến trúc hiện tại của repo đã xoay quanh:

- `src/field.py`
- `src/ecc.py`
- `src/ecdsa_toy.py`
- `src/bitcoin_tx.py`
- `src/nonce_attack.py`
- `src/shamir.py`
- `src/ecdlp_attacks.py`
- `app.py`

Tức là toàn bộ hệ thống đã được thiết kế để phục vụ:
- toy ECC
- toy ECDSA
- transaction authentication demo
- nonce-failure demo
- optimization demo

Nếu chuyển sang Schnorr/MuSig2 implementation, repo sẽ phải thay đổi đáng kể ở:
- mô hình chữ ký
- mô hình nonce
- verification flow
- transaction context explanation
- test strategy

Điều đó không cần thiết cho mục tiêu hiện tại.

## 6. Kết luận phạm vi

Tóm lại:

- Bitcoin truyền thống dùng **ECDSA trên secp256k1** để xác thực giao dịch.
- **BIP340** giới thiệu Schnorr signatures trên `secp256k1`.
- **Taproot/Schnorr** là bối cảnh Bitcoin hiện đại quan trọng, nhưng không phải mục tiêu triển khai chính của repo này.
- **BIP327 / MuSig2** là chuẩn multisignature hiện đại tương thích với BIP340.
- Repo này vẫn tập trung vào **ECDSA** vì phù hợp với chủ đề môn học, phù hợp với demo reused nonce attack, phù hợp với câu chuyện transaction authentication truyền thống, và phù hợp với kiến trúc code hiện tại.

Repo này:
- **không triển khai Schnorr**
- **không triển khai MuSig2**
- **không thay thế trọng tâm ECDSA**

## Tài liệu tham khảo

1. BIP340, *Schnorr Signatures for secp256k1*.  
   https://bips.xyz/0340

2. BIP327, *MuSig2 for BIP340-compatible Multi-Signatures*.  
   https://bips.xyz/327

3. Bitcoin Developer Documentation, *Transactions* và tài liệu developer guide/reference liên quan.  
   https://developer.bitcoin.org/devguide/transactions.html  
   https://developer.bitcoin.org/reference/transactions.html
