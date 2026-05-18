import sys
import os
import shutil
import subprocess
import tempfile
import time
from math import gcd
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.express as px
import pandas as pd

from src.ecc import Curve, Point
from src.ecdsa_toy import ECDSAParams, sign, verify, hash_message_to_int
from src.shamir import naive_mul_add, shamir_mul

# ============= CẤU HÌNH TRANG =============
st.set_page_config(page_title="🔐 ECC/ECDSA - Mô phỏng Tương tác", layout="wide")

# ============= GLOBAL PARAMETERS =============
# Đường cong Toy: y^2 = x^3 + 7 mod 223
# Được chọn để chạy nhanh nhưng đủ để minh họa các khái niệm
TOY_CURVE = Curve(p=223, a=0, b=7)
GENERATOR_POINT = Point(47, 71)
ORDER_N = 21
# TODO: Có thể thay toy curve bằng một subgroup có prime order để demo ECDSA ít edge case hơn.
# Nhưng khi đổi n phải chọn lại G sao cho order(G) = n.
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


def safe_mod_inverse(a, n):
    """Trả về nghịch đảo modulo nếu tồn tại, ngược lại trả về None."""
    a = a % n
    if gcd(a, n) != 1:
        return None
    try:
        return pow(a, -1, n)
    except ValueError:
        return None


def validate_nonce(k, n):
    """Kiểm tra nonce k có hợp lệ với modulo n hay không."""
    if not isinstance(k, int):
        return False, "Nonce k phải là số nguyên."
    if not (1 <= k < n):
        return False, f"Nonce k phải nằm trong khoảng 1 <= k < n, với n = {n}."
    if gcd(k, n) != 1:
        return False, (
            "Nonce k không hợp lệ vì không tồn tại nghịch đảo modulo n. "
            "Trong ECDSA, k phải khả nghịch modulo n. Với toy demo n = 21 là hợp số "
            "nên nhiều k không có nghịch đảo; đây là hạn chế của mô hình minh họa, "
            "không phải lỗi của ECDSA thật."
        )
    return True, ""


def can_run_reused_nonce_attack(msg1, msg2, h1, h2, r1, s1, r2, s2, n):
    """Kiểm tra các điều kiện toán học trước khi khôi phục k và d."""
    if msg1 == msg2:
        return False, (
            "Hai thông điệp giống nhau tạo ra cùng hash modulo n và thường tạo ra hai chữ ký "
            "giống nhau khi dùng cùng nonce. Khi đó ta không có hai phương trình độc lập để "
            "khôi phục nonce k hoặc private key d. Reused Nonce Attack chỉ có ý nghĩa khi "
            "cùng một nonce k được dùng cho hai thông điệp khác nhau."
        )
    if h1 == h2:
        return False, (
            "Hai thông điệp tuy khác nhau nhưng lại có cùng hash modulo n trong toy demo này. "
            "Vì h1 - h2 = 0, công thức khôi phục nonce không cung cấp đủ thông tin để tìm lại k. "
            "Đây là do n = 21 quá nhỏ; hãy thử đổi nội dung một trong hai tin nhắn."
        )
    if r1 != r2:
        return False, (
            "Hai chữ ký không có cùng r, nên UI không xem đây là mẫu reused nonce hợp lệ để tấn công."
        )
    if s1 == s2:
        return False, (
            "Hai chữ ký có s1 = s2 nên s1 - s2 = 0. Không thể lấy nghịch đảo của 0 modulo n, "
            "và không đủ thông tin để khôi phục nonce."
        )

    s_diff = (s1 - s2) % n
    if gcd(s_diff, n) != 1:
        return False, (
            f"Không thể khôi phục nonce vì s1 - s2 = {s_diff} modulo {n} không có nghịch đảo. "
            "Đây là edge case của toy curve với n = 21 là hợp số. Trong secp256k1 thật, n là "
            "order nguyên tố rất lớn nên các mẫu hợp lệ không gặp hạn chế này."
        )
    if gcd(r1 % n, n) != 1:
        return False, (
            f"Không thể khôi phục private key vì r = {r1 % n} không có nghịch đảo modulo {n}. "
            "Đây là hạn chế của toy curve n = 21, không phải lỗi của ECDSA thật."
        )
    return True, ""


def get_openssl_path():
    """Tìm executable OpenSSL trong PATH."""
    return shutil.which("openssl")


def run_openssl_cmd(args, cwd=None):
    """Chạy lệnh OpenSSL bằng subprocess list args, không dùng shell."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        return True, result
    except FileNotFoundError:
        return False, "Không tìm thấy OpenSSL trong PATH."
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        if not details:
            details = f"Lệnh trả về mã lỗi {exc.returncode}."
        return False, f"OpenSSL không thực thi thành công: {details}"


def openssl_version(openssl_path):
    """Lấy chuỗi phiên bản OpenSSL."""
    ok, result = run_openssl_cmd([openssl_path, "version"])
    if not ok:
        return result
    return result.stdout.strip()


def run_openssl_secp256k1_experiment(message: str, iterations: int):
    """Ký, verify và benchmark ECDSA secp256k1 bằng OpenSSL thật."""
    openssl_path = get_openssl_path()
    if not openssl_path:
        return {"error": "Không tìm thấy OpenSSL trong PATH."}

    iterations = max(1, int(iterations))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        private_key = tmp_path / "ec_private.pem"
        public_key = tmp_path / "ec_public.pem"
        message_file = tmp_path / "message.txt"
        signature_file = tmp_path / "sig.bin"

        message_file.write_text(message, encoding="utf-8")

        commands = [
            [openssl_path, "ecparam", "-name", "secp256k1", "-genkey", "-noout", "-out", private_key.name],
            [openssl_path, "ec", "-in", private_key.name, "-pubout", "-out", public_key.name],
            [openssl_path, "dgst", "-sha256", "-sign", private_key.name, "-out", signature_file.name, message_file.name],
            [openssl_path, "dgst", "-sha256", "-verify", public_key.name, "-signature", signature_file.name, message_file.name],
        ]

        for command in commands:
            ok, result = run_openssl_cmd(command, cwd=tmpdir)
            if not ok:
                return {"error": result}

        signature_hex = signature_file.read_bytes().hex()
        version = openssl_version(openssl_path)

        sign_start = time.perf_counter()
        for _ in range(iterations):
            ok, result = run_openssl_cmd(
                [openssl_path, "dgst", "-sha256", "-sign", private_key.name, "-out", signature_file.name, message_file.name],
                cwd=tmpdir,
            )
            if not ok:
                return {"error": result}
        sign_total_time = time.perf_counter() - sign_start

        verify_start = time.perf_counter()
        verify_success = True
        for _ in range(iterations):
            ok, result = run_openssl_cmd(
                [openssl_path, "dgst", "-sha256", "-verify", public_key.name, "-signature", signature_file.name, message_file.name],
                cwd=tmpdir,
            )
            if not ok:
                verify_success = False
                return {"error": result}
        verify_total_time = time.perf_counter() - verify_start

        sign_avg_ms = (sign_total_time / iterations) * 1000
        verify_avg_ms = (verify_total_time / iterations) * 1000

        return {
            "openssl_version": version,
            "curve": "secp256k1",
            "hash": "SHA-256",
            "message": message,
            "signature_hex": signature_hex,
            "verify_success": verify_success,
            "sign_total_time": sign_total_time,
            "sign_avg_ms": sign_avg_ms,
            "verify_total_time": verify_total_time,
            "verify_avg_ms": verify_avg_ms,
            "sign_ops_per_sec": iterations / sign_total_time if sign_total_time > 0 else 0,
            "verify_ops_per_sec": iterations / verify_total_time if verify_total_time > 0 else 0,
        }


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
    - Khóa công khai (Public Key): điểm $Q$ trên đường cong, tính bằng $Q = d \\cdot G$
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
        "Phép nhân vô hướng $d \\cdot G$ dựa trên phép cộng điểm (Point Addition)",
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
    
    with st.expander("ℹ️ Lưu ý về toy order n = 21", expanded=True):
        st.info(
            "Trong ECDSA thật trên secp256k1, n là order nguyên tố rất lớn. Vì vậy mọi k "
            "trong khoảng 1 <= k < n đều khả nghịch modulo n. Còn trong toy demo này, "
            "n = 21 là hợp số nên các giá trị như 3, 7, 14... không có nghịch đảo modulo 21."
        )
    
    col_key, col_nonce = st.columns(2)
    with col_key:
        d_victim = int(st.number_input(
            "🔑 Private key d",
            min_value=1,
            max_value=ORDER_N - 1,
            value=2,
            step=1,
        ))
    with col_nonce:
        k_reuse = int(st.number_input(
            "🎲 Nonce k dùng lại",
            min_value=1,
            max_value=ORDER_N - 1,
            value=4,
            step=1,
        ))
    
    col1, col2 = st.columns(2)
    with col1:
        msg1 = st.text_input("📝 Tin nhắn 1", value="Thanh toan 1 BTC cho Alice", max_chars=100)
    with col2:
        msg2 = st.text_input("📝 Tin nhắn 2", value="Thanh toan 2 BTC cho Bob", max_chars=100)
    
    if st.button("⚡ Tiến hành mô phỏng tấn công"):
        is_valid_nonce, nonce_message = validate_nonce(k_reuse, ECDSA_PARAMS.n)
        if not is_valid_nonce:
            st.warning(nonce_message)
        else:
            st.info(f"🔍 **Giả sử**: Nạn nhân dùng d = {d_victim} và vô tình dùng lại nonce k = {k_reuse}")

            try:
                r1, s1 = sign(ECDSA_PARAMS, d_victim, msg1.encode("utf-8"), k=k_reuse)
                r2, s2 = sign(ECDSA_PARAMS, d_victim, msg2.encode("utf-8"), k=k_reuse)
            except ValueError as sign_error:
                raw_message = str(sign_error)
                if "r=0" in raw_message:
                    st.warning(
                        "Tham số đang chọn tạo ra r = 0 nên chữ ký ECDSA không hợp lệ. "
                        "Đây là edge case của toy curve n = 21; hãy thử private key hoặc nonce khác."
                    )
                elif "s=0" in raw_message or "not coprime" in raw_message:
                    st.warning(
                        "Tham số đang chọn tạo ra giá trị s không khả nghịch modulo n, nên toy ECDSA "
                        "không thể tạo chữ ký hợp lệ. Đây là hạn chế của demo n = 21 là hợp số."
                    )
                else:
                    st.warning(
                        "Không thể tạo chữ ký hợp lệ với tham số hiện tại trên toy curve n = 21. "
                        "Hãy thử private key, nonce hoặc message khác."
                    )
            else:
                h1 = hash_message_to_int(msg1.encode("utf-8"), ECDSA_PARAMS.n)
                h2 = hash_message_to_int(msg2.encode("utf-8"), ECDSA_PARAMS.n)

                col_sig1, col_sig2 = st.columns(2)
                with col_sig1:
                    st.info(f"**Chữ ký 1 (msg1):**\n- h₁ = {h1}\n- r₁ = {r1}\n- s₁ = {s1}")
                with col_sig2:
                    st.info(f"**Chữ ký 2 (msg2):**\n- h₂ = {h2}\n- r₂ = {r2}\n- s₂ = {s2}")

                if r1 == r2:
                    st.warning(
                        f"⚠️ Cả 2 chữ ký đều có r = {r1}. Đây là dấu hiệu nonce k bị dùng lại. "
                        "Ta cần kiểm tra thêm hash và s1, s2 để xem có đủ điều kiện khôi phục khóa hay không."
                    )

                st.divider()
                st.subheader("🔓 Kiểm tra điều kiện khôi phục")

                s_diff_mod = (s1 - s2) % ECDSA_PARAMS.n
                diagnostic_rows = [
                    {
                        "Điều kiện": "msg1 != msg2",
                        "Giá trị": str(msg1 != msg2),
                        "Kết luận": "OK" if msg1 != msg2 else "Không đủ hai thông điệp độc lập",
                    },
                    {
                        "Điều kiện": "h1 != h2",
                        "Giá trị": str(h1 != h2),
                        "Kết luận": "OK" if h1 != h2 else "Hash collision modulo n; không đủ thông tin khôi phục k",
                    },
                    {
                        "Điều kiện": "r1 == r2",
                        "Giá trị": str(r1 == r2),
                        "Kết luận": "OK" if r1 == r2 else "Không có dấu hiệu dùng lại nonce",
                    },
                    {
                        "Điều kiện": "s1 != s2",
                        "Giá trị": str(s1 != s2),
                        "Kết luận": "OK" if s1 != s2 else "s1 - s2 = 0; không thể lấy nghịch đảo",
                    },
                    {
                        "Điều kiện": "gcd(s1 - s2, n) == 1",
                        "Giá trị": f"gcd({s_diff_mod}, {ECDSA_PARAMS.n}) = {gcd(s_diff_mod, ECDSA_PARAMS.n)}",
                        "Kết luận": "OK" if gcd(s_diff_mod, ECDSA_PARAMS.n) == 1 else "s1 - s2 không khả nghịch modulo n",
                    },
                    {
                        "Điều kiện": "gcd(r1, n) == 1",
                        "Giá trị": f"gcd({r1 % ECDSA_PARAMS.n}, {ECDSA_PARAMS.n}) = {gcd(r1 % ECDSA_PARAMS.n, ECDSA_PARAMS.n)}",
                        "Kết luận": "OK" if gcd(r1 % ECDSA_PARAMS.n, ECDSA_PARAMS.n) == 1 else "r1 không khả nghịch modulo n",
                    },
                ]
                st.dataframe(pd.DataFrame(diagnostic_rows), use_container_width=True)

                can_recover, reason = can_run_reused_nonce_attack(
                    msg1, msg2, h1, h2, r1, s1, r2, s2, ECDSA_PARAMS.n
                )

                if not can_recover:
                    st.warning(reason)
                    st.dataframe(pd.DataFrame([
                        {"Giá trị": "h1", "Kết quả": h1},
                        {"Giá trị": "h2", "Kết quả": h2},
                        {"Giá trị": "r1, s1", "Kết quả": f"{r1}, {s1}"},
                        {"Giá trị": "r2, s2", "Kết quả": f"{r2}, {s2}"},
                        {"Giá trị": "k gốc", "Kết quả": k_reuse},
                        {"Giá trị": "private key gốc", "Kết quả": d_victim},
                    ]), use_container_width=True)
                else:
                    s_diff_inv = safe_mod_inverse(s1 - s2, ECDSA_PARAMS.n)
                    r_inv = safe_mod_inverse(r1, ECDSA_PARAMS.n)

                    if s_diff_inv is None or r_inv is None:
                        st.warning(
                            "Không thể chạy attack vì một mẫu số không có nghịch đảo modulo n. "
                            "UI đã dừng trước khi gọi công thức khôi phục để tránh lỗi kỹ thuật."
                        )
                    else:
                        k_recovered = ((h1 - h2) * s_diff_inv) % ECDSA_PARAMS.n
                        d_recovered = ((s1 * k_recovered - h1) * r_inv) % ECDSA_PARAMS.n

                        st.success(f"✅ Khôi phục nonce: k' = {k_recovered}")
                        st.success(f"✅ Khôi phục private key: d' = {d_recovered}")

                        result_rows = [
                            {"Giá trị": "h1", "Kết quả": h1},
                            {"Giá trị": "h2", "Kết quả": h2},
                            {"Giá trị": "r1, s1", "Kết quả": f"{r1}, {s1}"},
                            {"Giá trị": "r2, s2", "Kết quả": f"{r2}, {s2}"},
                            {"Giá trị": "k gốc", "Kết quả": k_reuse},
                            {"Giá trị": "k khôi phục", "Kết quả": k_recovered},
                            {"Giá trị": "private key gốc", "Kết quả": d_victim},
                            {"Giá trị": "private key khôi phục", "Kết quả": d_recovered},
                        ]
                        st.dataframe(pd.DataFrame(result_rows), use_container_width=True)

                        if k_recovered == k_reuse and d_recovered == d_victim:
                            st.success("🎯 **Khớp — tấn công thành công**")
                        else:
                            st.error("Không khớp — do giới hạn của toy curve / tham số không phù hợp")
    
    render_learning_summary("Reused Nonce Attack", [
        "Nonce k trong ECDSA phải là **duy nhất** cho mỗi chữ ký",
        "Reuse nonce với **hai thông điệp khác nhau** có thể làm lộ private key",
        "Nếu hai message giống nhau thì không tạo ra hai phương trình độc lập để khôi phục k hoặc d",
        "Toy curve n = 21 chỉ dùng để minh họa, có nhiều edge case toán học không xuất hiện trong secp256k1 thật"
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
def render_static_openssl_benchmark():
    """Hiển thị kết quả benchmark OpenSSL đã lưu sẵn."""
    st.markdown("""
    Kết quả benchmark cố định từ `results/openssl_benchmark.txt`, dùng để so sánh ECDSA với RSA.
    """)
    
    with st.expander("🔧 Các lệnh đã thực thi"):
        st.code("""
.\\openssl_demo\\gen_keys.ps1
.\\openssl_demo\\sign_verify.ps1
.\\openssl_demo\\benchmark.ps1
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
        
        Để tạo file này, chạy lệnh trong PowerShell từ thư mục gốc của repo:
        ```powershell
        .\\openssl_demo\\benchmark.ps1
        ```
        """)


def demo_openssl_summary():
    """Hiển thị kết quả thực nghiệm OpenSSL với visualization."""
    st.title("5️⃣ Thực nghiệm OpenSSL trên secp256k1")
    
    st.markdown("""
    Phần này chạy ECDSA thật trên **secp256k1** bằng OpenSSL, khác với toy curve `n = 21`
    ở các phần trước. `secp256k1` là đường cong được Bitcoin sử dụng. OpenSSL là thư viện
    tối ưu nên kết quả benchmark phản ánh thực nghiệm hệ thống tốt hơn mô phỏng Python toy.
    """)
    
    tab_static, tab_interactive = st.tabs([
        " Kết quả benchmark có sẵn",
        " Thực nghiệm tương tác",
    ])
    
    with tab_static:
        render_static_openssl_benchmark()
    
    with tab_interactive:
        openssl_path = get_openssl_path()
        if not openssl_path:
            st.error("Không tìm thấy OpenSSL trong PATH.")
            st.info("Hãy cài OpenSSL và đảm bảo lệnh openssl chạy được trong terminal/PowerShell.")
        else:
            st.info(f"OpenSSL version: `{openssl_version(openssl_path)}`")
            message = st.text_area("Message", value="Hello Bitcoin", height=100)
            iterations = int(st.number_input(
                "Số lần benchmark",
                min_value=1,
                max_value=1000,
                value=100,
                step=10,
            ))
            
            if st.button(" Chạy thực nghiệm OpenSSL"):
                with st.spinner("Đang tạo key, ký, verify và benchmark bằng OpenSSL..."):
                    result = run_openssl_secp256k1_experiment(message, iterations)
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    if result["verify_success"]:
                        st.success("Verify thành công.")
                    else:
                        st.error("Verify thất bại.")
                    
                    signature_hex = result["signature_hex"]
                    signature_display = (
                        f"{signature_hex[:80]}..." if len(signature_hex) > 80 else signature_hex
                    )
                    st.code(signature_display, language="text")
                    
                    metrics_df = pd.DataFrame([
                        {"Metric": "OpenSSL version", "Value": result["openssl_version"]},
                        {"Metric": "Curve", "Value": result["curve"]},
                        {"Metric": "Hash", "Value": result["hash"]},
                        {"Metric": "Verify", "Value": "Success" if result["verify_success"] else "Failed"},
                        {"Metric": "Sign total time", "Value": f"{result['sign_total_time'] * 1000:.3f} ms"},
                        {"Metric": "Sign avg", "Value": f"{result['sign_avg_ms']:.3f} ms/op"},
                        {"Metric": "Sign speed", "Value": f"{result['sign_ops_per_sec']:.2f} ops/s"},
                        {"Metric": "Verify total time", "Value": f"{result['verify_total_time'] * 1000:.3f} ms"},
                        {"Metric": "Verify avg", "Value": f"{result['verify_avg_ms']:.3f} ms/op"},
                        {"Metric": "Verify speed", "Value": f"{result['verify_ops_per_sec']:.2f} ops/s"},
                    ])
                    st.dataframe(metrics_df, use_container_width=True)
                    
                    chart_df = pd.DataFrame([
                        {"Operation": "Sign avg ms/op", "Average ms/op": result["sign_avg_ms"]},
                        {"Operation": "Verify avg ms/op", "Average ms/op": result["verify_avg_ms"]},
                    ])
                    fig = px.bar(
                        chart_df,
                        x="Operation",
                        y="Average ms/op",
                        title="OpenSSL secp256k1: Sign vs Verify",
                        labels={"Operation": "Thao tác", "Average ms/op": "ms/op"},
                    )
                    st.plotly_chart(fig, use_container_width=True)

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
