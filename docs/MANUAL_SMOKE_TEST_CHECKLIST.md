# Checklist kiểm thử thủ công Streamlit

Tài liệu này dùng để kiểm tra thủ công app Streamlit trước khi demo hoặc nộp báo cáo. Chỉ đánh dấu hoàn thành sau khi đã chạy thật trên máy.

## 1. Trước khi chạy ứng dụng

Chạy các lệnh sau từ thư mục gốc repository:

```powershell
python -m pytest -q
python -m compileall app.py src tests
streamlit run app.py
```

Ghi chú:

- Nếu `pytest` báo warning liên quan `.pytest_cache` nhưng toàn bộ test đều pass, có thể ghi chú warning đó và tiếp tục.
- Không được kết luận Streamlit đã pass nếu chưa tự chạy app và đi qua checklist thủ công bên dưới.
- App chỉ dùng toy curve, toy key và dữ liệu local; không nhập private key thật, ví thật hoặc dữ liệu giao dịch thật.

## 2. Checklist theo từng page

### Page 0: Mở đầu

- [ ] App mở được trên trình duyệt local.
- [ ] Bản đồ project hiển thị rõ mạch public-key crypto → ECC → ECDSA → Bitcoin case study.
- [ ] Navigation/sidebar hoạt động và chuyển page được.

### Page 1: Từ khóa bí mật đến khóa công khai

- [ ] Page giải thích symmetric crypto và public-key crypto mở được.
- [ ] Nội dung không gợi ý đây là hệ mật mã production.
- [ ] Wording giữ đúng mục tiêu giáo dục, không chuyển thành blockchain hype.

### Page 2: RSA, ElGamal/DH và ECC

- [ ] Khu vực benchmark mở được.
- [ ] Wording nói rõ benchmark đo hiệu năng, không đo an toàn.
- [ ] Page không claim ECDSA luôn nhanh hơn RSA trong mọi thao tác.
- [ ] Nếu chạy benchmark, kết quả được trình bày như trade-off phụ thuộc máy, curve và implementation.

### Page 3: Nền tảng toán học ECC

- [ ] Visualization toy curve mở được.
- [ ] Demo `Q = dG` hoạt động.
- [ ] Double-and-add trace hoạt động nếu phần trace được bật.
- [ ] Cảnh báo toy curve không an toàn và không phải secp256k1 hiển thị rõ.

### Page 4: ECDLP

- [ ] Brute force demo chạy và recover được toy private key.
- [ ] Baby-step Giant-step demo chạy và recover được toy private key.
- [ ] Pollard rho section vẫn mở/chạy được.
- [ ] Nếu Pollard rho không tìm được collision hữu ích, page hiển thị caveat thay vì overclaim.
- [ ] Cảnh báo toy attack không phá Bitcoin/secp256k1 hiển thị rõ.

### Page 5: Chữ ký số ECDSA

- [ ] ECDSA sign/verify thành công với message gốc.
- [ ] Tampered message verify fail.
- [ ] Wrong signature hoặc wrong public key fail nếu phần demo đó có sẵn.
- [ ] Nonce `k` được giải thích là giá trị bí mật dùng một lần cho mỗi chữ ký.
- [ ] Page không mô tả toy ECDSA là production crypto.

### Page 6: Bitcoin case study

- [ ] Mint/sign/verify/broadcast flow trong toy lab hoạt động.
- [ ] Tampered transaction bị reject.
- [ ] Wrong-key/Mallory case bị reject.
- [ ] Double spend bị reject.
- [ ] Page nói rõ đây là P2PKH-like educational model, không phải ví thật.
- [ ] Page không claim đang triển khai Bitcoin Script, sighash hoặc consensus thật.

### Page 7: Nonce attack

- [ ] Reused nonce demo recover được nonce `k`.
- [ ] Reused nonce demo recover được private key `d`.
- [ ] Known nonce explanation/demo hoạt động nếu có trong page.
- [ ] Page nói rõ đây là lỗi triển khai ECDSA, không phải ECDLP bị phá.
- [ ] Partial nonce leakage chỉ được trình bày ở mức giải thích nếu không có yêu cầu riêng.

### Page 8: Phòng thủ và tối ưu

- [ ] Defense checklist mở được.
- [ ] Cấu hình nguy hiểm tạo risk cao hoặc fatal risk.
- [ ] Cấu hình an toàn hơn cải thiện risk.
- [ ] Shamir's trick result bằng naive result.
- [ ] Page nói rõ Shamir's trick tối ưu verification, không phòng thủ nonce attack.
- [ ] Risk score được trình bày là giáo dục, không phải audit thật.

### Page 9: OpenSSL và kết luận

- [ ] Page OpenSSL mở được.
- [ ] Nếu máy có OpenSSL, generate key/sign/verify hoạt động.
- [ ] Tampered message verify fail.
- [ ] Page nói rõ OpenSSL message signing không phải full Bitcoin transaction signing.
- [ ] Kết luận giữ đúng mạch ECC → ECDLP → ECDSA → Bitcoin UTXO case study → nonce → defense → optimization → OpenSSL.

## 3. Bảng ghi kết quả kiểm thử thủ công

| Page | Nội dung kiểm tra | Kết quả | Ghi chú |
|---|---|---|---|
| [ ] Page 0 | App mở, project map hiển thị, navigation hoạt động |  |  |
| [ ] Page 1 | Symmetric/public-key explanation mở, wording an toàn |  |  |
| [ ] Page 2 | Benchmark section mở, wording performance-not-security đúng |  |  |
| [ ] Page 3 | Toy curve visualization, `Q = dG`, double-and-add, warning toy curve |  |  |
| [ ] Page 4 | Brute force, BSGS, Pollard rho, warning toy attack |  |  |
| [ ] Page 5 | Sign/verify pass, tampered fail, nonce explanation rõ |  |  |
| [ ] Page 6 | Mint/sign/verify/broadcast, tamper reject, wrong key reject, double spend reject |  |  |
| [ ] Page 7 | Reused nonce recover `k`, recover `d`, known nonce, implementation failure wording |  |  |
| [ ] Page 8 | Defense checklist, risk gate, Shamir equals naive, Shamir wording đúng |  |  |
| [ ] Page 9 | OpenSSL page, key/sign/verify, tampered fail, not Bitcoin transaction signing |  |  |

## 4. Ghi chú khi báo cáo kết quả

- Chỉ ghi “Streamlit smoke test passed” nếu đã chạy `streamlit run app.py` và đi qua checklist này.
- Nếu OpenSSL không có trong `PATH`, ghi rõ Page 9 chỉ kiểm tra được phần UI/cảnh báo môi trường, chưa kiểm tra được sign/verify bằng OpenSSL.
- Nếu một demo toy rơi vào edge-case, ghi lại tham số đã dùng và thử lại với tham số hợp lệ thay vì diễn giải sai về bảo mật thật.
