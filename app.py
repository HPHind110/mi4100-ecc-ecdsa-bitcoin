import sys
import os
import copy
import shutil
import subprocess
import tempfile
import time
import hashlib
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


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="🔐 Mô phỏng ECC/ECDSA trong Bitcoin",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================
st.markdown(
    """
<style>
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding-top: 18px;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: white !important;
    }

    h1, h2, h3 {
        color: #1a202c;
        font-weight: 700;
        letter-spacing: -0.4px;
    }

    h1 {
        border-bottom: 3px solid #667eea;
        padding-bottom: 12px;
        margin-bottom: 20px;
    }

    button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.15s ease !important;
    }

    button:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    }

    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #dbe4f0 100%);
        border-radius: 10px;
        padding: 14px;
    }

    [data-testid="stAlert"] {
        border-radius: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# GLOBAL PARAMETERS
# ============================================================
ECDSA_PARAMS = get_demo_params()
TOY_CURVE = ECDSA_PARAMS.curve
GENERATOR_POINT = ECDSA_PARAMS.G
ORDER_N = ECDSA_PARAMS.n

DEMOS = [
    {"id": 0, "title": "0. Bức tranh tổng quan", "desc": "Bài toán sở hữu trong Bitcoin"},
    {"id": 1, "title": "1. Quyền sở hữu trong Bitcoin", "desc": "Quyền chi tiêu UTXO"},
    {"id": 2, "title": "2. ECC: Q = dG", "desc": "Khóa bí mật sinh khóa công khai"},
    {"id": 3, "title": "3. ECDLP: Vì sao Q không làm lộ d?", "desc": "Độ khó của việc đi ngược từ Q về d"},
    {"id": 4, "title": "4. ECDSA: Ký và kiểm tra chữ ký", "desc": "Ký và kiểm tra thông điệp"},
    {"id": 5, "title": "5. Phòng lab giao dịch Bitcoin mô phỏng", "desc": "UTXO mô phỏng + chữ ký ECDSA"},
    {"id": 6, "title": "6. Tấn công ECDSA khi dùng lại nonce", "desc": "Tấn công tái sử dụng nonce"},
    {"id": 7, "title": "7. Ghi chú phòng thủ nonce", "desc": "Phòng thủ khi triển khai ECDSA"},
    {"id": 8, "title": "8. Thủ thuật Shamir", "desc": "Tối ưu bước kiểm tra chữ ký"},
    {"id": 9, "title": "9. Bonus: OpenSSL secp256k1", "desc": "Đối chiếu toy demo với công cụ thật"}
]

if "page_id" not in st.session_state:
    st.session_state.page_id = 0


# ============================================================
# GENERAL UI HELPERS
# ============================================================
@st.cache_data
def get_curve_points(p: int, a: int, b: int):
    """Tính tất cả điểm trên đường cong mô phỏng để vẽ."""
    points = []
    for x in range(p):
        rhs = (x**3 + a * x + b) % p
        for y in range(p):
            if (y**2) % p == rhs:
                points.append((x, y))
    return points

@st.cache_data
def get_real_curve_points(a: int, b: int, x_min: float, x_max: float, samples: int = 700):
    """Tạo dữ liệu để vẽ đường cong y^2 = x^3 + ax + b trên số thực.

    Đây chỉ là hình trực giác hình học.
    ECC trong mật mã không chạy trên số thực, mà chạy trên trường hữu hạn F_p.
    """
    rows = []

    for i in range(samples + 1):
        x = x_min + (x_max - x_min) * i / samples
        rhs = x**3 + a * x + b

        if rhs < 0:
            continue

        y = rhs ** 0.5

        rows.append({
            "x": x,
            "y": y,
            "Nhánh": "y = +sqrt(x³ + ax + b)",
        })

        if y != 0:
            rows.append({
                "x": x,
                "y": -y,
                "Nhánh": "y = -sqrt(x³ + ax + b)",
            })

    return pd.DataFrame(rows)


def set_page(page_id: int) -> None:
    st.session_state.page_id = max(0, min(int(page_id), len(DEMOS) - 1))


def next_page() -> None:
    set_page(st.session_state.page_id + 1)


def prev_page() -> None:
    set_page(st.session_state.page_id - 1)


def render_header(current_page_id: int) -> None:
    demo = DEMOS[current_page_id]
    progress_pct = (current_page_id + 1) / len(DEMOS)

    col1, col2, col3 = st.columns([0.15, 1, 0.25], gap="large")
    with col1:
        st.markdown("## 🔐")
    with col2:
        st.markdown(f"### {demo['title']}")
        st.caption(f"📝 {demo['desc']}")
    with col3:
        st.metric("Tiến độ", f"{int(progress_pct * 100)}%", f"{current_page_id + 1}/{len(DEMOS)}")

    st.progress(progress_pct)
    st.divider()


def render_sidebar_navigation() -> None:
    """Navigation bằng button callback, tránh lỗi radio state kéo page_id về trang cũ."""
    with st.sidebar:
        st.markdown("## 📚 Bài học")
        st.markdown("---")

        for demo in DEMOS:
            is_current = demo["id"] == st.session_state.page_id
            prefix = "▶️ " if is_current else ""
            label = f"{prefix}{demo['title']}"
            st.button(
                label,
                key=f"nav_page_{demo['id']}",
                use_container_width=True,
                on_click=set_page,
                args=(demo["id"],),
            )

        st.markdown("---")
        st.markdown("### ⚙️ Công cụ")

        if st.button("🔄 Reset toàn bộ trạng thái mô phỏng", use_container_width=True):
            if "openssl_lab" in st.session_state:
                old_workdir = st.session_state.openssl_lab.get("workdir")
                if old_workdir and Path(old_workdir).exists():
                    shutil.rmtree(old_workdir, ignore_errors=True)

            st.session_state.clear()
            st.session_state.page_id = 0
            st.rerun()

        with st.expander("ℹ️ Về dự án", expanded=False):
            st.markdown(
                """
                **Dự án mô phỏng ECC/ECDSA trong Bitcoin**

                Mạch chính:

                1. Bài toán quyền sở hữu trong Bitcoin
                2. Quyền chi tiêu UTXO
                3. ECC: `Q = dG`
                4. Độ khó ECDLP
                5. Ký số bằng ECDSA
                6. Phòng lab giao dịch Bitcoin mô phỏng
                7. Tấn công khi dùng lại nonce
                8. Phòng thủ + tối ưu
                9. OpenSSL secp256k1

                **Lưu ý:** code mô phỏng để học, không dùng cho ví thật.
                """
            )


def render_navigation_footer() -> None:
    current_id = st.session_state.page_id
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.button(
            "⬅️ Trước",
            disabled=current_id <= 0,
            use_container_width=True,
            on_click=prev_page,
            key="footer_prev",
        )
    with col2:
        st.caption(f"📍 Trang {current_id + 1} / {len(DEMOS)}")
    with col3:
        st.button(
            "Tiếp ➡️",
            disabled=current_id >= len(DEMOS) - 1,
            use_container_width=True,
            on_click=next_page,
            key="footer_next",
        )


def render_page_intro(question: str, idea: str, demo: str) -> None:
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        st.markdown("#### ❓ Câu hỏi")
        st.markdown(f"*{question}*")
    with col2:
        st.markdown("#### 💡 Ý tưởng")
        st.markdown(f"*{idea}*")
    with col3:
        st.markdown("#### 🎯 Demo chứng minh")
        st.markdown(f"*{demo}*")
    st.divider()


def render_term_notes(notes: list[tuple[str, str]]) -> None:
    """Hiển thị ghi chú thuật ngữ để người mới không bị ngợp."""
    with st.expander("📌 Dịch nhanh thuật ngữ", expanded=False):
        for term, explanation in notes:
            st.markdown(f"**{term}:** {explanation}")


def render_learning_summary(title: str, points: list[str]) -> None:
    with st.container(border=True):
        st.markdown(f"### 📚 {title}")
        for i, point in enumerate(points, 1):
            st.markdown(f"**{i}.** {point}")

def render_ecdsa_formula_box() -> None:
    """Hiển thị công thức ECDSA ở mức vừa đủ cho phần demo ký/verify."""
    with st.expander("📐 Công thức ECDSA bên dưới demo", expanded=False):
        st.markdown(
            """
            ECDSA có hai pha chính: **ký** và **kiểm tra chữ ký**.

            Trong đó:

            - `m`: dữ liệu cần ký
            - `h`: giá trị băm của dữ liệu
            - `d`: khóa bí mật
            - `Q = dG`: khóa công khai
            - `k`: nonce dùng một lần khi ký
            - `(r, s)`: chữ ký ECDSA
            """
        )

        col_sign, col_verify = st.columns(2)

        with col_sign:
            st.markdown("#### 1. Ký bằng private key")

            st.latex(r"h = H(m) \bmod n")
            st.latex(r"R = kG")
            st.latex(r"r = x_R \bmod n")
            st.latex(r"s = k^{-1}(h + rd) \bmod n")

            st.caption(
                "Người ký cần private key d và nonce k. "
                "Nếu k bị lộ hoặc bị dùng lại, private key có thể bị lộ."
            )

        with col_verify:
            st.markdown("#### 2. Kiểm tra bằng public key")

            st.latex(r"w = s^{-1} \bmod n")
            st.latex(r"u_1 = hw \bmod n")
            st.latex(r"u_2 = rw \bmod n")
            st.latex(r"P = u_1G + u_2Q")
            st.latex(r"\text{valid} \iff x_P \bmod n = r")

            st.caption(
                "Người kiểm tra chỉ cần message, chữ ký (r, s) và public key Q. "
                "Không cần biết private key d."
            )

        st.info(
            "Điểm quan trọng: verification kiểm tra một quan hệ toán học giữa message, chữ ký và public key. "
            "Nó không khôi phục private key."
        )

def render_ecdsa_verification_trace(params, Q, message: bytes, signature: tuple[int, int]) -> None:
    """Hiển thị các giá trị trung gian trong bước ECDSA verification.

    Đây là trace giáo dục để người học thấy verify không phải hộp đen.
    Không dùng cho production crypto.
    """
    r, s = signature
    n = params.n

    h = hash_message_to_int(message, n)
    w = safe_mod_inverse(s, n)

    if w is None:
        st.error("Không thể trace verify vì s không có nghịch đảo modulo n.")
        return

    u1 = (h * w) % n
    u2 = (r * w) % n

    p1 = params.curve.scalar_mul(u1, params.G)
    p2 = params.curve.scalar_mul(u2, Q)
    P = params.curve.point_add(p1, p2)

    if P.is_infinity:
        x_mod_n = None
        final_check = False
    else:
        x_mod_n = P.x % n
        final_check = x_mod_n == r

    rows = [
        {
            "Bước": "Hash dữ liệu",
            "Công thức": "h = H(m) mod n",
            "Giá trị": h,
            "Ý nghĩa": "Rút gọn dữ liệu cần ký thành một số modulo n",
        },
        {
            "Bước": "Nghịch đảo của s",
            "Công thức": "w = s^(-1) mod n",
            "Giá trị": w,
            "Ý nghĩa": "Chuẩn bị hệ số để kiểm tra chữ ký",
        },
        {
            "Bước": "Hệ số u1",
            "Công thức": "u1 = h*w mod n",
            "Giá trị": u1,
            "Ý nghĩa": "Phần phụ thuộc vào message",
        },
        {
            "Bước": "Hệ số u2",
            "Công thức": "u2 = r*w mod n",
            "Giá trị": u2,
            "Ý nghĩa": "Phần phụ thuộc vào chữ ký",
        },
        {
            "Bước": "Tính điểm kiểm tra",
            "Công thức": "P = u1*G + u2*Q",
            "Giá trị": point_to_text(P),
            "Ý nghĩa": "Kết hợp generator G và public key Q",
        },
        {
            "Bước": "So sánh cuối",
            "Công thức": "x(P) mod n == r",
            "Giá trị": f"{x_mod_n} == {r}",
            "Ý nghĩa": "Nếu đúng thì chữ ký hợp lệ",
        },
    ]

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if final_check:
        st.success("Trace verify hợp lệ: x(P) mod n khớp với r.")
    else:
        st.error("Trace verify không hợp lệ: x(P) mod n không khớp với r.")


def point_to_text(P) -> str:
    if P is None:
        return "None"
    if getattr(P, "is_infinity", False):
        return "Infinity"
    return f"({P.x}, {P.y})"


def safe_mod_inverse(a: int, n: int):
    a = a % n
    if gcd(a, n) != 1:
        return None
    try:
        return pow(a, -1, n)
    except ValueError:
        return None

def trace_double_and_add(curve, k: int, P):
    """Tạo bảng mô phỏng quá trình tính kP bằng double-and-add.

    Hàm này chỉ phục vụ UI giáo dục:
    - Không thay thế scalar_mul thật.
    - Không dùng cho production crypto.
    - Mục tiêu là giúp người học thấy kP được tạo từ cộng điểm và nhân đôi điểm.
    """
    if k < 0:
        raise ValueError("Demo này chỉ minh họa k >= 0.")

    old_add_count = getattr(curve, "add_count", None)
    old_double_count = getattr(curve, "double_count", None)

    try:
        result = curve.scalar_mul(0, P)  # điểm vô cực
        addend = P
        remaining = k
        bit_index = 0
        rows = []

        while remaining > 0:
            bit = remaining & 1

            result_before = result
            addend_before = addend

            if bit == 1:
                result = curve.point_add(result, addend)
                action = "Bit = 1 nên cộng result + addend"
            else:
                action = "Bit = 0 nên giữ nguyên result"

            doubled_addend = curve.point_add(addend, addend)

            rows.append({
                "Bước": bit_index + 1,
                "Bit đang xét": f"b{bit_index} = {bit}",
                "Addend hiện tại": point_to_text(addend_before),
                "Result trước": point_to_text(result_before),
                "Thao tác": action,
                "Result sau": point_to_text(result),
                "Chuẩn bị vòng sau": f"2 * {point_to_text(addend_before)} = {point_to_text(doubled_addend)}",
            })

            addend = doubled_addend
            remaining >>= 1
            bit_index += 1

        return rows, result

    finally:
        if old_add_count is not None:
            curve.add_count = old_add_count
        if old_double_count is not None:
            curve.double_count = old_double_count

def validate_nonce(k: int, n: int):
    if not isinstance(k, int):
        return False, "Nonce k phải là số nguyên."
    if not (1 <= k < n):
        return False, f"Nonce k phải nằm trong khoảng 1 <= k < n, với n = {n}."
    if gcd(k, n) != 1:
        return False, "Nonce k không hợp lệ vì không tồn tại nghịch đảo modulo n."
    return True, ""

def render_ecdsa_signing_trace(params, d: int, message: bytes, k: int, signature: tuple[int, int]) -> None:
    """Hiển thị các bước tạo chữ ký ECDSA trên toy curve."""
    r, s = signature
    n = params.n

    h = hash_message_to_int(message, n)
    R = params.curve.scalar_mul(k, params.G)

    if R.is_infinity:
        st.error("Không thể trace ký vì R = kG là điểm vô cực.")
        return

    r_calc = R.x % n
    k_inv = safe_mod_inverse(k, n)

    if k_inv is None:
        st.error("Không thể trace ký vì k không có nghịch đảo modulo n.")
        return

    h_plus_rd = (h + r_calc * d) % n
    s_calc = (k_inv * h_plus_rd) % n

    rows = [
        {
            "Bước": "Hash dữ liệu",
            "Công thức": "h = H(m) mod n",
            "Giá trị": h,
            "Ý nghĩa": "Rút gọn dữ liệu cần ký thành một số modulo n",
        },
        {
            "Bước": "Tính điểm nonce",
            "Công thức": "R = kG",
            "Giá trị": point_to_text(R),
            "Ý nghĩa": "Nonce k tạo ra điểm R trên đường cong",
        },
        {
            "Bước": "Tính r",
            "Công thức": "r = x(R) mod n",
            "Giá trị": r_calc,
            "Ý nghĩa": "Lấy hoành độ của R rồi rút gọn modulo n",
        },
        {
            "Bước": "Nghịch đảo nonce",
            "Công thức": "k^(-1) mod n",
            "Giá trị": k_inv,
            "Ý nghĩa": "ECDSA cần k có nghịch đảo modulo n",
        },
        {
            "Bước": "Tính phần h + rd",
            "Công thức": "h + r*d mod n",
            "Giá trị": h_plus_rd,
            "Ý nghĩa": "Trộn dữ liệu cần ký, chữ ký r và khóa bí mật d",
        },
        {
            "Bước": "Tính s",
            "Công thức": "s = k^(-1)(h + r*d) mod n",
            "Giá trị": s_calc,
            "Ý nghĩa": "Tạo thành phần thứ hai của chữ ký",
        },
    ]

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if r_calc == r and s_calc == s:
        st.success(f"Trace ký khớp chữ ký đã tạo: r = {r}, s = {s}.")
    else:
        st.warning(
            f"Trace chưa khớp chữ ký đã tạo. Trace ra r = {r_calc}, s = {s_calc}, "
            f"nhưng chữ ký đang lưu là r = {r}, s = {s}."
        )

def can_run_reused_nonce_attack(msg1, msg2, h1, h2, r1, s1, r2, s2, n):
    if msg1 == msg2:
        return False, "Hai message giống nhau không tạo ra hai phương trình độc lập."
    if h1 == h2:
        return False, "Hai thông điệp khác nhau nhưng mã băm modulo n bị trùng trong mô phỏng nhỏ."
    if r1 != r2:
        return False, "r1 != r2 nên UI không xem đây là mẫu reused nonce hợp lệ."
    if s1 == s2:
        return False, "s1 = s2 nên s1 - s2 = 0, không có nghịch đảo."
    s_diff = (s1 - s2) % n
    if gcd(s_diff, n) != 1:
        return False, f"s1 - s2 = {s_diff} không khả nghịch modulo {n}."
    if gcd(r1 % n, n) != 1:
        return False, f"r = {r1 % n} không khả nghịch modulo {n}."
    return True, ""


def recover_private_key_from_known_nonce(h: int, r: int, s: int, k: int, n: int):
    """Khôi phục private key d khi biết nonce k trong một chữ ký ECDSA.

    Từ công thức:
        s = k^(-1)(h + r*d) mod n

    Suy ra:
        d = (s*k - h) * r^(-1) mod n
    """
    r_inv = safe_mod_inverse(r, n)

    if r_inv is None:
        return None, "Không thể khôi phục vì r không có nghịch đảo modulo n."

    d_recovered = ((s * k - h) * r_inv) % n
    return d_recovered, ""


def find_valid_nonce_for_messages(params, d: int, messages: list[str]):
    """Tìm một nonce k có thể ký hợp lệ tất cả message trong toy demo.

    Toy curve nhỏ nên một số k có thể rơi vào edge-case như r = 0 hoặc s = 0.
    Hàm này giúp UI demo ổn định hơn.
    """
    for k in range(1, params.n):
        ok_nonce, _ = validate_nonce(k, params.n)
        if not ok_nonce:
            continue

        try:
            signatures = [
                sign(params, d, msg.encode("utf-8"), k=k)
                for msg in messages
            ]
            return k, signatures
        except Exception:
            continue

    return None, None


# ============================================================
# BITCOIN TX LAB COMPATIBILITY HELPERS
# These wrappers make the app more robust if src.bitcoin_tx uses
# slightly different field/method names.
# ============================================================
def make_outpoint(txid: str, index: int):
    try:
        return OutPoint(txid=txid, index=index)
    except TypeError:
        try:
            return OutPoint(txid=txid, vout=index)
        except TypeError:
            return OutPoint(txid, index)


def outpoint_index(outpoint) -> int:
    return getattr(outpoint, "index", getattr(outpoint, "vout", 0))


def outpoint_key(outpoint) -> str:
    return f"{outpoint.txid}:{outpoint_index(outpoint)}"


def short_outpoint(outpoint) -> str:
    return f"{outpoint.txid[:12]}...:{outpoint_index(outpoint)}"


def make_tx_input(outpoint):
    try:
        return TxInput(previous_output=outpoint)
    except TypeError:
        try:
            return TxInput(prevout=outpoint)
        except TypeError:
            try:
                return TxInput(outpoint)
            except TypeError:
                return TxInput(prevout=outpoint, signature=None, public_key=None)


def get_input_outpoint(tx_input):
    for attr in ("previous_output", "prevout", "outpoint"):
        if hasattr(tx_input, attr):
            return getattr(tx_input, attr)
    raise AttributeError("TxInput không có previous_output/prevout/outpoint.")


def get_input_signature(tx_input):
    return getattr(tx_input, "signature", None)


def get_input_public_key(tx_input):
    return getattr(tx_input, "public_key", getattr(tx_input, "pubkey", None))


def set_input_public_key(tx_input, pubkey):
    if hasattr(tx_input, "public_key"):
        setattr(tx_input, "public_key", pubkey)
    elif hasattr(tx_input, "pubkey"):
        setattr(tx_input, "pubkey", pubkey)
    else:
        setattr(tx_input, "public_key", pubkey)


def set_input_signature(tx_input, signature):
    setattr(tx_input, "signature", signature)


def utxo_add(utxo_set, outpoint, output):
    try:
        return utxo_set.add_utxo(outpoint, output)
    except TypeError:
        return utxo_set.add_utxo(outpoint.txid, outpoint_index(outpoint), output)


def utxo_get_output(utxo_set, outpoint):
    if hasattr(utxo_set, "get_output"):
        return utxo_set.get_output(outpoint)
    if hasattr(utxo_set, "get_utxo"):
        return utxo_set.get_utxo(outpoint)
    try:
        return utxo_set[outpoint_key(outpoint)]
    except Exception:
        return None


def utxo_exists(utxo_set, outpoint) -> bool:
    if hasattr(utxo_set, "exists"):
        try:
            return bool(utxo_set.exists(outpoint))
        except TypeError:
            pass
    return utxo_get_output(utxo_set, outpoint) is not None


def utxo_is_unspent(utxo_set, outpoint) -> bool:
    if hasattr(utxo_set, "is_unspent"):
        try:
            return bool(utxo_set.is_unspent(outpoint))
        except TypeError:
            pass
    return utxo_exists(utxo_set, outpoint)


def utxo_apply_transaction(utxo_set, params, tx) -> bool:
    if hasattr(utxo_set, "apply_transaction"):
        return bool(utxo_set.apply_transaction(params, tx))
    if hasattr(utxo_set, "validate_and_apply_transaction"):
        return bool(utxo_set.validate_and_apply_transaction(params, tx))
    # Fallback: verify all inputs and mark spent if possible.
    ok = all(verify_transaction_input(params, tx, i, utxo_set) for i in range(len(tx.inputs)))
    if ok and hasattr(utxo_set, "mark_spent"):
        for tx_input in tx.inputs:
            utxo_set.mark_spent(get_input_outpoint(tx_input))
    return ok


def tx_lab_signature_verifies(tx, input_index: int) -> bool:
    tx_input = tx.inputs[input_index]
    signature = get_input_signature(tx_input)
    public_key = get_input_public_key(tx_input)
    if signature is None or public_key is None:
        return False
    try:
        return bool(verify(ECDSA_PARAMS, public_key, serialize_unsigned_tx(tx), signature))
    except Exception:
        return False


def tx_lab_verify_details(tx, input_index: int, utxo_set):
    tx_input = tx.inputs[input_index]
    outpoint = get_input_outpoint(tx_input)
    output = utxo_get_output(utxo_set, outpoint)
    public_key = get_input_public_key(tx_input)
    signature = get_input_signature(tx_input)

    exists = utxo_exists(utxo_set, outpoint)
    unspent = utxo_is_unspent(utxo_set, outpoint)
    hash_matches = (
        output is not None
        and public_key is not None
        and pubkey_hash_demo(public_key) == output.pubkey_hash
    )
    sig_ok = signature is not None and tx_lab_signature_verifies(tx, input_index)

    try:
        overall = bool(verify_transaction_input(ECDSA_PARAMS, tx, input_index, utxo_set))
    except Exception:
        overall = False

    return {
        "exists": exists,
        "unspent": unspent,
        "hash_matches": hash_matches,
        "signature_verifies": sig_ok,
        "overall": overall,
    }


def render_verification_table(details: dict) -> None:
    rows = [
        {
            "Bước kiểm tra": "UTXO được tham chiếu có tồn tại không",
            "Kết quả": details["exists"],
            "Ý nghĩa": "OutPoint nằm trong tập UTXO mô phỏng",
        },
        {
            "Bước kiểm tra": "UTXO còn chưa bị tiêu không",
            "Kết quả": details["unspent"],
            "Ý nghĩa": "UTXO chưa bị đánh dấu là đã tiêu",
        },
        {
            "Bước kiểm tra": "Mã băm khóa công khai có khớp điều kiện khóa không",
            "Kết quả": details["hash_matches"],
            "Ý nghĩa": "Khóa công khai khớp mã băm đang khóa UTXO",
        },
        {
            "Bước kiểm tra": "Chữ ký ECDSA có hợp lệ không",
            "Kết quả": details["signature_verifies"],
            "Ý nghĩa": "Chữ ký hợp lệ với dữ liệu giao dịch chưa ký",
        },
        {
            "Bước kiểm tra": "Kết luận cuối cùng của bộ kiểm tra mô phỏng",
            "Kết quả": details["overall"],
            "Ý nghĩa": "Kết luận cuối cùng của verify_transaction_input",
        },
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ============================================================
# TX LAB STATE
# ============================================================
def make_demo_wallet(name: str, private_key: int) -> dict:
    public_key = ECDSA_PARAMS.curve.scalar_mul(private_key, ECDSA_PARAMS.G)
    return {
        "name": name,
        "private_key": private_key,
        "public_key": public_key,
        "pubkey_hash": pubkey_hash_demo(public_key),
    }


def new_tx_lab_state() -> dict:
    wallets = {
        "Alice": make_demo_wallet("Alice", 2),
        "Bob": make_demo_wallet("Bob", 5),
        "Mallory": make_demo_wallet("Mallory", 10),
    }
    return {
        "wallets": wallets,
        "utxo_set": UTXOSet(),
        "known_utxos": [],
        "draft_tx": None,
        "signed_tx": None,
        "last_verify_details": None,
        "action_log": ["Đã khởi tạo phòng lab mô phỏng."],
        "tx_counter": 0,
        "selected_scenario": "Kịch bản đúng: Alice trả Bob",
    }


def init_tx_lab_state() -> None:
    if "tx_lab" not in st.session_state:
        st.session_state.tx_lab = new_tx_lab_state()


def reset_tx_lab_state() -> None:
    st.session_state.tx_lab = new_tx_lab_state()


def lab_log(message: str) -> None:
    st.session_state.tx_lab["action_log"].append(message)


def mint_utxo(owner_name: str, amount: int) -> None:
    lab = st.session_state.tx_lab
    wallet = lab["wallets"][owner_name]
    lab["tx_counter"] += 1

    # Dùng fake funding txid để tránh collision khi mint nhiều lần cùng amount/owner.
    raw = f"funding:{owner_name}:{amount}:{lab['tx_counter']}:{time.time_ns()}".encode("utf-8")
    txid = hashlib.sha256(raw).hexdigest()
    outpoint = make_outpoint(txid, 0)
    output = TxOutput(amount=int(amount), pubkey_hash=wallet["pubkey_hash"])

    utxo_add(lab["utxo_set"], outpoint, output)
    lab["known_utxos"].append(
        {
            "outpoint": outpoint,
            "output": output,
            "created_for": owner_name,
            "created_by": "mint",
        }
    )
    lab_log(f"Đã tạo UTXO {amount} đơn vị mô phỏng cho {owner_name}: {short_outpoint(outpoint)}")


def infer_owner_from_pubkey_hash(pubkey_hash: str) -> str:
    lab = st.session_state.tx_lab
    for name, wallet in lab["wallets"].items():
        if wallet["pubkey_hash"] == pubkey_hash:
            return name
    return "Unknown"


def utxo_table_rows():
    lab = st.session_state.tx_lab
    rows = []
    seen = set()

    for item in lab["known_utxos"]:
        outpoint = item["outpoint"]
        key = outpoint_key(outpoint)
        if key in seen:
            continue
        seen.add(key)

        output = item["output"]
        rows.append(
            {
                "OutPoint": short_outpoint(outpoint),
                "Chủ sở hữu/điều kiện khóa": infer_owner_from_pubkey_hash(output.pubkey_hash),
                "Số tiền demo": output.amount,
                "Chưa bị tiêu?": utxo_is_unspent(lab["utxo_set"], outpoint),
                "Mã giao dịch đầy đủ (txid)": outpoint.txid,
                "Vị trí output": outpoint_index(outpoint),
            }
        )
    return rows


def spendable_outpoints_for(owner_name: str):
    lab = st.session_state.tx_lab
    owner_hash = lab["wallets"][owner_name]["pubkey_hash"]
    result = []
    seen = set()

    for item in lab["known_utxos"]:
        outpoint = item["outpoint"]
        output = item["output"]
        key = outpoint_key(outpoint)
        if key in seen:
            continue
        seen.add(key)

        if output.pubkey_hash == owner_hash and utxo_is_unspent(lab["utxo_set"], outpoint):
            result.append(outpoint)

    return result


def find_known_output(outpoint):
    lab = st.session_state.tx_lab
    for item in lab["known_utxos"]:
        if outpoint_key(item["outpoint"]) == outpoint_key(outpoint):
            return item["output"]
    return utxo_get_output(lab["utxo_set"], outpoint)


def build_unsigned_tx(sender: str, receiver: str, outpoint, amount: int) -> None:
    lab = st.session_state.tx_lab
    receiver_wallet = lab["wallets"][receiver]

    tx = Transaction(
        inputs=[make_tx_input(outpoint)],
        outputs=[
            TxOutput(
                amount=int(amount),
                pubkey_hash=receiver_wallet["pubkey_hash"],
            )
        ],
    )

    lab["draft_tx"] = tx
    lab["signed_tx"] = None
    lab["last_verify_details"] = None
    lab_log(f"Đã tạo giao dịch chưa ký: {sender} -> {receiver}, amount={amount}, input={short_outpoint(outpoint)}")


def sign_lab_tx(signer: str) -> None:
    lab = st.session_state.tx_lab
    if lab["draft_tx"] is None:
        st.warning("Chưa có giao dịch nháp. Hãy tạo giao dịch trước.")
        return

    tx = copy.deepcopy(lab["draft_tx"])
    private_key = lab["wallets"][signer]["private_key"]

    try:
        sign_transaction_input(ECDSA_PARAMS, tx, 0, private_key)
    except Exception as exc:
        st.error(f"Không ký được giao dịch: {exc}")
        lab_log(f"Ký thất bại với người ký {signer}: {exc}")
        return

    lab["signed_tx"] = tx
    lab["last_verify_details"] = None
    lab_log(f"Đã ký giao dịch nháp bằng {signer}.")


def verify_lab_tx() -> None:
    lab = st.session_state.tx_lab
    if lab["signed_tx"] is None:
        st.warning("Chưa có giao dịch đã ký.")
        return

    details = tx_lab_verify_details(lab["signed_tx"], 0, lab["utxo_set"])
    lab["last_verify_details"] = details

    if details["overall"]:
        st.success("✅ Node mô phỏng CHẤP NHẬN giao dịch.")
        lab_log("Node kiểm tra giao dịch: CHẤP NHẬN.")
    else:
        st.error("❌ Node mô phỏng TỪ CHỐI giao dịch.")
        lab_log("Node kiểm tra giao dịch: TỪ CHỐI.")


def broadcast_lab_tx() -> None:
    lab = st.session_state.tx_lab
    if lab["signed_tx"] is None:
        st.warning("Chưa có giao dịch đã ký để gửi/áp dụng.")
        return

    tx = lab["signed_tx"]
    accepted = utxo_apply_transaction(lab["utxo_set"], ECDSA_PARAMS, tx)

    if not accepted:
        st.error("❌ Giao dịch bị bộ kiểm tra UTXO mô phỏng từ chối.")
        lab_log("Giao dịch bị từ chối.")
        lab["last_verify_details"] = tx_lab_verify_details(tx, 0, lab["utxo_set"])
        return

    # Thêm các output mới vào known_utxos nếu UTXOSet chưa tự expose được.
    txid = txid_demo(tx)
    for i, output in enumerate(tx.outputs):
        new_outpoint = make_outpoint(txid, i)
        if not utxo_exists(lab["utxo_set"], new_outpoint):
            utxo_add(lab["utxo_set"], new_outpoint, output)

        if all(outpoint_key(item["outpoint"]) != outpoint_key(new_outpoint) for item in lab["known_utxos"]):
            lab["known_utxos"].append(
                {
                    "outpoint": new_outpoint,
                    "output": output,
                    "created_for": infer_owner_from_pubkey_hash(output.pubkey_hash),
                    "created_by": "transaction",
                }
            )

    st.success("✅ Giao dịch được chấp nhận. Tập UTXO đã được cập nhật.")
    lab_log(f"Giao dịch được áp dụng. Mã giao dịch mới={txid[:12]}...")


def render_action_log() -> None:
    lab = st.session_state.tx_lab
    with st.expander("🧾 Nhật ký thao tác", expanded=True):
        for i, line in enumerate(lab["action_log"][-20:], 1):
            st.write(f"{i}. {line}")


def render_current_tx(label: str, tx) -> None:
    st.markdown(f"#### {label}")
    if tx is None:
        st.info("Chưa có giao dịch.")
        return

    try:
        st.code(serialize_unsigned_tx(tx).decode("utf-8"), language="json")
    except Exception as exc:
        st.warning(f"Không chuyển giao dịch sang dạng dữ liệu được: {exc}")

    try:
        st.caption(f"mã băm giao dịch mô phỏng: `{txid_demo(tx)}`")
    except Exception:
        pass

    if tx.inputs:
        tx_input = tx.inputs[0]
        signature = get_input_signature(tx_input)
        public_key = get_input_public_key(tx_input)
        if signature is not None or public_key is not None:
            st.code(
                f"chữ ký = {signature}\nkhóa công khai = {point_to_text(public_key)}",
                language="text",
            )


# ============================================================
# PAGE 0
# ============================================================
def demo_big_picture():
    st.title("0. Bức tranh tổng quan")
    render_page_intro(
        "Bitcoin cần giải bài toán gì trong môi trường không có ngân hàng trung gian?",
        "Điều cần chứng minh không phải danh tính tài khoản, mà là quyền chi tiêu một UTXO cụ thể.",
        "Trang này đặt toàn bộ mạch: quyền sở hữu -> UTXO -> ECC -> ECDLP -> ECDSA -> xác thực giao dịch.",
    )

    st.info(
        "Luận điểm trung tâm: Bitcoin không dùng ECC/ECDSA để mã hóa giao dịch. "
        "Bitcoin dùng chữ ký số để xác thực quyền chi tiêu."
    )

    render_term_notes([
        ("UTXO", "Unspent Transaction Output: khoản đầu ra chưa bị tiêu, giống một tờ tiền rời rạc."),
        ("Quyền chi tiêu", "khả năng chứng minh mình được phép tiêu một UTXO cụ thể."),
        ("ECDSA", "thuật toán ký số: khóa bí mật dùng để ký, khóa công khai dùng để kiểm tra."),
        ("ECDLP", "bài toán khó: biết G và Q = dG nhưng rất khó tìm lại d khi tham số đủ lớn."),
    ])

    storyline = [
        {
            "Bước": "0",
            "Câu hỏi": "Bitcoin cần chứng minh điều gì?",
            "Ý chính": "Quyền chi tiêu UTXO mà không lộ khóa bí mật",
        },
        {
            "Bước": "1",
            "Câu hỏi": "Quyền chi tiêu được biểu diễn thế nào?",
            "Ý chính": "Ai thỏa điều kiện khóa của UTXO thì tiêu được",
        },
        {
            "Bước": "2",
            "Câu hỏi": "Khóa bí mật tạo khóa công khai thế nào?",
            "Ý chính": "Q = dG",
        },
        {
            "Bước": "3",
            "Câu hỏi": "Vì sao có Q mà không suy ra được d?",
            "Ý chính": "ECDLP khó trên secp256k1",
        },
        {
            "Bước": "4",
            "Câu hỏi": "ECDSA ký và kiểm tra chữ ký thế nào?",
            "Ý chính": "Private key ký, public key kiểm tra",
        },
        {
            "Bước": "5",
            "Câu hỏi": "ECDSA đi vào giao dịch Bitcoin thế nào?",
            "Ý chính": "Chữ ký mở khóa UTXO trong input",
        },
        {
            "Bước": "6",
            "Câu hỏi": "Triển khai sai thì sao?",
            "Ý chính": "Lặp nonce k có thể lộ private key",
        },
        {
            "Bước": "7",
            "Câu hỏi": "Phòng thủ thế nào?",
            "Ý chính": "RFC6979, constant-time, chuẩn hóa chữ ký",
        },
        {
            "Bước": "8",
            "Câu hỏi": "Tối ưu kiểm tra chữ ký thế nào?",
            "Ý chính": "Shamir's trick tính u1G + u2Q nhanh hơn",
        },
        {
            "Bước": "9",
            "Câu hỏi": "Toy demo liên hệ công cụ thật thế nào?",
            "Ý chính": "Bonus: đối chiếu với OpenSSL secp256k1",
        }
    ]
    st.dataframe(pd.DataFrame(storyline), use_container_width=True)

    render_learning_summary(
        "Bức tranh tổng quan",
        [
            "Bắt đầu từ bài toán sở hữu trong môi trường không tin cậy.",
            "ECC/ECDSA dùng để chứng minh quyền chi tiêu, không dùng để mã hóa giao dịch.",
            "Phòng lab giao dịch mô phỏng là cầu nối giữa ECDSA và luồng UTXO giống Bitcoin.",
        ],
    )


# ============================================================
# PAGE 1
# ============================================================
def demo_ownership_in_bitcoin():
    st.title("1. Quyền sở hữu trong Bitcoin")
    render_page_intro(
        "Quyền sở hữu (ownership) trong Bitcoin được biểu diễn thế nào?",
        "Quyền sở hữu không phải là tài khoản/mật khẩu hay một dòng số dư. Trong mô hình UTXO, sở hữu nghĩa là mở được đúng khoản tiền chưa tiêu.",
        "Trang này mô tả mô hình giống P2PKH: mã băm khóa công khai khóa UTXO, còn chữ ký + khóa công khai dùng để mở khóa.",
    )

    st.warning(
        "Đây chỉ là mô hình giáo dục giống P2PKH, không phải Bitcoin thật. "
        "Bitcoin thật có nhiều loại Script và điều kiện tiêu khác nhau."
    )

    rows = [
        {"Lớp": "UTXO", "Ý nghĩa": "Một khoản đầu ra chưa bị tiêu, có điều kiện khóa riêng"},
        {"Lớp": "Điều kiện khóa (locking condition)", "Ý nghĩa": "Trong demo: mã băm của khóa công khai"},
        {"Lớp": "Dữ liệu mở khóa (unlocking data)", "Ý nghĩa": "Trong demo: chữ ký số + khóa công khai"},
        {"Lớp": "Kiểm tra", "Ý nghĩa": "mã băm khóa công khai khớp điều kiện khóa và chữ ký ECDSA hợp lệ"},
        {"Lớp": "Lượt tiêu được chấp nhận", "Ý nghĩa": "UTXO tồn tại, chưa bị tiêu, và điều kiện khóa được đáp ứng"},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    render_learning_summary(
        "Ownership",
        [
            "Ví không thật sự chứa coin; ví giữ khóa bí mật (private key).",
            "UTXO set mới là nơi biểu diễn các output còn tiêu được.",
            "Chữ ký hợp lệ là cách chứng minh quyền mở khóa UTXO trong mô phỏng.",
        ],
    )


# ============================================================
# PAGE 2
# ============================================================
def demo_ecc_toy_curve():
    st.title("2. ECC: Từ khóa bí mật đến khóa công khai")

    render_page_intro(
        "Khóa bí mật tạo ra khóa công khai như thế nào?",
        "Trong ECC, khóa bí mật d là một số nguyên được giữ kín. Từ d, ta tính khóa công khai Q bằng phép nhân điểm: Q = dG.",
        "Ở phần này, ta dùng một đường cong mô phỏng nhỏ để thấy trực quan quá trình tạo Q từ d.",
    )

    st.warning(
        f"Đây là đường cong mô phỏng rất nhỏ: p = {DEMO_P}, a = {DEMO_A}, b = {DEMO_B}, "
        f"G = {point_to_text(GENERATOR_POINT)}, n = {ORDER_N}. "
        "Đường cong này chỉ dùng để học, không phải secp256k1 và không an toàn cho bảo mật thật."
    )

    render_term_notes([
        (
            "Khóa bí mật d",
            "Một số nguyên do người dùng giữ kín. Trong Bitcoin thật, đây là giá trị tuyệt đối không được để lộ."
        ),
        (
            "Khóa công khai Q",
            "Một điểm trên đường cong elliptic, được tính từ khóa bí mật theo công thức Q = dG."
        ),
        (
            "Điểm sinh G",
            "Một điểm cố định đã được chọn trước. Có thể hiểu G là điểm xuất phát để tạo khóa công khai."
        ),
        (
            "Đường cong mô phỏng",
            "Một curve nhỏ để dễ tính toán và trực quan hóa. Nó giúp hiểu ý tưởng, nhưng không dùng cho hệ thống thật."
        ),
        (
            "Trường hữu hạn F_p",
            "Tập các số 0, 1, ..., p-1 với phép cộng, trừ, nhân, chia đều lấy phần dư modulo p. ECC trong mật mã chạy trên môi trường rời rạc này."
        ),
        (
            "secp256k1",
            "Đường cong Bitcoin dùng trong ECDSA truyền thống, có dạng y² = x³ + 7 trên một trường hữu hạn rất lớn."
        ),
    ])

    st.latex(rf"y^2 \equiv x^3 + {DEMO_A}x + {DEMO_B} \pmod{{{DEMO_P}}}")

    with st.container(border=True):
        st.markdown("### ₿ Liên hệ với Bitcoin: secp256k1")

        st.markdown(
            """
            Bitcoin truyền thống dùng đường cong **secp256k1**. Nó cũng có dạng:

            ```text
            y² = x³ + ax + b mod p
            ```

            nhưng với:

            ```text
            a = 0
            b = 7
            ```

            nên phương trình trở thành:

            ```text
            y² = x³ + 7 mod p
            ```

            Điểm khác biệt ở đây là: trong demo ta dùng trường nhỏ như `F_p` để dễ vẽ,
            còn Bitcoin dùng một trường hữu hạn 256-bit rất lớn. Vì vậy demo này giúp hiểu ý tưởng,
            chứ không mô phỏng độ an toàn thật của Bitcoin.
            """
        )

    d = st.slider(
        "🔑 Chọn khóa bí mật mô phỏng d",
        min_value=1,
        max_value=ORDER_N - 1,
        value=min(5, ORDER_N - 1),
    )

    Q = ECDSA_PARAMS.curve.scalar_mul(d, ECDSA_PARAMS.G)

    st.success(
        f"Khóa công khai được tạo ra: Q = {d}G = {point_to_text(Q)}"
    )

    with st.expander("🔎 Xem quá trình double-and-add tạo Q", expanded=False):
        st.markdown(
            """
            Phép nhân điểm `Q = dG` không phải là nhân từng tọa độ của điểm `G` với số `d`.

            Trong ECC, `dG` nghĩa là cộng điểm `G` với chính nó nhiều lần:

            ```text
            dG = G + G + ... + G
            ```

            Nhưng nếu cộng lặp từng lần thì rất chậm. Vì vậy ta dùng **double-and-add**:
            biểu diễn `d` dưới dạng nhị phân, rồi kết hợp hai thao tác:

            - **double**: nhân đôi điểm hiện tại.
            - **add**: cộng điểm vào kết quả khi bit đang xét bằng 1.
            """
        )

        st.code(
            f"d = {d}\n"
            f"binary(d) = {bin(d)}\n"
            f"Q = dG = {d}G",
            language="text",
        )

        trace_rows, trace_result = trace_double_and_add(
            ECDSA_PARAMS.curve,
            d,
            ECDSA_PARAMS.G,
        )

        st.dataframe(pd.DataFrame(trace_rows), use_container_width=True)

        if trace_result == Q:
            st.success(
                f"Kết quả cuối cùng của double-and-add khớp với Q: {point_to_text(trace_result)}"
            )
        else:
            st.error(
                f"Kết quả trace không khớp. Trace = {point_to_text(trace_result)}, Q = {point_to_text(Q)}"
            )

        st.info(
            "Ý nghĩa: tính Q từ d là nhanh vì double-and-add dùng số bit của d, "
            "không cần cộng G lặp lại d lần. Nhưng đi ngược từ Q về d lại là bài toán ECDLP."
        )

    # points = get_curve_points(
    #     ECDSA_PARAMS.curve.p,
    #     ECDSA_PARAMS.curve.a,
    #     ECDSA_PARAMS.curve.b,
    # )

    # df = pd.DataFrame(points, columns=["x", "y"])

    # colors, sizes, labels = [], [], []

    # for x, y in points:
    #     if x == ECDSA_PARAMS.G.x and y == ECDSA_PARAMS.G.y:
    #         colors.append("Điểm sinh G")
    #         sizes.append(18)
    #         labels.append("G")
    #     elif not Q.is_infinity and x == Q.x and y == Q.y:
    #         colors.append("Khóa công khai Q")
    #         sizes.append(18)
    #         labels.append("Q")
    #     else:
    #         colors.append("Điểm trên đường cong")
    #         sizes.append(6)
    #         labels.append("point")

    # df["type"] = colors
    # df["size"] = sizes
    # df["label"] = labels

    # fig = px.scatter(
    #     df,
    #     x="x",
    #     y="y",
    #     color="type",
    #     size="size",
    #     hover_name="label",
    #     title=f"Các điểm trên đường cong mô phỏng trên trường F_{DEMO_P}",
    # )

    # st.plotly_chart(fig, use_container_width=True)

    viz_tab_real, viz_tab_finite = st.tabs([
        "🌊 Trực giác hình học trên số thực",
        f"🔢 Điểm rời rạc trên F_{DEMO_P}",
    ])

    with viz_tab_real:
        st.markdown(
            """
            Trên số thực, elliptic curve nhìn giống một đường cong mượt.
            Hình này chỉ để lấy trực giác hình học.

            Nhưng trong mật mã, ta không dùng toàn bộ đường cong mượt này.
            Ta làm việc trên trường hữu hạn `F_p`, nên chỉ còn các điểm rời rạc.
            """
        )

        real_choice = st.radio(
            "Chọn đường cong để quan sát",
            [
                "Đường cong mô phỏng hiện tại",
                "Dạng Bitcoin: y² = x³ + 7",
            ],
            horizontal=True,
        )

        if real_choice == "Dạng Bitcoin: y² = x³ + 7":
            real_a, real_b = 0, 7
            real_title = "Trực giác hình học của dạng Bitcoin: y² = x³ + 7"
        else:
            real_a, real_b = DEMO_A, DEMO_B
            real_title = f"Trực giác hình học của đường cong mô phỏng: y² = x³ + {DEMO_A}x + {DEMO_B}"

        real_df = get_real_curve_points(
            real_a,
            real_b,
            x_min=-5,
            x_max=8,
            samples=900,
        )

        if real_df.empty:
            st.warning("Không có đủ điểm thực để vẽ trong khoảng hiện tại.")
        else:
            fig_real = px.line(
                real_df,
                x="x",
                y="y",
                color="Nhánh",
                title=real_title,
            )

            fig_real.update_layout(
                height=520,
                xaxis_title="x",
                yaxis_title="y",
            )

            fig_real.update_yaxes(
                scaleanchor="x",
                scaleratio=1,
            )

            st.plotly_chart(fig_real, use_container_width=True)

        st.info(
            "Hình này giúp hiểu trực giác 'đường cong'. "
            "Phần mật mã nằm ở tab bên cạnh: các điểm rời rạc trên F_p."
        )

    with viz_tab_finite:
        st.markdown(
            f"""
            Đây là đường cong trên trường hữu hạn `F_{DEMO_P}`.

            Nghĩa là `x` và `y` chỉ nhận các giá trị:

            ```text
            0, 1, 2, ..., {DEMO_P - 1}
            ```

            và mọi phép tính đều lấy phần dư modulo `{DEMO_P}`.
            Vì vậy hình không còn là đường cong mượt, mà là một tập các điểm rời rạc.
            """
        )

        points = get_curve_points(
            ECDSA_PARAMS.curve.p,
            ECDSA_PARAMS.curve.a,
            ECDSA_PARAMS.curve.b,
        )

        df = pd.DataFrame(points, columns=["x", "y"])

        colors, sizes, labels = [], [], []

        q_is_normal_point = Q is not None and not getattr(Q, "is_infinity", False)

        for x, y in points:
            if x == ECDSA_PARAMS.G.x and y == ECDSA_PARAMS.G.y:
                colors.append("Điểm sinh G")
                sizes.append(18)
                labels.append("G")
            elif q_is_normal_point and x == Q.x and y == Q.y:
                colors.append("Khóa công khai Q")
                sizes.append(18)
                labels.append("Q")
            else:
                colors.append("Điểm trên đường cong")
                sizes.append(7)
                labels.append("point")

        df["type"] = colors
        df["size"] = sizes
        df["label"] = labels

        fig = px.scatter(
            df,
            x="x",
            y="y",
            color="type",
            size="size",
            hover_name="label",
            title=f"Các điểm trên đường cong mô phỏng trên trường F_{DEMO_P}",
        )

        fig.update_layout(
            height=560,
            xaxis_title=f"x trong F_{DEMO_P}",
            yaxis_title=f"y trong F_{DEMO_P}",
        )

        fig.update_xaxes(
            dtick=1,
            range=[-1, DEMO_P],
            showgrid=True,
        )

        fig.update_yaxes(
            dtick=1,
            range=[-1, DEMO_P],
            showgrid=True,
            scaleanchor="x",
            scaleratio=1,
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "G là điểm sinh. Q là khóa công khai được tạo từ Q = dG. "
            "Các điểm còn lại chỉ là những điểm thỏa phương trình trên F_p."
        )

    render_learning_summary(
        "ECC",
        [
            "Khóa bí mật d là một số nguyên được giữ kín.",
            "Khóa công khai Q là một điểm trên đường cong, được tính bằng Q = dG.",
            "Phép nhân điểm dG được tính hiệu quả bằng double-and-add: kết hợp cộng điểm và nhân đôi điểm.",
            "Tính Q từ d là nhanh, nhưng tìm ngược d từ Q là bài toán ECDLP.",
            "Đây là nền tảng giúp Bitcoin công khai khóa Q mà vẫn không làm lộ khóa bí mật d.",
        ],
    )


# ============================================================
# ECDLP ATTACK HELPERS: BRUTE FORCE / BSGS / POLLARD RHO
# ============================================================
def point_key(P):
    """Biến một điểm elliptic thành key để lưu trong dict."""
    if P is None:
        return ("none",)
    if getattr(P, "is_infinity", False):
        return ("inf",)
    return (int(P.x), int(P.y))


def curve_add_point(curve, P, Q):
    """Cộng hai điểm elliptic, viết kiểu phòng thủ để hợp nhiều version Curve."""
    if hasattr(curve, "add"):
        return curve.add(P, Q)
    if hasattr(curve, "point_add"):
        return curve.point_add(P, Q)
    if hasattr(curve, "add_points"):
        return curve.add_points(P, Q)

    try:
        return P + Q
    except Exception as exc:
        raise AttributeError(
            "Không tìm thấy hàm cộng điểm. Cần có curve.add(P,Q), "
            "curve.point_add(P,Q), curve.add_points(P,Q), hoặc Point.__add__."
        ) from exc


def brute_force_dlog_demo(curve, G, Q, n: int):
    """Tìm d bằng brute force: thử từng k cho tới khi kG = Q."""
    rows = []
    recovered = None

    for k in range(0, n):
        candidate = curve.scalar_mul(k, G)
        match = candidate == Q

        rows.append({
            "k thử": k,
            "kG": point_to_text(candidate),
            "Trùng với Q?": match,
        })

        if match and recovered is None:
            recovered = k

    return {
        "method": "Brute force",
        "recovered": recovered,
        "steps": len(rows),
        "memory": "O(1)",
        "rows": rows,
        "success": recovered is not None,
    }


def baby_step_giant_step_demo(curve, G, Q, n: int):
    """Baby-step Giant-step cho ECDLP trên đường cong mô phỏng.

    Ý tưởng:
    - Viết d = i*m + j, với m ≈ √n.
    - Baby step: lưu bảng jG.
    - Giant step: thử Q - i(mG).
    - Khi hai phía gặp nhau, suy ra d = i*m + j.

    Độ phức tạp:
    - Thời gian: O(√n)
    - Bộ nhớ: O(√n)
    """
    m = int(n ** 0.5)
    if m * m < n:
        m += 1

    baby_table = {}
    baby_rows = []

    for j in range(m):
        point = curve.scalar_mul(j, G)
        key = point_key(point)

        if key not in baby_table:
            baby_table[key] = j

        baby_rows.append({
            "j": j,
            "jG": point_to_text(point),
            "Ghi chú": "baby step: bước nhỏ",
        })

    # Vì G có order n nên -mG = (n - m)G.
    negative_mG = curve.scalar_mul((n - m) % n, G)

    giant_rows = []
    gamma = Q
    recovered = None
    matched_i = None
    matched_j = None

    for i in range(m):
        key = point_key(gamma)
        found = key in baby_table

        giant_rows.append({
            "i": i,
            "Q - i(mG)": point_to_text(gamma),
            "Có trong bảng baby-step?": found,
        })

        if found:
            matched_i = i
            matched_j = baby_table[key]
            recovered = (i * m + matched_j) % n
            break

        gamma = curve_add_point(curve, gamma, negative_mG)

    return {
        "method": "Baby-step Giant-step",
        "recovered": recovered,
        "steps": len(baby_rows) + len(giant_rows),
        "memory": f"{len(baby_table)} điểm ≈ O(√n)",
        "m": m,
        "baby_rows": baby_rows,
        "giant_rows": giant_rows,
        "matched_i": matched_i,
        "matched_j": matched_j,
        "success": recovered is not None,
    }


def pollard_rho_step(curve, G, Q, X, a: int, b: int, n: int):
    """Một bước random-walk cho Pollard rho.

    Ta luôn giữ:
        X = aG + bQ

    Partition dùng x mod 3 để demo dễ hiểu.
    """
    if X is None or getattr(X, "is_infinity", False):
        bucket = 0
    else:
        bucket = int(X.x) % 3

    if bucket == 0:
        # X <- X + G
        X = curve_add_point(curve, X, G)
        a = (a + 1) % n
    elif bucket == 1:
        # X <- 2X
        X = curve.scalar_mul(2, X)
        a = (2 * a) % n
        b = (2 * b) % n
    else:
        # X <- X + Q
        X = curve_add_point(curve, X, Q)
        b = (b + 1) % n

    return X, a, b


def pollard_rho_dlog_demo(curve, G, Q, n: int, max_steps: int = 1000):
    """Pollard rho cho ECDLP trên đường cong mô phỏng.

    Ý tưởng:
    - Cho hai con trỏ chạy trong nhóm điểm.
    - Khi hai con trỏ gặp nhau tại cùng một điểm, ta có collision.
    - Từ collision có thể suy ra d nếu mẫu số khả nghịch modulo n.

    Độ phức tạp kỳ vọng:
    - Thời gian: O(√n)
    - Bộ nhớ: O(1)
    """
    starts = [
        (1, 0),
        (0, 1),
        (1, 1),
        (2, 3),
        (3, 5),
        (5, 8),
        (8, 13),
    ]

    all_rows = []
    degenerate_count = 0

    for start_idx, (a0, b0) in enumerate(starts, 1):
        X0 = curve_add_point(
            curve,
            curve.scalar_mul(a0 % n, G),
            curve.scalar_mul(b0 % n, Q),
        )

        tortoise = (X0, a0 % n, b0 % n)
        hare = (X0, a0 % n, b0 % n)

        for step in range(1, max_steps + 1):
            tortoise = pollard_rho_step(curve, G, Q, *tortoise, n)
            hare = pollard_rho_step(curve, G, Q, *hare, n)
            hare = pollard_rho_step(curve, G, Q, *hare, n)

            X1, a1, b1 = tortoise
            X2, a2, b2 = hare

            collision = point_key(X1) == point_key(X2)

            all_rows.append({
                "Lần chạy": start_idx,
                "Bước": step,
                "Tortoise X": point_to_text(X1),
                "Hare X": point_to_text(X2),
                "Collision?": collision,
            })

            if not collision:
                continue

            numerator = (a1 - a2) % n
            denominator = (b2 - b1) % n
            denominator_inv = safe_mod_inverse(denominator, n)

            if denominator_inv is None:
                degenerate_count += 1
                break

            recovered = (numerator * denominator_inv) % n

            if curve.scalar_mul(recovered, G) == Q:
                return {
                    "method": "Pollard rho",
                    "status": "success",
                    "recovered": recovered,
                    "steps": step,
                    "memory": "O(1)",
                    "rows": all_rows,
                    "degenerate_count": degenerate_count,
                    "note": "Tìm được collision hữu ích.",
                }

            degenerate_count += 1
            break

    return {
        "method": "Pollard rho",
        "status": "failure",
        "recovered": None,
        "steps": len(all_rows),
        "memory": "O(1)",
        "rows": all_rows,
        "degenerate_count": degenerate_count,
        "note": "Không tìm được collision hữu ích trong giới hạn bước. Đây là chuyện có thể xảy ra trong demo random-walk nhỏ.",
    }



# ============================================================
# PAGE 3
# ============================================================
def demo_ecdlp_explanation():
    st.title("3. ECDLP: Vì sao public key không làm lộ private key?")

    render_page_intro(
        "Vì sao biết Q mà không suy ra được d?",
        "Trong ECC, khóa công khai được tạo từ khóa bí mật theo công thức Q = dG.",
        "Ta thử đóng vai attacker trên đường cong mô phỏng: brute force, Baby-step Giant-step và Pollard rho.",
    )

    st.warning(
        f"Đây là đường cong mô phỏng rất nhỏ, n = {ORDER_N}, chỉ dùng để minh họa ý tưởng. "
        "Không brute force secp256k1 và không thử với khóa Bitcoin thật."
    )

    render_term_notes([
        (
            "ECDLP",
            "Elliptic Curve Discrete Logarithm Problem: biết G và Q = dG, tìm lại d."
        ),
        (
            "Brute force",
            "Thử lần lượt từng k cho đến khi kG = Q. Dễ hiểu nhất, nhưng chậm nhất: O(n)."
        ),
        (
            "Baby-step Giant-step",
            "Chia d thành d = i*m + j. Lưu bảng các bước nhỏ jG, rồi nhảy bước lớn từ Q. Thời gian O(√n), bộ nhớ O(√n)."
        ),
        (
            "Pollard rho",
            "Đi random-walk trong nhóm điểm để tìm collision. Kỳ vọng O(√n), dùng ít bộ nhớ hơn BSGS, nhưng khó giải thích hơn."
        ),
        (
            "secp256k1",
            "Đường cong elliptic mà Bitcoin dùng trong ECDSA truyền thống. Tham số thật lớn hơn đường cong mô phỏng rất nhiều."
        ),
    ])

    d_secret = st.slider(
        "Chọn khóa bí mật mô phỏng d",
        min_value=1,
        max_value=ORDER_N - 1,
        value=min(5, ORDER_N - 1),
    )

    Q = ECDSA_PARAMS.curve.scalar_mul(d_secret, ECDSA_PARAMS.G)

    st.info(
        f"Khóa công khai được tạo ra từ khóa bí mật: "
        f"Q = {d_secret}G = {point_to_text(Q)}"
    )

    st.markdown(
        """
        Bây giờ ta giả sử attacker chỉ biết `G` và `Q`, không biết `d`.
        Các thuật toán bên dưới đều cố tìm lại `d` trên **đường cong mô phỏng nhỏ**.
        """
    )

    brute_result = brute_force_dlog_demo(
        ECDSA_PARAMS.curve,
        ECDSA_PARAMS.G,
        Q,
        ORDER_N,
    )

    show_bsgs = st.checkbox(
        "Hiện thêm Baby-step Giant-step",
        value=True,
        help="BSGS giúp so sánh độ phức tạp: từ O(n) xuống O(√n), nhưng tốn thêm bộ nhớ.",
    )

    show_rho = st.checkbox(
        "Hiện thêm Pollard rho",
        value=False,
        help="Pollard rho là phần nâng cao. Với n nhỏ/prime như 23 thì dễ demo hơn, nhưng vẫn có thể gặp collision suy biến.",
    )

    bsgs_result = None
    rho_result = None

    if show_bsgs:
        bsgs_result = baby_step_giant_step_demo(
            ECDSA_PARAMS.curve,
            ECDSA_PARAMS.G,
            Q,
            ORDER_N,
        )

    if show_rho:
        max_steps = int(st.slider(
            "Giới hạn số bước Pollard rho",
            min_value=50,
            max_value=3000,
            value=500,
            step=50,
        ))

        rho_result = pollard_rho_dlog_demo(
            ECDSA_PARAMS.curve,
            ECDSA_PARAMS.G,
            Q,
            ORDER_N,
            max_steps=max_steps,
        )

    summary_rows = [
        {
            "Thuật toán": "Brute force",
            "Ý tưởng": "Thử từng k",
            "Độ phức tạp": "O(n) thời gian, O(1) bộ nhớ",
            "d tìm được": brute_result["recovered"],
            "Số bước demo": brute_result["steps"],
            "Kết quả": "Thành công" if brute_result["success"] else "Thất bại",
        },
    ]

    if bsgs_result is not None:
        summary_rows.append({
            "Thuật toán": "Baby-step Giant-step",
            "Ý tưởng": "Gặp nhau ở giữa: d = i*m + j",
            "Độ phức tạp": "O(√n) thời gian, O(√n) bộ nhớ",
            "d tìm được": bsgs_result["recovered"],
            "Số bước demo": bsgs_result["steps"],
            "Kết quả": "Thành công" if bsgs_result["success"] else "Thất bại",
        })

    if rho_result is not None:
        summary_rows.append({
            "Thuật toán": "Pollard rho",
            "Ý tưởng": "Random-walk tìm collision",
            "Độ phức tạp": "O(√n) kỳ vọng, O(1) bộ nhớ",
            "d tìm được": rho_result["recovered"],
            "Số bước demo": rho_result["steps"],
            "Kết quả": "Thành công" if rho_result["status"] == "success" else "Chưa thành công",
        })

    st.subheader("So sánh nhanh")
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    tabs = ["1️⃣ Brute force"]

    if show_bsgs:
        tabs.append("2️⃣ Baby-step Giant-step")

    if show_rho:
        tabs.append("3️⃣ Pollard rho")

    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        st.markdown(
            """
            **Brute force** là cách ngây thơ nhất: thử `k = 0, 1, 2, ...`
            cho tới khi tìm được `kG = Q`.

            Nó dễ hiểu, nhưng nếu `n` cực lớn thì gần như bất khả thi.
            """
        )

        st.dataframe(
            pd.DataFrame(brute_result["rows"]),
            use_container_width=True,
        )

        if brute_result["success"]:
            st.success(f"Brute force tìm được d = {brute_result['recovered']}.")

    tab_index = 1

    if show_bsgs and bsgs_result is not None:
        with tab_objects[tab_index]:
            st.markdown(
                f"""
                **Baby-step Giant-step** chọn `m = ceil(sqrt(n)) = {bsgs_result['m']}`.

                Ta viết:

                ```text
                d = i*m + j
                Q = dG = i(mG) + jG
                Q - i(mG) = jG
                ```

                Nghĩa là:

                - Một bên lưu các **bước nhỏ** `jG`.
                - Một bên nhảy **bước lớn** `Q - i(mG)`.
                - Khi hai bên gặp nhau thì tìm được `d`.
                """
            )

            col_baby, col_giant = st.columns(2)

            with col_baby:
                st.markdown("#### Baby steps: lưu bảng jG")
                st.dataframe(
                    pd.DataFrame(bsgs_result["baby_rows"]),
                    use_container_width=True,
                )

            with col_giant:
                st.markdown("#### Giant steps: thử Q - i(mG)")
                st.dataframe(
                    pd.DataFrame(bsgs_result["giant_rows"]),
                    use_container_width=True,
                )

            if bsgs_result["success"]:
                st.success(
                    f"BSGS tìm được d = {bsgs_result['recovered']} "
                    f"với i = {bsgs_result['matched_i']}, j = {bsgs_result['matched_j']}."
                )
            else:
                st.warning("BSGS chưa tìm được d. Kiểm tra lại order n hoặc phép cộng điểm.")

        tab_index += 1

    if show_rho and rho_result is not None:
        with tab_objects[tab_index]:
            st.markdown(
                """
                **Pollard rho** cũng cố tìm `d`, nhưng không lưu bảng lớn như BSGS.
                Nó cho hai con trỏ chạy trong nhóm điểm. Khi hai con trỏ gặp nhau
                tại cùng một điểm, ta có một phương trình để suy ra `d`.

                Vì đây là random-walk trên đường cong mô phỏng, đôi khi collision bị suy biến.
                Khi đó app sẽ báo rõ thay vì giả vờ thành công.
                """
            )

            if rho_result["status"] == "success":
                st.success(f"Pollard rho tìm được d = {rho_result['recovered']}.")
            else:
                st.warning(rho_result["note"])

            st.caption(f"Số collision suy biến: {rho_result['degenerate_count']}")

            rows = rho_result["rows"][:200]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

            if len(rho_result["rows"]) > 200:
                st.caption("Chỉ hiển thị 200 dòng đầu để tránh bảng quá dài.")

    st.info(
        "Kết luận quan trọng: các thuật toán này phá được đường cong mô phỏng vì n rất nhỏ. "
        "Với secp256k1 thật, kể cả thuật toán O(√n) vẫn quá lớn để tấn công thực tế bằng máy tính cổ điển."
    )

    render_learning_summary(
        "ECDLP",
        [
            "Brute force dễ hiểu nhưng mất O(n) bước.",
            "Baby-step Giant-step giảm xuống O(√n) thời gian nhưng phải lưu O(√n) điểm.",
            "Pollard rho cũng khoảng O(√n) kỳ vọng và dùng ít bộ nhớ hơn, nhưng demo khó trực quan hơn.",
            "Các thuật toán này giúp bài có màu độ phức tạp, nhưng không có nghĩa là phá được Bitcoin thật.",
        ],
    )



def find_tampered_message_that_fails(Q, signature, original_msg: str) -> str:
    """Tìm một dữ liệu đã sửa khiến verify trả về False.

    Vì toy curve rất nhỏ, đôi khi hai message khác nhau vẫn rơi vào edge case
    làm verify True. Hàm này chỉ phục vụ demo UI: thử một vài biến thể cho tới
    khi tìm được message chắc chắn bị từ chối.
    """
    candidates = [
        original_msg + " [đã sửa]",
        original_msg + "!",
        original_msg.replace("Bitcoin", "Mallory"),
        "Mallory sửa nội dung sau khi ký",
        "Alice trả Mallory 100 BTC",
        "Nội dung này đã bị thay đổi",
    ]

    for candidate in candidates:
        if candidate != original_msg and not verify(
            ECDSA_PARAMS,
            Q,
            candidate.encode("utf-8"),
            signature,
        ):
            return candidate

    for i in range(1, 200):
        candidate = f"{original_msg} [đã sửa #{i}]"
        if not verify(ECDSA_PARAMS, Q, candidate.encode("utf-8"), signature):
            return candidate

    return original_msg + " [đã sửa]"

# ============================================================
# PAGE 4
# ============================================================
def demo_ecdsa_sign_verify():
    st.title("4. ECDSA: Ký và kiểm tra chữ ký")

    render_page_intro(
        "ECDSA chứng minh quyền sở hữu khóa bí mật như thế nào?",
        "Người ký dùng khóa bí mật để tạo chữ ký; người kiểm tra dùng khóa công khai để xác minh chữ ký.",
        "Điểm quan trọng là quá trình kiểm tra không cần biết khóa bí mật, nhưng vẫn xác nhận được chữ ký có đến từ đúng người ký hay không.",
    )

    st.warning(
        f"Đây là ECDSA mô phỏng trên đường cong rất nhỏ, n = {ORDER_N}, chỉ dùng để học. "
        "Không dùng cho khóa thật, ví thật hoặc giao dịch Bitcoin thật."
    )

    render_term_notes([
        (
            "Ký số",
            "Dùng khóa bí mật để tạo một chữ ký gắn với dữ liệu cụ thể."
        ),
        (
            "Kiểm tra chữ ký",
            "Dùng khóa công khai để kiểm tra chữ ký có hợp lệ với dữ liệu đã ký hay không."
        ),
        (
            "Chữ ký ECDSA",
            "Một cặp số (r, s), được tạo từ khóa bí mật, dữ liệu cần ký và nonce k."
        ),
        (
            "Hash",
            "Hàm băm biến dữ liệu thành một giá trị ngắn hơn, đóng vai trò như dấu vân tay của dữ liệu."
        ),
    ])

    render_ecdsa_formula_box()

    col1, col2, col3 = st.columns(3)

    with col1:
        d_demo = int(st.number_input(
            "🔑 Khóa bí mật d",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(10, ORDER_N - 1),
        ))

    with col2:
        k_demo = int(st.number_input(
            "🎲 Nonce mô phỏng k",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(3, ORDER_N - 1),
            help=(
                "Nonce chỉ dùng một lần khi ký. "
                "Page 6 sẽ cho thấy dùng lại nonce nguy hiểm như thế nào."
            ),
        ))

    with col3:
        Q_demo = ECDSA_PARAMS.curve.scalar_mul(d_demo, ECDSA_PARAMS.G)
        st.info(f"Khóa công khai tương ứng: Q = {point_to_text(Q_demo)}")

    msg_original = st.text_input(
        "📝 Dữ liệu cần ký",
        value="Hello Bitcoin",
        max_chars=120,
    )

    if st.button("🖊️ Tạo chữ ký", use_container_width=True):
        ok_nonce, nonce_msg = validate_nonce(k_demo, ECDSA_PARAMS.n)

        if not ok_nonce:
            st.warning(nonce_msg)
        else:
            try:
                r, s = sign(
                    ECDSA_PARAMS,
                    d_demo,
                    msg_original.encode("utf-8"),
                    k=k_demo,
                )

                st.session_state.sign_demo = {
                    "r": r,
                    "s": s,
                    "Q": Q_demo,
                    "msg": msg_original,
                    "d": d_demo,
                    "k": k_demo,
                }

                st.success(f"Đã tạo chữ ký ECDSA: r = {r}, s = {s}")

            except Exception as exc:
                st.error(f"Lỗi khi ký: {exc}")

    if "sign_demo" in st.session_state:
        data = st.session_state.sign_demo
        r, s, Q, msg = data["r"], data["s"], data["Q"], data["msg"]
        d = data.get("d")
        k = data.get("k")

        st.divider()
        st.subheader("🖊️ Quá trình tạo chữ ký")

        if d is not None and k is not None:
            with st.expander("🖊️ Xem các bước tạo chữ ký với số cụ thể", expanded=True):
                render_ecdsa_signing_trace(
                    ECDSA_PARAMS,
                    d,
                    msg.encode("utf-8"),
                    k,
                    (r, s),
                )
        else:
            st.info("Hãy bấm tạo lại chữ ký để xem trace quá trình ký với nonce k.")

        st.divider()
        st.subheader("🔍 Kiểm tra chữ ký")

        valid_original = verify(ECDSA_PARAMS, Q, msg.encode("utf-8"), (r, s))

        st.success(
            f"Kiểm tra với dữ liệu gốc: {valid_original}"
        )

        with st.expander("🧮 Xem các bước kiểm tra chữ ký với số cụ thể", expanded=False):
            render_ecdsa_verification_trace(
                ECDSA_PARAMS,
                Q,
                msg.encode("utf-8"),
                (r, s),
            )

        tampered_key = "ecdsa_tampered_message"

        if "ecdsa_tampered_message_next" in st.session_state:
            st.session_state[tampered_key] = st.session_state.pop("ecdsa_tampered_message_next")
        elif tampered_key not in st.session_state:
            st.session_state[tampered_key] = "Hello Hacker"

        col_tamper_input, col_tamper_button = st.columns([2, 1])

        with col_tamper_input:
            tampered = st.text_input(
                "🧪 Thử sửa dữ liệu sau khi ký",
                max_chars=120,
                key=tampered_key,
            )

        with col_tamper_button:
            st.write("")
            st.write("")
            if st.button("🎯 Tạo dữ liệu sửa chắc chắn bị từ chối", use_container_width=True):
                st.session_state.ecdsa_tampered_message_next = find_tampered_message_that_fails(
                    Q,
                    (r, s),
                    msg,
                )
                st.rerun()

        valid_tampered = verify(ECDSA_PARAMS, Q, tampered.encode("utf-8"), (r, s))

        hash_original = hash_message_to_int(msg.encode("utf-8"), ECDSA_PARAMS.n)
        hash_tampered = hash_message_to_int(tampered.encode("utf-8"), ECDSA_PARAMS.n)

        st.dataframe(
            pd.DataFrame([
                {
                    "Dữ liệu": "Gốc",
                    "Message": msg,
                    "h = H(m) mod n": hash_original,
                    "Verify": valid_original,
                },
                {
                    "Dữ liệu": "Đã sửa",
                    "Message": tampered,
                    "h = H(m) mod n": hash_tampered,
                    "Verify": valid_tampered,
                },
            ]),
            use_container_width=True,
        )

        with st.expander("🧮 Xem các bước kiểm tra chữ ký với dữ liệu đã sửa", expanded=False):
            render_ecdsa_verification_trace(
                ECDSA_PARAMS,
                Q,
                tampered.encode("utf-8"),
                (r, s),
            )

        if valid_tampered:
            st.warning(
                "Dữ liệu đã sửa vẫn được chấp nhận trong mô phỏng nhỏ. "
                "Điều này xảy ra vì n quá nhỏ, nên sau khi lấy H(m) mod n và kiểm tra x(P) mod n, "
                "một số message khác nhau vẫn có thể vô tình thỏa cùng điều kiện verify. "
                "Trong tham số thật như secp256k1, xác suất này là cực nhỏ."
            )
        else:
            st.error(
                "Dữ liệu đã sửa bị từ chối. Điều này cho thấy chữ ký ECDSA gắn chặt với dữ liệu ban đầu."
            )

    render_learning_summary(
        "ECDSA",
        [
            "Khóa bí mật d dùng để tạo chữ ký, còn khóa công khai Q dùng để kiểm tra chữ ký.",
            "Chữ ký ECDSA là cặp số (r, s), gắn với dữ liệu đã ký.",
            "Bước verify kiểm tra quan hệ x(u1G + u2Q) mod n = r, không cần biết private key.",
            "Nếu dữ liệu bị sửa, giá trị hash thay đổi, làm quan hệ kiểm tra thường không còn đúng.",
            "Trong Bitcoin, dữ liệu được ký không phải là một câu văn, mà là dữ liệu giao dịch cần được ủy quyền.",
        ],
    )


# ============================================================
# PAGE 5 - NEW INTERACTIVE TX LAB
# ============================================================
def demo_interactive_bitcoin_transaction_lab():
    st.title("5. Phòng lab giao dịch Bitcoin mô phỏng")
    render_page_intro(
        "ECDSA đi vào giao dịch giống Bitcoin như thế nào?",
        "Chữ ký + khóa công khai là dữ liệu mở khóa, dùng để chứng minh người gửi có quyền tiêu một UTXO.",
        "Người dùng tự tạo UTXO, tạo giao dịch, ký, kiểm tra, áp dụng giao dịch, sửa phá và thử tiêu hai lần.",
    )

    st.warning(
        "Đây chỉ là mô hình giáo dục giống P2PKH. Không phải Bitcoin thật, không có Script đầy đủ, "
        "không có quy tắc ký thật của Bitcoin, không có đồng thuận mạng, không kết nối network và không dùng khóa thật."
    )

    render_term_notes([
        ("UTXO", "khoản đầu ra chưa bị tiêu. Muốn tiêu phải tham chiếu đúng UTXO đó."),
        ("OutPoint", "địa chỉ của một UTXO cũ, gồm mã giao dịch txid và vị trí output."),
        ("Giao dịch chưa ký", "giao dịch mới có đầu vào/đầu ra nhưng chưa có chữ ký mở khóa."),
        ("Gửi/áp dụng", "trong demo nghĩa là cho node mô phỏng kiểm tra và cập nhật tập UTXO."),
        ("Tiêu hai lần", "cố dùng lại cùng một UTXO đã tiêu; node phải từ chối."),
    ])

    init_tx_lab_state()
    lab = st.session_state.tx_lab

    scenario = st.selectbox(
        "🎬 Kịch bản hướng dẫn",
        [
            "Kịch bản đúng: Alice trả Bob",
            "Sửa số tiền sau khi ký",
            "Mallory cố tiêu UTXO của Alice",
            "Tiêu cùng một UTXO hai lần",
            "Chế độ tự do",
        ],
        index=[
            "Kịch bản đúng: Alice trả Bob",
            "Sửa số tiền sau khi ký",
            "Mallory cố tiêu UTXO của Alice",
            "Tiêu cùng một UTXO hai lần",
            "Chế độ tự do",
        ].index(lab.get("selected_scenario", "Kịch bản đúng: Alice trả Bob")),
    )
    lab["selected_scenario"] = scenario

    scenario_steps = {
        "Kịch bản đúng: Alice trả Bob": [
            "Tạo UTXO cho Alice",
            "Tạo giao dịch Alice -> Bob",
            "Ký bằng khóa của Alice",
            "Node kiểm tra giao dịch",
            "Gửi/áp dụng giao dịch vào tập UTXO",
        ],
        "Sửa số tiền sau khi ký": [
            "Tạo UTXO cho Alice",
            "Tạo giao dịch Alice -> Bob",
            "Ký bằng khóa của Alice",
            "Sửa số tiền sau khi ký",
            "Node kiểm tra giao dịch: dự kiến bị từ chối",
        ],
        "Mallory cố tiêu UTXO của Alice": [
            "Tạo UTXO cho Alice",
            "Tạo giao dịch cố tiêu UTXO của Alice",
            "Ký bằng khóa của Mallory",
            "Node kiểm tra giao dịch: dự kiến bị từ chối",
        ],
        "Tiêu cùng một UTXO hai lần": [
            "Tạo UTXO cho Alice",
            "Tạo giao dịch Alice -> Bob",
            "Ký bằng khóa của Alice",
            "Gửi lần đầu: dự kiến được chấp nhận",
            "Gửi lại cùng giao dịch: dự kiến bị từ chối",
        ],
        "Chế độ tự do": ["Tự bấm các thao tác trong các tab bên dưới."],
    }

    with st.expander("✅ Checklist demo gợi ý", expanded=True):
        for i, step in enumerate(scenario_steps[scenario], 1):
            st.write(f"{i}. {step}")

    tabs = st.tabs(
        [
            "1️⃣ Ví mô phỏng & tập UTXO",
            "2️⃣ Tạo giao dịch",
            "3️⃣ Ký & kiểm tra",
            "4️⃣ Sửa phá / tấn công / tiêu hai lần",
        ]
    )

    # ---------------- TAB 1 ----------------
    with tabs[0]:
        st.subheader("Ví mô phỏng: Alice, Bob, Mallory")

        st.caption(
            "“Ví mô phỏng” ở đây chỉ là một bộ khóa giả lập để học cách ký và kiểm tra giao dịch, "
            "không phải ví Bitcoin thật. Các khóa này được cố định để demo dễ lặp lại và không liên quan đến tài sản thật."
        )

        wallet_rows = []
        for wallet in lab["wallets"].values():
            wallet_rows.append(
                {
                    "Tên": wallet["name"],
                    "Khóa bí mật d (private key)": wallet["private_key"],
                    "Khóa công khai Q (public key)": point_to_text(wallet["public_key"]),
                    "Mã băm khóa công khai (PubKey Hash)": wallet["pubkey_hash"],
                }
            )
        st.dataframe(pd.DataFrame(wallet_rows), use_container_width=True)

        st.subheader("Tạo UTXO demo")
        st.caption(
            "Ở đây, 'tạo UTXO' nghĩa là tạo một khoản tiền mô phỏng thuộc về Alice/Bob/Mallory. "
            "Nó giống như phát cho nhân vật một tờ tiền demo để lát nữa thử tiêu."
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            mint_owner = st.selectbox("Tạo cho", ["Alice", "Bob", "Mallory"], key="mint_owner")
        with col2:
            mint_amount = int(st.number_input("Số tiền demo", min_value=1, max_value=100, value=10, key="mint_amount"))
        with col3:
            st.write("")
            st.write("")
            if st.button("➕ Tạo UTXO", use_container_width=True):
                mint_utxo(mint_owner, mint_amount)
                st.rerun()

        if st.button("🧹 Reset phòng lab giao dịch", use_container_width=True):
            reset_tx_lab_state()
            st.rerun()

        st.subheader("Tập UTXO hiện tại trong mô phỏng")
        rows = utxo_table_rows()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("Chưa có UTXO. Hãy tạo UTXO cho Alice hoặc Bob.")

        render_action_log()

    # ---------------- TAB 2 ----------------
    with tabs[1]:
        st.subheader("Tạo giao dịch chưa ký")

        sender = st.selectbox("Người gửi", ["Alice", "Bob", "Mallory"], key="build_sender")
        spendable = spendable_outpoints_for(sender)

        if not spendable:
            st.warning(f"{sender} chưa có UTXO chưa bị tiêu. Qua tab 1 tạo UTXO trước.")
        else:
            spendable_map = {short_outpoint(op): op for op in spendable}

            with st.form("build_tx_form"):
                selected_label = st.selectbox("Chọn UTXO đầu vào", list(spendable_map.keys()))
                receiver = st.selectbox("Người nhận", ["Bob", "Alice", "Mallory"], key="build_receiver")
                selected_outpoint = spendable_map[selected_label]
                selected_output = find_known_output(selected_outpoint)
                max_amount = int(selected_output.amount if selected_output is not None else 1)
                amount = int(st.number_input("Số tiền demo", min_value=1, max_value=max_amount, value=max_amount))
                submitted = st.form_submit_button("🧾 Tạo giao dịch chưa ký")

            if submitted:
                build_unsigned_tx(sender, receiver, selected_outpoint, amount)
                st.rerun()

        render_current_tx("Giao dịch nháp hiện tại", lab["draft_tx"])
        render_action_log()

    # ---------------- TAB 3 ----------------
    with tabs[2]:
        st.subheader("Ký & kiểm tra")

        if lab["draft_tx"] is None:
            st.info("Chưa có giao dịch nháp. Qua tab 2 tạo giao dịch trước.")
        else:
            render_current_tx("Giao dịch nháp", lab["draft_tx"])

            col1, col2, col3 = st.columns(3)
            with col1:
                signer = st.selectbox("Người ký", ["Alice", "Bob", "Mallory"], key="tx_signer")
                if st.button("✍️ Ký giao dịch đang chọn", use_container_width=True):
                    sign_lab_tx(signer)
                    st.rerun()

            with col2:
                st.write("")
                st.write("")
                if st.button("🧪 Node kiểm tra giao dịch", use_container_width=True):
                    verify_lab_tx()

            with col3:
                st.write("")
                st.write("")
                if st.button("📣 Gửi / áp dụng vào tập UTXO", use_container_width=True):
                    broadcast_lab_tx()
                    st.rerun()

            render_current_tx("Giao dịch đã ký", lab["signed_tx"])

            if lab["last_verify_details"] is not None:
                st.subheader("Chi tiết kiểm tra")
                render_verification_table(lab["last_verify_details"])

        render_action_log()

    # ---------------- TAB 4 ----------------
    with tabs[3]:
        st.subheader("Sửa phá / tấn công / tiêu hai lần")

        if lab["signed_tx"] is None:
            st.info("Chưa có giao dịch đã ký. Qua tab 3 ký giao dịch trước.")
        else:
            render_current_tx("Giao dịch đã ký hiện tại", lab["signed_tx"])

            col1, col2 = st.columns(2)
            with col1:
                # if st.button("🔧 Sửa số tiền sau khi ký", use_container_width=True):
                #     tx = copy.deepcopy(lab["signed_tx"])
                #     tx.outputs[0] = TxOutput(
                #         amount=int(tx.outputs[0].amount) + 1,
                #         pubkey_hash=tx.outputs[0].pubkey_hash,
                #     )
                #     lab["signed_tx"] = tx
                #     lab["last_verify_details"] = None
                #     lab_log("Đã sửa số tiền sau khi ký.")
                #     st.rerun()

                current_amount = int(lab["signed_tx"].outputs[0].amount)

                input_outpoint = get_input_outpoint(lab["signed_tx"].inputs[0])
                input_output = find_known_output(input_outpoint)

                if input_output is not None:
                    input_amount = int(input_output.amount)
                else:
                    input_amount = current_amount

                max_tamper_amount = max(input_amount + 20, current_amount + 20, 100)
                default_tamper_amount = min(current_amount + 1, max_tamper_amount)

                tampered_amount = int(st.number_input(
                    "🔧 Nhập số tiền mới sau khi ký",
                    min_value=1,
                    max_value=max_tamper_amount,
                    value=default_tamper_amount,
                    key="tamper_amount_after_sign",
                    help=(
                        "Số tiền này sẽ được ghi đè vào output của giao dịch đã ký. "
                        "Vì chữ ký cũ được tạo trên dữ liệu giao dịch ban đầu, việc đổi số tiền sẽ làm verify thất bại."
                    ),
                ))

                if st.button("🔧 Áp dụng số tiền mới", use_container_width=True):
                    if tampered_amount == current_amount:
                        st.warning("Số tiền mới đang giống số tiền cũ, nên giao dịch chưa thật sự bị sửa.")
                    else:
                        tx = copy.deepcopy(lab["signed_tx"])
                        tx.outputs[0] = TxOutput(
                            amount=tampered_amount,
                            pubkey_hash=tx.outputs[0].pubkey_hash,
                        )

                        lab["signed_tx"] = tx
                        lab["last_verify_details"] = None

                        lab_log(
                            f"Đã sửa số tiền sau khi ký: {current_amount} -> {tampered_amount}."
                        )

                        st.rerun()

                if st.button("🔧 Đổi người nhận sang Mallory", use_container_width=True):
                    tx = copy.deepcopy(lab["signed_tx"])
                    tx.outputs[0] = TxOutput(
                        amount=int(tx.outputs[0].amount),
                        pubkey_hash=lab["wallets"]["Mallory"]["pubkey_hash"],
                    )
                    lab["signed_tx"] = tx
                    lab["last_verify_details"] = None
                    lab_log("Đã đổi người nhận sang Mallory sau khi ký.")
                    st.rerun()

                if st.button("🦹 Thay khóa công khai mở khóa bằng của Mallory", use_container_width=True):
                    tx = copy.deepcopy(lab["signed_tx"])
                    set_input_public_key(tx.inputs[0], lab["wallets"]["Mallory"]["public_key"])
                    lab["signed_tx"] = tx
                    lab["last_verify_details"] = None
                    lab_log("Đã thay khóa công khai mở khóa bằng khóa của Mallory.")
                    st.rerun()

            with col2:
                if st.button("🦹 Ký giao dịch nháp bằng Mallory", use_container_width=True):
                    sign_lab_tx("Mallory")
                    st.rerun()

                if st.button("♻️ Thử tiêu hai lần giao dịch hiện tại", use_container_width=True):
                    tx = lab["signed_tx"]
                    first = utxo_apply_transaction(lab["utxo_set"], ECDSA_PARAMS, tx)
                    second = utxo_apply_transaction(lab["utxo_set"], ECDSA_PARAMS, tx)

                    if first and not second:
                        st.success("✅ Lần tiêu thứ nhất được chấp nhận, lần tiêu thứ hai bị từ chối.")
                    elif not first:
                        st.error("❌ Lần tiêu thứ nhất đã bị từ chối. Giao dịch có thể đã sai hoặc UTXO đã bị tiêu.")
                    else:
                        st.error("⚠️ Lần tiêu thứ hai lại được chấp nhận ngoài dự kiến. Cần kiểm tra implementation UTXOSet.")

                    lab_log(f"Kiểm tra tiêu hai lần: first={first}, second={second}")

                if st.button("🧪 Kiểm tra giao dịch đã bị sửa", use_container_width=True):
                    verify_lab_tx()

            if lab["last_verify_details"] is not None:
                st.subheader("Chi tiết kiểm tra")
                render_verification_table(lab["last_verify_details"])

        render_action_log()

    render_learning_summary(
        "Phòng lab giao dịch Bitcoin mô phỏng",
        [
            "Chữ ký ECDSA không đứng một mình; trong mô hình này, nó là dữ liệu mở khóa dùng để chứng minh quyền tiêu một UTXO cụ thể.",
            "Một giao dịch chỉ được chấp nhận khi UTXO được tham chiếu tồn tại, chưa bị tiêu, mã băm khóa công khai khớp điều kiện khóa và chữ ký ECDSA hợp lệ.",
            "Sửa số tiền hoặc người nhận sau khi ký sẽ làm dữ liệu giao dịch thay đổi, khiến chữ ký cũ không còn hợp lệ.",
            "Người khác không thể dùng khóa của họ để tiêu UTXO của Alice, vì mã băm khóa công khai không khớp điều kiện khóa của UTXO.",
            "Double spend bị từ chối vì cùng một UTXO không được tiêu hai lần trong tập UTXO mô phỏng.",
        ],
    )


# ============================================================
# PAGE 6
# ============================================================
def demo_reused_nonce_attack():
    st.title("6. Tấn công ECDSA khi dùng lại nonce")
    render_page_intro(
        "ECDSA có chắc chắn an toàn không?",
        "ECDSA phụ thuộc vào toán học đúng và triển khai đúng. Nonce k là số dùng một lần, không được tái sử dụng.",
        "Người dùng chọn d, k và hai thông điệp; app thử khôi phục lại k và khóa bí mật.",
    )

    st.warning(
        "Đây là tấn công mô phỏng để học. Nó minh họa lỗi triển khai khi dùng lại nonce, "
        "không có nghĩa là ECDSA đúng chuẩn bị phá."
    )

    render_term_notes([
        ("Nonce k", "số bí mật dùng một lần khi ký ECDSA. Mỗi chữ ký phải dùng k mới."),
        ("Dùng lại nonce", "dùng cùng k cho hai thông điệp khác nhau; đây là lỗi rất nguy hiểm."),
        ("Nghịch đảo modulo", "phép chia trong số học modulo; chỉ tồn tại khi hai số nguyên tố cùng nhau."),
        ("Khôi phục khóa", "từ hai chữ ký lỗi, kẻ tấn công có thể tính lại khóa bí mật trong mô phỏng."),
    ])

    st.latex(r"k' = (h_1 - h_2)(s_1 - s_2)^{-1} \pmod n")
    st.latex(r"d' = (s_1 k' - h_1)r^{-1} \pmod n")

    # col_key, col_nonce = st.columns(2)
    # with col_key:
    #     d_victim = int(st.number_input("🔑 Khóa bí mật d", min_value=1, max_value=ORDER_N - 1, value=min(2, ORDER_N - 1)))
    # with col_nonce:
    #     k_reuse = int(st.number_input("🎲 Reused nonce k", min_value=1, max_value=ORDER_N - 1, value=min(4, ORDER_N - 1)))

    col_key, col_nonce = st.columns(2)

    with col_key:
        d_victim = int(st.number_input(
            "🔑 Khóa bí mật d",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(3, ORDER_N - 1),
            help="Private key mô phỏng. Giá trị này không phải nguyên nhân trực tiếp gây lỗi nghịch đảo nonce.",
        ))

    with col_nonce:
        k_reuse = int(st.number_input(
            "🎲 Nonce k",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(5, ORDER_N - 1),
            help="Nonce dùng khi ký. Nếu k bị lộ hoặc bị dùng lại, private key có thể bị khôi phục.",
        ))

    col1, col2 = st.columns(2)
    with col1:
        msg1 = st.text_input("Thông điệp 1", value="Thanh toan 1 BTC cho Alice", max_chars=120)
    with col2:
        msg2 = st.text_input("Thông điệp 2", value="Thanh toan 2 BTC cho Bob", max_chars=120)

    attack_mode = st.radio(
        "Chọn kiểu tấn công nonce",
        [
            "Reused nonce: dùng lại k cho hai chữ ký",
            "Known nonce: nonce k bị lộ trong một chữ ký",
            "Partial nonce leakage: ghi chú lý thuyết",
        ],
        horizontal=False,
    )


    if st.button("⚡ Chạy mô phỏng tấn công", use_container_width=True):
        ok_nonce, nonce_msg = validate_nonce(k_reuse, ECDSA_PARAMS.n)

        if not ok_nonce:
            st.warning(nonce_msg)
            return

        if attack_mode == "Partial nonce leakage: ghi chú lý thuyết":
            st.info(
                "Partial nonce leakage là trường hợp nonce k không bị lộ hoàn toàn, "
                "nhưng rò rỉ một phần qua nhiều chữ ký, ví dụ qua side-channel hoặc RNG yếu. "
                "Trong thực tế, dạng này có thể dẫn tới lattice attack. "
                "Project này chỉ ghi chú lý thuyết, không demo lattice để tránh làm lệch trọng tâm."
            )

            st.dataframe(
                pd.DataFrame([
                    {
                        "Kiểu lỗi": "Reused nonce",
                        "Dữ liệu attacker cần": "Hai chữ ký dùng cùng k",
                        "Kết quả": "Khôi phục k rồi khôi phục d",
                        "Demo trong app": "Có",
                    },
                    {
                        "Kiểu lỗi": "Known nonce",
                        "Dữ liệu attacker cần": "Một chữ ký và nonce k bị lộ",
                        "Kết quả": "Khôi phục d từ một chữ ký",
                        "Demo trong app": "Có",
                    },
                    {
                        "Kiểu lỗi": "Partial nonce leakage",
                        "Dữ liệu attacker cần": "Nhiều chữ ký với k bị rò một phần",
                        "Kết quả": "Có thể khôi phục d bằng kỹ thuật nâng cao như lattice attack",
                        "Demo trong app": "Không, chỉ ghi chú",
                    },
                ]),
                use_container_width=True,
            )

            return

        if attack_mode == "Reused nonce: dùng lại k cho hai chữ ký":
            try:
                r1, s1 = sign(ECDSA_PARAMS, d_victim, msg1.encode("utf-8"), k=k_reuse)
                r2, s2 = sign(ECDSA_PARAMS, d_victim, msg2.encode("utf-8"), k=k_reuse)
            except Exception as exc:
                st.warning(
                    f"Không tạo được chữ ký với k = {k_reuse}: {exc}. "
                    "Toy curve quá nhỏ nên có thể gặp edge-case. App sẽ thử tìm một nonce hợp lệ khác."
                )

                auto_k, signatures = find_valid_nonce_for_messages(
                    ECDSA_PARAMS,
                    d_victim,
                    [msg1, msg2],
                )

                if auto_k is None:
                    st.error("Không tìm được nonce hợp lệ cho hai thông điệp hiện tại.")
                    return

                k_reuse = auto_k
                (r1, s1), (r2, s2) = signatures
                st.info(f"Đã tự chọn nonce hợp lệ k = {k_reuse} để tiếp tục demo.")

            h1 = hash_message_to_int(msg1.encode("utf-8"), ECDSA_PARAMS.n)
            h2 = hash_message_to_int(msg2.encode("utf-8"), ECDSA_PARAMS.n)

            st.subheader("1. Hai chữ ký dùng cùng nonce")

            st.dataframe(
                pd.DataFrame([
                    {"Thông điệp": "msg1", "h": h1, "r": r1, "s": s1},
                    {"Thông điệp": "msg2", "h": h2, "r": r2, "s": s2},
                ]),
                use_container_width=True,
            )

            can_recover, reason = can_run_reused_nonce_attack(
                msg1,
                msg2,
                h1,
                h2,
                r1,
                s1,
                r2,
                s2,
                ECDSA_PARAMS.n,
            )

            if not can_recover:
                st.warning(reason)
                return

            s_diff_inv = safe_mod_inverse(s1 - s2, ECDSA_PARAMS.n)
            r_inv = safe_mod_inverse(r1, ECDSA_PARAMS.n)

            if s_diff_inv is None or r_inv is None:
                st.warning("Mẫu số không khả nghịch modulo n.")
                return

            k_recovered = ((h1 - h2) * s_diff_inv) % ECDSA_PARAMS.n
            d_recovered = ((s1 * k_recovered - h1) * r_inv) % ECDSA_PARAMS.n

            st.subheader("2. Khôi phục nonce và private key")

            st.dataframe(
                pd.DataFrame([
                    {"Giá trị": "k ban đầu", "Kết quả": k_reuse},
                    {"Giá trị": "k khôi phục", "Kết quả": k_recovered},
                    {"Giá trị": "d ban đầu", "Kết quả": d_victim},
                    {"Giá trị": "d khôi phục", "Kết quả": d_recovered},
                ]),
                use_container_width=True,
            )

            if k_recovered == k_reuse and d_recovered == d_victim:
                st.success("🎯 Tấn công thành công: đã khôi phục nonce và khóa bí mật.")
            else:
                st.error("Không khớp. Đây là edge-case của đường cong mô phỏng / tham số hiện tại.")

        elif attack_mode == "Known nonce: nonce k bị lộ trong một chữ ký":
            try:
                r, s = sign(ECDSA_PARAMS, d_victim, msg1.encode("utf-8"), k=k_reuse)
            except Exception as exc:
                st.warning(
                    f"Không tạo được chữ ký với k = {k_reuse}: {exc}. "
                    "App sẽ thử tìm một nonce hợp lệ khác."
                )

                auto_k, signatures = find_valid_nonce_for_messages(
                    ECDSA_PARAMS,
                    d_victim,
                    [msg1],
                )

                if auto_k is None:
                    st.error("Không tìm được nonce hợp lệ cho thông điệp hiện tại.")
                    return

                k_reuse = auto_k
                r, s = signatures[0]
                st.info(f"Đã tự chọn nonce hợp lệ k = {k_reuse} để tiếp tục demo.")

            h = hash_message_to_int(msg1.encode("utf-8"), ECDSA_PARAMS.n)

            st.subheader("1. Một chữ ký có nonce bị lộ")

            st.dataframe(
                pd.DataFrame([
                    {
                        "Message": msg1,
                        "h = H(m) mod n": h,
                        "r": r,
                        "s": s,
                        "nonce k bị lộ": k_reuse,
                    }
                ]),
                use_container_width=True,
            )

            st.latex(r"d' = (s k - h)r^{-1} \pmod n")

            d_recovered, reason = recover_private_key_from_known_nonce(
                h,
                r,
                s,
                k_reuse,
                ECDSA_PARAMS.n,
            )

            if d_recovered is None:
                st.warning(reason)
                return

            st.subheader("2. Khôi phục private key từ nonce bị lộ")

            st.dataframe(
                pd.DataFrame([
                    {"Giá trị": "d ban đầu", "Kết quả": d_victim},
                    {"Giá trị": "d khôi phục", "Kết quả": d_recovered},
                ]),
                use_container_width=True,
            )

            if d_recovered == d_victim:
                st.success("🎯 Tấn công thành công: chỉ cần biết nonce k của một chữ ký là khôi phục được private key.")
            else:
                st.error("Không khớp. Đây là edge-case của đường cong mô phỏng.")

    render_learning_summary(
        "Tấn công liên quan đến nonce",
        [
            "Reused nonce: dùng lại cùng k cho hai thông điệp khác nhau có thể làm lộ k và private key d.",
            "Known nonce: nếu k của một chữ ký bị lộ, private key d có thể bị khôi phục ngay từ công thức ECDSA.",
            "Partial nonce leakage là hướng nâng cao: k chỉ rò một phần nhưng qua nhiều chữ ký vẫn có thể nguy hiểm.",
            "Page 6 không phá ECDLP; nó minh họa rằng triển khai ECDSA sai có thể làm private key bay màu.",
        ],
    )


# ============================================================
# PAGE 7
# ============================================================
def demo_nonce_defense_notes():
    st.title("7. Phòng thủ nonce trong ECDSA")

    render_page_intro(
        "Nonce reuse nguy hiểm, vậy phòng thủ thế nào?",
        "ECDSA chỉ an toàn khi cả toán học và triển khai đều đúng kỷ luật.",
        "Trang này tóm tắt các nguyên tắc quan trọng: không dùng lại nonce, sinh nonce an toàn, tránh rò rỉ qua side-channel và dùng thư viện mật mã đã được kiểm chứng.",
    )

    render_term_notes([
        (
            "Nonce k",
            "Giá trị bí mật dùng một lần trong mỗi chữ ký ECDSA. Nếu lặp lại hoặc bị đoán được, khóa bí mật có thể bị lộ."
        ),
        (
            "RFC6979-style",
            "Cách sinh nonce xác định từ khóa bí mật và thông điệp, giúp giảm rủi ro do nguồn random yếu."
        ),
        (
            "Constant-time",
            "Kỹ thuật viết code sao cho thời gian chạy không phụ thuộc vào dữ liệu bí mật."
        ),
        (
            "Side-channel",
            "Kênh rò rỉ phụ như thời gian chạy, cache, điện năng hoặc lỗi triển khai."
        ),
        (
            "Thư viện trưởng thành",
            "Thư viện mật mã đã được kiểm thử, audit và sử dụng rộng rãi, thay vì tự viết crypto cho sản phẩm thật."
        ),
    ])

    rows = [
        {
            "Cách phòng thủ": "Không bao giờ dùng lại nonce k",
            "Ý nghĩa": "Mỗi chữ ký ECDSA phải có nonce riêng. Lặp nonce có thể làm lộ khóa bí mật.",
        },
        {
            "Cách phòng thủ": "Dùng nguồn ngẫu nhiên đáng tin cậy",
            "Ý nghĩa": "Nếu nonce được sinh ngẫu nhiên, bộ sinh số ngẫu nhiên phải đủ mạnh và không bị lệch.",
        },
        {
            "Cách phòng thủ": "Sinh nonce xác định kiểu RFC6979",
            "Ý nghĩa": "Nonce được tạo từ khóa bí mật và thông điệp, giúp giảm phụ thuộc vào random bên ngoài.",
        },
        {
            "Cách phòng thủ": "Triển khai constant-time",
            "Ý nghĩa": "Giảm nguy cơ lộ thông tin bí mật qua thời gian chạy hoặc các kênh phụ.",
        },
        {
            "Cách phòng thủ": "Dùng thư viện mật mã đã được kiểm chứng",
            "Ý nghĩa": "Hệ thống thật nên dùng thư viện trưởng thành, không tự viết ECDSA production từ demo học tập.",
        },
    ]

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    render_learning_summary(
        "Phòng thủ nonce",
        [
            "Nonce trong ECDSA là giá trị cực kỳ nhạy cảm: không được lặp lại, không được đoán được và không được rò rỉ.",
            "RFC6979-style nonce giúp giảm rủi ro từ nguồn random yếu, nhưng không thay thế toàn bộ yêu cầu triển khai an toàn.",
            "Toy code chỉ dùng để học ý tưởng; hệ thống thật phải dùng thư viện mật mã trưởng thành và được kiểm chứng.",
        ],
    )


# ============================================================
# PAGE 8
# ============================================================
def demo_shamir_trick():
    st.title("8. Thủ thuật Shamir")
    render_page_intro(
        "Có thể tối ưu ECDSA verification không?",
        "Bước kiểm tra chữ ký cần tính biểu thức u1G + u2Q.",
        "Demo so sánh cách tính trực tiếp với thủ thuật Shamir để thấy có thể giảm số phép toán.",
    )

    st.warning("Đây là demo tối ưu mô phỏng. Nó là phần bonus, không phải trọng tâm quyền sở hữu Bitcoin.")

    render_term_notes([
        ("Kiểm tra", "bước kiểm tra chữ ký."),
        ("u1G + u2Q", "biểu thức cần tính trong bước kiểm tra ECDSA."),
        ("Trực tiếp", "cách làm trực tiếp: tính từng phần riêng rồi cộng lại."),
        ("Shamir", "mẹo tính đồng thời hai phép nhân điểm để giảm số phép toán."),
    ])

    col1, col2 = st.columns(2)
    with col1:
        u1_demo = int(st.number_input("u1", value=13, min_value=1))
    with col2:
        u2_demo = int(st.number_input("u2", value=19, min_value=1))

    Q_demo = ECDSA_PARAMS.curve.scalar_mul(5, ECDSA_PARAMS.G)
    st.caption(f"Q = 5G = {point_to_text(Q_demo)}")

    if st.button("📊 Chạy so sánh", use_container_width=True):
        ECDSA_PARAMS.curve.reset_counters()
        p_naive = naive_mul_add(ECDSA_PARAMS.curve, u1_demo, ECDSA_PARAMS.G, u2_demo, Q_demo)
        naive_add, naive_double = ECDSA_PARAMS.curve.add_count, ECDSA_PARAMS.curve.double_count

        ECDSA_PARAMS.curve.reset_counters()
        p_shamir = shamir_mul(ECDSA_PARAMS.curve, u1_demo, ECDSA_PARAMS.G, u2_demo, Q_demo)
        shamir_add, shamir_double = ECDSA_PARAMS.curve.add_count, ECDSA_PARAMS.curve.double_count

        df = pd.DataFrame(
            {
                "Cách làm": ["Trực tiếp", "Trực tiếp", "Shamir", "Shamir"],
                "Phép toán": ["Cộng điểm", "Nhân đôi điểm", "Cộng điểm", "Nhân đôi điểm"],
                "Số lượng": [naive_add, naive_double, shamir_add, shamir_double],
            }
        )
        fig = px.bar(df, x="Cách làm", y="Số lượng", color="Phép toán", barmode="group", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

        st.write(f"Kết quả cách trực tiếp: {point_to_text(p_naive)}")
        st.write(f"Kết quả Shamir: {point_to_text(p_shamir)}")

        if p_naive == p_shamir:
            st.success("Hai cách cho cùng kết quả.")
        else:
            st.error("Kết quả khác nhau. Kiểm tra implementation.")

    render_learning_summary(
        "Thủ thuật Shamir",
        [
            "Shamir's trick tối ưu tính u1G + u2Q.",
            "Đây là phần tối ưu thuật toán/hiệu năng.",
            "Không nên để phần này lấn át phần ký giao dịch và chứng minh quyền chi tiêu.",
        ],
    )


# ============================================================
# PAGE 9 OPENSSL - INTERACTIVE LAB
# ============================================================
def get_openssl_path():
    return shutil.which("openssl")


def run_openssl_cmd(args, cwd=None):
    """Chạy lệnh OpenSSL. Dùng cho các lệnh phải thành công."""
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
        return False, details or f"Lệnh trả về mã lỗi {exc.returncode}."


def run_openssl_verify_cmd(args, cwd=None):
    """Chạy lệnh verify.

    Khác run_openssl_cmd ở chỗ verify thất bại không phải lỗi app.
    Nó là kết quả hợp lệ khi nội dung bị sửa hoặc chữ ký không khớp.
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        output = (result.stdout or result.stderr or "").strip()
        return True, result.returncode == 0, output
    except FileNotFoundError:
        return False, False, "Không tìm thấy OpenSSL trong PATH."


def openssl_version(openssl_path):
    ok, result = run_openssl_cmd([openssl_path, "version"])
    if not ok:
        return result
    return result.stdout.strip()


def init_openssl_lab_state():
    """Khởi tạo workspace tạm cho OpenSSL lab.

    Không dùng tempfile.TemporaryDirectory ở đây vì Streamlit rerun sau mỗi lần bấm nút.
    Nếu dùng TemporaryDirectory trong một hàm chạy một lần, thư mục sẽ bị xóa ngay sau hàm.
    Ta cần giữ file key/signature qua nhiều thao tác nên dùng mkdtemp + session_state.
    """
    if "openssl_lab" in st.session_state:
        workdir = st.session_state.openssl_lab.get("workdir")
        if workdir and Path(workdir).exists():
            return

    workdir = tempfile.mkdtemp(prefix="ecc_ecdsa_openssl_lab_")
    workdir_path = Path(workdir)

    st.session_state.openssl_lab = {
        "workdir": str(workdir_path),
        "private_key": str(workdir_path / "ec_private.pem"),
        "public_key": str(workdir_path / "ec_public.pem"),
        "message_file": str(workdir_path / "message.txt"),
        "verify_file": str(workdir_path / "verify_message.txt"),
        "signature_file": str(workdir_path / "sig.bin"),
        "keys_generated": False,
        "message_signed": False,
        "original_message": "",
        "signature_hex": "",
        "last_verify": None,
        "action_log": ["OpenSSL lab đã được khởi tạo."],
    }


def reset_openssl_lab_state():
    """Xóa workspace cũ và tạo lại lab."""
    old_lab = st.session_state.get("openssl_lab")
    if old_lab:
        old_workdir = old_lab.get("workdir")
        if old_workdir and Path(old_workdir).exists():
            shutil.rmtree(old_workdir, ignore_errors=True)

    if "openssl_lab" in st.session_state:
        del st.session_state.openssl_lab

    init_openssl_lab_state()


def openssl_lab_log(message: str):
    st.session_state.openssl_lab["action_log"].append(message)


def render_openssl_action_log():
    with st.expander("🧾 Nhật ký thao tác OpenSSL", expanded=False):
        for i, line in enumerate(st.session_state.openssl_lab["action_log"][-20:], 1):
            st.write(f"{i}. {line}")


def generate_openssl_secp256k1_keys():
    """Sinh cặp khóa secp256k1 bằng OpenSSL."""
    init_openssl_lab_state()
    lab = st.session_state.openssl_lab

    openssl_path = get_openssl_path()
    if not openssl_path:
        st.error("Không tìm thấy OpenSSL trong PATH.")
        return

    workdir = lab["workdir"]
    private_key = Path(lab["private_key"])
    public_key = Path(lab["public_key"])

    commands = [
        [
            openssl_path,
            "ecparam",
            "-name",
            "secp256k1",
            "-genkey",
            "-noout",
            "-out",
            private_key.name,
        ],
        [
            openssl_path,
            "ec",
            "-in",
            private_key.name,
            "-pubout",
            "-out",
            public_key.name,
        ],
    ]

    for command in commands:
        ok, result = run_openssl_cmd(command, cwd=workdir)
        if not ok:
            st.error(result)
            openssl_lab_log(f"Sinh khóa thất bại: {result}")
            return

    lab["keys_generated"] = True
    lab["message_signed"] = False
    lab["signature_hex"] = ""
    lab["last_verify"] = None

    st.success("✅ Đã sinh cặp khóa secp256k1 bằng OpenSSL.")
    openssl_lab_log("Đã sinh cặp khóa secp256k1.")


def sign_original_message_with_openssl(message: str):
    """Ký nội dung gốc bằng private key secp256k1."""
    init_openssl_lab_state()
    lab = st.session_state.openssl_lab

    if not lab["keys_generated"]:
        st.warning("Chưa có khóa. Hãy bấm 'Sinh cặp khóa secp256k1' trước.")
        return

    openssl_path = get_openssl_path()
    if not openssl_path:
        st.error("Không tìm thấy OpenSSL trong PATH.")
        return

    workdir = lab["workdir"]
    private_key = Path(lab["private_key"])
    message_file = Path(lab["message_file"])
    signature_file = Path(lab["signature_file"])

    message_file.write_text(message, encoding="utf-8")

    ok, result = run_openssl_cmd(
        [
            openssl_path,
            "dgst",
            "-sha256",
            "-sign",
            private_key.name,
            "-out",
            signature_file.name,
            message_file.name,
        ],
        cwd=workdir,
    )

    if not ok:
        st.error(result)
        openssl_lab_log(f"Ký thất bại: {result}")
        return

    lab["message_signed"] = True
    lab["original_message"] = message
    lab["signature_hex"] = signature_file.read_bytes().hex()
    lab["last_verify"] = None

    st.success("✅ Đã ký nội dung gốc.")
    openssl_lab_log("Đã ký nội dung gốc bằng private key secp256k1.")


def verify_message_with_old_signature(verify_message: str):
    """Kiểm tra một nội dung bất kỳ bằng chữ ký đã tạo từ nội dung gốc."""
    init_openssl_lab_state()
    lab = st.session_state.openssl_lab

    if not lab["keys_generated"]:
        st.warning("Chưa có khóa. Hãy sinh khóa trước.")
        return

    if not lab["message_signed"]:
        st.warning("Chưa có chữ ký. Hãy ký nội dung gốc trước.")
        return

    openssl_path = get_openssl_path()
    if not openssl_path:
        st.error("Không tìm thấy OpenSSL trong PATH.")
        return

    workdir = lab["workdir"]
    public_key = Path(lab["public_key"])
    signature_file = Path(lab["signature_file"])
    verify_file = Path(lab["verify_file"])

    verify_file.write_text(verify_message, encoding="utf-8")

    ok, accepted, output = run_openssl_verify_cmd(
        [
            openssl_path,
            "dgst",
            "-sha256",
            "-verify",
            public_key.name,
            "-signature",
            signature_file.name,
            verify_file.name,
        ],
        cwd=workdir,
    )

    if not ok:
        st.error(output)
        openssl_lab_log(f"Không chạy được verify: {output}")
        return

    lab["last_verify"] = {
        "verify_message": verify_message,
        "accepted": accepted,
        "output": output,
        "same_as_original": verify_message == lab["original_message"],
    }

    if accepted:
        st.success("✅ Nội dung kiểm tra được chấp nhận. Chữ ký khớp.")
        openssl_lab_log("Verify thành công: nội dung kiểm tra khớp chữ ký.")
    else:
        st.error("❌ Nội dung kiểm tra bị từ chối. Chữ ký không khớp.")
        openssl_lab_log("Verify thất bại: nội dung kiểm tra không khớp chữ ký.")


def benchmark_current_openssl_signature(iterations: int):
    """Đo thời gian ký và kiểm tra trên nội dung gốc hiện tại."""
    init_openssl_lab_state()
    lab = st.session_state.openssl_lab

    if not lab["keys_generated"]:
        st.warning("Chưa có khóa. Hãy sinh khóa trước.")
        return None

    if not lab["message_signed"]:
        st.warning("Chưa có chữ ký. Hãy ký nội dung gốc trước.")
        return None

    openssl_path = get_openssl_path()
    if not openssl_path:
        st.error("Không tìm thấy OpenSSL trong PATH.")
        return None

    iterations = max(1, int(iterations))

    workdir = lab["workdir"]
    private_key = Path(lab["private_key"])
    public_key = Path(lab["public_key"])
    message_file = Path(lab["message_file"])
    signature_file = Path(lab["signature_file"])

    sign_start = time.perf_counter()
    for _ in range(iterations):
        ok, result = run_openssl_cmd(
            [
                openssl_path,
                "dgst",
                "-sha256",
                "-sign",
                private_key.name,
                "-out",
                signature_file.name,
                message_file.name,
            ],
            cwd=workdir,
        )
        if not ok:
            st.error(result)
            return None
    sign_total = time.perf_counter() - sign_start

    verify_start = time.perf_counter()
    for _ in range(iterations):
        ok, accepted, output = run_openssl_verify_cmd(
            [
                openssl_path,
                "dgst",
                "-sha256",
                "-verify",
                public_key.name,
                "-signature",
                signature_file.name,
                message_file.name,
            ],
            cwd=workdir,
        )
        if not ok or not accepted:
            st.error(output or "Verify thất bại trong lúc benchmark.")
            return None
    verify_total = time.perf_counter() - verify_start

    result = {
        "iterations": iterations,
        "sign_avg_ms": (sign_total / iterations) * 1000,
        "verify_avg_ms": (verify_total / iterations) * 1000,
        "sign_ops_per_sec": iterations / sign_total if sign_total > 0 else 0,
        "verify_ops_per_sec": iterations / verify_total if verify_total > 0 else 0,
    }

    openssl_lab_log(f"Đã benchmark {iterations} lần.")
    return result


def demo_openssl_summary():
    st.title("9. Demo OpenSSL secp256k1")
    render_page_intro(
        "Mô phỏng nhỏ liên hệ công cụ thật thế nào?",
        "Toy curve giúp hiểu toán; OpenSSL secp256k1 cho thấy việc ký và kiểm tra chữ ký bằng công cụ thật.",
        "Người dùng tự sinh khóa, ký nội dung gốc, rồi tự sửa nội dung để thấy chữ ký cũ bị từ chối.",
    )

    st.warning(
        "Demo này ký một đoạn chữ/file bằng secp256k1. Đây không phải ký giao dịch Bitcoin đầy đủ, "
        "không có Bitcoin Script và không có quy tắc sighash/consensus của Bitcoin thật."
    )

    render_term_notes([
        ("OpenSSL", "công cụ/thư viện mật mã phổ biến, dùng để chạy thử ký và kiểm tra chữ ký thật."),
        ("secp256k1", "đường cong elliptic Bitcoin dùng cho ECDSA truyền thống."),
        ("Nội dung gốc", "dữ liệu được ký ban đầu."),
        ("Nội dung kiểm tra", "dữ liệu đem đi kiểm tra với chữ ký cũ. Nếu sửa khác nội dung gốc thì phải bị từ chối."),
        ("Tính toàn vẹn (integrity)", "chỉ cần dữ liệu bị sửa sau khi ký, chữ ký cũ sẽ không còn hợp lệ."),
    ])

    init_openssl_lab_state()
    lab = st.session_state.openssl_lab

    openssl_path = get_openssl_path()
    if openssl_path:
        st.info(f"OpenSSL hiện tại: `{openssl_version(openssl_path)}`")
    else:
        st.error("Không tìm thấy OpenSSL trong PATH. Hãy cài OpenSSL hoặc thêm vào PATH trước.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "1️⃣ Sinh khóa",
        "2️⃣ Ký nội dung gốc",
        "3️⃣ Tự sửa và kiểm tra",
        "4️⃣ Đo thời gian",
    ])

    # ---------------- TAB 1 ----------------
    with tab1:
        st.subheader("1. Sinh cặp khóa secp256k1")

        st.markdown(
            """
            Ở bước này, OpenSSL tạo ra:

            - **Private key**: khóa bí mật, dùng để ký.
            - **Public key**: khóa công khai, dùng để kiểm tra chữ ký.

            Đây là key tạm nằm trong thư mục tạm của app, không phải ví Bitcoin thật.
            """
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Sinh cặp khóa secp256k1", use_container_width=True):
                generate_openssl_secp256k1_keys()
                st.rerun()

        with col2:
            if st.button("🧹 Reset OpenSSL lab", use_container_width=True):
                reset_openssl_lab_state()
                st.rerun()

        st.write(f"Đã có khóa chưa? **{lab['keys_generated']}**")

        if lab["keys_generated"]:
            st.success("Đã có khóa. Chuyển sang tab 2 để ký nội dung gốc.")
            with st.expander("Xem vị trí file tạm", expanded=False):
                st.code(
                    f"Private key: {lab['private_key']}\n"
                    f"Public key : {lab['public_key']}",
                    language="text",
                )

    # ---------------- TAB 2 ----------------
    with tab2:
        st.subheader("2. Ký nội dung gốc")

        st.markdown(
            """
            Hãy nhập nội dung gốc rồi bấm ký. Chữ ký sinh ra sẽ chỉ hợp lệ với đúng nội dung này.
            Sau đó sang tab 3 để thử giữ nguyên hoặc sửa nội dung.
            """
        )

        original_message = st.text_area(
            "Nội dung gốc sẽ được ký",
            value=lab["original_message"] or "Alice trả Bob 1 BTC mô phỏng",
            height=120,
        )

        if st.button("✍️ Ký nội dung gốc bằng OpenSSL", use_container_width=True):
            sign_original_message_with_openssl(original_message)
            st.rerun()

        if lab["message_signed"]:
            st.success("Đã có chữ ký cho nội dung gốc.")
            st.caption("Phần đầu chữ ký dạng hex:")
            st.code(lab["signature_hex"][:160] + "...", language="text")

    # ---------------- TAB 3 ----------------
    with tab3:
        st.subheader("3. Tự sửa nội dung và kiểm tra chữ ký cũ")

        st.markdown(
            """
            Đây là phần trực quan nhất:

            - Nếu **nội dung kiểm tra giống nội dung gốc**, chữ ký phải hợp lệ.
            - Nếu **sửa dù chỉ một ký tự**, chữ ký cũ phải bị từ chối.

            Đây chính là tính toàn vẹn của chữ ký số.
            """
        )

        if not lab["message_signed"]:
            st.info("Hãy sang tab 2 ký nội dung gốc trước.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Nội dung gốc đã ký")
                st.text_area(
                    "Nội dung gốc",
                    value=lab["original_message"],
                    height=140,
                    disabled=True,
                    key="openssl_original_display",
                )

            with col2:
                st.markdown("#### Nội dung đem đi kiểm tra")

                if "openssl_verify_message_next" in st.session_state:
                    st.session_state.openssl_verify_message = st.session_state.pop("openssl_verify_message_next")
                elif "openssl_verify_message" not in st.session_state:
                    st.session_state.openssl_verify_message = lab["original_message"]

                verify_message = st.text_area(
                    "Có thể giữ nguyên hoặc tự sửa để thử",
                    height=140,
                    key="openssl_verify_message",
                )

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                if st.button("✅ Kiểm tra với nội dung hiện tại", use_container_width=True):
                    verify_message_with_old_signature(verify_message)
                    st.rerun()

            with col_b:
                if st.button("🧪 Tạo bản bị sửa mẫu", use_container_width=True):
                    st.session_state.openssl_verify_message_next = lab["original_message"] + " [đã bị sửa]"
                    st.rerun()

            with col_c:
                if st.button("↩️ Khôi phục giống nội dung gốc", use_container_width=True):
                    st.session_state.openssl_verify_message_next = lab["original_message"]
                    st.rerun()

            if lab["last_verify"] is not None:
                result = lab["last_verify"]

                st.divider()
                st.subheader("Kết quả kiểm tra")

                result_rows = [
                    {
                        "Mục": "Nội dung kiểm tra có giống nội dung gốc không?",
                        "Kết quả": result["same_as_original"],
                    },
                    {
                        "Mục": "Chữ ký cũ có được chấp nhận không?",
                        "Kết quả": result["accepted"],
                    },
                    {
                        "Mục": "Thông báo OpenSSL",
                        "Kết quả": result["output"],
                    },
                ]
                st.dataframe(pd.DataFrame(result_rows), use_container_width=True)

                if result["accepted"]:
                    st.success(
                        "Nội dung kiểm tra khớp chữ ký. Điều này thường xảy ra khi nó giống đúng nội dung gốc đã ký."
                    )
                else:
                    st.error(
                        "Nội dung kiểm tra không khớp chữ ký cũ. Nếu bạn đã sửa nội dung, đây là kết quả đúng."
                    )

                st.info(
                    "Liên hệ Bitcoin: nếu ai đó sửa số tiền hoặc người nhận sau khi giao dịch đã được ký, "
                    "chữ ký cũ sẽ không còn khớp với dữ liệu giao dịch nữa, nên node sẽ từ chối."
                )

    # ---------------- TAB 4 ----------------
    with tab4:
        st.subheader("4. Đo thời gian ký và kiểm tra chữ ký")

        st.markdown(
            """
            Phần này đo thời gian chạy OpenSSL trên máy hiện tại. Kết quả chỉ mang tính tham khảo vì còn phụ thuộc vào máy,
            phiên bản OpenSSL và môi trường chạy.
            """
        )

        iterations = int(st.slider("Số lần chạy thử", min_value=1, max_value=100, value=10))

        if st.button("📊 Đo thời gian", use_container_width=True):
            result = benchmark_current_openssl_signature(iterations)

            if result is not None:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"Chỉ số": "Số lần chạy", "Giá trị": result["iterations"]},
                            {"Chỉ số": "Thời gian ký trung bình (ms/lần)", "Giá trị": f"{result['sign_avg_ms']:.4f}"},
                            {"Chỉ số": "Thời gian kiểm tra trung bình (ms/lần)", "Giá trị": f"{result['verify_avg_ms']:.4f}"},
                            {"Chỉ số": "Số lần ký mỗi giây", "Giá trị": f"{result['sign_ops_per_sec']:.2f}"},
                            {"Chỉ số": "Số lần kiểm tra mỗi giây", "Giá trị": f"{result['verify_ops_per_sec']:.2f}"},
                        ]
                    ),
                    use_container_width=True,
                )

                fig_df = pd.DataFrame(
                    [
                        {"Phép toán": "Ký", "ms/lần": result["sign_avg_ms"]},
                        {"Phép toán": "Kiểm tra", "ms/lần": result["verify_avg_ms"]},
                    ]
                )
                fig = px.bar(
                    fig_df,
                    x="Phép toán",
                    y="ms/lần",
                    title="OpenSSL secp256k1: thời gian ký và kiểm tra chữ ký",
                )
                st.plotly_chart(fig, use_container_width=True)

    render_openssl_action_log()

    render_learning_summary(
        "OpenSSL",
        [
            "secp256k1 là đường cong elliptic thật có liên quan trực tiếp đến Bitcoin truyền thống.",
            "OpenSSL cho thấy ký/kiểm tra chữ ký không chỉ là toy code tự viết.",
            "Chữ ký chỉ hợp lệ với đúng nội dung đã ký; sửa nội dung sẽ làm kiểm tra thất bại.",
            "Không được nhầm ký một thông điệp đơn giản với ký giao dịch Bitcoin đầy đủ.",
        ],
    )


# ============================================================
# MAIN
# ============================================================
def main():
    if "page_id" not in st.session_state:
        st.session_state.page_id = 0

    render_sidebar_navigation()
    render_header(st.session_state.page_id)

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
        demo_interactive_bitcoin_transaction_lab()
    elif page_id == 6:
        demo_reused_nonce_attack()
    elif page_id == 7:
        demo_nonce_defense_notes()
    elif page_id == 8:
        demo_shamir_trick()
    elif page_id == 9:
        demo_openssl_summary()

    st.divider()
    render_navigation_footer()


if __name__ == "__main__":
    main()
