import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd

from src.ecc import Curve, Point
from src.ecdsa_toy import ECDSAParams, sign, verify, hash_message_to_int
from src.nonce_attack import recover_nonce_from_reuse, recover_private_key_from_nonce
from src.shamir import naive_mul_add, shamir_mul

# ============= CẤU HÌNH TRANG =============
st.set_page_config(page_title="🔐 ECC/ECDSA - Mô phỏng Tương tác", layout="wide")

# ============= GLOBAL PARAMETERS =============
# Đường cong Toy: y^2 = x^3 + 7 mod 223
# Được chọn để chạy nhanh nhưng đủ để minh họa các khái niệm
TOY_CURVE = Curve(p=223, a=0, b=7)
GENERATOR_POINT = Point(47, 71)
ORDER_N = 21
ECDSA_PARAMS = ECDSAParams(curve=TOY_CURVE, G=GENERATOR_POINT, n=ORDER_N)

# Danh sách demos
DEMOS = [
    {"id": 0, "title": "1️⃣ ECC Toy Curve", "desc": "Làm quen với Elliptic Curve"},
    {"id": 1, "title": "2️⃣ ECDSA Sign/Verify", "desc": "Ký và xác minh thông điệp"},
    {"id": 2, "title": "3️⃣ Reused Nonce Attack", "desc": "Tấn công tái sử dụng nonce"},
    {"id": 3, "title": "4️⃣ Shamir's Trick", "desc": "Tối ưu hóa phép toán"},
    {"id": 4, "title": "5️⃣ OpenSSL Demo", "desc": "Thực nghiệm secp256k1"},
]

# ============= UTILITY FUNCTIONS =============
@st.cache_data
def get_curve_points(p, a, b):
    """Tính toán tất cả điểm trên đường cong để vẽ biểu đồ."""
    points = []
    for x in range(p):
        rhs = (x**3 + a*x + b) % p
        for y in range(p):
            if (y**2) % p == rhs:
                points.append((x, y))
    return points

def render_header(current_page_id):
    """Hiển thị header với progress bar và breadcrumb."""
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        st.markdown("## 🔐 ECC/ECDSA")
    
    with col2:
        # Progress bar
        progress = (current_page_id + 1) / len(DEMOS)
        st.progress(progress, text=f"Bước {current_page_id + 1}/{len(DEMOS)}")
    
    with col3:
        st.caption(f"Phần: {current_page_id + 1}/{len(DEMOS)}")
    
    st.divider()

def render_navigation(current_page_id):
    """Hiển thị nút Previous/Next."""
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if current_page_id > 0:
            if st.button("⬅️ Bước trước", use_container_width=True):
                st.session_state.page_id = current_page_id - 1
                st.rerun()
    
    with col2:
        st.markdown("")  # Placeholder
    
    with col3:
        if current_page_id < len(DEMOS) - 1:
            if st.button("Bước tiếp ➡️", use_container_width=True):
                st.session_state.page_id = current_page_id + 1
                st.rerun()

def render_learning_summary(title, points):
    """Hiển thị tóm tắt kiến thức đã học."""
    with st.expander("📚 Tóm tắt kiến thức"):
        st.markdown(f"### {title}")
        for point in points:
            st.markdown(f"- {point}")


# ============= DEMO 1: ECC TOY CURVE =============
def demo_ecc_toy_curve():
    """Minh họa các điểm trên đường cong Elliptic."""
    st.title("1️⃣ Đường cong Elliptic (ECC)")
    
    with st.columns(3)[1]:
        st.latex(r"y^2 \equiv x^3 + 7 \pmod{223}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📌 **Generator Point G**: ({GENERATOR_POINT.x}, {GENERATOR_POINT.y})")
    with col2:
        st.info(f"📌 **Order (Cấp)**: {ORDER_N}")
    
    st.markdown("""
    **Nguyên lý:**
    - Khóa bí mật (Private Key): số nguyên $d$
    - Khóa công khai (Public Key): điểm $Q$ trên đường cong, tính bằng $Q = d \cdot G$
    - **One-way function**: Tính $Q$ từ $d$ rất nhanh, nhưng tìm ngược $d$ từ $Q$ là vô cùng khó (ECDLP)
    """)
    
    # Interaction
    d = st.slider("🔑 Chọn khóa bí mật d", min_value=1, max_value=ORDER_N-1, value=5, 
                   help="Số nguyên từ 1 đến n-1")
    
    Q = ECDSA_PARAMS.curve.scalar_mul(d, ECDSA_PARAMS.G)
    
    with st.container(border=True):
        st.success(f"✅ **Khóa công khai**: Q = {d} × G = **({Q.x}, {Q.y})**")
    
    # Visualize curve
    st.subheader("📊 Trực quan hóa Curve")
    points = get_curve_points(ECDSA_PARAMS.curve.p, ECDSA_PARAMS.curve.a, ECDSA_PARAMS.curve.b)
    df = pd.DataFrame(points, columns=['x', 'y'])
    
    colors, sizes, labels = [], [], []
    for x, y in points:
        if x == ECDSA_PARAMS.G.x and y == ECDSA_PARAMS.G.y:
            colors.append('Generator (G)')
            sizes.append(20)
            labels.append('Generator')
        elif x == Q.x and y == Q.y:
            colors.append('Public Key (Q)')
            sizes.append(20)
            labels.append('Public Key')
        else:
            colors.append('Điểm trên Curve')
            sizes.append(6)
            labels.append('Curve Point')
    
    df['color'] = colors
    df['size'] = sizes
    df['label'] = labels
    
    fig = px.scatter(df, x='x', y='y', color='color', size='size', 
                     hover_name='label',
                     color_discrete_map={
                         'Generator (G)': '#00CC96',
                         'Public Key (Q)': '#EF553B',
                         'Điểm trên Curve': '#D3D3D3'
                     },
                     title="Các điểm trên trường hữu hạn F₂₂₃",
                     labels={'x': 'X coordinate', 'y': 'Y coordinate'})
    fig.update_layout(showlegend=True, hovermode='closest')
    st.plotly_chart(fig, use_container_width=True)
    
    render_learning_summary("ECC Toy Curve", [
        "Đường cong Elliptic được định nghĩa bởi phương trình $y^2 = x^3 + ax + b$ trên trường hữu hạn",
        "Phép nhân vô hướng $d \cdot G$ dựa trên phép cộng điểm (Point Addition)",
        "Độ khó của ECDLP đảm bảo an toàn mật mã"
    ])


# ============= DEMO 2: ECDSA SIGN/VERIFY =============
def demo_ecdsa_sign_verify():
    """Minh họa quy trình ký và xác minh."""
    st.title("2️⃣ Chữ ký số ECDSA (Sign/Verify)")
    
    st.markdown("""
    **Quy trình:**
    1. **Ký (Sign)**: Dùng khóa bí mật $d$ tạo chữ ký $(r, s)$ trên thông điệp
    2. **Xác minh (Verify)**: Dùng khóa công khai $Q$ kiểm chứng $(r, s)$ có hợp lệ
    3. **Tính chất**: Nếu thông điệp thay đổi 1 ký tự, chữ ký sẽ bị từ chối
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        d_demo = st.number_input("🔑 Khóa bí mật d", min_value=1, max_value=ORDER_N-1, value=10)
        Q_demo = ECDSA_PARAMS.curve.scalar_mul(d_demo, ECDSA_PARAMS.G)
        st.caption(f"Khóa công khai Q: ({Q_demo.x}, {Q_demo.y})")
    
    with col2:
        st.info("Ngoài có thể chọn khóa bí mật trong range, bạn cũng có thể nhập số cụ thể")
    
    msg_original = st.text_input("📝 Tin nhắn gốc", value="Hello Bitcoin", max_chars=100)
    
    col_sign1, col_sign2, col_sign3 = st.columns([1, 2, 1])
    with col_sign2:
        if st.button("🖊️ Ký tin nhắn", use_container_width=True):
            try:
                r, s = sign(ECDSA_PARAMS, d_demo, msg_original.encode('utf-8'))
                st.session_state.r = r
                st.session_state.s = s
                st.session_state.Q = Q_demo
                st.session_state.msg_original = msg_original
                st.success(f"✅ **Chữ ký tạo thành công!**\n- r = {r}\n- s = {s}")
            except Exception as e:
                st.error(f"❌ Lỗi ký: {e}")
    
    # Verification section
    if 'r' in st.session_state and 's' in st.session_state:
        st.divider()
        st.subheader("🔍 Kiểm chứng Chữ ký (Verification)")
        
        r = st.session_state.r
        s = st.session_state.s
        Q = st.session_state.Q
        msg_orig = st.session_state.msg_original
        
        # Verify original message
        is_valid_orig = verify(ECDSA_PARAMS, Q, msg_orig.encode('utf-8'), (r, s))
        
        with st.container(border=True):
            if is_valid_orig:
                st.success(f"✅ Tin nhắn gốc '{msg_orig}': **HỢP LỆ**")
            else:
                st.error(f"❌ Tin nhắn gốc '{msg_orig}': **KHÔNG HỢP LỆ**")
        
        st.write("---")
        
        # Try tampered message
        st.markdown("**Thử sửa đổi tin nhắn:**")
        msg_tampered = st.text_input("📝 Nhập tin nhắn bị sửa", value="Hello Hacker", max_chars=100)
        
        if msg_tampered != msg_orig:
            is_valid_tampered = verify(ECDSA_PARAMS, Q, msg_tampered.encode('utf-8'), (r, s))
            
            with st.container(border=True):
                if is_valid_tampered:
                    st.success(f"✅ Tin nhắn sửa '{msg_tampered}': **HỢP LỆ**")
                else:
                    st.error(f"❌ Tin nhắn sửa '{msg_tampered}': **KHÔNG HỢP LỆ**")
            
            with st.expander("💡 Giải thích"):
                st.markdown("""
                Khi tin nhắn thay đổi:
                1. Hash của tin nhắn $H(m)$ sẽ khác
                2. Phương trình xác minh tính ra điểm $X$ khác
                3. Tọa độ $x$ của $X$ không khớp với 'ổ khóa' $r$ ban đầu
                4. Chữ ký bị **từ chối** ➜ **Phát hiện tampering!**
                """)
    
    render_learning_summary("ECDSA Sign/Verify", [
        "ECDSA đảm bảo **tính xác thực**: Chỉ có người biết khóa bí mật mới có thể ký",
        "Đảm bảo **tính toàn vẹn**: Nếu tin nhắn bị sửa, chữ ký sẽ bị từ chối",
        "Không thể phủ nhận: Người ký không thể phủ nhận đã ký tin nhắn"
    ])


# ============= DEMO 3: REUSED NONCE ATTACK =============
def demo_reused_nonce_attack():
    """Minh họa tấn công tái sử dụng nonce."""
    st.title("3️⃣ Tấn công Tái sử dụng Nonce (Reused Nonce Attack)")
    
    st.warning("""
    ⚠️ **CẢNH BÁO GIÁO DỤC**: Đây là mô phỏng trên đường cong toán học cực nhỏ. 
    Mã này chỉ để minh họa nguyên lý, tuyệt đối không dùng trong thực tế.
    """)
    
    st.markdown("""
    **Nguyên lý Tấn công:**
    
    Trong ECDSA, mỗi chữ ký phải dùng một nonce $k$ **duy nhất**. 
    Nếu vô tình ký 2 tin nhắn khác nhau bằng cùng $k$, khóa bí mật $d$ sẽ bị lộ!
    
    **Công thức khôi phục**:
    - $k' = (h_1 - h_2)(s_1 - s_2)^{-1} \\pmod n$
    - $d' = (s_1 \\cdot k' - h_1) \\cdot r^{-1} \\pmod n$
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        msg1 = st.text_input("📝 Tin nhắn 1", value="Thanh toan 1 BTC cho Alice", max_chars=100)
    with col2:
        msg2 = st.text_input("📝 Tin nhắn 2", value="Thanh toan 2 BTC cho Bob", max_chars=100)
    
    # Hard-coded demo values (với giải thích)
    d_victim = 2
    k_reuse = 4
    
    with st.expander("ℹ️ Tại sao hard-coded?"):
        st.markdown(f"""
        - **Khóa bí mật của nạn nhân**: d = {d_victim}
        - **Nonce vô tình bị dùng lại**: k = {k_reuse}
        
        Những giá trị này được chọn để đảm bảo tấn công thành công trên đường cong toy nhỏ này.
        Các giá trị khác có thể không bao giờ trích xuất được khóa bí mật do những hạn chế toán học.
        """)
    
    if st.button("⚡ Tiến hành mô phỏng tấn công"):
        st.info(f"🔍 **Giả sử**: Nạn nhân dùng d = {d_victim} và vô tình dùng lại nonce k = {k_reuse}")
        
        try:
            # Ký 2 tin nhắn với cùng nonce
            r1, s1 = sign(ECDSA_PARAMS, d_victim, msg1.encode('utf-8'), k=k_reuse)
            r2, s2 = sign(ECDSA_PARAMS, d_victim, msg2.encode('utf-8'), k=k_reuse)
            
            col_sig1, col_sig2 = st.columns(2)
            with col_sig1:
                st.info(f"**Chữ ký 1 (msg1):**\n- r₁ = {r1}\n- s₁ = {s1}")
            with col_sig2:
                st.info(f"**Chữ ký 2 (msg2):**\n- r₂ = {r2}\n- s₂ = {s2}")
            
            if r1 == r2:
                st.error(f"🚨 **PHÁT HIỆN**: Cả 2 chữ ký đều có r = {r1}! Đây là dấu hiệu nonce bị tái sử dụng!")
            
            st.divider()
            st.subheader("🔓 Quá trình giải mã khóa bí mật")
            
            # Recover nonce
            h1 = hash_message_to_int(msg1.encode('utf-8'), ECDSA_PARAMS.n)
            h2 = hash_message_to_int(msg2.encode('utf-8'), ECDSA_PARAMS.n)
            
            st.write(f"**Bước 1**: Hash của 2 tin nhắn")
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.write(f"$h_1 = H(msg_1) = {h1}$")
            with col_h2:
                st.write(f"$h_2 = H(msg_2) = {h2}$")
            
            k_recovered = recover_nonce_from_reuse(h1, h2, s1, s2, ECDSA_PARAMS.n)
            st.success(f"✅ **Bước 2**: Phục hồi nonce $k' = {k_recovered}$")
            if k_recovered == k_reuse:
                st.caption("✓ Nonce được phục hồi chính xác!")
            
            d_recovered = recover_private_key_from_nonce(h1, r1, s1, k_recovered, ECDSA_PARAMS.n)
            st.success(f"✅ **Bước 3**: Phục hồi khóa bí mật $d' = {d_recovered}$")
            
            st.divider()
            
            if d_victim == d_recovered:
                st.success(f"""
                🎯 **TẤN CÔNG THÀNH CÔNG!**
                
                Khóa bí mật đã bị lấy cắp:
                - Giá trị khôi phục: d' = {d_recovered}
                - Giá trị thực tế: d = {d_victim}
                - **Trùng khớp 100%**
                """)
            else:
                st.error("Tấn công thất bại. Giá trị khôi phục không khớp.")
                
        except Exception as e:
            st.error(f"❌ Lỗi mô phỏng: {e}")
    
    render_learning_summary("Reused Nonce Attack", [
        "Nonce trong ECDSA phải là **duy nhất** cho từng chữ ký",
        "Tái sử dụng nonce là **lỗi tham khảo** có thể dẫn đến lộ khóa bí mật",
        "Bitcoin/Ethereum sử dụng RNG cao cấp để tránh tái sử dụng nonce",
        "Một số ví cũ có bug nonce đã bị lợi dụng để ăn cắp tiền"
    ])


# ============= DEMO 4: SHAMIR'S TRICK =============
def demo_shamir_trick():
    """Minh họa tối ưu hóa bằng Shamir's Trick."""
    st.title("4️⃣ Tối ưu hóa Shamir's Trick")
    
    st.markdown("""
    **Vấn đề**: 
    Xác minh ECDSA yêu cầu tính $X = u_1G + u_2Q$.
    Cách **truyền thống** (Naive): Tính $u_1G$ và $u_2Q$ độc lập, rồi cộng.
    
    **Giải pháp - Shamir's Trick**:
    Kết hợp các vòng lặp bit của $u_1$ và $u_2$ để tính đồng thời.
    Kết quả: **Giảm đáng kể** số phép nhân đôi điểm (Doublings).
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        u1_demo = st.number_input("Hệ số u₁", value=13, min_value=1)
    with col2:
        u2_demo = st.number_input("Hệ số u₂", value=19, min_value=1)
    
    Q_demo2 = ECDSA_PARAMS.curve.scalar_mul(5, ECDSA_PARAMS.G)
    st.caption(f"Q = 5 × G = ({Q_demo2.x}, {Q_demo2.y})")
    
    if st.button("📊 Chạy so sánh hiệu năng"):
        # Naive method
        ECDSA_PARAMS.curve.reset_counters()
        p_naive = naive_mul_add(ECDSA_PARAMS.curve, u1_demo, ECDSA_PARAMS.G, u2_demo, Q_demo2)
        naive_add, naive_double = ECDSA_PARAMS.curve.add_count, ECDSA_PARAMS.curve.double_count
        
        # Shamir method
        ECDSA_PARAMS.curve.reset_counters()
        p_shamir = shamir_mul(ECDSA_PARAMS.curve, u1_demo, ECDSA_PARAMS.G, u2_demo, Q_demo2)
        shamir_add, shamir_double = ECDSA_PARAMS.curve.add_count, ECDSA_PARAMS.curve.double_count
        
        # Prepare data
        comparison_data = {
            "Phương pháp": ["Naive"] * 2 + ["Shamir's Trick"] * 2,
            "Phép toán": ["Cộng điểm", "Nhân đôi", "Cộng điểm", "Nhân đôi"],
            "Số lượng": [naive_add, naive_double, shamir_add, shamir_double]
        }
        df_comp = pd.DataFrame(comparison_data)
        
        fig = px.bar(df_comp, x="Phương pháp", y="Số lượng", color="Phép toán", 
                     barmode="group", text_auto=True,
                     title="So sánh khối lượng tính toán (Càng thấp càng tốt)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary
        st.divider()
        col_save1, col_save2, col_save3 = st.columns(3)
        
        with col_save1:
            st.metric("Tiết kiệm Cộng", naive_add - shamir_add, 
                     f"{((naive_add - shamir_add) / naive_add * 100):.1f}%")
        with col_save2:
            st.metric("Tiết kiệm Nhân đôi", naive_double - shamir_double,
                     f"{((naive_double - shamir_double) / naive_double * 100):.1f}%")
        with col_save3:
            total_saved = (naive_add - shamir_add) + (naive_double - shamir_double)
            st.metric("Tổng phép toán tiết kiệm", total_saved, "")
        
        st.success(f"""
        ✅ **Kết luận**: Nhờ tính đồng thời, Shamir's Trick đã giảm được 
        **{naive_add - shamir_add} phép cộng** và **{naive_double - shamir_double} phép nhân đôi** 
        so với cách tính truyền thống!
        """)
    
    render_learning_summary("Shamir's Trick", [
        "Shamir's Trick là kỹ thuật tối ưu hóa **phép cộng scalar**",
        "Giảm số lần thực hiện phép **nhân đôi** vốn rất tốn kém",
        "Được sử dụng trong các thư viện mật mã hiệu năng cao (libsecp256k1, etc)",
        "Tiết kiệm ~20-30% chi phí tính toán trong thực tế"
    ])


# ============= HELPER: PARSE BENCHMARK =============
def parse_benchmark_file(file_path):
    """Parse OpenSSL benchmark file và trích xuất dữ liệu."""
    benchmarks = {
        "RSA": [],
        "ECDSA": []
    }
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Parse data lines (chứa "bits" và số liệu)
            if "bits" in line and ("rsa" in line.lower() or "ecdsa" in line.lower()):
                parts = line.split()
                
                # Xác định algorithm name
                if "rsa" in line.lower():
                    algo_name = f"RSA {parts[1]}"
                    try:
                        sign_time = float(parts[-4].replace('s', ''))
                        verify_time = float(parts[-3].replace('s', ''))
                        sign_per_sec = float(parts[-2])
                        verify_per_sec = float(parts[-1])
                        
                        benchmark_data = {
                            "name": algo_name,
                            "sign_time": sign_time * 1000,
                            "verify_time": verify_time * 1000,
                            "sign_per_sec": sign_per_sec,
                            "verify_per_sec": verify_per_sec
                        }
                        benchmarks["RSA"].append(benchmark_data)
                    except (ValueError, IndexError):
                        continue
                else:
                    # ECDSA
                    try:
                        bit_size = parts[0]
                        curve_name = " ".join(parts[1:-4])
                        algo_name = f"{bit_size}b {curve_name}"
                        
                        sign_time = float(parts[-4].replace('s', ''))
                        verify_time = float(parts[-3].replace('s', ''))
                        sign_per_sec = float(parts[-2])
                        verify_per_sec = float(parts[-1])
                        
                        benchmark_data = {
                            "name": algo_name,
                            "sign_time": sign_time * 1000,
                            "verify_time": verify_time * 1000,
                            "sign_per_sec": sign_per_sec,
                            "verify_per_sec": verify_per_sec
                        }
                        benchmarks["ECDSA"].append(benchmark_data)
                    except (ValueError, IndexError):
                        continue
        
        return benchmarks
    except Exception as e:
        st.error(f"Lỗi parse file: {e}")
        return None


# ============= DEMO 5: OPENSSL DEMO =============
def demo_openssl_summary():
    """Hiển thị kết quả thực nghiệm OpenSSL với visualization."""
    st.title("5️⃣ Thực nghiệm OpenSSL trên secp256k1")
    
    st.markdown("""
    Dự án sử dụng OpenSSL để minh họa quy trình ký ECDSA trên **đường cong chuẩn Bitcoin** (`secp256k1`).
    Đồng thời benchmark tốc độ so với RSA.
    """)
    
    with st.expander("🔧 Các lệnh đã thực thi"):
        st.code("""
.\openssl_demo\gen_keys.ps1
.\openssl_demo\sign_verify.ps1
.\openssl_demo\benchmark.ps1
        """, language="powershell")
    
    benchmark_file = os.path.join("results", "openssl_benchmark.txt")
    
    if os.path.exists(benchmark_file):
        benchmarks = parse_benchmark_file(benchmark_file)
        
        if benchmarks and (benchmarks["RSA"] or benchmarks["ECDSA"]):
            # Chart 1: Sign Time
            st.subheader("📊 So sánh Hiệu năng Ký (Sign Time)")
            
            rsa_data = benchmarks["RSA"]
            ecdsa_data = benchmarks["ECDSA"][:6] if len(benchmarks["ECDSA"]) > 6 else benchmarks["ECDSA"]
            
            all_algos = []
            all_times = []
            all_colors = []
            
            for item in rsa_data:
                all_algos.append(item["name"])
                all_times.append(item["sign_time"])
                all_colors.append("RSA")
            
            for item in ecdsa_data:
                all_algos.append(item["name"])
                all_times.append(item["sign_time"])
                all_colors.append("ECDSA")
            
            df_sign = pd.DataFrame({
                "Algorithm": all_algos,
                "Sign Time (ms)": all_times,
                "Type": all_colors
            })
            
            fig_sign = px.bar(df_sign, x="Algorithm", y="Sign Time (ms)", color="Type",
                             color_discrete_map={"RSA": "#EF553B", "ECDSA": "#00CC96"},
                             title="Thời gian Ký - Càng thấp càng tốt",
                             labels={"Algorithm": "Thuật toán", "Sign Time (ms)": "Thời gian (ms)"})
            fig_sign.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_sign, use_container_width=True)
            
            # Chart 2: Verify Time
            st.subheader("📊 So sánh Hiệu năng Xác minh (Verify Time)")
            
            all_algos_v = []
            all_times_v = []
            all_colors_v = []
            
            for item in rsa_data:
                all_algos_v.append(item["name"])
                all_times_v.append(item["verify_time"])
                all_colors_v.append("RSA")
            
            for item in ecdsa_data:
                all_algos_v.append(item["name"])
                all_times_v.append(item["verify_time"])
                all_colors_v.append("ECDSA")
            
            df_verify = pd.DataFrame({
                "Algorithm": all_algos_v,
                "Verify Time (ms)": all_times_v,
                "Type": all_colors_v
            })
            
            fig_verify = px.bar(df_verify, x="Algorithm", y="Verify Time (ms)", color="Type",
                               color_discrete_map={"RSA": "#EF553B", "ECDSA": "#00CC96"},
                               title="Thời gian Xác minh - Càng thấp càng tốt",
                               labels={"Algorithm": "Thuật toán", "Verify Time (ms)": "Thời gian (ms)"})
            fig_verify.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_verify, use_container_width=True)
            
            # Chart 3: Speed
            st.subheader("📊 Tốc độ Ký (Operations/second) - Càng cao càng tốt")
            
            all_algos_speed = []
            all_speeds = []
            all_colors_speed = []
            
            for item in rsa_data:
                all_algos_speed.append(item["name"])
                all_speeds.append(item["sign_per_sec"])
                all_colors_speed.append("RSA")
            
            for item in ecdsa_data:
                all_algos_speed.append(item["name"])
                all_speeds.append(item["sign_per_sec"])
                all_colors_speed.append("ECDSA")
            
            df_speed = pd.DataFrame({
                "Algorithm": all_algos_speed,
                "Sign/s": all_speeds,
                "Type": all_colors_speed
            })
            
            fig_speed = px.bar(df_speed, x="Algorithm", y="Sign/s", color="Type",
                              color_discrete_map={"RSA": "#EF553B", "ECDSA": "#00CC96"},
                              title="Tốc độ Ký (ops/sec) - Càng cao càng tốt",
                              labels={"Algorithm": "Thuật toán", "Sign/s": "Số lần/giây"})
            fig_speed.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_speed, use_container_width=True)
            
            # Summary metrics
            st.divider()
            st.subheader("📈 Tóm tắt Kết quả")
            
            col1, col2, col3 = st.columns(3)
            
            if rsa_data and ecdsa_data:
                fastest_rsa = max(rsa_data, key=lambda x: x["sign_per_sec"])
                fastest_ecdsa = max(ecdsa_data, key=lambda x: x["sign_per_sec"])
                
                with col1:
                    st.metric(
                        "🏆 RSA Nhanh nhất",
                        fastest_rsa["name"],
                        f"{fastest_rsa['sign_per_sec']:.0f} ops/s"
                    )
                
                with col2:
                    st.metric(
                        "🏆 ECDSA Nhanh nhất",
                        fastest_ecdsa["name"],
                        f"{fastest_ecdsa['sign_per_sec']:.0f} ops/s"
                    )
                
                with col3:
                    speedup = fastest_ecdsa["sign_per_sec"] / fastest_rsa["sign_per_sec"]
                    st.metric(
                        "⚡ ECDSA nhanh hơn RSA",
                        f"{speedup:.1f}x",
                        ""
                    )
            
            st.divider()
            
            # Detailed tables
            st.subheader("📋 Bảng Chi tiết")
            
            tab1, tab2 = st.tabs(["RSA", "ECDSA"])
            
            with tab1:
                if rsa_data:
                    df_rsa_table = pd.DataFrame(rsa_data)
                    df_rsa_table = df_rsa_table[["name", "sign_time", "verify_time", "sign_per_sec", "verify_per_sec"]]
                    df_rsa_table.columns = ["Algorithm", "Sign (ms)", "Verify (ms)", "Sign/s", "Verify/s"]
                    st.dataframe(df_rsa_table, use_container_width=True)
                else:
                    st.info("Không có dữ liệu RSA")
            
            with tab2:
                if ecdsa_data:
                    df_ecdsa_table = pd.DataFrame(ecdsa_data)
                    df_ecdsa_table = df_ecdsa_table[["name", "sign_time", "verify_time", "sign_per_sec", "verify_per_sec"]]
                    df_ecdsa_table.columns = ["Algorithm", "Sign (ms)", "Verify (ms)", "Sign/s", "Verify/s"]
                    st.dataframe(df_ecdsa_table, use_container_width=True)
                else:
                    st.info("Không có dữ liệu ECDSA")
            
            with st.expander("💡 Phân tích kết quả"):
                st.markdown("""
                **Nhận xét chính**:
                
                1. **ECDSA Nhanh Hơn**: ECDSA (đặc biệt nistp256) **nhanh hơn 20-40x** so với RSA 2048 trong phép ký
                
                2. **Kích thước Khóa Nhỏ**: 
                   - RSA 2048 ≈ ECDSA 256 (về mức độ bảo mật)
                   - Nhưng ECDSA 256-bit nhỏ gọn hơn nhiều
                
                3. **Ứng dụng Bitcoin**:
                   - Bitcoin sử dụng `secp256k1` (256-bit ECDSA)
                   - Lý do: Tốc độ nhanh + kích thước chữ ký nhỏ
                   - Chữ ký Bitcoin: ~64 byte vs RSA ~256 byte
                   - Tiết kiệm dung lượng blockchain
                
                4. **Kết luận**: ECDSA là lựa chọn tối ưu cho:
                   - ✅ Blockchain & Cryptocurrency
                   - ✅ IoT devices (tài nguyên hạn chế)
                   - ✅ High-frequency trading systems
                   - ✅ Bất cứ nơi nào cần tốc độ + hiệu quả
                """)
        else:
            st.warning("⚠️ Không thể parse dữ liệu từ file benchmark")
    else:
        st.warning(f"""
        ⚠️ Không tìm thấy file `results/openssl_benchmark.txt`.
        
        Để tạo file này, chạy lệnh trong PowerShell:
        ```powershell
        cd f:\CAC_Project
        .\openssl_demo\benchmark.ps1
        ```
        """)
    
    render_learning_summary("OpenSSL Demo", [
        "OpenSSL là thư viện mã nguồn mở, được sử dụng rộng rãi trong thực tế",
        "`secp256k1` là đường cong tiêu chuẩn được Bitcoin chọn",
        "ECDSA có lợi thế lớn về kích thước & tốc độ so với RSA",
        "Hiểu được hiệu năng thực tế giúp thiết kế hệ thống tốt hơn"
    ])


# ============= MAIN APPLICATION =============
def main():
    # Initialize session state
    if "page_id" not in st.session_state:
        st.session_state.page_id = 0
    
    render_header(st.session_state.page_id)
    
    # Page dispatcher
    page_id = st.session_state.page_id
    
    if page_id == 0:
        demo_ecc_toy_curve()
    elif page_id == 1:
        demo_ecdsa_sign_verify()
    elif page_id == 2:
        demo_reused_nonce_attack()
    elif page_id == 3:
        demo_shamir_trick()
    elif page_id == 4:
        demo_openssl_summary()
    
    st.divider()
    render_navigation(st.session_state.page_id)


if __name__ == "__main__":
    main()
