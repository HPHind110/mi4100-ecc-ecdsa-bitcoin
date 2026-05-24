import sys
import os
import copy
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

from src.ecdsa_toy import sign, verify, hash_message_to_int
from src.shamir import naive_mul_add, shamir_mul
from src.demo_params import DEMO_A, DEMO_B, DEMO_P, get_demo_params
from src.bitcoin_tx import (
    OutPoint,
    Transaction,
    TxInput,
    TxOutput,
    UTXOSet,
    pubkey_hash_demo,
    serialize_unsigned_tx,
    sign_transaction_input,
    txid_demo,
    verify_transaction_input,
)

# ============= CẤU HÌNH TRANG =============
st.set_page_config(page_title="🔐 ECC/ECDSA - Mô phỏng Tương tác", layout="wide")

# ============= GLOBAL PARAMETERS =============
# Đường cong toy prime-order, dùng chung cho toàn bộ demo giáo dục.
ECDSA_PARAMS = get_demo_params()
TOY_CURVE = ECDSA_PARAMS.curve
GENERATOR_POINT = ECDSA_PARAMS.G
ORDER_N = ECDSA_PARAMS.n

# Danh sách demos
DEMOS = [
    {"id": 0, "title": "0. Big Picture", "desc": "Bài toán sở hữu trong Bitcoin"},
    {"id": 1, "title": "1. Ownership in Bitcoin", "desc": "UTXO spending authority"},
    {"id": 2, "title": "2. ECC: Q = dG", "desc": "Private key sinh public key"},
    {"id": 3, "title": "3. ECDLP: Why Q does not reveal d", "desc": "Độ khó đảo ngược"},
    {"id": 4, "title": "4. ECDSA Sign/Verify", "desc": "Ký và xác minh thông điệp"},
    {"id": 5, "title": "5. Mini Bitcoin Transaction Signing", "desc": "Toy UTXO + chữ ký ECDSA"},
    {"id": 6, "title": "6. ECDSA Reused Nonce Attack", "desc": "Tấn công tái sử dụng nonce"},
    {"id": 7, "title": "7. Nonce Defense Notes", "desc": "Phòng thủ khi triển khai ECDSA"},
    {"id": 8, "title": "8. Shamir's Trick", "desc": "Tối ưu hóa verification"},
    {"id": 9, "title": "9. OpenSSL secp256k1 Demo", "desc": "Công cụ mật mã thật"},
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


def render_page_intro(question: str, idea: str, demo: str) -> None:
    """Hiển thị ba mục bắt buộc ở đầu mỗi trang theo storyline Q0-Q8."""
    st.markdown(f"**Câu hỏi**\n\n{question}")
    st.markdown(f"**Ý tưởng**\n\n{idea}")
    st.markdown(f"**Demo chứng minh điều gì?**\n\n{demo}")


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
            "Trong ECDSA, k phải khả nghịch modulo n."
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
            "Đây là do toy curve rất nhỏ; hãy thử đổi nội dung một trong hai tin nhắn."
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
            "Đây là edge case của toy curve rất nhỏ, không phải bài học chính của ECDSA thật."
        )
    if gcd(r1 % n, n) != 1:
        return False, (
            f"Không thể khôi phục private key vì r = {r1 % n} không có nghịch đảo modulo {n}. "
            "Đây là hạn chế của toy curve rất nhỏ, không phải lỗi của ECDSA thật."
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


# ============= PAGE 0: BIG PICTURE =============
def demo_big_picture():
    """Trang tổng quan bắt đầu từ bài toán sở hữu, không bắt đầu từ công thức."""
    st.title("0. Big Picture")
    render_page_intro(
        "Bitcoin cần giải bài toán gì trong môi trường không có ngân hàng trung gian?",
        "Điều cần chứng minh không phải là danh tính tài khoản, mà là quyền chi tiêu một tài sản số cụ thể.",
        "Trang này đặt toàn bộ mạch: Bitcoin ownership problem -> UTXO spending authority -> ECC -> ECDLP -> ECDSA -> transaction authentication.",
    )

    st.info(
        "Luận điểm trung tâm: Bitcoin không dùng ECC/ECDSA để mã hóa transaction. "
        "Bitcoin dùng ECDSA để xác thực spending authority."
    )

    storyline = [
        {"Step": "0", "Question": "Bitcoin cần giải bài toán gì?", "Answer": "Proof of spending authority"},
        {"Step": "1", "Question": "Ownership được biểu diễn thế nào?", "Answer": "Khả năng thỏa spending condition của UTXO"},
        {"Step": "2", "Question": "Private key tạo public key thế nào?", "Answer": "Q = dG trên elliptic curve group"},
        {"Step": "3", "Question": "Vì sao Q không lộ d?", "Answer": "ECDLP khó trên tham số thật như secp256k1"},
        {"Step": "4", "Question": "ECDSA hoạt động thế nào?", "Answer": "Private key ký, public key xác minh"},
        {"Step": "5", "Question": "ECDSA vào transaction thế nào?", "Answer": "Signature mở khóa UTXO trong toy P2PKH-like model"},
        {"Step": "6", "Question": "Triển khai sai thì sao?", "Answer": "Nonce reuse có thể làm lộ private key"},
        {"Step": "7", "Question": "Phòng thủ thế nào?", "Answer": "Nonce discipline, RFC6979-style, constant-time libraries"},
        {"Step": "8", "Question": "Có thể tối ưu verification không?", "Answer": "Shamir's trick cho u1G + u2Q"},
        {"Step": "9", "Question": "Toy math liên hệ công cụ thật thế nào?", "Answer": "OpenSSL secp256k1 message/file signing"},
    ]
    st.dataframe(pd.DataFrame(storyline), use_container_width=True)

    render_learning_summary("Big Picture", [
        "Bắt đầu từ bài toán sở hữu trong môi trường không tin cậy",
        "ECC/ECDSA là cơ chế chứng minh quyền chi tiêu, không phải cơ chế mã hóa transaction",
        "Mini transaction demo là lớp nối giữa chữ ký thông điệp và Bitcoin-like UTXO flow",
    ])


# ============= PAGE 1: OWNERSHIP IN BITCOIN =============
def demo_ownership_in_bitcoin():
    """Giải thích ownership theo UTXO spending condition."""
    st.title("1. Ownership in Bitcoin")
    render_page_intro(
        "Quyền sở hữu trong Bitcoin được biểu diễn thế nào?",
        "Ownership không phải username/password hay một balance field. Trong UTXO model, ownership là khả năng thỏa spending condition của một UTXO.",
        "Trang này làm rõ P2PKH-like educational model: locking condition là public key hash, unlocking data là signature + public key.",
    )

    st.warning(
        "P2PKH-like educational model only. Trong real Bitcoin, spending authority tổng quát hơn: "
        "nó nghĩa là thỏa script/spending condition tương ứng, không phải lúc nào cũng chỉ một chữ ký ECDSA."
    )

    model_rows = [
        {"Layer": "UTXO", "Meaning": "Một output chưa chi tiêu, có điều kiện khóa riêng"},
        {"Layer": "Locking condition", "Meaning": "Trong demo: public key hash của chủ sở hữu"},
        {"Layer": "Unlocking data", "Meaning": "Trong demo: signature + public key"},
        {"Layer": "Verification", "Meaning": "hash(public key) khớp lock và ECDSA signature hợp lệ"},
        {"Layer": "Accepted spend", "Meaning": "UTXO tồn tại, chưa spent, và spending condition được thỏa"},
    ]
    st.dataframe(pd.DataFrame(model_rows), use_container_width=True)

    st.info(
        "Ở bước này có thể xem ECDSA như black box: valid signature -> spending authority demonstrated; "
        "invalid signature -> spending authority not demonstrated."
    )

    render_learning_summary("Ownership in Bitcoin", [
        "Bitcoin-like ownership gắn với UTXO cụ thể",
        "Toy P2PKH-like model dùng public key hash làm điều kiện khóa",
        "Signature không chứng minh quyền chung chung; nó mở khóa một điều kiện chi tiêu cụ thể",
    ])


# ============= PAGE 2: ECC TOY CURVE =============
def demo_ecc_toy_curve():
    """Minh họa các điểm trên đường cong Elliptic."""
    st.title("2. ECC: Q = dG")
    render_page_intro(
        "Private key sinh ra public key như thế nào?",
        "ECC cung cấp phép nhân vô hướng trên nhóm điểm elliptic curve: Q = dG.",
        "Demo cho thấy chọn private key toy d, tính public key Q, và trực quan hóa các điểm trên toy curve.",
    )
    st.warning(
        f"toy curve only: p = {DEMO_P}, a = {DEMO_A}, b = {DEMO_B}, "
        f"G = ({GENERATOR_POINT.x}, {GENERATOR_POINT.y}), n = {ORDER_N}. "
        "Đây không phải secp256k1 và không an toàn."
    )
    
    with st.columns(3)[1]:
        st.latex(rf"y^2 \equiv x^3 + {DEMO_A}x + {DEMO_B} \pmod{{{DEMO_P}}}")
    
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
                     title=f"Các điểm trên trường hữu hạn F_{DEMO_P}",
                     labels={'x': 'X coordinate', 'y': 'Y coordinate'})
    fig.update_layout(showlegend=True, hovermode='closest')
    st.plotly_chart(fig, use_container_width=True)
    
    render_learning_summary("ECC Toy Curve", [
        "Đường cong Elliptic được định nghĩa bởi phương trình $y^2 = x^3 + ax + b$ trên trường hữu hạn",
        "Phép nhân vô hướng $d \\cdot G$ dựa trên phép cộng điểm (Point Addition)",
        "Độ khó của ECDLP đảm bảo an toàn mật mã"
    ])


# ============= PAGE 3: ECDLP =============
def demo_ecdlp_explanation():
    """Minh họa ECDLP trên toy curve và cảnh báo không brute-force secp256k1."""
    st.title("3. ECDLP: Why Q does not reveal d")
    render_page_intro(
        "Vì sao biết public key Q mà không suy ra private key d?",
        "Bài toán ECDLP: biết G và Q = dG, tìm d. Toy curve nhỏ có thể brute force, còn secp256k1 thật thì không khả thi với generic classical attacks đã biết.",
        "Demo brute force trên toy curve để thấy ý tưởng đảo ngược là thử từng k; BSGS giảm độ phức tạp xuống O(sqrt(n)); Pollard rho chỉ là experimental toy demo.",
    )
    st.warning(
        f"toy curve only. Demo này dùng curve rất nhỏ với n = {ORDER_N} để học ECDLP, "
        "không brute force secp256k1 và không liên quan tới real Bitcoin keys."
    )
    st.info(
        "Pollard rho trong repo được đánh dấu experimental: chỉ dùng cho toy curve, có thể thất bại do va chạm suy biến/giới hạn bước, "
        "và không có nghĩa là làm giảm bảo mật Bitcoin."
    )

    d_secret = st.slider("Chọn toy private key d", min_value=1, max_value=ORDER_N - 1, value=5)
    Q = ECDSA_PARAMS.curve.scalar_mul(d_secret, ECDSA_PARAMS.G)
    st.info(f"Public key Q = dG = {d_secret}G = Point(x={Q.x}, y={Q.y})")

    attempts = []
    recovered = None
    for k in range(1, ORDER_N + 1):
        candidate = ECDSA_PARAMS.curve.scalar_mul(k, ECDSA_PARAMS.G)
        attempts.append({
            "k": k,
            "kG": "Infinity" if candidate.is_infinity else f"({candidate.x}, {candidate.y})",
            "matches Q": candidate == Q,
        })
        if candidate == Q and recovered is None:
            recovered = k

    st.dataframe(pd.DataFrame(attempts), use_container_width=True)
    st.success(f"Toy brute force recovered d = {recovered}.")
    st.caption(
        "Bài học: brute force O(n) chỉ chạy được vì toy n rất nhỏ. Với secp256k1, n có kích thước khoảng 256 bit."
    )

    render_learning_summary("ECDLP", [
        "ECDLP hỏi: given G and Q = dG, find d",
        "Toy curve nhỏ giúp quan sát brute force",
        "Real secp256k1 không bị brute force bởi demo code",
    ])


# ============= PAGE 4: ECDSA SIGN/VERIFY =============
def demo_ecdsa_sign_verify():
    """Minh họa quy trình ký và xác minh."""
    st.title("4. ECDSA Sign/Verify")
    render_page_intro(
        "ECDSA ký và xác minh như thế nào?",
        "Private key tạo signature. Public key xác minh signature. Verifier không cần private key.",
        "Demo ký một message bằng toy ECDSA, verify thành công, rồi sửa message để thấy signature bị từ chối.",
    )
    st.warning(
        f"toy curve only. Demo dùng n = {ORDER_N}, không phải secp256k1 và không an toàn."
    )
    
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


# ============= PAGE 5: MINI BITCOIN TRANSACTION SIGNING =============
def demo_mini_bitcoin_transaction_signing():
    """Minh họa ECDSA trong luồng mini Bitcoin transaction / UTXO."""
    st.title("5. Mini Bitcoin Transaction Signing")
    render_page_intro(
        "ECDSA đi vào Bitcoin-like transaction như thế nào?",
        "Trong toy UTXO flow, signature + public key là unlocking data để chứng minh quyền chi tiêu UTXO.",
        "Demo cho thấy Alice có UTXO, tạo transaction trả Bob, ký deterministic unsigned transaction data, rồi node toy verify UTXO + public key hash + signature.",
    )

    st.warning(
        "P2PKH-like educational model trên toy UTXO set. not real Bitcoin consensus. "
        "not real Bitcoin transaction serialization. not real Bitcoin signing. "
        "not full Script / sighash / consensus. Không kết nối Bitcoin network."
    )

    alice_private_key = 2
    bob_private_key = 5
    mallory_private_key = 10

    alice_public_key = ECDSA_PARAMS.curve.scalar_mul(alice_private_key, ECDSA_PARAMS.G)
    bob_public_key = ECDSA_PARAMS.curve.scalar_mul(bob_private_key, ECDSA_PARAMS.G)
    mallory_public_key = ECDSA_PARAMS.curve.scalar_mul(mallory_private_key, ECDSA_PARAMS.G)

    alice_pubkey_hash = pubkey_hash_demo(alice_public_key)
    bob_pubkey_hash = pubkey_hash_demo(bob_public_key)
    mallory_pubkey_hash = pubkey_hash_demo(mallory_public_key)

    funding_tx = Transaction(
        inputs=[],
        outputs=[TxOutput(amount=10, pubkey_hash=alice_pubkey_hash)],
    )
    funding_outpoint = OutPoint(txid_demo(funding_tx), 0)

    utxo_set = UTXOSet()
    utxo_set.add_utxo(funding_outpoint, funding_tx.outputs[0])

    spend_tx = Transaction(
        inputs=[TxInput(previous_output=funding_outpoint)],
        outputs=[TxOutput(amount=10, pubkey_hash=bob_pubkey_hash)],
    )
    sign_transaction_input(ECDSA_PARAMS, spend_tx, 0, alice_private_key)

    unsigned_bytes = serialize_unsigned_tx(spend_tx)
    demo_tx_hash = txid_demo(spend_tx)
    signature = spend_tx.inputs[0].signature
    public_key = spend_tx.inputs[0].public_key

    st.subheader("1. Alice owns a toy UTXO")
    ownership_rows = [
        {"Field": "Owner", "Value": "Alice"},
        {"Field": "Toy amount", "Value": "10 demo units"},
        {"Field": "Referenced outpoint", "Value": f"{funding_outpoint.txid[:16]}...:{funding_outpoint.index}"},
        {"Field": "Locking condition", "Value": "hash(public key Alice)"},
        {"Field": "Alice pubkey hash", "Value": alice_pubkey_hash},
    ]
    st.dataframe(pd.DataFrame(ownership_rows), use_container_width=True)

    st.subheader("2. Alice creates a transaction paying Bob")
    tx_rows = [
        {"Role": "Input", "Content": f"Spend toy UTXO {funding_outpoint.txid[:16]}...:{funding_outpoint.index}"},
        {"Role": "Output", "Content": f"Pay 10 demo units to Bob pubkey hash {bob_pubkey_hash}"},
    ]
    st.dataframe(pd.DataFrame(tx_rows), use_container_width=True)

    st.subheader("3. Deterministic unsigned serialization and demo transaction hash")
    st.caption("serialize_unsigned_tx(tx) dùng JSON với sort_keys=True trong module src.bitcoin_tx.")
    st.code(unsigned_bytes.decode("utf-8"), language="json")
    st.info(f"demo transaction hash: `{demo_tx_hash}`")

    st.subheader("4. Alice signs the transaction data")
    st.caption(
        "Toy ECDSA ký deterministic unsigned transaction data; hàm ECDSA toy hash dữ liệu này "
        f"nội bộ modulo n = {ORDER_N}. Đây không phải real Bitcoin sighash."
    )
    if signature and public_key:
        st.code(
            f"signature = (r={signature[0]}, s={signature[1]})\n"
            f"public_key = Point(x={public_key.x}, y={public_key.y})",
            language="text",
        )

    st.subheader("5. Node verifies spending authority")
    referenced_output = utxo_set.get_output(funding_outpoint)
    hash_matches = (
        referenced_output is not None
        and public_key is not None
        and pubkey_hash_demo(public_key) == referenced_output.pubkey_hash
    )
    signature_verifies = (
        signature is not None
        and public_key is not None
        and verify(ECDSA_PARAMS, public_key, unsigned_bytes, signature)
    )
    valid_spend = verify_transaction_input(ECDSA_PARAMS, spend_tx, 0, utxo_set)

    validation_rows = [
        {
            "Check": "referenced UTXO exists",
            "Result": utxo_set.exists(funding_outpoint),
            "Meaning": "OutPoint nằm trong toy UTXO set",
        },
        {
            "Check": "UTXO is unspent",
            "Result": utxo_set.is_unspent(funding_outpoint),
            "Meaning": "UTXO chưa bị đánh dấu spent",
        },
        {
            "Check": "hash(public key) matches locking condition",
            "Result": hash_matches,
            "Meaning": "public key Alice khớp pubkey hash đã khóa UTXO",
        },
        {
            "Check": "ECDSA signature verifies",
            "Result": signature_verifies,
            "Meaning": "signature hợp lệ với unsigned transaction data",
        },
    ]
    st.dataframe(pd.DataFrame(validation_rows), use_container_width=True)

    if valid_spend:
        st.success("Valid spend accepted in the toy model.")
    else:
        st.error("Valid spend unexpectedly rejected.")

    st.subheader("6. Failure cases")

    tampered_amount_tx = copy.deepcopy(spend_tx)
    tampered_amount_tx.outputs[0] = TxOutput(
        amount=9,
        pubkey_hash=tampered_amount_tx.outputs[0].pubkey_hash,
    )

    tampered_recipient_tx = copy.deepcopy(spend_tx)
    tampered_recipient_tx.outputs[0] = TxOutput(
        amount=tampered_recipient_tx.outputs[0].amount,
        pubkey_hash=mallory_pubkey_hash,
    )

    wrong_public_key_tx = copy.deepcopy(spend_tx)
    wrong_public_key_tx.inputs[0].public_key = mallory_public_key

    mallory_signed_tx = Transaction(
        inputs=[TxInput(previous_output=funding_outpoint)],
        outputs=[TxOutput(amount=10, pubkey_hash=bob_pubkey_hash)],
    )
    sign_transaction_input(ECDSA_PARAMS, mallory_signed_tx, 0, mallory_private_key)

    spent_utxo_set = copy.deepcopy(utxo_set)
    first_spend_accepted = spent_utxo_set.apply_transaction(ECDSA_PARAMS, spend_tx)
    second_spend_accepted = verify_transaction_input(ECDSA_PARAMS, spend_tx, 0, spent_utxo_set)

    missing_utxo_set = UTXOSet()

    failure_rows = [
        {
            "Case": "tampered amount",
            "Accepted?": verify_transaction_input(ECDSA_PARAMS, tampered_amount_tx, 0, utxo_set),
            "Why rejected": "amount đổi nên unsigned serialization và signature check không còn khớp",
        },
        {
            "Case": "tampered recipient / locking condition",
            "Accepted?": verify_transaction_input(ECDSA_PARAMS, tampered_recipient_tx, 0, utxo_set),
            "Why rejected": "recipient pubkey hash đổi nên transaction data khác chữ ký ban đầu",
        },
        {
            "Case": "wrong public key",
            "Accepted?": verify_transaction_input(ECDSA_PARAMS, wrong_public_key_tx, 0, utxo_set),
            "Why rejected": "hash(public key Mallory) không khớp locking condition của Alice",
        },
        {
            "Case": "Mallory signs with another key",
            "Accepted?": verify_transaction_input(ECDSA_PARAMS, mallory_signed_tx, 0, utxo_set),
            "Why rejected": "signature/public key của Mallory không mở được UTXO khóa bởi Alice",
        },
        {
            "Case": "double spend",
            "Accepted?": first_spend_accepted and second_spend_accepted,
            "Why rejected": "sau lần chi tiêu đầu, toy UTXO set đánh dấu UTXO là spent",
        },
        {
            "Case": "missing UTXO",
            "Accepted?": verify_transaction_input(ECDSA_PARAMS, spend_tx, 0, missing_utxo_set),
            "Why rejected": "referenced OutPoint không tồn tại trong toy UTXO set",
        },
    ]
    st.dataframe(pd.DataFrame(failure_rows), use_container_width=True)

    rejected_count = sum(not row["Accepted?"] for row in failure_rows)
    st.success(f"{rejected_count}/{len(failure_rows)} failure cases rejected by the toy verifier.")

    render_learning_summary("Mini Bitcoin Transaction Signing", [
        "Trong P2PKH-like educational model, ownership được minh họa bằng khả năng mở khóa UTXO",
        "Unlocking data gồm signature + public key; locking condition là public key hash",
        "Signature gắn với transaction data cụ thể nên sửa amount hoặc recipient sẽ fail",
        "Toy UTXO set chặn missing UTXO và double spend",
        "Demo này không phải real Bitcoin signing, không phải full Script / sighash / consensus",
    ])


# ============= PAGE 6: REUSED NONCE ATTACK =============
def demo_reused_nonce_attack():
    """Minh họa tấn công tái sử dụng nonce."""
    st.title("6. ECDSA Reused Nonce Attack")
    render_page_intro(
        "ECDSA có chắc chắn an toàn không?",
        "ECDSA phụ thuộc vào cả giả định toán học và kỷ luật triển khai. Nonce k phải mới, bí mật và không được tái sử dụng.",
        "Demo cho thấy hai chữ ký toy dùng cùng nonce có thể làm khôi phục nonce k và private key d.",
    )
    
    st.warning("""
    ⚠️ **CẢNH BÁO GIÁO DỤC**: nonce reuse attack demonstrates implementation failure.
    Đây là mô phỏng trên toy curve only, không phải secp256k1. Điều này không có nghĩa
    ECDSA đúng chuẩn bị phá vỡ; nó cho thấy triển khai ECDSA sai nonce có thể chết.
    """)
    
    st.markdown("""
    **Nguyên lý Tấn công:**
    
    Trong ECDSA, mỗi chữ ký phải dùng một nonce $k$ **duy nhất**. 
    Nếu vô tình ký 2 tin nhắn khác nhau bằng cùng $k$, khóa bí mật $d$ sẽ bị lộ!
    
    **Công thức khôi phục**:
    - $k' = (h_1 - h_2)(s_1 - s_2)^{-1} \\pmod n$
    - $d' = (s_1 \\cdot k' - h_1) \\cdot r^{-1} \\pmod n$
    """)
    
    with st.expander(f"ℹ️ Lưu ý về toy order n = {ORDER_N}", expanded=True):
        st.info(
            "Toy curve trong app có order nhỏ để dễ quan sát phép toán. "
            "secp256k1 thật có order nguyên tố rất lớn và không thể brute force bằng demo này."
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
                        "Đây là edge case của toy curve rất nhỏ; hãy thử private key hoặc nonce khác."
                    )
                elif "s=0" in raw_message or "not coprime" in raw_message:
                    st.warning(
                        "Tham số đang chọn tạo ra giá trị s không khả nghịch modulo n, nên toy ECDSA "
                        "không thể tạo chữ ký hợp lệ. Đây là hạn chế của toy demo rất nhỏ."
                    )
                else:
                    st.warning(
                        "Không thể tạo chữ ký hợp lệ với tham số hiện tại trên toy curve. "
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
        "Toy curve chỉ dùng để minh họa, không phải secp256k1 và không an toàn"
    ])


# ============= PAGE 7: NONCE DEFENSE NOTES =============
def demo_nonce_defense_notes():
    """Ghi chú phòng thủ sau reused nonce attack."""
    st.title("7. Nonce Defense Notes")
    render_page_intro(
        "Nếu nonce reuse nguy hiểm, phòng thủ thế nào?",
        "Good cryptography = strong math + correct implementation discipline. Nonce generation, side-channel discipline và thư viện trưởng thành đều quan trọng.",
        "Trang này không triển khai RFC6979 đầy đủ; nó giải thích hướng phòng thủ đúng sau khi đã xem reused nonce attack.",
    )
    st.warning(
        "nonce defense notes are educational, not production guidance. Toy code trong repo không production-safe."
    )

    defense_rows = [
        {
            "Defense": "Never reuse nonce k",
            "Meaning": "Mỗi chữ ký ECDSA cần nonce riêng; reuse k có thể lộ private key.",
        },
        {
            "Defense": "Secure randomness",
            "Meaning": "Nếu randomized signing được dùng, RNG phải đáng tin cậy và không bị bias nghiêm trọng.",
        },
        {
            "Defense": "Deterministic ECDSA / RFC6979-style",
            "Meaning": "Sinh nonce từ private key + message theo quy trình xác định để giảm phụ thuộc RNG ngoài.",
        },
        {
            "Defense": "Constant-time implementation",
            "Meaning": "Tránh rò rỉ timing/side-channel ở scalar multiplication, inversion, signing.",
        },
        {
            "Defense": "Use mature crypto libraries",
            "Meaning": "Production nên dùng thư viện được review như libsecp256k1/OpenSSL, không tự viết toy ECDSA.",
        },
    ]
    st.dataframe(pd.DataFrame(defense_rows), use_container_width=True)

    st.info(
        "RFC6979-style deterministic nonce giúp giảm rủi ro RNG yếu, nhưng không tự nó giải quyết mọi rủi ro triển khai "
        "như side-channel, lỗi validation, memory safety hoặc misuse API."
    )

    render_learning_summary("Nonce Defense Notes", [
        "Nonce reuse là implementation failure, không phải bằng chứng rằng công thức ECDSA sai",
        "Phòng thủ cần RNG/nonce discipline, constant-time code và thư viện đã được review",
        "Toy code chỉ để học, không dùng cho ví thật hoặc private key thật",
    ])


# ============= PAGE 8: SHAMIR'S TRICK =============
def demo_shamir_trick():
    """Minh họa tối ưu hóa bằng Shamir's Trick."""
    st.title("8. Shamir's Trick")
    render_page_intro(
        "Có thể tối ưu ECDSA verification không?",
        "Verification cần tính u1G + u2Q. Shamir's trick tối ưu simultaneous scalar multiplication.",
        "Demo so sánh số phép cộng/nhân đôi giữa cách naive và Shamir trên toy curve.",
    )
    st.warning(
        "toy curve only. Đây là bonus optimization demo, không phải trọng tâm Bitcoin ownership."
    )
    
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
    Kết quả benchmark cố định từ `results/openssl_benchmark.txt`, dùng để so sánh RSA với các phép đo `openssl speed`
    mà OpenSSL hỗ trợ trong môi trường hiện tại.
    """)
    st.info(
        "`openssl speed ecdsap256` đo ECDSA trên NIST P-256 / prime256v1. "
        "Nếu OpenSSL không liệt kê secp256k1 trực tiếp thì không được coi đây là benchmark secp256k1."
    )
    
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
                    st.metric("Tỉ lệ sign throughput", f"{speedup:.1f}x", "ECDSA/RSA trên bộ dữ liệu hiện có")
            
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
                
                1. **Đọc đúng phạm vi dữ liệu**: `ecdsap256` trong `openssl speed` là **NIST P-256 / prime256v1**,
                   không phải `secp256k1`. Nếu output không ghi `secp256k1` rõ ràng, không nên gán nhãn như vậy.
                
                2. **Kích thước khóa/chữ ký**: 
                   - RSA 2048 ≈ ECDSA 256 (về mức độ bảo mật)
                   - Nhưng ECDSA 256-bit nhỏ gọn hơn nhiều
                
                3. **Hiệu năng phụ thuộc ngữ cảnh**:
                   - Kết quả phụ thuộc operation, key size, curve, implementation và máy chạy
                   - RSA verification có thể rất nhanh tùy public exponent và cách OpenSSL triển khai
                   - Không có kết luận phổ quát kiểu "ECDSA luôn nhanh hơn RSA"

                4. **Liên hệ với Bitcoin**:
                   - Bitcoin sử dụng `secp256k1` (256-bit ECDSA)
                   - Benchmark `openssl speed` ở đây chỉ là tham chiếu hiệu năng cho các thuật toán/curve mà OpenSSL benchmark được
                   - Demo `gen_keys/sign_verify` mới là phần kết nối trực tiếp tới `secp256k1`
                   - Chữ ký Bitcoin: ~64 byte vs RSA ~256 byte
                   - Tiết kiệm dung lượng blockchain
                
                5. **Kết luận phù hợp**:
                   - ECC/ECDSA thường hấp dẫn vì khóa và chữ ký nhỏ
                   - Nhưng lựa chọn giữa RSA và ECDSA vẫn phải dựa trên workload cụ thể
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
    st.title("9. OpenSSL secp256k1 Demo")
    render_page_intro(
        "Toy demo có liên hệ công cụ thật không?",
        "Toy curve giải thích toán học; OpenSSL secp256k1 cho thấy message/file signing bằng công cụ mật mã thật.",
        "Demo chạy OpenSSL để tạo key tạm, ký message/file, verify thành công và benchmark cẩn trọng.",
    )
    st.warning(
        "OpenSSL signs a message/file, not a full Bitcoin transaction. Đây không phải real Bitcoin transaction signing, "
        "không phải Script, không phải sighash consensus."
    )
    
    st.markdown("""
    Phần này chạy ECDSA thật trên **secp256k1** bằng OpenSSL, khác với toy curve nhỏ
    ở các phần trước. `secp256k1` là đường cong được Bitcoin sử dụng. OpenSSL là thư viện
    tối ưu nên phần sign/verify secp256k1 này giúp nối toy math với công cụ thật. Benchmark
    `openssl speed` bên dưới vẫn cần đọc đúng theo curve mà OpenSSL thực sự benchmark được.
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
        "Demo sign/verify secp256k1 là phần kết nối với Bitcoin rõ ràng hơn benchmark `openssl speed`",
        "So sánh RSA/ECDSA phải đọc theo operation, key size, curve, implementation và machine"
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
        demo_big_picture()
    elif page_id == 1:
        demo_ownership_in_bitcoin()
    elif page_id == 2:
        demo_ecc_toy_curve()
    elif page_id == 3:
        demo_ecdlp_explanation()
    elif page_id == 4:
        demo_ecdsa_sign_verify()
    elif page_id == 5:
        demo_mini_bitcoin_transaction_signing()
    elif page_id == 6:
        demo_reused_nonce_attack()
    elif page_id == 7:
        demo_nonce_defense_notes()
    elif page_id == 8:
        demo_shamir_trick()
    elif page_id == 9:
        demo_openssl_summary()
    
    st.divider()
    render_navigation(st.session_state.page_id)


if __name__ == "__main__":
    main()
