import sys
import os
# Đảm bảo Python có thể import từ thư mục src/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd

from src.ecc import Curve, Point
from src.ecdsa_toy import ECDSAParams, sign, verify, hash_message_to_int
from src.nonce_attack import recover_nonce_from_reuse, recover_private_key_from_nonce
from src.shamir import naive_mul_add, shamir_mul

# Thiết lập cấu hình trang
st.set_page_config(page_title="Mô phỏng ECC/ECDSA", layout="wide")

@st.cache_data
def get_curve_points(p, a, b):
    """Tính toán tất cả các điểm trên đường cong đồ chơi để vẽ đồ thị."""
    points = []
    for x in range(p):
        rhs = (x**3 + a*x + b) % p
        for y in range(p):
            if (y**2) % p == rhs:
                points.append((x, y))
    return points

def main():
    st.sidebar.title("Điều hướng")
    page = st.sidebar.radio("Chọn Demo:", [
        "1. ECC Toy Curve",
        "2. ECDSA Sign/Verify",
        "3. Reused Nonce Attack",
        "4. Shamir's Trick",
        "5. OpenSSL Demo Summary"
    ])

    # Thiết lập tham số đường cong đồ chơi toàn cục cho các demo
    # y^2 = x^3 + 7 mod 223
    toy_curve = Curve(p=223, a=0, b=7)
    G = Point(47, 71)
    n = 21
    params = ECDSAParams(curve=toy_curve, G=G, n=n)

    if page == "1. ECC Toy Curve":
        st.title("Mô phỏng Đường cong Elliptic (ECC)")
        st.markdown("Đường cong sử dụng: **$y^2 = x^3 + 7 \pmod{223}$**")
        st.markdown(f"Điểm gốc (Generator Point): **$G = ({G.x}, {G.y})$** với cấp (order) **$n = {n}$**")
        
        st.info("Trong ECC, Khóa bí mật (Private Key) là một số nguyên $d$. Khóa công khai (Public Key) là một điểm $Q$ trên đường cong, được tính bằng phép nhân vô hướng $Q = d \cdot G$. Việc tính $Q$ từ $d$ rất nhanh, nhưng tìm ngược $d$ từ $Q$ là một bài toán vô cùng khó (ECDLP).")

        d = st.slider("Chọn khóa bí mật (Private Key) d:", min_value=1, max_value=n-1, value=5)
        
        # Tính khóa công khai
        Q = toy_curve.scalar_mul(d, G)
        st.success(f"**Khóa công khai (Public Key): Q = {d} * G = ({Q.x}, {Q.y})**")
        
        # Vẽ biểu đồ các điểm trên đường cong
        points = get_curve_points(toy_curve.p, toy_curve.a, toy_curve.b)
        df = pd.DataFrame(points, columns=['x', 'y'])
        
        colors = []
        sizes = []
        labels = []
        for x, y in points:
            if x == G.x and y == G.y:
                colors.append('green')
                sizes.append(15)
                labels.append('G (Gốc)')
            elif x == Q.x and y == Q.y:
                colors.append('red')
                sizes.append(15)
                labels.append('Q (Public Key)')
            else:
                colors.append('lightgrey')
                sizes.append(6)
                labels.append('Điểm thuộc Curve')
                
        df['color'] = colors
        df['size'] = sizes
        df['label'] = labels
        
        fig = px.scatter(df, x='x', y='y', color='color', size='size', 
                         hover_name='label',
                         color_discrete_map={'green': '#00CC96', 'red': '#EF553B', 'lightgrey': '#D3D3D3'},
                         title="Các điểm trên trường hữu hạn F_223")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    elif page == "2. ECDSA Sign/Verify":
        st.title("Chữ ký số ECDSA (Sign / Verify)")
        st.markdown("Minh họa quy trình ký và xác minh tin nhắn. Hệ thống đảm bảo tính xác thực và toàn vẹn dữ liệu: nếu tin nhắn bị sửa đổi (tampered), bản băm (hash) sẽ thay đổi dẫn đến chữ ký bị từ chối.")
        
        # Khóa bí mật mô phỏng
        d = st.number_input("Chọn khóa bí mật d:", min_value=1, max_value=n-1, value=10)
        Q = toy_curve.scalar_mul(d, G)
        st.write(f"Khóa công khai Q: **({Q.x}, {Q.y})**")
        
        msg_goc = st.text_input("Nhập tin nhắn gốc:", value="Hello Bitcoin")
        
        if st.button("Ký tin nhắn"):
            try:
                # Ký tin nhắn
                r, s = sign(params, d, msg_goc.encode('utf-8'))
                st.session_state.r = r
                st.session_state.s = s
                st.success(f"**Chữ ký hợp lệ được tạo ra:** (r = {r}, s = {s})")
            except Exception as e:
                st.error(f"Lỗi khi ký: {e}")
                
        if 'r' in st.session_state and 's' in st.session_state:
            st.divider()
            st.subheader("Kiểm chứng (Verification)")
            r = st.session_state.r
            s = st.session_state.s
            
            # Xác minh thông điệp gốc
            is_valid_goc = verify(params, Q, msg_goc.encode('utf-8'), (r, s))
            if is_valid_goc:
                st.success(f"Xác minh tin nhắn gốc ('{msg_goc}'): **HỢP LỆ**")
            else:
                st.error(f"Xác minh tin nhắn gốc ('{msg_goc}'): **KHÔNG HỢP LỆ**")
                
            # Mô phỏng việc sửa đổi thông điệp
            msg_fake = st.text_input("Thử sửa nội dung tin nhắn:", value="Hello Hacker")
            if msg_fake != msg_goc:
                is_valid_fake = verify(params, Q, msg_fake.encode('utf-8'), (r, s))
                if is_valid_fake:
                    st.success(f"Xác minh tin nhắn bị sửa ('{msg_fake}'): **HỢP LỆ**")
                else:
                    st.error(f"Xác minh tin nhắn bị sửa ('{msg_fake}'): **KHÔNG HỢP LỆ**")
                    st.info("💡 **Giải thích:** Khi thông điệp thay đổi, giá trị băm $H(m)$ thay đổi, khiến cho phương trình xác minh tính ra một điểm $X$ khác. Do đó, tọa độ $x$ của $X$ không còn khớp với 'ổ khóa' $r$ ban đầu, dẫn đến việc chữ ký bị từ chối.")

    elif page == "3. Reused Nonce Attack":
        st.title("Tấn công tái sử dụng Nonce (Reused Nonce Attack)")
        st.warning("⚠️ **CẢNH BÁO GIÁO DỤC:** Đây là mô phỏng trên đường cong toán học cực nhỏ (Toy Curve). Mã nguồn này chỉ dùng để minh họa nguyên lý, tuyệt đối không dùng trong hệ thống thực tế, không scan blockchain và không nhằm mục đích lấy cắp tài sản thật.")
        
        st.markdown("Trong ECDSA, mỗi chữ ký bắt buộc phải dùng một số ngẫu nhiên $k$ (nonce) duy nhất. Nếu vô tình ký 2 tin nhắn khác nhau bằng cùng một số $k$, khóa bí mật $d$ sẽ bị lộ ngay lập tức!")
        
        col1, col2 = st.columns(2)
        with col1:
            msg1 = st.text_input("Tin nhắn 1:", value="Thanh toan 1 BTC cho Alice")
        with col2:
            msg2 = st.text_input("Tin nhắn 2:", value="Thanh toan 2 BTC cho Bob")
        
        # Hardcode để minh họa chắc chắn thành công (như trong src/nonce_attack.py)
        d_attack = 2
        k_reuse = 4
        
        if st.button("Tiến hành mô phỏng tấn công"):
            st.write(f"Khóa bí mật thực tế của nạn nhân: $d$ = **{d_attack}**")
            st.write(f"Nonce vô tình bị dùng lại: $k$ = **{k_reuse}**")
            
            try:
                r1, s1 = sign(params, d_attack, msg1.encode('utf-8'), k=k_reuse)
                r2, s2 = sign(params, d_attack, msg2.encode('utf-8'), k=k_reuse)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**Chữ ký 1:**\n- r = {r1}\n- s1 = {s1}")
                with c2:
                    st.info(f"**Chữ ký 2:**\n- r = {r2}\n- s2 = {s2}")
                    
                st.error("🚨 Nhận thấy tham số `r` của 2 chữ ký giống hệt nhau! Kẻ tấn công biết rằng nonce đã bị tái sử dụng.")
                
                # Tiến hành khôi phục
                h1 = hash_message_to_int(msg1.encode('utf-8'), params.n)
                h2 = hash_message_to_int(msg2.encode('utf-8'), params.n)
                
                st.markdown("---")
                st.markdown("**Quá trình giải mã:**")
                k_recovered = recover_nonce_from_reuse(h1, h2, s1, s2, params.n)
                st.write(f"1. Phục hồi nonce $k$ thông qua hai chữ ký: $k' = (h_1 - h_2)(s_1 - s_2)^{{-1}} \pmod n = $ **{k_recovered}**")
                
                d_recovered = recover_private_key_from_nonce(h1, r1, s1, k_recovered, params.n)
                st.write(f"2. Phục hồi khóa bí mật $d$: $d' = (s_1 \cdot k' - h_1)r^{{-1}} \pmod n = $ **{d_recovered}**")
                
                if d_attack == d_recovered:
                    st.success(f"🎯 **Tấn công thành công!** Khóa bí mật đã bị lấy cắp: d' = {d_recovered} (Khớp với khóa gốc).")
                else:
                    st.error("Tấn công thất bại.")
            except Exception as e:
                st.error(f"Lỗi mô phỏng: {e}")

    elif page == "4. Shamir's Trick":
        st.title("Tối ưu hóa bằng Shamir's Trick")
        st.markdown("Quá trình xác minh chữ ký ECDSA đòi hỏi phải tính phương trình $X = u_1G + u_2Q$. Cách tính truyền thống (Naive) là tính độc lập $u_1G$ và $u_2Q$ sau đó cộng lại. Tuy nhiên, thủ thuật Shamir (Shamir's Trick) cho phép kết hợp các vòng lặp bit của $u_1$ và $u_2$ để tính đồng thời, giúp giảm bớt số lần thực hiện phép nhân đôi điểm (Doublings) vốn rất tốn kém chi phí toán học.")
        
        col1, col2 = st.columns(2)
        with col1:
            u1 = st.number_input("Hệ số u1:", value=13)
        with col2:
            u2 = st.number_input("Hệ số u2:", value=19)
            
        Q = toy_curve.scalar_mul(5, G)
        
        if st.button("Chạy đo lường hiệu năng"):
            # Cách truyền thống (Naive)
            toy_curve.reset_counters()
            p_naive = naive_mul_add(toy_curve, u1, G, u2, Q)
            naive_add, naive_double = toy_curve.add_count, toy_curve.double_count
            
            # Tối ưu bằng Shamir
            toy_curve.reset_counters()
            p_shamir = shamir_mul(toy_curve, u1, G, u2, Q)
            shamir_add, shamir_double = toy_curve.add_count, toy_curve.double_count
            
            data = {
                "Phương pháp": ["Truyền thống (Naive)", "Truyền thống (Naive)", "Thủ thuật Shamir", "Thủ thuật Shamir"],
                "Phép toán": ["Cộng điểm (Additions)", "Nhân đôi (Doublings)", "Cộng điểm (Additions)", "Nhân đôi (Doublings)"],
                "Số lượng": [naive_add, naive_double, shamir_add, shamir_double]
            }
            df = pd.DataFrame(data)
            
            fig = px.bar(df, x="Phương pháp", y="Số lượng", color="Phép toán", barmode="group",
                         title="So sánh khối lượng tính toán (Càng thấp càng tốt)", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
            
            st.success(f"**Kết luận:** Nhờ tính đồng thời, thuật toán Shamir đã giảm được **{naive_add - shamir_add} phép cộng điểm** và **{naive_double - shamir_double} phép nhân đôi điểm** so với cách tính rời rạc.")

    elif page == "5. OpenSSL Demo Summary":
        st.title("Thực nghiệm OpenSSL trên secp256k1")
        st.markdown("Dự án sử dụng công cụ mã nguồn mở OpenSSL để minh họa quy trình tạo chữ ký ECDSA trên đường cong chuẩn của Bitcoin (`secp256k1`), đồng thời benchmark tốc độ so với hệ mật RSA.")
        
        st.subheader("Các lệnh đã thực thi trong dự án:")
        st.code(".\openssl_demo\gen_keys.ps1\n.\openssl_demo\sign_verify.ps1\n.\openssl_demo\benchmark.ps1", language="powershell")
        
        st.subheader("Tóm tắt kết quả Benchmark:")
        benchmark_file = os.path.join("results", "openssl_benchmark.txt")
        if os.path.exists(benchmark_file):
            with open(benchmark_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            st.text_area("Nội dung file results/openssl_benchmark.txt", content, height=400)
            
            st.info("💡 **Phân tích:** Dựa vào log, tốc độ ký của thuật toán ECDSA `nistp256` (hoặc `secp256k1`) vượt trội đáng kể so với RSA 2048/3072 bit. Kích thước chữ ký nhỏ và tốc độ ký nhanh biến ECDSA thành lựa chọn lý tưởng cho mạng lưới Bitcoin và các ứng dụng cần độ phản hồi cao.")
        else:
            st.warning(f"Không tìm thấy file {benchmark_file}. Vui lòng chạy lệnh `.\openssl_demo\benchmark.ps1` trước để xuất kết quả.")

if __name__ == "__main__":
    main()
