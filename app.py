import sys
import os
import copy
import shutil
import subprocess
import tempfile
import time
import hashlib
import re
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
        background: #f8f9fa;
        padding-top: 18px;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #262730 !important;
    }

    [data-testid="stSidebar"] button {
        background-color: #667eea !important;
        color: white !important;
        border: none !important;
    }

    [data-testid="stSidebar"] button:hover {
        background-color: #764ba2 !important;
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
    {"id": 0, "title": "0. Mở đầu", "desc": "Từ mật mã khóa công khai đến ECC/ECDSA"},
    {"id": 1, "title": "1. Từ khóa bí mật đến khóa công khai", "desc": "Key distribution, hybrid và bài toán khó"},
    {"id": 2, "title": "2. RSA, ElGamal/DH và ECC", "desc": "So sánh nền toán + benchmark chạy thật"},
    {"id": 3, "title": "3. Nền tảng toán học ECC", "desc": "Trường hữu hạn, đường cong, Q = dG"},
    {"id": 4, "title": "4. ECDLP", "desc": "Brute force, BSGS, Pollard rho"},
    {"id": 5, "title": "5. Chữ ký số ECDSA", "desc": "Keygen, signing, verification, nonce k"},
    {"id": 6, "title": "6. Bitcoin case study", "desc": "ECDSA mở khóa UTXO mô phỏng"},
    {"id": 7, "title": "7. Nonce attack", "desc": "Reused nonce, known nonce, partial leakage"},
    {"id": 8, "title": "8. Phòng thủ và tối ưu", "desc": "RFC6979, constant-time, Shamir's trick"},
    {"id": 9, "title": "9. OpenSSL và kết luận", "desc": "secp256k1 thật + tổng kết đề tài"},
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

                1. Vì sao cần mật mã khóa công khai?
                2. Từ mật mã khóa bí mật đến public-key crypto
                3. So sánh RSA, ElGamal/DH và ECC
                4. Nền tảng toán học ECC: `Q = dG`
                5. ECDLP và độ khó đi ngược từ `Q` về `d`
                6. Chữ ký số ECDSA
                7. Bitcoin như case study của ECDSA
                8. Nonce attack
                9. Phòng thủ, tối ưu và OpenSSL

                **Lưu ý:** code mô phỏng để học, không dùng cho ví thật, khóa thật hoặc giao dịch thật.
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
    st.title("0. Mở đầu: Vì sao cần ECC/ECDSA?")

    render_page_intro(
        "Vì sao cần mật mã khóa công khai?",
        "Mật mã khóa bí mật rất nhanh, nhưng gặp bài toán phân phối khóa khi số người dùng tăng lên. "
        "Mật mã khóa công khai ra đời để hỗ trợ trao đổi khóa, xác thực và chữ ký số.",
        "Trang này đặt bản đồ toàn bộ đề tài: từ symmetric crypto đến public-key crypto, rồi đến ECC, ECDSA và Bitcoin case study.",
    )

    st.info(
        "Luận điểm trung tâm: đề tài này không bắt đầu từ Bitcoin. "
        "Trọng tâm là ECC và ECDSA trong mật mã khóa công khai; "
        "Bitcoin là case study cho chữ ký số trong môi trường không cần trusted third party. "
        "Trong case study đó, ECDSA giúp chứng minh quyền chi tiêu UTXO mà không cần tiết lộ private key."
    )

    render_term_notes([
        (
            "Mật mã khóa bí mật",
            "Một khóa dùng chung cho cả mã hóa và giải mã. Nhanh, nhưng khó phân phối khóa an toàn khi có nhiều người dùng."
        ),
        (
            "Mật mã khóa công khai",
            "Mỗi người có một public key để công khai và một private key để giữ bí mật. Mô hình này hỗ trợ trao đổi khóa, xác thực và chữ ký số."
        ),
        (
            "Bài toán khó",
            "Một bài toán tính xuôi dễ nhưng đi ngược rất khó nếu không có thông tin bí mật hoặc không đủ tài nguyên tính toán."
        ),
        (
            "ECC",
            "Elliptic Curve Cryptography: mật mã khóa công khai dựa trên nhóm điểm của đường cong elliptic."
        ),
        (
            "ECDLP",
            "Elliptic Curve Discrete Logarithm Problem: biết G và Q = dG, tìm lại d. Đây là bài toán khó đứng sau ECC."
        ),
        (
            "ECDSA",
            "Elliptic Curve Digital Signature Algorithm: thuật toán chữ ký số dựa trên ECC. Bitcoin truyền thống dùng ECDSA để xác thực quyền chi tiêu."
        ),
    ])

    st.markdown("## Bản đồ logic của đề tài")

    st.graphviz_chart("""
    digraph {
        rankdir=LR;

        node [
            shape=box,
            style="rounded,filled",
            fillcolor="#F8FAFC",
            color="#64748B",
            fontname="Arial"
        ];

        edge [
            color="#475569",
            fontname="Arial"
        ];

        "Mật mã khóa bí mật\\nnhanh nhưng dùng chung khóa"
            -> "Bài toán\\nphân phối khóa";

        "Bài toán\\nphân phối khóa"
            -> "Mật mã\\nkhóa công khai";

        "Mật mã\\nkhóa công khai"
            -> "RSA\\nFactorization / RSA problem";

        "Mật mã\\nkhóa công khai"
            -> "Diffie-Hellman / ElGamal\\nDiscrete Logarithm Problem";

        "Mật mã\\nkhóa công khai"
            -> "ECC\\nElliptic Curve Cryptography";

        "ECC\\nElliptic Curve Cryptography"
            -> "ECDLP\\nQ = dG khó đảo ngược";

        "ECDLP\\nQ = dG khó đảo ngược"
            -> "ECDSA\\nChữ ký số trên ECC";

        "ECDSA\\nChữ ký số trên ECC"
            -> "Bitcoin case study\\nXác thực quyền chi tiêu UTXO";
    }
    """)

    st.caption(
        "Sơ đồ này cho thấy Bitcoin không phải điểm xuất phát của đề tài. "
        "Bitcoin xuất hiện ở cuối như một ứng dụng thực tế của ECDSA, còn nền tảng chính là ECC và ECDLP."
    )

    st.markdown("## Ba câu hỏi dẫn dắt")

    question_rows = [
        {
            "Câu hỏi": "1. Vì sao cần mật mã khóa công khai?",
            "Ý chính": "Mật mã đối xứng nhanh nhưng gặp bài toán phân phối khóa. Public-key crypto giúp trao đổi khóa, xác thực và ký số.",
            "Trang liên quan": "Page 1",
        },
        {
            "Câu hỏi": "2. Vì sao ECC đáng học?",
            "Ý chính": "ECC dựa trên ECDLP, cho phép tạo public key Q = dG từ private key d, trong khi chiều ngược Q -> d rất khó.",
            "Trang liên quan": "Page 2, Page 3, Page 4",
        },
        {
            "Câu hỏi": "3. Vì sao chọn Bitcoin làm case study?",
            "Ý chính": "Bitcoin là case study cho chữ ký số trong môi trường không cần trusted third party; ECDSA giúp chứng minh quyền chi tiêu UTXO mà không cần tiết lộ private key.",
            "Trang liên quan": "Page 5, Page 6",
        },
    ]

    st.dataframe(
        pd.DataFrame(question_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## Lộ trình demo")

    roadmap = [
        {
            "Page": "0",
            "Tên": "Mở đầu",
            "Dụng ý": "Đặt bản đồ: public-key crypto -> ECC -> ECDSA -> Bitcoin case study",
        },
        {
            "Page": "1",
            "Tên": "Từ khóa bí mật đến khóa công khai",
            "Dụng ý": "Giải thích bài toán phân phối khóa, hybrid cryptosystem, one-way/trapdoor/hard problems",
        },
        {
            "Page": "2",
            "Tên": "RSA, ElGamal/DH và ECC",
            "Dụng ý": "So sánh các hệ khóa công khai tiêu biểu và benchmark chạy thật bằng OpenSSL",
        },
        {
            "Page": "3",
            "Tên": "Nền tảng toán học ECC",
            "Dụng ý": "Hiểu trường hữu hạn, đường cong elliptic, cộng điểm, nhân điểm và Q = dG",
        },
        {
            "Page": "4",
            "Tên": "ECDLP",
            "Dụng ý": "Đóng vai attacker thử tìm d từ Q bằng brute force, BSGS và Pollard rho",
        },
        {
            "Page": "5",
            "Tên": "Chữ ký số ECDSA",
            "Dụng ý": "Tạo chữ ký, kiểm tra chữ ký, thấy vai trò của nonce k",
        },
        {
            "Page": "6",
            "Tên": "Bitcoin case study",
            "Dụng ý": "Mô phỏng UTXO, locking/unlocking data, public key hash, signature trong input và node verification",
        },
        {
            "Page": "7",
            "Tên": "Nonce attack",
            "Dụng ý": "Cho thấy reused nonce hoặc known nonce có thể làm lộ private key",
        },
        {
            "Page": "8",
            "Tên": "Phòng thủ và tối ưu",
            "Dụng ý": "Tóm tắt RFC6979, constant-time, side-channel và Shamir's trick",
        },
        {
            "Page": "9",
            "Tên": "OpenSSL và kết luận",
            "Dụng ý": "Đối chiếu toy demo với công cụ thật secp256k1 và tổng kết toàn bộ đề tài",
        },
    ]

    st.dataframe(
        pd.DataFrame(roadmap),
        use_container_width=True,
        hide_index=True,
    )

    render_learning_summary(
        "Mở đầu",
        [
            "Mật mã khóa công khai xuất hiện vì mật mã khóa bí mật gặp bài toán phân phối khóa khi hệ thống có nhiều người dùng.",
            "RSA, ElGamal/DH và ECC đều là các hướng public-key crypto, nhưng dựa trên các bài toán khó khác nhau.",
            "ECC đáng học vì nó dựa trên ECDLP: tính Q = dG thì nhanh, nhưng tìm d từ Q là rất khó khi tham số đủ lớn.",
            "ECDSA là một ứng dụng chữ ký số quan trọng của ECC.",
            "Bitcoin được chọn làm case study vì nó dùng chữ ký số trong môi trường không cần trusted third party; ECDSA giúp chứng minh quyền chi tiêu UTXO mà không để lộ private key.",
        ],
    )

# ============================================================
# PAGE 1
# ============================================================

def demo_symmetric_to_public_key():
    st.title("1. Từ khóa bí mật đến khóa công khai")

    render_page_intro(
        "Vì sao mật mã khóa công khai ra đời?",
        "Mật mã khóa bí mật rất nhanh, nhưng gặp bài toán phân phối khóa khi số người dùng tăng lên.",
        "Ta so sánh số khóa cần quản lý trong mô hình khóa bí mật theo từng cặp và mô hình khóa công khai.",
    )

    st.info(
        "Trang này là phần bối cảnh mật mã học. "
        "Mục tiêu chưa phải học ECC ngay, mà là hiểu vì sao public-key cryptography cần thiết, "
        "và vì sao các bài toán khó như RSA problem, DLP, ECDLP trở thành nền tảng của mật mã hiện đại."
    )

    render_term_notes([
        (
            "Mật mã khóa bí mật / symmetric cryptography",
            "Hai bên dùng cùng một khóa bí mật để mã hóa và giải mã. Ví dụ hiện đại: AES."
        ),
        (
            "Bài toán phân phối khóa",
            "Trước khi liên lạc an toàn, hai bên phải có cách chia sẻ khóa bí mật. Khi số người dùng tăng, việc quản lý khóa trở nên rất khó."
        ),
        (
            "Mật mã khóa công khai / public-key cryptography",
            "Mỗi người có một public key để công khai và một private key để giữ bí mật. Public key có thể gửi cho mọi người, private key không được để lộ."
        ),
        (
            "Hybrid cryptosystem",
            "Mô hình kết hợp: public-key dùng để trao đổi khóa hoặc xác thực, còn symmetric-key dùng để mã hóa dữ liệu lớn."
        ),
        (
            "One-way function",
            "Hàm tính xuôi dễ nhưng đi ngược khó. Ví dụ trong ECC: biết d thì tính Q = dG dễ, nhưng biết Q thì tìm d khó."
        ),
        (
            "Trapdoor one-way function",
            "Hàm một chiều có cửa sập: nếu biết thông tin bí mật đặc biệt thì có thể đi ngược dễ hơn. RSA là ví dụ kinh điển."
        ),
        (
            "Hard problem",
            "Bài toán toán học khó làm nền cho mật mã khóa công khai, ví dụ factorization, discrete logarithm, ECDLP."
        ),
    ])

    st.markdown("## 1. Bài toán phân phối khóa")

    st.markdown(
        """
        Giả sử có `N` người trong một hệ thống.

        Nếu dùng **mật mã khóa bí mật theo từng cặp**, mỗi cặp người cần một khóa riêng.
        Số khóa cần quản lý là:

        """
    )

    st.latex(r"\frac{N(N-1)}{2}")

    st.markdown(
        """
        Còn với **mật mã khóa công khai**, mỗi người chỉ cần một cặp khóa:

        ```text
        private key: giữ bí mật
        public key: công khai cho người khác dùng
        ```

        Số cặp khóa cần quản lý là:
        """
    )

    st.latex(r"N")

    n_users = st.slider(
        "👥 Chọn số người dùng trong hệ thống",
        min_value=2,
        max_value=500,
        value=10,
        step=1,
    )

    symmetric_keys = n_users * (n_users - 1) // 2
    public_key_pairs = n_users

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Số người dùng",
            n_users,
        )

    with col2:
        st.metric(
            "Khóa đối xứng theo từng cặp",
            symmetric_keys,
        )

    with col3:
        st.metric(
            "Cặp khóa công khai",
            public_key_pairs,
        )

    comparison_rows = [
        {
            "Mô hình": "Mật mã khóa bí mật theo từng cặp",
            "Số khóa cần quản lý": symmetric_keys,
            "Công thức": "N(N-1)/2",
            "Ý nghĩa": "Mỗi cặp người dùng cần một khóa bí mật riêng.",
        },
        {
            "Mô hình": "Mật mã khóa công khai",
            "Số cặp khóa cần quản lý": public_key_pairs,
            "Công thức": "N",
            "Ý nghĩa": "Mỗi người giữ một private key và công bố một public key.",
        },
    ]

    st.dataframe(
        pd.DataFrame(comparison_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## 2. Tốc độ tăng số khóa")

    growth_rows = []

    for n in range(2, n_users + 1):
        growth_rows.append({
            "Số người dùng": n,
            "Khóa đối xứng theo từng cặp": n * (n - 1) // 2,
            "Cặp khóa công khai": n,
        })

    growth_df = pd.DataFrame(growth_rows)

    growth_long_df = growth_df.melt(
        id_vars="Số người dùng",
        value_vars=[
            "Khóa đối xứng theo từng cặp",
            "Cặp khóa công khai",
        ],
        var_name="Mô hình",
        value_name="Số khóa",
    )

    fig = px.line(
        growth_long_df,
        x="Số người dùng",
        y="Số khóa",
        color="Mô hình",
        markers=True,
        title="Số khóa cần quản lý khi số người dùng tăng",
    )

    fig.update_layout(
        height=520,
        xaxis_title="Số người dùng N",
        yaxis_title="Số khóa / cặp khóa",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.success(
        "Ý nghĩa: mật mã khóa công khai không làm symmetric crypto biến mất, "
        "nhưng giải quyết rất tốt bài toán phân phối khóa và xác thực trong hệ thống lớn."
    )

    st.markdown("## 3. Public-key crypto không thay thế hoàn toàn symmetric crypto")

    model_rows = [
        {
            "Mô hình": "Symmetric cryptography",
            "Dùng khóa thế nào?": "Hai bên dùng chung một khóa bí mật.",
            "Mạnh ở đâu?": "Rất nhanh, phù hợp mã hóa dữ liệu lớn.",
            "Vấn đề": "Khó phân phối khóa an toàn khi có nhiều người dùng.",
        },
        {
            "Mô hình": "Public-key cryptography",
            "Dùng khóa thế nào?": "Mỗi người có public key và private key.",
            "Mạnh ở đâu?": "Trao đổi khóa, xác thực, chữ ký số.",
            "Vấn đề": "Thường chậm hơn symmetric crypto.",
        },
        {
            "Mô hình": "Hybrid cryptosystem",
            "Dùng khóa thế nào?": "Public-key dùng để trao đổi khóa hoặc xác thực; symmetric-key dùng để mã hóa dữ liệu chính.",
            "Mạnh ở đâu?": "Kết hợp được ưu điểm của cả hai mô hình.",
            "Vấn đề": "Cần thiết kế giao thức cẩn thận.",
        },
    ]

    st.dataframe(
        pd.DataFrame(model_rows),
        use_container_width=True,
        hide_index=True,
    )

    with st.container(border=True):
        st.markdown("### Ví dụ trực giác về hybrid cryptosystem")

        st.markdown(
            """
            Trong nhiều hệ thống thực tế, public-key crypto không trực tiếp mã hóa toàn bộ dữ liệu lớn.

            Mạch thường gặp là:

            ```text
            1. Dùng public-key crypto để trao đổi một session key.
            2. Dùng session key đó với symmetric crypto để mã hóa dữ liệu lớn.
            3. Dùng chữ ký số để xác thực người gửi hoặc xác thực dữ liệu.
            ```

            Vì vậy, public-key crypto giống như “cơ chế bắt tay an toàn”,
            còn symmetric crypto giống như “động cơ tốc độ cao” để mã hóa dữ liệu chính.
            """
        )

    st.markdown("## 4. One-way, trapdoor và các bài toán khó")

    hard_problem_rows = [
        {
            "Hệ / họ mật mã": "RSA",
            "Bài toán nền tảng": "Factorization / RSA problem",
            "Dạng public key": "(n, e)",
            "Dạng private key": "d",
            "Ghi chú": "RSA là ví dụ kinh điển của trapdoor one-way function.",
        },
        {
            "Hệ / họ mật mã": "Diffie-Hellman / ElGamal",
            "Bài toán nền tảng": "Discrete Logarithm Problem",
            "Dạng public key": "y = g^x mod p",
            "Dạng private key": "x",
            "Ghi chú": "Dựa trên log rời rạc trong nhóm hữu hạn.",
        },
        {
            "Hệ / họ mật mã": "ECC",
            "Bài toán nền tảng": "Elliptic Curve Discrete Logarithm Problem",
            "Dạng public key": "Q = dG",
            "Dạng private key": "d",
            "Ghi chú": "Dựa trên log rời rạc trong nhóm điểm elliptic curve.",
        },
    ]

    st.dataframe(
        pd.DataFrame(hard_problem_rows),
        use_container_width=True,
        hide_index=True,
    )

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### RSA: trapdoor one-way function")
        st.markdown(
            """
            Với RSA, tính xuôi dễ nếu biết public key.

            Nhưng để đi ngược hoặc tạo private key, cần thông tin bí mật liên quan đến phân tích:

            ```text
            n = p × q
            ```

            Nếu biết `p` và `q`, ta có “cửa sập” để tính private key.
            """
        )

    with col_right:
        st.markdown("### ECC: bài toán một chiều khó đảo")
        st.markdown(
            """
            Với ECC, public key được tạo bởi:

            ```text
            Q = dG
            ```

            Biết `d` thì tính `Q` nhanh.

            Nhưng biết `G` và `Q`, tìm lại `d` chính là ECDLP.
            Khi tham số đủ lớn, bài toán này rất khó.
            """
        )

    st.warning(
        "Cẩn thận: RSA thường được trình bày như trapdoor one-way function kinh điển. "
        "ECC thì nên hiểu là dựa trên một quan hệ một chiều khó đảo: Q = dG dễ tính xuôi, khó tìm ngược d từ Q."
    )

    render_learning_summary(
        "Từ khóa bí mật đến khóa công khai",
        [
            "Mật mã khóa bí mật rất nhanh, nhưng gặp bài toán phân phối khóa khi số người dùng tăng lên.",
            "Mật mã khóa công khai giúp giải quyết trao đổi khóa, xác thực và chữ ký số.",
            "Trong thực tế, nhiều hệ thống dùng mô hình hybrid: public-key cho bắt tay/xác thực, symmetric-key cho mã hóa dữ liệu lớn.",
            "RSA, Diffie-Hellman/ElGamal và ECC đều thuộc public-key cryptography nhưng dựa trên các bài toán khó khác nhau.",
            "Page sau sẽ đặt RSA, ElGamal/DH và ECC cạnh nhau để so sánh trực tiếp hơn, rồi benchmark một số thao tác bằng OpenSSL.",
        ],
    )


def run_openssl_speed_once(algorithms: list[str], seconds: int = 2):
    """Chạy benchmark OpenSSL speed và parse kết quả sign/verify.

    Đây là benchmark chạy thật trên máy hiện tại.
    Kết quả phụ thuộc CPU, OpenSSL version và môi trường chạy.
    """
    openssl_path = shutil.which("openssl")

    if openssl_path is None:
        return None, "Không tìm thấy OpenSSL trong PATH. Hãy cài OpenSSL hoặc thêm openssl.exe vào PATH."

    cmd = [openssl_path, "speed", "-seconds", str(seconds), *algorithms]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(30, seconds * max(1, len(algorithms)) * 8),
            check=False,
        )
    except Exception as exc:
        return None, f"Không chạy được OpenSSL benchmark: {exc}"

    raw = (completed.stdout or "") + "\n" + (completed.stderr or "")

    rows = []

    # Ví dụ RSA/DSA:
    # rsa 2048 bits 0.000650s 0.000022s 1539.1 45198.2
    pattern_classic = re.compile(
        r"^(rsa|dsa)\s+(\d+)\s+bits\s+"
        r"([0-9.]+)s\s+([0-9.]+)s\s+([0-9.]+)\s+([0-9.]+)",
        re.IGNORECASE,
    )

    # Ví dụ ECDSA:
    # 256 bits ecdsa (nistp256) 0.0000s 0.0001s 33256.1 12769.3
    pattern_ecdsa = re.compile(
        r"^(\d+)\s+bits\s+ecdsa\s+\(([^)]+)\)\s+"
        r"([0-9.]+)s\s+([0-9.]+)s\s+([0-9.]+)\s+([0-9.]+)",
        re.IGNORECASE,
    )

    for line in raw.splitlines():
        line = line.strip()

        m1 = pattern_classic.match(line)
        if m1:
            kind, bits, sign_time, verify_time, sign_per_s, verify_per_s = m1.groups()

            rows.append({
                "Thuật toán": f"{kind.upper()} {bits}",
                "Loại": kind.upper(),
                "Bits": int(bits),
                "Sign time (s)": float(sign_time),
                "Verify time (s)": float(verify_time),
                "Sign/s": float(sign_per_s),
                "Verify/s": float(verify_per_s),
            })
            continue

        m2 = pattern_ecdsa.match(line)
        if m2:
            bits, curve, sign_time, verify_time, sign_per_s, verify_per_s = m2.groups()

            rows.append({
                "Thuật toán": f"ECDSA {curve}",
                "Loại": "ECDSA",
                "Bits": int(bits),
                "Sign time (s)": float(sign_time),
                "Verify time (s)": float(verify_time),
                "Sign/s": float(sign_per_s),
                "Verify/s": float(verify_per_s),
            })

    if not rows:
        return None, raw

    return pd.DataFrame(rows), raw

def render_live_public_key_benchmark():
    st.markdown("### ⚡ Benchmark chạy thật bằng OpenSSL")

    st.warning(
        "Benchmark phụ thuộc vào CPU, phiên bản OpenSSL và môi trường chạy. "
        "Kết quả chỉ dùng để quan sát trade-off, không phải kết luận tuyệt đối."
    )

    st.info(
        "`ecdsap256` trong `openssl speed` là ECDSA trên NIST P-256, "
        "không phải secp256k1 của Bitcoin. Page 9 mới dùng secp256k1 để ký/verify thật."
    )

    st.caption(
        "Gợi ý đọc kết quả: hãy tách riêng hai thao tác signing và verification. "
        "Một thuật toán có thể ký rất nhanh nhưng verify không nhanh nhất, hoặc ngược lại."
    )

    selected = st.multiselect(
        "Chọn thuật toán để benchmark",
        options=[
            "rsa2048",
            "rsa3072",
            "dsa2048",
            "ecdsap256",
            "ecdsap384",
        ],
        default=["rsa2048", "rsa3072", "ecdsap256"],
        help=(
            "RSA 2048/3072 dùng để so sánh với ECDSA. "
            "DSA 2048 có thể không được hỗ trợ đầy đủ tùy bản OpenSSL."
        ),
    )

    seconds = st.slider(
        "Số giây benchmark mỗi thuật toán",
        min_value=1,
        max_value=5,
        value=2,
    )

    if st.button("🚀 Chạy OpenSSL benchmark", use_container_width=True):
        if not selected:
            st.warning("Hãy chọn ít nhất một thuật toán.")
            return

        with st.spinner("Đang chạy OpenSSL speed..."):
            df, raw = run_openssl_speed_once(selected, seconds)

        if df is None:
            st.error("Không parse được kết quả benchmark.")
            with st.expander("Xem output thô từ OpenSSL", expanded=True):
                st.code(raw, language="text")
            return

        st.session_state["public_key_benchmark_df"] = df
        st.session_state["public_key_benchmark_raw"] = raw

    if "public_key_benchmark_df" in st.session_state:
        df = st.session_state["public_key_benchmark_df"]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        sign_chart = px.bar(
            df,
            x="Thuật toán",
            y="Sign/s",
            title="Tốc độ ký: số chữ ký mỗi giây",
        )
        sign_chart.update_layout(
            height=480,
            xaxis_title="Thuật toán",
            yaxis_title="Sign/s",
        )
        st.plotly_chart(sign_chart, use_container_width=True)

        verify_chart = px.bar(
            df,
            x="Thuật toán",
            y="Verify/s",
            title="Tốc độ kiểm tra chữ ký: số verify mỗi giây",
        )
        verify_chart.update_layout(
            height=480,
            xaxis_title="Thuật toán",
            yaxis_title="Verify/s",
        )
        st.plotly_chart(verify_chart, use_container_width=True)

        with st.expander("Xem output thô từ OpenSSL", expanded=False):
            st.code(st.session_state.get("public_key_benchmark_raw", ""), language="text")

        render_benchmark_interpretation(df)

def render_benchmark_interpretation(df: pd.DataFrame) -> None:
    """Giải thích kết quả benchmark RSA/DSA/ECDSA ở Page 2.

    Hàm này không thay thế benchmark. Nó chỉ giúp người học đọc kết quả đúng:
    - Không kết luận ECC luôn nhanh hơn RSA.
    - Phân biệt sign và verify.
    - Không nhầm ECDSA P-256 với secp256k1.
    """
    if df is None or df.empty:
        return

    required_cols = {"Thuật toán", "Sign/s", "Verify/s"}
    if not required_cols.issubset(set(df.columns)):
        return

    st.markdown("### 🧠 Cách đọc kết quả benchmark")

    fastest_sign = df.loc[df["Sign/s"].idxmax()]
    fastest_verify = df.loc[df["Verify/s"].idxmax()]

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Ký nhanh nhất trong lượt chạy",
            fastest_sign["Thuật toán"],
            f"{float(fastest_sign['Sign/s']):.1f} sign/s",
        )

    with col2:
        st.metric(
            "Verify nhanh nhất trong lượt chạy",
            fastest_verify["Thuật toán"],
            f"{float(fastest_verify['Verify/s']):.1f} verify/s",
        )

    def find_row(keyword: str):
        mask = df["Thuật toán"].astype(str).str.lower().str.contains(keyword.lower(), regex=False)
        if mask.any():
            return df[mask].iloc[0]
        return None

    rsa2048 = find_row("RSA 2048")
    rsa3072 = find_row("RSA 3072")
    dsa2048 = find_row("DSA 2048")
    ecdsa_p256 = find_row("nistp256")
    ecdsa_p384 = find_row("nistp384")

    insight_rows = []

    if rsa2048 is not None:
        ratio = float(rsa2048["Verify/s"]) / max(float(rsa2048["Sign/s"]), 1e-12)
        insight_rows.append({
            "Nhận xét": "RSA 2048 verify nhanh hơn sign rất nhiều",
            "Số liệu": f"{ratio:.2f} lần",
            "Ý nghĩa": "RSA verification thường rất nhanh vì public exponent thường nhỏ.",
        })

    if rsa3072 is not None:
        ratio = float(rsa3072["Verify/s"]) / max(float(rsa3072["Sign/s"]), 1e-12)
        insight_rows.append({
            "Nhận xét": "RSA 3072 verify cũng nhanh hơn sign rất nhiều",
            "Số liệu": f"{ratio:.2f} lần",
            "Ý nghĩa": "Khi tăng kích thước khóa RSA, signing/private operation nặng hơn rõ rệt.",
        })

    if ecdsa_p256 is not None and rsa2048 is not None:
        ratio = float(ecdsa_p256["Sign/s"]) / max(float(rsa2048["Sign/s"]), 1e-12)
        insight_rows.append({
            "Nhận xét": "ECDSA P-256 sign nhanh hơn RSA 2048 sign trong lượt chạy này",
            "Số liệu": f"{ratio:.2f} lần",
            "Ý nghĩa": "Đây là một lợi thế hiệu năng nổi bật của ECDSA P-256 ở thao tác ký.",
        })

        verify_ratio = float(rsa2048["Verify/s"]) / max(float(ecdsa_p256["Verify/s"]), 1e-12)
        insight_rows.append({
            "Nhận xét": "RSA 2048 verify nhanh hơn ECDSA P-256 verify trong lượt chạy này",
            "Số liệu": f"{verify_ratio:.2f} lần",
            "Ý nghĩa": "Không nên kết luận ECC luôn nhanh hơn RSA ở mọi thao tác.",
        })

    if ecdsa_p256 is not None and rsa3072 is not None:
        ratio = float(ecdsa_p256["Sign/s"]) / max(float(rsa3072["Sign/s"]), 1e-12)
        insight_rows.append({
            "Nhận xét": "ECDSA P-256 sign nhanh hơn RSA 3072 sign trong lượt chạy này",
            "Số liệu": f"{ratio:.2f} lần",
            "Ý nghĩa": "Khi RSA tăng kích thước khóa, signing chậm đi rất rõ.",
        })

    if ecdsa_p256 is not None and ecdsa_p384 is not None:
        sign_ratio = float(ecdsa_p256["Sign/s"]) / max(float(ecdsa_p384["Sign/s"]), 1e-12)
        verify_ratio = float(ecdsa_p256["Verify/s"]) / max(float(ecdsa_p384["Verify/s"]), 1e-12)

        insight_rows.append({
            "Nhận xét": "ECDSA P-256 nhanh hơn ECDSA P-384 đáng kể",
            "Số liệu": f"sign ≈ {sign_ratio:.2f} lần, verify ≈ {verify_ratio:.2f} lần",
            "Ý nghĩa": "Curve khác nhau và mức an toàn khác nhau có thể làm hiệu năng khác nhau rất mạnh.",
        })

    if dsa2048 is not None and ecdsa_p256 is not None:
        sign_ratio = float(ecdsa_p256["Sign/s"]) / max(float(dsa2048["Sign/s"]), 1e-12)
        verify_ratio = float(ecdsa_p256["Verify/s"]) / max(float(dsa2048["Verify/s"]), 1e-12)

        insight_rows.append({
            "Nhận xét": "ECDSA P-256 nhanh hơn DSA 2048 trong lượt chạy này",
            "Số liệu": f"sign ≈ {sign_ratio:.2f} lần, verify ≈ {verify_ratio:.2f} lần",
            "Ý nghĩa": "DSA giúp hiểu họ chữ ký dựa trên discrete log; ECDSA là biến thể trên elliptic curve.",
        })

    if insight_rows:
        st.dataframe(
            pd.DataFrame(insight_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Kết luận đúng từ benchmark")

    conclusion_rows = [
        {
            "Kết luận sai dễ mắc": "ECC luôn nhanh hơn RSA.",
            "Cách hiểu đúng": "Không. Benchmark cho thấy ECDSA P-256 sign rất nhanh, nhưng RSA verify vẫn cực nhanh.",
        },
        {
            "Kết luận sai dễ mắc": "So sánh RSA 2048 bit với ECC 256 bit bằng số bit thô.",
            "Cách hiểu đúng": "Không nên so số bit trực tiếp. RSA và ECC dùng bài toán khó khác nhau nên kích thước khóa không cùng ý nghĩa.",
        },
        {
            "Kết luận sai dễ mắc": "ecdsap256 là secp256k1.",
            "Cách hiểu đúng": "Không. ecdsap256 trong OpenSSL speed là NIST P-256. Bitcoin truyền thống dùng secp256k1, được demo riêng ở Page 9.",
        },
        {
            "Kết luận sai dễ mắc": "Benchmark là bằng chứng an toàn.",
            "Cách hiểu đúng": "Không. Benchmark chỉ đo hiệu năng. An toàn còn phụ thuộc tham số, bài toán khó, nonce discipline, constant-time và implementation.",
        },
    ]

    st.dataframe(
        pd.DataFrame(conclusion_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.success(
        "Thông điệp nên chốt ở Page 2: ECC đáng học không phải vì nó thắng RSA ở mọi phép đo, "
        "mà vì nó tạo ra một trade-off rất mạnh giữa kích thước khóa, hiệu năng và mức an toàn. "
        "ECDSA là một ứng dụng chữ ký số quan trọng của trade-off đó."
    )

# ============================================================
# PAGE 2
# ============================================================

def demo_public_key_systems_and_benchmark():
    st.title("2. RSA, ElGamal/DH và ECC")

    render_page_intro(
        "ECC nằm ở đâu trong bản đồ mật mã khóa công khai?",
        "RSA, ElGamal/DH và ECC đều là public-key crypto, nhưng dựa trên các bài toán khó và đối tượng toán học khác nhau.",
        "Ta so sánh lý thuyết, so sánh chữ ký số, rồi chạy benchmark OpenSSL thật cho RSA/DSA/ECDSA.",
    )

    st.info(
        "Dụng ý của page này: kéo trọng tâm đề tài về ECC. "
        "Bitcoin không phải điểm xuất phát; Bitcoin chỉ là case study ở phía sau. "
        "Trước khi tới Bitcoin, ta cần thấy ECC đứng cạnh RSA và ElGamal/DH như một họ mật mã khóa công khai."
    )

    render_term_notes([
        (
            "RSA",
            "Hệ mật mã khóa công khai dựa trên số học modulo n = p*q. Thường gắn với bài toán phân tích số nguyên lớn và RSA problem."
        ),
        (
            "Diffie-Hellman / ElGamal",
            "Họ giao thức dựa trên discrete logarithm trong nhóm hữu hạn, thường viết dạng y = g^x mod p."
        ),
        (
            "ECC",
            "Elliptic Curve Cryptography: thay nhóm số modulo bằng nhóm điểm trên đường cong elliptic."
        ),
        (
            "ECDLP",
            "Bài toán log rời rạc trên đường cong elliptic: biết G và Q = dG, tìm lại d."
        ),
        (
            "ECDSA P-256",
            "ECDSA trên đường cong NIST P-256. Đây là curve OpenSSL speed thường benchmark bằng lệnh ecdsap256."
        ),
        (
            "secp256k1",
            "Đường cong Bitcoin dùng trong ECDSA truyền thống. Không được nhầm với ecdsap256 của OpenSSL speed."
        ),
    ])

    tab_map, tab_sig, tab_bench = st.tabs([
        "🧭 Bản đồ public-key systems",
        "✍️ So sánh chữ ký số",
        "⚡ Benchmark chạy thật",
    ])

    with tab_map:
        st.markdown("## 1. RSA, ElGamal/DH và ECC khác nhau ở đâu?")

        rows = [
            {
                "Hệ": "RSA",
                "Public key": "(n, e)",
                "Private key": "d",
                "Bài toán khó": "Factorization / RSA problem",
                "Ứng dụng": "Mã hóa, chữ ký số",
                "Ghi chú": "Trapdoor one-way function kinh điển",
            },
            {
                "Hệ": "Diffie-Hellman / ElGamal",
                "Public key": "y = g^x mod p",
                "Private key": "x",
                "Bài toán khó": "Discrete Logarithm Problem",
                "Ứng dụng": "Trao đổi khóa, mã hóa, chữ ký họ DLP",
                "Ghi chú": "Log rời rạc trên nhóm hữu hạn",
            },
            {
                "Hệ": "ECC",
                "Public key": "Q = dG",
                "Private key": "d",
                "Bài toán khó": "ECDLP",
                "Ứng dụng": "ECDH, ECDSA, EdDSA",
                "Ghi chú": "Log rời rạc trên nhóm điểm elliptic curve",
            },
        ]

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("## 2. Từ DLP đến ECDLP")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### DLP trong nhóm modulo")
            st.latex(r"y = g^x \pmod p")
            st.markdown(
                """
                Trong Diffie-Hellman / ElGamal, private key thường là `x`,
                public key là `y`.

                Biết `g`, `p`, `y`, tìm lại `x` là bài toán log rời rạc.
                """
            )

        with col2:
            st.markdown("### ECDLP trong nhóm điểm elliptic curve")
            st.latex(r"Q = dG")
            st.markdown(
                """
                Trong ECC, private key là `d`, public key là điểm `Q`.

                Biết `G` và `Q`, tìm lại `d` là ECDLP.
                """
            )

        st.success(
            "Ý tưởng lớn: ECC không phải một thứ tách rời khỏi mật mã khóa công khai. "
            "Nó là một cách xây public-key crypto bằng nhóm điểm elliptic curve thay vì nhóm số modulo."
        )

    with tab_sig:
        st.markdown("## 1. Chữ ký số trong các hệ public-key")

        signature_rows = [
            {
                "Chữ ký": "RSA signature",
                "Nền tảng": "RSA problem",
                "Signing": "Dùng private exponent",
                "Verification": "Dùng public exponent",
                "Ghi chú": "Verify thường rất nhanh",
            },
            {
                "Chữ ký": "DSA / ElGamal-style",
                "Nền tảng": "DLP",
                "Signing": "Dùng nonce k",
                "Verification": "Kiểm tra quan hệ log rời rạc",
                "Ghi chú": "Nhạy cảm với nonce",
            },
            {
                "Chữ ký": "ECDSA",
                "Nền tảng": "ECDLP",
                "Signing": "Dùng nonce k và R = kG",
                "Verification": "Tính u1G + u2Q",
                "Ghi chú": "Bitcoin dùng ECDSA truyền thống trên secp256k1",
            },
        ]

        st.info(
            "Benchmark ở tab sau thường cho thấy một trade-off thú vị: "
            "RSA verify rất nhanh, còn ECDSA P-256 có thể ký rất nhanh. "
            "Vì vậy không nên hỏi 'RSA hay ECC nhanh hơn?' một cách chung chung; "
            "phải hỏi nhanh hơn ở thao tác nào, với curve/key size nào, trên máy nào."
        )

        st.dataframe(
            pd.DataFrame(signature_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("## 2. Vì sao ECDSA đáng chú ý?")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### Key generation")
            st.latex(r"Q = dG")
            st.caption("Private key d tạo public key Q bằng phép nhân điểm.")

        with col2:
            st.markdown("### Signing")
            st.latex(r"R = kG")
            st.latex(r"s = k^{-1}(h + rd) \bmod n")
            st.caption("Nonce k cực kỳ nhạy cảm. Sai nonce là private key bay màu.")

        with col3:
            st.markdown("### Verification")
            st.latex(r"P = u_1G + u_2Q")
            st.latex(r"\mathrm{valid} \iff x(P) \bmod n = r")
            st.caption("Verify dùng public key Q, không cần biết private key d.")

        st.warning(
            "Page này chỉ so sánh vị trí của các chữ ký. "
            "Page 5 mới đi sâu vào trace từng bước ký và verify của ECDSA."
        )

    with tab_bench:
        render_live_public_key_benchmark()

    render_learning_summary(
        "RSA, ElGamal/DH và ECC",
        [
            "RSA, ElGamal/DH và ECC đều thuộc mật mã khóa công khai, nhưng dựa trên các bài toán khó khác nhau.",
            "RSA thường gắn với factorization/RSA problem; ElGamal/DH gắn với discrete logarithm; ECC gắn với ECDLP.",
            "ECC thay nhóm số modulo bằng nhóm điểm trên đường cong elliptic.",
            "ECDSA là chữ ký số dựa trên ECC, trong đó nonce k đóng vai trò cực kỳ nhạy cảm.",
            "Benchmark giúp quan sát trade-off hiệu năng, không phải để kết luận ECC luôn nhanh hơn RSA ở mọi tiêu chí.",
            "Bitcoin sẽ được dùng ở các page sau như một case study thực tế của ECDSA.",
        ],
    )


# ============================================================
# PAGE 3
# ============================================================
def demo_ecc_toy_curve():
    st.title("3. Nền tảng toán học ECC: Q = dG")

    render_page_intro(
        "ECC tạo public key từ private key như thế nào?",
        "Trong ECC, private key d là một số nguyên được giữ kín. Public key Q là một điểm trên đường cong, được tính bằng Q = dG.",
        "Ta dùng toy curve để nhìn thấy trường hữu hạn, đường cong elliptic, điểm sinh G, phép nhân điểm và double-and-add.",
    )

    st.warning(
        f"Đây là đường cong mô phỏng rất nhỏ: p = {DEMO_P}, a = {DEMO_A}, b = {DEMO_B}, "
        f"G = {point_to_text(GENERATOR_POINT)}, n = {ORDER_N}. "
        "Nó chỉ dùng để học toán và trực quan hóa, không an toàn cho bảo mật thật."
    )

    render_term_notes([
        (
            "Trường hữu hạn F_p",
            "Tập các số 0, 1, ..., p-1. Mọi phép cộng, trừ, nhân, chia đều lấy phần dư modulo p."
        ),
        (
            "Đường cong elliptic",
            "Tập các điểm (x, y) thỏa phương trình y² ≡ x³ + ax + b mod p, cộng thêm điểm vô cực."
        ),
        (
            "Điểm sinh G",
            "Một điểm cố định trên đường cong. Từ G, ta tạo các điểm khác bằng phép cộng điểm lặp lại."
        ),
        (
            "Private key d",
            "Một số nguyên bí mật. Trong hệ thật, d phải được sinh ngẫu nhiên đủ mạnh và tuyệt đối không để lộ."
        ),
        (
            "Public key Q",
            "Một điểm trên đường cong, được tính từ private key bằng Q = dG."
        ),
        (
            "Phép nhân điểm dG",
            "Không phải nhân từng tọa độ với d. Nó là phép cộng điểm G với chính nó nhiều lần, được tính nhanh bằng double-and-add."
        ),
        (
            "ECDLP",
            "Bài toán đi ngược: biết G và Q = dG, tìm lại d. Đây là nội dung của Page 4."
        ),
    ])

    st.markdown("## 1. Đường cong elliptic trên trường hữu hạn")

    st.markdown(
        """
        Trong demo này, ta dùng một đường cong nhỏ trên trường hữu hạn `F_p`:

        """
    )

    st.latex(rf"y^2 \equiv x^3 + {DEMO_A}x + {DEMO_B} \pmod{{{DEMO_P}}}")

    st.markdown(
        """
        Điều quan trọng: trong mật mã, đường cong không phải là một nét vẽ mượt trên mặt phẳng thực.
        Nó là một **tập điểm rời rạc** trên trường hữu hạn.

        Vì vậy page này dùng hai cách nhìn:

        ```text
        1. Đường cong trên số thực: để lấy trực giác hình học.
        2. Điểm rời rạc trên F_p: để đúng với bản chất mật mã.
        ```
        """
    )

    with st.container(border=True):
        st.markdown("### Case study nhỏ: secp256k1 trong Bitcoin")

        st.markdown(
            """
            Bitcoin truyền thống dùng curve **secp256k1**, cũng thuộc họ elliptic curve trên trường hữu hạn.

            Dạng phương trình của secp256k1 là:

            ```text
            y² = x³ + 7 mod p
            ```

            Trong page này, ta không mô phỏng độ an toàn thật của secp256k1.
            Ta chỉ dùng toy curve nhỏ để thấy cơ chế toán học phía sau ECC.
            Bitcoin sẽ quay lại ở Page 6 như một case study của ECDSA.
            """
        )

    st.markdown("## 2. Từ private key d đến public key Q")

    d = st.slider(
        "🔑 Chọn private key mô phỏng d",
        min_value=1,
        max_value=ORDER_N - 1,
        value=min(5, ORDER_N - 1),
        help="Trong demo nhỏ này, d chỉ là một số nguyên nhỏ. Trong hệ thật, d phải là số bí mật rất lớn và được sinh an toàn.",
    )

    Q = ECDSA_PARAMS.curve.scalar_mul(d, ECDSA_PARAMS.G)

    col_d, col_g, col_q = st.columns(3)

    with col_d:
        st.metric("Private key d", d)

    with col_g:
        st.metric("Điểm sinh G", point_to_text(ECDSA_PARAMS.G))

    with col_q:
        st.metric("Public key Q", point_to_text(Q))

    st.success(
        f"Public key được tạo ra bằng phép nhân điểm: Q = {d}G = {point_to_text(Q)}"
    )

    with st.expander("🔎 Xem quá trình double-and-add tạo Q", expanded=False):
        st.markdown(
            """
            Phép nhân điểm `Q = dG` không phải là nhân từng tọa độ của `G` với `d`.

            Trong ECC:

            ```text
            dG = G + G + ... + G
            ```

            Nhưng cộng lặp từng lần sẽ chậm. Vì vậy ta dùng **double-and-add**:
            biểu diễn `d` dưới dạng nhị phân, rồi xử lý từng bit.

            - Nếu bit đang xét bằng `1`, ta cộng thêm điểm hiện tại vào kết quả.
            - Sau mỗi vòng, ta nhân đôi điểm hiện tại để chuẩn bị cho bit tiếp theo.
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

        st.dataframe(
            pd.DataFrame(trace_rows),
            use_container_width=True,
            hide_index=True,
        )

        if trace_result == Q:
            st.success(
                f"Kết quả cuối cùng của double-and-add khớp với Q: {point_to_text(trace_result)}"
            )
        else:
            st.error(
                f"Kết quả trace không khớp. Trace = {point_to_text(trace_result)}, Q = {point_to_text(Q)}"
            )

        st.info(
            "Ý nghĩa: tính Q từ d là nhanh vì double-and-add phụ thuộc vào số bit của d. "
            "Nhưng đi ngược từ Q về d lại là bài toán ECDLP, và sẽ được mô phỏng ở Page 4."
        )

    st.markdown("## 3. Nhìn ECC bằng hai lớp trực quan")

    viz_tab_real, viz_tab_finite = st.tabs([
        "🌊 Trực giác hình học trên số thực",
        f"🔢 Bản chất rời rạc trên F_{DEMO_P}",
    ])

    with viz_tab_real:
        st.markdown(
            """
            Trên số thực, elliptic curve nhìn giống một đường cong mượt.
            Hình này chỉ dùng để lấy trực giác hình học về “đường cong”.

            Nhưng hệ ECC trong mật mã không chạy trực tiếp trên đường cong mượt này.
            Nó chạy trên trường hữu hạn `F_p`, nên đối tượng thật là các điểm rời rạc ở tab bên cạnh.
            """
        )

        real_choice = st.radio(
            "Chọn đường cong để quan sát",
            [
                "Toy curve đang dùng trong demo",
                "Dạng secp256k1: y² = x³ + 7",
            ],
            horizontal=True,
        )

        if real_choice == "Dạng secp256k1: y² = x³ + 7":
            real_a, real_b = 0, 7
            real_title = "Trực giác hình học của dạng secp256k1: y² = x³ + 7"
        else:
            real_a, real_b = DEMO_A, DEMO_B
            real_title = f"Trực giác hình học của toy curve: y² = x³ + {DEMO_A}x + {DEMO_B}"

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
            "Đọc hình này đúng cách: nó giúp hiểu chữ “curve”, nhưng chưa phải bản chất crypto. "
            "Bản chất crypto nằm ở tab điểm rời rạc trên F_p."
        )

    with viz_tab_finite:
        st.markdown(
            f"""
            Đây là toy curve trên trường hữu hạn `F_{DEMO_P}`.

            Tọa độ `x` và `y` chỉ nhận các giá trị:

            ```text
            0, 1, 2, ..., {DEMO_P - 1}
            ```

            và mọi phép toán đều lấy phần dư modulo `{DEMO_P}`.
            Vì vậy, thay vì một đường cong mượt, ta thu được một tập điểm rời rạc.
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
                colors.append("Public key Q")
                sizes.append(18)
                labels.append("Q")
            else:
                colors.append("Điểm trên toy curve")
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
            title=f"Các điểm trên toy curve trong trường F_{DEMO_P}",
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
            "G là điểm sinh cố định. Q là public key được tạo từ Q = dG. "
            "Các điểm còn lại là những điểm thỏa phương trình elliptic curve trên F_p."
        )

    st.markdown("## 4. Vì sao Page 3 dẫn sang Page 4?")

    bridge_rows = [
        {
            "Chiều tính toán": "Từ d đến Q",
            "Bài toán": "Q = dG",
            "Độ khó trực giác": "Nhanh",
            "Vì sao?": "Dùng double-and-add, phụ thuộc vào số bit của d.",
        },
        {
            "Chiều tính toán": "Từ Q về d",
            "Bài toán": "Tìm d sao cho Q = dG",
            "Độ khó trực giác": "Rất khó với tham số thật",
            "Vì sao?": "Đây là ECDLP, Page 4 sẽ thử brute force, BSGS và Pollard rho trên toy curve.",
        },
    ]

    st.dataframe(
        pd.DataFrame(bridge_rows),
        use_container_width=True,
        hide_index=True,
    )

    render_learning_summary(
        "Nền tảng toán học ECC",
        [
            "ECC làm việc trên nhóm điểm của đường cong elliptic trên trường hữu hạn F_p.",
            "Private key d là một số bí mật; public key Q là một điểm được tính bằng Q = dG.",
            "Phép nhân điểm dG được tính hiệu quả bằng double-and-add.",
            "Đường cong thực giúp lấy trực giác hình học, còn các điểm rời rạc trên F_p mới gần với bản chất mật mã.",
            "Tính Q từ d là nhanh; tìm ngược d từ Q là ECDLP.",
            "Đây là nền tảng chung của các hệ ECC. Bitcoin chỉ là một case study dùng ECDSA trên nền ECC.",
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
# PAGE 4
# ============================================================

def demo_ecdlp_explanation():
    st.title("4. ECDLP: Vì sao Q không làm lộ d?")

    render_page_intro(
        "Vì sao biết public key Q mà không suy ra được private key d?",
        "Page 3 cho thấy tính xuôi Q = dG là nhanh. Page này thử chiều ngược: biết G và Q, tìm lại d.",
        "Ta đóng vai attacker trên toy curve và thử ba hướng: brute force, Baby-step Giant-step và Pollard rho.",
    )

    st.warning(
        f"Đây là toy curve rất nhỏ, n = {ORDER_N}, chỉ dùng để học và trực quan hóa. "
        "Không dùng demo này để thử với curve thật, khóa thật, ví thật hoặc hệ thống thật."
    )

    render_term_notes([
        (
            "ECDLP",
            "Elliptic Curve Discrete Logarithm Problem: biết G và Q = dG, tìm lại d."
        ),
        (
            "Attacker biết gì?",
            "Trong mô hình này, attacker biết đường cong, điểm sinh G và public key Q. Attacker không biết private key d."
        ),
        (
            "Brute force",
            "Thử lần lượt từng k rồi kiểm tra kG có bằng Q không. Dễ hiểu nhất, nhưng tốn O(n) thời gian."
        ),
        (
            "Baby-step Giant-step",
            "Thuật toán gặp nhau ở giữa: giảm thời gian xuống O(√n), nhưng phải lưu O(√n) điểm."
        ),
        (
            "Pollard rho",
            "Dùng random-walk để tìm collision. Kỳ vọng O(√n) thời gian và dùng ít bộ nhớ hơn BSGS."
        ),
        (
            "Toy curve vs curve thật",
            "Toy curve có n nhỏ nên phá được. Curve thật có tham số rất lớn nên các demo này không thể dùng để phá khóa thật."
        ),
    ])

    st.markdown("## 1. Thiết lập bài toán ECDLP")

    d_secret = st.slider(
        "🔐 Chọn private key bí mật mô phỏng d",
        min_value=1,
        max_value=ORDER_N - 1,
        value=min(5, ORDER_N - 1),
        help="Trong demo, ta cố tình cho d nhỏ để có thể nhìn thấy attacker tìm lại d như thế nào.",
    )

    Q = ECDSA_PARAMS.curve.scalar_mul(d_secret, ECDSA_PARAMS.G)

    col_curve, col_secret, col_public = st.columns(3)

    with col_curve:
        st.metric("Order mô phỏng n", ORDER_N)

    with col_secret:
        st.metric("Private key d", d_secret)

    with col_public:
        st.metric("Public key Q", point_to_text(Q))

    st.success(
        f"Hệ thống tạo public key bằng chiều dễ: Q = {d_secret}G = {point_to_text(Q)}"
    )

    st.markdown("### Attacker nhìn thấy gì?")

    attacker_rows = [
        {
            "Đối tượng": "Đường cong",
            "Attacker biết?": True,
            "Vai trò": "Tham số công khai của hệ ECC.",
        },
        {
            "Đối tượng": "Điểm sinh G",
            "Attacker biết?": True,
            "Vai trò": "Điểm gốc dùng để sinh public key.",
        },
        {
            "Đối tượng": "Public key Q",
            "Attacker biết?": True,
            "Vai trò": "Điểm được công khai, Q = dG.",
        },
        {
            "Đối tượng": "Private key d",
            "Attacker biết?": False,
            "Vai trò": "Bí mật cần bảo vệ.",
        },
    ]

    st.dataframe(
        pd.DataFrame(attacker_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "Bài toán của attacker: tìm một số k sao cho kG = Q. "
        "Nếu tìm được k, attacker đã khôi phục được private key d."
    )

    st.markdown("## 2. Chọn thuật toán tấn công trên toy curve")

    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:
        show_bsgs = st.checkbox(
            "Hiện Baby-step Giant-step",
            value=True,
            help="BSGS giúp so sánh O(n) với O(√n), nhưng cần thêm bộ nhớ để lưu bảng baby steps.",
        )

    with col_opt2:
        show_rho = st.checkbox(
            "Hiện Pollard rho",
            value=False,
            help="Pollard rho là phần nâng cao. Có thể gặp collision suy biến trên toy curve nhỏ.",
        )

    brute_result = brute_force_dlog_demo(
        ECDSA_PARAMS.curve,
        ECDSA_PARAMS.G,
        Q,
        ORDER_N,
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

    st.markdown("## 3. So sánh kết quả")

    summary_rows = [
        {
            "Thuật toán": "Brute force",
            "Ý tưởng": "Thử từng k cho đến khi kG = Q",
            "Thời gian": "O(n)",
            "Bộ nhớ": "O(1)",
            "d tìm được": brute_result["recovered"],
            "Số bước demo": brute_result["steps"],
            "Kết quả": "Thành công" if brute_result["success"] else "Thất bại",
        },
    ]

    if bsgs_result is not None:
        summary_rows.append({
            "Thuật toán": "Baby-step Giant-step",
            "Ý tưởng": "Gặp nhau ở giữa: d = i*m + j",
            "Thời gian": "O(√n)",
            "Bộ nhớ": "O(√n)",
            "d tìm được": bsgs_result["recovered"],
            "Số bước demo": bsgs_result["steps"],
            "Kết quả": "Thành công" if bsgs_result["success"] else "Thất bại",
        })

    if rho_result is not None:
        summary_rows.append({
            "Thuật toán": "Pollard rho",
            "Ý tưởng": "Random-walk tìm collision",
            "Thời gian": "O(√n) kỳ vọng",
            "Bộ nhớ": "O(1)",
            "d tìm được": rho_result["recovered"],
            "Số bước demo": rho_result["steps"],
            "Kết quả": "Thành công" if rho_result["status"] == "success" else "Chưa thành công",
        })

    st.dataframe(
        pd.DataFrame(summary_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## 4. Xem chi tiết từng thuật toán")

    tabs = ["1️⃣ Brute force"]

    if show_bsgs:
        tabs.append("2️⃣ Baby-step Giant-step")

    if show_rho:
        tabs.append("3️⃣ Pollard rho")

    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        st.markdown(
            """
            **Brute force** là cách trực diện nhất:

            ```text
            thử k = 0, 1, 2, ...
            tính kG
            nếu kG = Q thì k chính là d
            ```

            Nó dễ hiểu, nhưng với `n` lớn thì số lần thử quá khổng lồ.
            """
        )

        st.dataframe(
            pd.DataFrame(brute_result["rows"]),
            use_container_width=True,
            hide_index=True,
        )

        if brute_result["success"]:
            st.success(f"Brute force tìm được d = {brute_result['recovered']}.")
        else:
            st.error("Brute force không tìm được d trong phạm vi toy order.")

    tab_index = 1

    if show_bsgs and bsgs_result is not None:
        with tab_objects[tab_index]:
            st.markdown(
                f"""
                **Baby-step Giant-step** dùng tư tưởng “gặp nhau ở giữa”.

                Chọn:

                ```text
                m = ceil(sqrt(n)) = {bsgs_result['m']}
                ```

                Viết private key dưới dạng:

                ```text
                d = i*m + j
                ```

                Khi đó:

                ```text
                Q = dG = (i*m + j)G
                Q - i(mG) = jG
                ```

                Nghĩa là ta làm hai phía:

                - **Baby steps:** lưu bảng các điểm `jG`.
                - **Giant steps:** thử các điểm `Q - i(mG)`.
                - Khi hai phía gặp nhau, suy ra `d = i*m + j`.
                """
            )

            col_baby, col_giant = st.columns(2)

            with col_baby:
                st.markdown("#### Baby steps: bảng jG")
                st.dataframe(
                    pd.DataFrame(bsgs_result["baby_rows"]),
                    use_container_width=True,
                    hide_index=True,
                )

            with col_giant:
                st.markdown("#### Giant steps: bảng Q - i(mG)")
                st.dataframe(
                    pd.DataFrame(bsgs_result["giant_rows"]),
                    use_container_width=True,
                    hide_index=True,
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
                **Pollard rho** cũng tìm `d`, nhưng không lưu bảng lớn như BSGS.

                Ý tưởng:

                ```text
                giữ X = aG + bQ
                cho hai con trỏ tortoise/hare chạy trong nhóm điểm
                nếu hai con trỏ gặp nhau tại cùng X thì có collision
                từ collision suy ra phương trình theo d
                ```

                Điểm mạnh: dùng ít bộ nhớ.

                Điểm khó chịu: trên toy curve nhỏ, random-walk có thể rơi vào collision suy biến.
                Khi đó app báo chưa thành công thay vì giả vờ phá được.
                """
            )

            if rho_result["status"] == "success":
                st.success(f"Pollard rho tìm được d = {rho_result['recovered']}.")
            else:
                st.warning(rho_result["note"])

            st.caption(f"Số collision suy biến: {rho_result['degenerate_count']}")

            rows = rho_result["rows"][:200]
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )

            if len(rho_result["rows"]) > 200:
                st.caption("Chỉ hiển thị 200 dòng đầu để tránh bảng quá dài.")

    st.markdown("## 5. Vì sao toy curve phá được, curve thật thì không?")

    scale_rows = [
        {
            "Môi trường": "Toy curve trong app",
            "Kích thước nhóm": f"n = {ORDER_N}",
            "Điều xảy ra": "Có thể thử hết hoặc dùng BSGS/Pollard rho trong vài bước.",
        },
        {
            "Môi trường": "Curve thật dùng trong hệ mật mã",
            "Kích thước nhóm": "Rất lớn, thường cỡ hàng trăm bit",
            "Điều xảy ra": "Brute force và thuật toán O(√n) vẫn vượt xa khả năng tính toán thực tế.",
        },
    ]

    st.dataframe(
        pd.DataFrame(scale_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "Kết luận quan trọng: Page này không chứng minh ECC yếu. "
        "Ngược lại, nó cho thấy với toy curve nhỏ thì ECDLP nhìn thấy được, "
        "còn với tham số thật thì chiều Q -> d là thứ được thiết kế để bất khả thi trong thực tế."
    )

    render_learning_summary(
        "ECDLP",
        [
            "ECDLP là bài toán tìm d khi biết G và Q = dG.",
            "Brute force dễ hiểu nhưng mất O(n) thời gian.",
            "Baby-step Giant-step giảm xuống O(√n) thời gian nhưng cần O(√n) bộ nhớ.",
            "Pollard rho cũng có thời gian kỳ vọng O(√n), dùng ít bộ nhớ hơn nhưng khó trực quan và có thể gặp collision suy biến trong toy demo.",
            "Toy curve phá được vì n rất nhỏ; curve thật an toàn vì n cực lớn.",
            "Page 5 sẽ dùng nền tảng này để giải thích ECDSA: ký bằng private key, verify bằng public key, nhưng không làm lộ private key.",
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
# PAGE 5
# ============================================================
def demo_ecdsa_sign_verify():
    st.title("5. Chữ ký số ECDSA")

    render_page_intro(
        "Làm sao chứng minh mình có private key mà không tiết lộ private key?",
        "ECDSA cho phép người ký dùng private key d để tạo chữ ký, còn người kiểm tra chỉ cần public key Q để xác minh.",
        "Ta chọn d, nonce k và message; sau đó tạo chữ ký, trace quá trình ký, verify message gốc và thử sửa message sau khi ký.",
    )

    st.warning(
        f"Đây là ECDSA mô phỏng trên toy curve rất nhỏ, n = {ORDER_N}. "
        "Nó chỉ dùng để học công thức và luồng xử lý. Không dùng cho khóa thật, ví thật hoặc giao dịch thật."
    )

    render_term_notes([
        (
            "Chữ ký số",
            "Cơ chế chứng minh một dữ liệu được ủy quyền bởi người giữ private key, nhưng không cần tiết lộ private key."
        ),
        (
            "Private key d",
            "Khóa bí mật dùng để ký. Nếu d bị lộ, attacker có thể giả mạo chữ ký."
        ),
        (
            "Public key Q",
            "Khóa công khai dùng để verify. Trong ECC, Q được tính từ Q = dG."
        ),
        (
            "Message m",
            "Dữ liệu cần ký. Trong demo là một chuỗi text; trong Bitcoin case study sau này là dữ liệu giao dịch."
        ),
        (
            "Hash h",
            "Giá trị băm của message, được rút gọn modulo n trước khi đưa vào công thức ký."
        ),
        (
            "Nonce k",
            "Giá trị dùng một lần khi ký ECDSA. Nếu k bị lộ hoặc bị dùng lại, private key có thể bị khôi phục."
        ),
        (
            "Chữ ký ECDSA (r, s)",
            "Cặp số được tạo từ message, private key d và nonce k."
        ),
    ])

    st.markdown("## 1. ECDSA nằm ở đâu trong họ chữ ký số?")

    signature_rows = [
        {
            "Chữ ký": "RSA signature",
            "Nền tảng": "RSA problem",
            "Signing": "Dùng private exponent",
            "Verification": "Dùng public exponent",
            "Điểm cần nhớ": "Verify thường rất nhanh, nhưng không dựa trên elliptic curve.",
        },
        {
            "Chữ ký": "DSA / ElGamal-style",
            "Nền tảng": "Discrete Logarithm Problem",
            "Signing": "Dùng nonce k",
            "Verification": "Kiểm tra quan hệ log rời rạc",
            "Điểm cần nhớ": "Nonce k rất nhạy cảm.",
        },
        {
            "Chữ ký": "ECDSA",
            "Nền tảng": "ECDLP",
            "Signing": "Dùng nonce k và điểm R = kG",
            "Verification": "Tính P = u1G + u2Q",
            "Điểm cần nhớ": "DSA-style signature trên nhóm điểm elliptic curve.",
        },
    ]

    st.dataframe(
        pd.DataFrame(signature_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "Page 2 đã so sánh RSA, ElGamal/DH và ECC ở mức bản đồ. "
        "Page này chỉ tập trung vào cơ chế ECDSA: ký như thế nào, verify như thế nào và vì sao nonce k nguy hiểm."
    )

    render_ecdsa_formula_box()

    st.markdown("## 2. Chọn khóa, nonce và dữ liệu cần ký")

    col1, col2, col3 = st.columns(3)

    with col1:
        d_demo = int(st.number_input(
            "🔑 Private key d",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(10, ORDER_N - 1),
            help="Private key mô phỏng. Trong hệ thật, d phải là số bí mật lớn và được sinh an toàn.",
        ))

    with col2:
        k_demo = int(st.number_input(
            "🎲 Nonce mô phỏng k",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(3, ORDER_N - 1),
            help=(
                "Nonce chỉ dùng một lần khi ký. "
                "Page 7 sẽ cho thấy reused nonce hoặc known nonce có thể làm lộ private key."
            ),
        ))

    with col3:
        Q_demo = ECDSA_PARAMS.curve.scalar_mul(d_demo, ECDSA_PARAMS.G)
        st.metric("Public key Q", point_to_text(Q_demo))

    key_rows = [
        {
            "Thành phần": "Private key d",
            "Giá trị": d_demo,
            "Công khai?": "Không",
            "Vai trò": "Dùng để tạo chữ ký.",
        },
        {
            "Thành phần": "Public key Q = dG",
            "Giá trị": point_to_text(Q_demo),
            "Công khai?": "Có",
            "Vai trò": "Dùng để kiểm tra chữ ký.",
        },
        {
            "Thành phần": "Nonce k",
            "Giá trị": k_demo,
            "Công khai?": "Không",
            "Vai trò": "Dùng một lần trong quá trình ký.",
        },
    ]

    st.dataframe(
        pd.DataFrame(key_rows),
        use_container_width=True,
        hide_index=True,
    )

    msg_original = st.text_input(
        "📝 Message cần ký",
        value="Hello ECDSA",
        max_chars=120,
        help="Trong demo là text. Trong Bitcoin case study, dữ liệu được ký là dữ liệu giao dịch.",
    )

    st.markdown("## 3. Tạo chữ ký ECDSA")

    if st.button("🖊️ Tạo chữ ký ECDSA", use_container_width=True):
        ok_nonce, nonce_msg = validate_nonce(k_demo, ECDSA_PARAMS.n)

        if not msg_original.strip():
            st.warning("Message không nên để trống trong demo này.")
        elif not ok_nonce:
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

                # Reset message sửa để tránh dùng lại trạng thái cũ từ lần ký trước.
                st.session_state["ecdsa_tampered_message"] = msg_original + " [đã sửa]"

                st.success(f"Đã tạo chữ ký ECDSA: r = {r}, s = {s}")

            except Exception as exc:
                st.error(
                    f"Lỗi khi ký: {exc}. "
                    "Toy curve nhỏ có thể gặp edge-case như r = 0, s = 0 hoặc nonce không phù hợp. "
                    "Hãy thử đổi k hoặc đổi message."
                )

    if "sign_demo" not in st.session_state:
        st.info("Hãy chọn d, k, message rồi bấm tạo chữ ký để xem trace signing và verification.")
        render_learning_summary(
            "ECDSA",
            [
                "ECDSA dùng private key d để tạo chữ ký, nhưng verify chỉ cần public key Q.",
                "Nonce k là thành phần cực kỳ nhạy cảm trong quá trình ký.",
                "Sau khi tạo chữ ký, page này sẽ cho thấy chữ ký gắn với message cụ thể như thế nào.",
            ],
        )
        return

    data = st.session_state.sign_demo
    r, s, Q, msg = data["r"], data["s"], data["Q"], data["msg"]
    d = data.get("d")
    k = data.get("k")

    st.divider()
    st.markdown("## 4. Chữ ký đã tạo")

    signature_rows = [
        {
            "Thành phần": "Message gốc",
            "Giá trị": msg,
            "Ý nghĩa": "Dữ liệu được ký.",
        },
        {
            "Thành phần": "r",
            "Giá trị": r,
            "Ý nghĩa": "Thành phần thứ nhất của chữ ký ECDSA.",
        },
        {
            "Thành phần": "s",
            "Giá trị": s,
            "Ý nghĩa": "Thành phần thứ hai của chữ ký ECDSA.",
        },
        {
            "Thành phần": "Public key Q",
            "Giá trị": point_to_text(Q),
            "Ý nghĩa": "Khóa công khai dùng để verify.",
        },
    ]

    st.dataframe(
        pd.DataFrame(signature_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## 5. Trace quá trình ký")

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

    st.markdown("## 6. Verify message gốc bằng public key")

    valid_original = verify(ECDSA_PARAMS, Q, msg.encode("utf-8"), (r, s))

    if valid_original:
        st.success("Message gốc verify thành công. Người kiểm tra chỉ cần public key Q, không cần private key d.")
    else:
        st.error("Message gốc verify thất bại. Có thể chữ ký đang rơi vào edge-case của toy curve.")

    with st.expander("🧮 Xem các bước kiểm tra chữ ký với message gốc", expanded=False):
        render_ecdsa_verification_trace(
            ECDSA_PARAMS,
            Q,
            msg.encode("utf-8"),
            (r, s),
        )

    st.markdown("## 7. Sửa message sau khi ký")

    st.markdown(
        """
        Bây giờ thử thay đổi dữ liệu sau khi đã ký.

        Nếu chữ ký thật sự gắn với message ban đầu, việc sửa message sẽ làm verify thất bại.
        Tuy nhiên, vì toy curve có `n` rất nhỏ, đôi khi message sửa vẫn vô tình verify True.
        Khi đó đây là hạn chế của mô phỏng nhỏ, không phải tính chất mong muốn trong hệ thật.
        """
    )

    tampered_key = "ecdsa_tampered_message"

    if "ecdsa_tampered_message_next" in st.session_state:
        st.session_state[tampered_key] = st.session_state.pop("ecdsa_tampered_message_next")
    elif tampered_key not in st.session_state:
        st.session_state[tampered_key] = msg + " [đã sửa]"

    col_tamper_input, col_tamper_button = st.columns([2, 1])

    with col_tamper_input:
        tampered = st.text_input(
            "🧪 Message sau khi bị sửa",
            max_chars=120,
            key=tampered_key,
        )

    with col_tamper_button:
        st.write("")
        st.write("")
        if st.button("🎯 Tìm message sửa chắc chắn bị từ chối", use_container_width=True):
            st.session_state.ecdsa_tampered_message_next = find_tampered_message_that_fails(
                Q,
                (r, s),
                msg,
            )
            st.rerun()

    valid_tampered = verify(ECDSA_PARAMS, Q, tampered.encode("utf-8"), (r, s))

    hash_original = hash_message_to_int(msg.encode("utf-8"), ECDSA_PARAMS.n)
    hash_tampered = hash_message_to_int(tampered.encode("utf-8"), ECDSA_PARAMS.n)

    compare_rows = [
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
    ]

    st.dataframe(
        pd.DataFrame(compare_rows),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("🧮 Xem các bước kiểm tra chữ ký với message đã sửa", expanded=False):
        render_ecdsa_verification_trace(
            ECDSA_PARAMS,
            Q,
            tampered.encode("utf-8"),
            (r, s),
        )

    if valid_tampered:
        st.warning(
            "Message đã sửa vẫn được chấp nhận trong toy demo. "
            "Nguyên nhân là n quá nhỏ, nên sau khi lấy H(m) mod n và kiểm tra x(P) mod n, "
            "một vài message khác nhau có thể vô tình thỏa điều kiện verify. "
            "Trong hệ thật với tham số lớn, xác suất kiểu này cực nhỏ."
        )
    else:
        st.success(
            "Message đã sửa bị từ chối. Đây là hành vi mong muốn: chữ ký ECDSA gắn với dữ liệu ban đầu."
        )

    render_learning_summary(
        "Chữ ký số ECDSA",
        [
            "ECDSA giúp chứng minh người ký có private key d mà không cần tiết lộ d.",
            "Key generation dùng Q = dG: private key là d, public key là Q.",
            "Signing dùng message, hash h, private key d và nonce k để tạo chữ ký (r, s).",
            "Verification dùng message, chữ ký (r, s) và public key Q để kiểm tra quan hệ P = u1G + u2Q.",
            "Nonce k cực kỳ nhạy cảm: dùng lại hoặc làm lộ k có thể làm lộ private key, nội dung này sẽ được mô phỏng ở Page 7.",
            "Trong Bitcoin case study, message không phải một câu text mà là dữ liệu giao dịch cần được ủy quyền.",
        ],
    )

# ============================================================
# PAGE 6
# ============================================================
def render_bitcoin_case_study_overview():
    """Giải thích phần ownership/UTXO trước khi vào transaction lab."""

    st.markdown("## 1. Bitcoin case study: ECDSA dùng để chứng minh quyền chi tiêu")

    st.markdown(
        """
        Trong mô hình giống Bitcoin, ví không “chứa coin” như tài khoản ngân hàng.

        Cách hiểu đúng hơn là:

        ```text
        Ví giữ private key.
        Blockchain/UTXO set ghi nhận các output chưa bị tiêu.
        Muốn tiêu một UTXO, người dùng phải đưa ra dữ liệu mở khóa hợp lệ.
        ```

        Với mô hình demo giống P2PKH:

        ```text
        UTXO bị khóa bởi public key hash.
        Người tiêu cung cấp public key + ECDSA signature.
        Node kiểm tra public key hash và chữ ký.
        ```
        """
    )

    st.info(
        "Có thể hiểu trực giác: quyền chi tiêu được truyền từ người này sang người khác bằng chữ ký số. "
        "Mỗi lần tiêu một UTXO, người chủ hiện tại ký dữ liệu giao dịch mới để chuyển giá trị sang điều kiện khóa mới."
    )

    ownership_rows = [
        {
            "Lớp": "Ví / Wallet",
            "Trong demo là gì?": "Bộ khóa của Alice, Bob, Mallory",
            "Ý nghĩa": "Ví giữ private key để ký, không trực tiếp chứa coin.",
        },
        {
            "Lớp": "UTXO",
            "Trong demo là gì?": "Một output chưa bị tiêu",
            "Ý nghĩa": "Đây là khoản tiền mô phỏng có thể được tiêu nếu mở khóa đúng.",
        },
        {
            "Lớp": "Locking condition",
            "Trong demo là gì?": "Public key hash",
            "Ý nghĩa": "Điều kiện khóa của UTXO: ai có public key tương ứng và chữ ký hợp lệ thì tiêu được.",
        },
        {
            "Lớp": "Unlocking data",
            "Trong demo là gì?": "Public key + ECDSA signature",
            "Ý nghĩa": "Dữ liệu người tiêu đưa vào input để chứng minh quyền chi tiêu.",
        },
        {
            "Lớp": "Node verification",
            "Trong demo là gì?": "Kiểm tra UTXO + public key hash + chữ ký",
            "Ý nghĩa": "Node chấp nhận hoặc từ chối giao dịch.",
        },
    ]

    st.dataframe(
        pd.DataFrame(ownership_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## 2. Luồng kiểm tra giao dịch trong mô phỏng")

    st.graphviz_chart("""
digraph {
    rankdir=LR;

    node [
        shape=box,
        style="rounded,filled",
        fillcolor="#F8FAFC",
        color="#64748B",
        fontname="Arial"
    ];

    edge [
        color="#475569",
        fontname="Arial"
    ];

    "Ví giữ\\nprivate key d"
        -> "Tạo public key\\nQ = dG";

    "Tạo public key\\nQ = dG"
        -> "Tính\\nPubKeyHash";

    "Tính\\nPubKeyHash"
        -> "UTXO bị khóa bởi\\nPubKeyHash";

    "Transaction chưa ký"
        -> "Ký bằng private key\\nECDSA signature";

    "Ký bằng private key\\nECDSA signature"
        -> "Unlocking data\\npublic key + signature";

    "UTXO bị khóa bởi\\nPubKeyHash"
        -> "Node verification";

    "Unlocking data\\npublic key + signature"
        -> "Node verification";

    "Node verification"
        -> "Accept / Reject";
}
""")

    st.caption(
        "Sơ đồ này là bản rút gọn của case study: ECDSA không mã hóa giao dịch, "
        "mà tạo chữ ký để chứng minh quyền tiêu một UTXO cụ thể."
    )

    st.markdown("## 3. Chữ ký số giải quyết phần nào, mạng node giải quyết phần nào?")

    st.markdown(
        """
        Một chữ ký hợp lệ chỉ chứng minh được:

        ```text
        Người ký có private key tương ứng với public key đang mở khóa UTXO.
        ```

        Nhưng chỉ chữ ký thôi chưa đủ để trả lời câu hỏi:

        ```text
        UTXO này đã bị tiêu trong một giao dịch khác trước đó chưa?
        ```

        Vì vậy, trong tinh thần Bitcoin, cần tách hai lớp:
        """
    )

    layer_rows = [
        {
            "Lớp": "Transaction validity",
            "Câu hỏi": "Giao dịch này có hợp lệ không?",
            "Node kiểm tra gì?": "UTXO tồn tại, chưa bị tiêu, public key hash khớp, chữ ký ECDSA hợp lệ.",
            "Project có mô phỏng?": "Có, trong Page 6.",
        },
        {
            "Lớp": "Shared transaction history",
            "Câu hỏi": "Toàn mạng đồng ý giao dịch nào xảy ra trước?",
            "Node/mạng cần gì?": "Giao dịch được công bố, đưa vào block, nối vào chain và được các node chấp nhận theo lịch sử chung.",
            "Project có mô phỏng?": "Không. Đây là phần consensus ngoài phạm vi ECC/ECDSA.",
        },
    ]

    st.dataframe(
        pd.DataFrame(layer_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.graphviz_chart("""
    digraph {
        rankdir=LR;

        node [
            shape=box,
            style="rounded,filled",
            fillcolor="#F8FAFC",
            color="#64748B",
            fontname="Arial"
        ];

        edge [
            color="#475569",
            fontname="Arial"
        ];

        "Transaction\\npublic data"
            -> "Node kiểm tra\\nUTXO + PubKeyHash + Signature";

        "Node kiểm tra\\nUTXO + PubKeyHash + Signature"
            -> "Valid transaction?";

        "Valid transaction?"
            -> "Đưa vào block\\ntrong mạng thật";

        "Đưa vào block\\ntrong mạng thật"
            -> "Lịch sử chung\\ncủa các node";

        "Lịch sử chung\\ncủa các node"
            -> "Double spend\\nbị loại";
    }
    """)

    st.caption(
        "Trong app này, ta mô phỏng lớp kiểm tra giao dịch hợp lệ. "
        "Phần block, chain, proof-of-work, consensus và lịch sử chung của toàn mạng được nhắc để hiểu đúng tinh thần Bitcoin, "
        "nhưng không triển khai vì nằm ngoài trọng tâm ECC/ECDSA."
    )

    st.markdown("## 4. Phòng lab tương tác")

    lab_rows = [
        {
            "Tab": "1️⃣ Ví & UTXO",
            "Dùng để làm gì?": "Xem ví Alice/Bob/Mallory và tạo UTXO demo.",
        },
        {
            "Tab": "2️⃣ Tạo giao dịch",
            "Dùng để làm gì?": "Chọn UTXO đầu vào, người nhận và amount để tạo transaction chưa ký.",
        },
        {
            "Tab": "3️⃣ Ký & kiểm tra",
            "Dùng để làm gì?": "Ký transaction bằng private key, node verify, rồi apply vào UTXO set.",
        },
        {
            "Tab": "4️⃣ Sửa phá / tấn công / tiêu hai lần",
            "Dùng để làm gì?": "Sửa amount, đổi receiver, thay public key, Mallory ký sai, hoặc thử double spend.",
        },
    ]

    st.dataframe(
        pd.DataFrame(lab_rows),
        use_container_width=True,
        hide_index=True,
    )


def demo_interactive_bitcoin_transaction_lab():
    st.title("6. Bitcoin case study: ECDSA mở khóa UTXO")

    render_page_intro(
        "ECDSA đi vào mô hình Bitcoin-like như thế nào?",
        "ECDSA dùng để chứng minh quyền tiêu một UTXO: người tiêu ký dữ liệu giao dịch bằng private key, còn node kiểm tra bằng public key và điều kiện khóa.",
        "Người dùng tự tạo UTXO, tạo transaction, ký, verify, apply vào UTXO set, rồi thử sửa transaction, sai khóa và double spend.",
    )

    st.warning(
        "Đây là mô hình giáo dục giống P2PKH, không phải Bitcoin thật. "
        "Demo không có Script đầy đủ, không có quy tắc ký thật của Bitcoin, không có đồng thuận mạng, "
        "không kết nối network và không dùng khóa thật."
    )

    render_term_notes([
        (
            "Wallet / Ví",
            "Trong demo, ví là bộ khóa của Alice, Bob, Mallory. Ví giữ private key để ký, không trực tiếp chứa coin."
        ),
        (
            "Node",
            "Máy/chương trình tham gia mạng Bitcoin. Node kiểm tra transaction, kiểm tra block và duy trì bản sao lịch sử hợp lệ theo luật mạng."
        ),
        (
            "Full node",
            "Node tự kiểm tra luật đồng thuận và transaction validity. Trong demo, ta chỉ mô phỏng một phần nhỏ vai trò kiểm tra transaction của node."
        ),
        (
            "UTXO",
            "Unspent Transaction Output: output chưa bị tiêu. Muốn tiêu phải tham chiếu đúng UTXO đó trong input của transaction mới."
        ),
        (
            "Input",
            "Phần của transaction dùng để tham chiếu UTXO cũ muốn tiêu. Input chứa OutPoint và dữ liệu mở khóa."
        ),
        (
            "Output",
            "Phần của transaction tạo ra UTXO mới. Output thường chứa số tiền và điều kiện khóa."
        ),
        (
            "OutPoint",
            "Địa chỉ của một UTXO cũ, thường gồm txid của transaction trước và vị trí output, gọi là vout."
        ),
        (
            "txid",
            "Mã định danh của transaction, thường được hiểu là hash của dữ liệu transaction. Trong demo là txid mô phỏng."
        ),
        (
            "vout",
            "Chỉ số vị trí của output trong transaction. Cặp txid:vout giúp xác định chính xác UTXO nào đang được tiêu."
        ),
        (
            "P2PKH",
            "Pay-to-Public-Key-Hash: kiểu khóa output truyền thống, trong đó UTXO bị khóa bởi mã băm của public key."
        ),
        (
            "PubKeyHash",
            "Mã băm của public key. Trong demo, UTXO khóa bằng PubKeyHash, người tiêu phải đưa public key khớp với hash này."
        ),
        (
            "Locking condition",
            "Điều kiện khóa của UTXO. Trong demo là PubKeyHash; trong Bitcoin thật thường được biểu diễn bằng script hoặc spending condition."
        ),
        (
            "Unlocking data",
            "Dữ liệu mở khóa trong input. Trong demo là public key + ECDSA signature."
        ),
        (
            "Script",
            "Cơ chế điều kiện chi tiêu trong Bitcoin thật. Demo này không triển khai Script đầy đủ, chỉ mô phỏng logic P2PKH ở mức giáo dục."
        ),
        (
            "Giao dịch chưa ký",
            "Transaction mới có input/output nhưng chưa có chữ ký mở khóa."
        ),
        (
            "Node verification",
            "Trong demo: node kiểm tra UTXO tồn tại, chưa bị tiêu, public key hash khớp và chữ ký ECDSA hợp lệ."
        ),
        (
            "Double spend",
            "Cố tiêu cùng một UTXO nhiều hơn một lần. Trong demo, UTXO set từ chối lần tiêu sau."
        ),
    ])

    render_bitcoin_case_study_overview()

    init_tx_lab_state()
    lab = st.session_state.tx_lab

    scenario_options = [
        "Kịch bản đúng: Alice trả Bob",
        "Sửa số tiền sau khi ký",
        "Đổi người nhận sang Mallory sau khi ký",
        "Mallory cố tiêu UTXO của Alice",
        "Thay public key mở khóa bằng của Mallory",
        "Tiêu cùng một UTXO hai lần",
        "Chế độ tự do",
    ]

    saved_scenario = lab.get("selected_scenario", "Kịch bản đúng: Alice trả Bob")
    if saved_scenario not in scenario_options:
        saved_scenario = "Kịch bản đúng: Alice trả Bob"

    scenario = st.selectbox(
        "🎬 Kịch bản hướng dẫn",
        scenario_options,
        index=scenario_options.index(saved_scenario),
    )
    lab["selected_scenario"] = scenario

    scenario_guides = {
        "Kịch bản đúng: Alice trả Bob": {
            "Mục tiêu": "Cho thấy flow hợp lệ: Alice có UTXO, tạo giao dịch trả Bob, ký bằng khóa Alice, node kiểm tra và chấp nhận.",
            "Các bước": [
                {"Tab": "1️⃣ Ví & UTXO", "Thao tác": "Tạo UTXO cho Alice, ví dụ amount = 10", "Kết quả mong đợi": "Bảng UTXO có một khoản thuộc về Alice"},
                {"Tab": "2️⃣ Tạo giao dịch", "Thao tác": "Chọn Alice là người gửi, chọn UTXO của Alice, chọn Bob là người nhận", "Kết quả mong đợi": "Có giao dịch nháp Alice → Bob"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Chọn người ký là Alice, bấm ký giao dịch", "Kết quả mong đợi": "Giao dịch có chữ ký và public key của Alice"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Bấm node kiểm tra giao dịch", "Kết quả mong đợi": "Node chấp nhận giao dịch"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Bấm gửi / áp dụng vào tập UTXO", "Kết quả mong đợi": "UTXO cũ của Alice bị tiêu, UTXO mới của Bob xuất hiện"},
            ],
            "Kết luận": "Alice chứng minh quyền tiêu UTXO bằng chữ ký ECDSA, không cần tiết lộ private key.",
        },
        "Sửa số tiền sau khi ký": {
            "Mục tiêu": "Cho thấy chữ ký gắn với dữ liệu transaction cụ thể. Sửa amount sau khi ký sẽ làm chữ ký cũ mất hiệu lực.",
            "Các bước": [
                {"Tab": "1️⃣ Ví & UTXO", "Thao tác": "Tạo UTXO cho Alice, ví dụ amount = 10", "Kết quả mong đợi": "Alice có UTXO chưa tiêu"},
                {"Tab": "2️⃣ Tạo giao dịch", "Thao tác": "Tạo transaction Alice → Bob", "Kết quả mong đợi": "Có giao dịch nháp"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Ký bằng Alice", "Kết quả mong đợi": "Giao dịch có chữ ký hợp lệ ban đầu"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Nhập số tiền mới, ví dụ đổi 10 thành 15, rồi bấm áp dụng", "Kết quả mong đợi": "Output amount bị thay đổi sau khi ký"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Bấm kiểm tra giao dịch đã bị sửa", "Kết quả mong đợi": "Node từ chối giao dịch"},
            ],
            "Kết luận": "ECDSA không ký một ý định mơ hồ, mà ký dữ liệu cụ thể. Đổi dữ liệu sau khi ký thì verify fail.",
        },
        "Đổi người nhận sang Mallory sau khi ký": {
            "Mục tiêu": "Cho thấy attacker không thể đổi người nhận sau khi transaction đã được ký.",
            "Các bước": [
                {"Tab": "1️⃣ Ví & UTXO", "Thao tác": "Tạo UTXO cho Alice", "Kết quả mong đợi": "Alice có UTXO chưa tiêu"},
                {"Tab": "2️⃣ Tạo giao dịch", "Thao tác": "Tạo transaction Alice → Bob", "Kết quả mong đợi": "Output ban đầu thuộc về Bob"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Ký bằng Alice", "Kết quả mong đợi": "Transaction Alice → Bob có chữ ký hợp lệ"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Bấm đổi người nhận sang Mallory", "Kết quả mong đợi": "Output bị đổi sang Mallory sau khi ký"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Bấm kiểm tra giao dịch đã bị sửa", "Kết quả mong đợi": "Node từ chối giao dịch"},
            ],
            "Kết luận": "Đổi receiver làm dữ liệu transaction thay đổi, nên chữ ký Alice tạo trước đó không còn hợp lệ.",
        },
        "Mallory cố tiêu UTXO của Alice": {
            "Mục tiêu": "Cho thấy người khác không thể dùng private key của mình để tiêu UTXO bị khóa bởi public key hash của Alice.",
            "Các bước": [
                {"Tab": "1️⃣ Ví & UTXO", "Thao tác": "Tạo UTXO cho Alice", "Kết quả mong đợi": "UTXO bị khóa bởi public key hash của Alice"},
                {"Tab": "2️⃣ Tạo giao dịch", "Thao tác": "Tạo transaction tiêu UTXO của Alice", "Kết quả mong đợi": "Có giao dịch nháp tham chiếu UTXO Alice"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Chọn người ký là Mallory rồi bấm ký", "Kết quả mong đợi": "Giao dịch có chữ ký/public key của Mallory"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Bấm node kiểm tra giao dịch", "Kết quả mong đợi": "Node từ chối giao dịch"},
            ],
            "Kết luận": "Mallory có thể ký bằng khóa của Mallory, nhưng public key hash của Mallory không khớp điều kiện khóa của UTXO Alice.",
        },
        "Thay public key mở khóa bằng của Mallory": {
            "Mục tiêu": "Cho thấy không thể thay public key trong unlocking data một cách tùy tiện.",
            "Các bước": [
                {"Tab": "1️⃣ Ví & UTXO", "Thao tác": "Tạo UTXO cho Alice", "Kết quả mong đợi": "UTXO khóa bởi public key hash của Alice"},
                {"Tab": "2️⃣ Tạo giao dịch", "Thao tác": "Tạo transaction Alice → Bob", "Kết quả mong đợi": "Có giao dịch nháp hợp lệ về mặt cấu trúc"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Ký bằng Alice", "Kết quả mong đợi": "Giao dịch có chữ ký và public key Alice"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Bấm thay khóa công khai mở khóa bằng của Mallory", "Kết quả mong đợi": "Unlocking public key bị đổi sang Mallory"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Bấm kiểm tra giao dịch đã bị sửa", "Kết quả mong đợi": "Node từ chối giao dịch"},
            ],
            "Kết luận": "Unlocking data phải khớp locking condition. Thay public key làm hash/public key không còn khớp với UTXO của Alice.",
        },
        "Tiêu cùng một UTXO hai lần": {
            "Mục tiêu": "Cho thấy vai trò của UTXO set trong chống double spend.",
            "Các bước": [
                {"Tab": "1️⃣ Ví & UTXO", "Thao tác": "Tạo UTXO cho Alice", "Kết quả mong đợi": "Alice có UTXO chưa tiêu"},
                {"Tab": "2️⃣ Tạo giao dịch", "Thao tác": "Tạo transaction Alice → Bob", "Kết quả mong đợi": "Có giao dịch nháp"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Ký bằng Alice", "Kết quả mong đợi": "Giao dịch đã ký hợp lệ"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Bấm thử tiêu hai lần giao dịch hiện tại", "Kết quả mong đợi": "Lần đầu được chấp nhận, lần hai bị từ chối"},
            ],
            "Kết luận": "Một UTXO chỉ được tiêu một lần. Sau lần tiêu đầu, UTXO không còn nằm trong trạng thái chưa tiêu.",
        },
        "Chế độ tự do": {
            "Mục tiêu": "Tự thử các thao tác để hiểu cơ chế UTXO, ECDSA và node verification.",
            "Các bước": [
                {"Tab": "1️⃣ Ví & UTXO", "Thao tác": "Tạo UTXO cho Alice/Bob/Mallory", "Kết quả mong đợi": "Có dữ liệu đầu vào để thử"},
                {"Tab": "2️⃣ Tạo giao dịch", "Thao tác": "Tạo transaction theo ý muốn", "Kết quả mong đợi": "Có giao dịch nháp"},
                {"Tab": "3️⃣ Ký & kiểm tra", "Thao tác": "Thử ký bằng đúng hoặc sai người", "Kết quả mong đợi": "Node chấp nhận hoặc từ chối theo điều kiện khóa"},
                {"Tab": "4️⃣ Sửa phá", "Thao tác": "Thử sửa amount, đổi receiver, thay public key hoặc double spend", "Kết quả mong đợi": "Quan sát node phản ứng"},
            ],
            "Kết luận": "Chế độ tự do dùng để tự kiểm tra hiểu biết sau khi đã đi qua các kịch bản mẫu.",
        },
    }

    with st.expander("✅ Hướng dẫn kịch bản đang chọn", expanded=True):
        guide = scenario_guides[scenario]

        st.markdown(f"**Mục tiêu:** {guide['Mục tiêu']}")
        st.dataframe(pd.DataFrame(guide["Các bước"]), use_container_width=True, hide_index=True)
        st.success(f"**Kết luận cần rút ra:** {guide['Kết luận']}")

        st.caption(
            "Gợi ý: nếu kết quả không giống kỳ vọng, hãy bấm “🧹 Reset phòng lab giao dịch” ở tab 1 rồi làm lại từ đầu."
        )

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

        st.caption(
            "Tab này dùng để kiểm tra các tình huống sai: sửa transaction sau khi ký, "
            "đổi người nhận, thay public key mở khóa, ký bằng Mallory hoặc thử tiêu hai lần cùng một UTXO."
        )

        # Cho phép Mallory ký giao dịch nháp ngay cả khi chưa có signed_tx.
        if lab["draft_tx"] is not None:
            with st.container(border=True):
                st.markdown("#### 🦹 Mallory cố ký giao dịch nháp")

                st.markdown(
                    "Nút này lấy giao dịch nháp hiện tại và ký bằng private key của Mallory. "
                    "Nếu giao dịch đang tiêu UTXO của Alice, node phải từ chối vì public key/hash của Mallory không khớp điều kiện khóa của Alice."
                )

                if st.button("🦹 Ký giao dịch nháp bằng Mallory", use_container_width=True):
                    sign_lab_tx("Mallory")
                    st.rerun()
        else:
            st.info("Chưa có giao dịch nháp. Qua tab 2 tạo giao dịch trước nếu muốn thử Mallory ký.")

        if lab["signed_tx"] is None:
            st.info(
                "Chưa có giao dịch đã ký để sửa phá. "
                "Qua tab 3 ký giao dịch trước, hoặc dùng nút Mallory bên trên nếu đã có giao dịch nháp."
            )
        else:
            render_current_tx("Giao dịch đã ký hiện tại", lab["signed_tx"])

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🔧 Sửa dữ liệu sau khi ký")

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
                st.markdown("#### 🧪 Kiểm tra / tiêu hai lần")

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
        "Bitcoin case study: ECDSA mở khóa UTXO",
        [
            "Ví không trực tiếp chứa coin; trong mô hình này, ví giữ private key để tạo chữ ký.",
            "UTXO set biểu diễn các output chưa bị tiêu, mỗi UTXO có một điều kiện khóa riêng.",
            "Trong mô hình giống P2PKH, UTXO bị khóa bởi public key hash; người tiêu cung cấp public key và ECDSA signature để mở khóa.",
            "Một giao dịch chỉ được chấp nhận khi UTXO tồn tại, chưa bị tiêu, public key hash khớp điều kiện khóa và chữ ký ECDSA hợp lệ.",
            "Sửa số tiền hoặc đổi người nhận sau khi ký làm dữ liệu transaction thay đổi, khiến chữ ký cũ không còn hợp lệ.",
            "Mallory không thể tiêu UTXO của Alice bằng khóa của mình, vì public key hash không khớp locking condition.",
            "Double spend bị từ chối vì cùng một UTXO không được tiêu hai lần trong UTXO set mô phỏng.",
            "Đây là case study của ECDSA trong Bitcoin, không phải mô phỏng đầy đủ Bitcoin protocol.",
        ],
    )


# ============================================================
# PAGE 7
# ============================================================
def demo_reused_nonce_attack():
    st.title("7. Nonce attack: khi ECDSA triển khai sai")

    render_page_intro(
        "ECDLP khó có đủ để bảo vệ private key không?",
        "Không đủ. Nếu ECDSA triển khai sai nonce k, attacker có thể khôi phục private key mà không cần giải ECDLP.",
        "Ta mô phỏng ba tình huống: dùng lại nonce, nonce bị lộ hoàn toàn, và rò rỉ một phần nonce ở mức ghi chú lý thuyết.",
    )

    st.warning(
        "Đây là mô phỏng giáo dục trên toy curve rất nhỏ. "
        "Page này không chứng minh ECDSA bị phá về mặt toán học; nó chứng minh rằng triển khai sai nonce có thể làm lộ private key."
    )

    render_term_notes([
        (
            "Nonce k",
            "Giá trị bí mật dùng một lần trong mỗi chữ ký ECDSA. Mỗi chữ ký phải dùng một k riêng và không được để lộ."
        ),
        (
            "Reused nonce",
            "Dùng cùng một nonce k để ký hai message khác nhau. Đây là lỗi triển khai rất nguy hiểm."
        ),
        (
            "Known nonce",
            "Nonce k của một chữ ký bị lộ hoàn toàn. Chỉ một chữ ký cũng đủ để khôi phục private key."
        ),
        (
            "Partial nonce leakage",
            "Nonce k không lộ toàn bộ, nhưng rò một phần qua nhiều chữ ký, ví dụ qua side-channel hoặc RNG yếu."
        ),
        (
            "Side-channel",
            "Kênh rò rỉ phụ như thời gian chạy, cache, điện năng hoặc lỗi triển khai."
        ),
        (
            "Lattice attack",
            "Nhóm kỹ thuật nâng cao có thể khai thác nhiều chữ ký với nonce bị rò một phần. Page này chỉ ghi chú, không demo."
        ),
    ])

    st.markdown("## 1. Thông điệp chính của page")

    thesis_rows = [
        {
            "Lớp bảo vệ": "ECDLP",
            "Nói gì?": "Biết G và Q = dG thì rất khó tìm lại d trên tham số thật.",
            "Page liên quan": "Page 4",
        },
        {
            "Lớp triển khai": "Nonce discipline",
            "Nói gì?": "ECDSA yêu cầu nonce k phải bí mật, không lặp lại và không rò rỉ.",
            "Page liên quan": "Page 7",
        },
        {
            "Bài học": "An toàn = toán học đúng + triển khai đúng",
            "Nói gì?": "Không cần phá ECDLP vẫn có thể lấy private key nếu nonce bị dùng sai.",
            "Page liên quan": "Page 7 -> Page 8",
        },
    ]

    st.dataframe(
        pd.DataFrame(thesis_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## 2. Chọn tham số mô phỏng")

    col_key, col_nonce = st.columns(2)

    with col_key:
        d_victim = int(st.number_input(
            "🔑 Private key nạn nhân d",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(3, ORDER_N - 1),
            help=(
                "Đây là private key mô phỏng của nạn nhân. "
                "Trong hệ thật, attacker không được biết d; mục tiêu của attack là khôi phục d."
            ),
        ))

    with col_nonce:
        k_reuse = int(st.number_input(
            "🎲 Nonce mô phỏng k",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(5, ORDER_N - 1),
            help=(
                "Nonce dùng khi ký. Nếu k bị dùng lại hoặc bị lộ, private key d có thể bị khôi phục."
            ),
        ))

    Q_victim = ECDSA_PARAMS.curve.scalar_mul(d_victim, ECDSA_PARAMS.G)

    key_rows = [
        {
            "Thành phần": "Private key d",
            "Giá trị": d_victim,
            "Attacker biết?": "Không",
            "Vai trò": "Khóa bí mật cần bảo vệ.",
        },
        {
            "Thành phần": "Public key Q = dG",
            "Giá trị": point_to_text(Q_victim),
            "Attacker biết?": "Có",
            "Vai trò": "Khóa công khai dùng để verify chữ ký.",
        },
        {
            "Thành phần": "Nonce k",
            "Giá trị": k_reuse,
            "Attacker biết?": "Tùy mode attack",
            "Vai trò": "Giá trị cực kỳ nhạy cảm trong ECDSA signing.",
        },
    ]

    st.dataframe(
        pd.DataFrame(key_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## 3. Chọn message và kiểu tấn công")

    col1, col2 = st.columns(2)

    with col1:
        msg1 = st.text_input(
            "Thông điệp 1",
            value="Thanh toan 1 BTC cho Alice",
            max_chars=120,
            help="Message thứ nhất. Trong Bitcoin case study, đây sẽ tương ứng với dữ liệu giao dịch được ký.",
        )

    with col2:
        msg2 = st.text_input(
            "Thông điệp 2",
            value="Thanh toan 2 BTC cho Bob",
            max_chars=120,
            help="Message thứ hai dùng cho reused nonce attack.",
        )

    attack_mode = st.radio(
        "Chọn kiểu tấn công nonce",
        [
            "Reused nonce: dùng lại k cho hai chữ ký",
            "Known nonce: nonce k bị lộ trong một chữ ký",
            "Partial nonce leakage: ghi chú lý thuyết",
        ],
        horizontal=False,
    )

    mode_rows = [
        {
            "Kiểu lỗi": "Reused nonce",
            "Attacker cần gì?": "Hai chữ ký khác message nhưng dùng cùng k",
            "Kết quả": "Khôi phục k rồi khôi phục d",
            "Demo?": "Có",
        },
        {
            "Kiểu lỗi": "Known nonce",
            "Attacker cần gì?": "Một chữ ký và nonce k bị lộ",
            "Kết quả": "Khôi phục d từ một chữ ký",
            "Demo?": "Có",
        },
        {
            "Kiểu lỗi": "Partial nonce leakage",
            "Attacker cần gì?": "Nhiều chữ ký với k bị rò một phần",
            "Kết quả": "Có thể khôi phục d bằng kỹ thuật nâng cao như lattice attack",
            "Demo?": "Không, chỉ ghi chú",
        },
    ]

    with st.expander("🧭 So sánh nhanh các kiểu lỗi nonce", expanded=False):
        st.dataframe(
            pd.DataFrame(mode_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("## 4. Chạy mô phỏng")

    if not st.button("⚡ Chạy mô phỏng tấn công", use_container_width=True):
        st.info("Chọn tham số và mode attack, rồi bấm nút để chạy mô phỏng.")
        render_learning_summary(
            "Nonce attack",
            [
                "ECDLP bảo vệ private key khỏi việc bị suy ngược từ public key Q.",
                "Nonce k trong ECDSA là lớp triển khai cực kỳ nhạy cảm.",
                "Nếu k bị dùng lại hoặc bị lộ, attacker có thể khôi phục private key bằng đại số modulo.",
                "Partial nonce leakage là hướng nâng cao: không demo lattice ở đây để giữ project đúng trọng tâm.",
            ],
        )
        return

    ok_nonce, nonce_msg = validate_nonce(k_reuse, ECDSA_PARAMS.n)

    if not ok_nonce:
        st.warning(nonce_msg)
        return

    if not msg1.strip():
        st.warning("Thông điệp 1 không nên để trống.")
        return

    if attack_mode == "Reused nonce: dùng lại k cho hai chữ ký":
        if not msg2.strip():
            st.warning("Thông điệp 2 không nên để trống khi chạy reused nonce attack.")
            return

        st.markdown("## 5. Reused nonce attack")

        st.markdown(
            """
            Khi cùng một nonce `k` được dùng để ký hai message khác nhau:

            """
        )

        st.latex(r"s_1 = k^{-1}(h_1 + r d) \pmod n")
        st.latex(r"s_2 = k^{-1}(h_2 + r d) \pmod n")

        st.markdown("Lấy hiệu hai phương trình, ta khử được phần chứa `d`:")

        st.latex(r"s_1 - s_2 = k^{-1}(h_1 - h_2) \pmod n")

        st.markdown("Từ đó khôi phục nonce:")

        st.latex(r"k' = (h_1 - h_2)(s_1 - s_2)^{-1} \pmod n")

        st.markdown("Sau khi biết `k`, khôi phục private key:")

        st.latex(r"d' = (s_1 k' - h_1)r^{-1} \pmod n")

        try:
            r1, s1 = sign(ECDSA_PARAMS, d_victim, msg1.encode("utf-8"), k=k_reuse)
            r2, s2 = sign(ECDSA_PARAMS, d_victim, msg2.encode("utf-8"), k=k_reuse)
        except Exception as exc:
            st.warning(
                f"Không tạo được chữ ký với k = {k_reuse}: {exc}. "
                "Toy curve nhỏ nên có thể gặp edge-case như r = 0, s = 0. "
                "App sẽ thử tự tìm một nonce hợp lệ khác."
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

        st.markdown("### 5.1. Hai chữ ký dùng cùng nonce")

        signature_rows = [
            {
                "Message": "msg1",
                "Nội dung": msg1,
                "h = H(m) mod n": h1,
                "r": r1,
                "s": s1,
                "nonce k": k_reuse,
            },
            {
                "Message": "msg2",
                "Nội dung": msg2,
                "h = H(m) mod n": h2,
                "r": r2,
                "s": s2,
                "nonce k": k_reuse,
            },
        ]

        st.dataframe(
            pd.DataFrame(signature_rows),
            use_container_width=True,
            hide_index=True,
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
            st.info(
                "Đây là edge-case của toy curve nhỏ hoặc message hiện tại. "
                "Hãy đổi message hoặc đổi nonce k rồi chạy lại."
            )
            return

        s_diff = (s1 - s2) % ECDSA_PARAMS.n
        h_diff = (h1 - h2) % ECDSA_PARAMS.n
        s_diff_inv = safe_mod_inverse(s1 - s2, ECDSA_PARAMS.n)
        r_inv = safe_mod_inverse(r1, ECDSA_PARAMS.n)

        if s_diff_inv is None or r_inv is None:
            st.warning("Mẫu số không khả nghịch modulo n, không thể khôi phục trong mẫu hiện tại.")
            return

        k_recovered = ((h1 - h2) * s_diff_inv) % ECDSA_PARAMS.n
        d_recovered = ((s1 * k_recovered - h1) * r_inv) % ECDSA_PARAMS.n

        st.markdown("### 5.2. Trace khôi phục k và d")

        trace_rows = [
            {
                "Bước": "Tính hiệu hash",
                "Công thức": "h1 - h2 mod n",
                "Giá trị": h_diff,
                "Ý nghĩa": "Phần khác nhau giữa hai message.",
            },
            {
                "Bước": "Tính hiệu chữ ký",
                "Công thức": "s1 - s2 mod n",
                "Giá trị": s_diff,
                "Ý nghĩa": "Mẫu số để khôi phục nonce.",
            },
            {
                "Bước": "Nghịch đảo hiệu chữ ký",
                "Công thức": "(s1 - s2)^(-1) mod n",
                "Giá trị": s_diff_inv,
                "Ý nghĩa": "Phép chia trong modulo n.",
            },
            {
                "Bước": "Khôi phục nonce",
                "Công thức": "k' = (h1 - h2)(s1 - s2)^(-1) mod n",
                "Giá trị": k_recovered,
                "Ý nghĩa": "Nonce ban đầu bị khôi phục.",
            },
            {
                "Bước": "Nghịch đảo r",
                "Công thức": "r^(-1) mod n",
                "Giá trị": r_inv,
                "Ý nghĩa": "Chuẩn bị khôi phục private key.",
            },
            {
                "Bước": "Khôi phục private key",
                "Công thức": "d' = (s1*k' - h1)r^(-1) mod n",
                "Giá trị": d_recovered,
                "Ý nghĩa": "Private key bị suy ra từ hai chữ ký lỗi.",
            },
        ]

        st.dataframe(
            pd.DataFrame(trace_rows),
            use_container_width=True,
            hide_index=True,
        )

        result_rows = [
            {"Giá trị": "k ban đầu", "Kết quả": k_reuse},
            {"Giá trị": "k khôi phục", "Kết quả": k_recovered},
            {"Giá trị": "d ban đầu", "Kết quả": d_victim},
            {"Giá trị": "d khôi phục", "Kết quả": d_recovered},
        ]

        st.dataframe(
            pd.DataFrame(result_rows),
            use_container_width=True,
            hide_index=True,
        )

        if k_recovered == k_reuse and d_recovered == d_victim:
            st.success(
                "🎯 Tấn công thành công: từ hai chữ ký dùng cùng nonce, attacker khôi phục được cả k và private key d."
            )
        else:
            st.error(
                "Kết quả không khớp. Đây có thể là edge-case của toy curve hoặc tham số hiện tại."
            )

    elif attack_mode == "Known nonce: nonce k bị lộ trong một chữ ký":
        st.markdown("## 5. Known nonce attack")

        st.markdown(
            """
            Với một chữ ký ECDSA:

            """
        )

        st.latex(r"s = k^{-1}(h + rd) \pmod n")

        st.markdown("Nếu attacker biết `k`, chỉ cần biến đổi đại số:")

        st.latex(r"d' = (s k - h)r^{-1} \pmod n")

        try:
            r, s = sign(ECDSA_PARAMS, d_victim, msg1.encode("utf-8"), k=k_reuse)
        except Exception as exc:
            st.warning(
                f"Không tạo được chữ ký với k = {k_reuse}: {exc}. "
                "App sẽ thử tự tìm một nonce hợp lệ khác."
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

        st.markdown("### 5.1. Một chữ ký có nonce bị lộ")

        known_rows = [
            {
                "Message": msg1,
                "h = H(m) mod n": h,
                "r": r,
                "s": s,
                "nonce k bị lộ": k_reuse,
            }
        ]

        st.dataframe(
            pd.DataFrame(known_rows),
            use_container_width=True,
            hide_index=True,
        )

        r_inv = safe_mod_inverse(r, ECDSA_PARAMS.n)

        if r_inv is None:
            st.warning("Không thể khôi phục vì r không có nghịch đảo modulo n.")
            return

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

        st.markdown("### 5.2. Trace khôi phục private key")

        trace_rows = [
            {
                "Bước": "Tính s*k - h",
                "Công thức": "s*k - h mod n",
                "Giá trị": (s * k_reuse - h) % ECDSA_PARAMS.n,
                "Ý nghĩa": "Tách phần chứa r*d từ công thức ký.",
            },
            {
                "Bước": "Tính nghịch đảo của r",
                "Công thức": "r^(-1) mod n",
                "Giá trị": r_inv,
                "Ý nghĩa": "Dùng để chia cho r trong modulo n.",
            },
            {
                "Bước": "Khôi phục private key",
                "Công thức": "d' = (s*k - h)r^(-1) mod n",
                "Giá trị": d_recovered,
                "Ý nghĩa": "Private key bị suy ra từ một chữ ký nếu nonce k bị lộ.",
            },
        ]

        st.dataframe(
            pd.DataFrame(trace_rows),
            use_container_width=True,
            hide_index=True,
        )

        result_rows = [
            {"Giá trị": "d ban đầu", "Kết quả": d_victim},
            {"Giá trị": "d khôi phục", "Kết quả": d_recovered},
        ]

        st.dataframe(
            pd.DataFrame(result_rows),
            use_container_width=True,
            hide_index=True,
        )

        if d_recovered == d_victim:
            st.success(
                "🎯 Tấn công thành công: chỉ cần biết nonce k của một chữ ký, attacker khôi phục được private key d."
            )
        else:
            st.error("Kết quả không khớp. Đây có thể là edge-case của toy curve.")

    elif attack_mode == "Partial nonce leakage: ghi chú lý thuyết":
        st.markdown("## 5. Partial nonce leakage")

        st.info(
            "Partial nonce leakage là trường hợp nonce k không bị lộ toàn bộ, "
            "nhưng một phần thông tin về k bị rò qua nhiều chữ ký."
        )

        leakage_rows = [
            {
                "Nguồn rò rỉ": "RNG yếu hoặc bị lệch",
                "Ví dụ": "Nonce không thật sự ngẫu nhiên, có bias hoặc lặp mẫu.",
                "Rủi ro": "Nhiều chữ ký có nonce yếu có thể làm lộ private key.",
            },
            {
                "Nguồn rò rỉ": "Timing side-channel",
                "Ví dụ": "Thời gian chạy phụ thuộc vào bit bí mật của k.",
                "Rủi ro": "Attacker đo thời gian để suy ra một phần nonce.",
            },
            {
                "Nguồn rò rỉ": "Cache / power side-channel",
                "Ví dụ": "Mẫu truy cập bộ nhớ hoặc điện năng tiết lộ một phần quá trình tính toán.",
                "Rủi ro": "Có thể gom nhiều chữ ký để tấn công nâng cao.",
            },
            {
                "Nguồn rò rỉ": "Lattice attack",
                "Ví dụ": "Dùng nhiều chữ ký với một phần nonce bị biết hoặc bị bias.",
                "Rủi ro": "Có thể khôi phục private key trong một số điều kiện.",
            },
        ]

        st.dataframe(
            pd.DataFrame(leakage_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.warning(
            "App không demo lattice attack vì đây là chủ đề cryptanalysis nâng cao. "
            "Trong project này, chỉ cần hiểu bài học chính: nonce k không được lặp, không được lộ và không được rò một phần."
        )

        st.markdown("### Vì sao không demo lattice ở đây?")

        reason_rows = [
            {
                "Lý do": "Lệch trọng tâm",
                "Giải thích": "Đề tài chính là ECC, ECDLP, ECDSA và Bitcoin case study; lattice attack sẽ kéo project sang cryptanalysis nâng cao.",
            },
            {
                "Lý do": "Cần nhiều nền toán hơn",
                "Giải thích": "Lattice attack cần kiến thức về lattice reduction, ví dụ LLL/BKZ.",
            },
            {
                "Lý do": "Dễ làm người xem quá tải",
                "Giải thích": "Demo reused nonce và known nonce đã đủ chứng minh nonce discipline quan trọng.",
            },
        ]

        st.dataframe(
            pd.DataFrame(reason_rows),
            use_container_width=True,
            hide_index=True,
        )

    render_learning_summary(
        "Nonce attack",
        [
            "Page 4 cho thấy ECDLP khó: biết Q rất khó suy ra d.",
            "Page 7 cho thấy một hướng khác: không cần giải ECDLP, chỉ cần ECDSA triển khai sai nonce là private key có thể bị lộ.",
            "Reused nonce: dùng cùng k cho hai message khác nhau có thể khôi phục k rồi khôi phục private key d.",
            "Known nonce: nếu k của một chữ ký bị lộ, private key d có thể bị khôi phục ngay từ công thức ECDSA.",
            "Partial nonce leakage: k chỉ rò một phần nhưng qua nhiều chữ ký vẫn có thể nguy hiểm, thường liên quan đến side-channel và lattice attack.",
            "Page 8 sẽ nói cách phòng thủ: nonce discipline, RFC6979-style, constant-time và dùng thư viện mật mã trưởng thành.",
        ],
    )

def render_ecdsa_defense_checklist_tab():
    st.markdown("## 1. Phòng thủ triển khai ECDSA")

    st.markdown(
        """
        Page 7 cho thấy: **không cần phá ECDLP**, chỉ cần nonce `k` bị dùng sai là private key có thể bay màu.

        Vì vậy, khi triển khai ECDSA thật, câu hỏi không chỉ là:

        ```text
        Toán học có đúng không?
        ```

        mà còn là:

        ```text
        Nonce có an toàn không?
        Code có rò thời gian không?
        Có dùng thư viện đáng tin không?
        ```
        """
    )

    threat_rows = [
        {
            "Mối đe dọa": "Attacker thấy nhiều chữ ký",
            "Liên quan": "Reused nonce, biased nonce, partial leakage",
            "Phòng thủ": "RFC6979/CSPRNG tốt, không reuse nonce",
        },
        {
            "Mối đe dọa": "Attacker đo thời gian chạy",
            "Liên quan": "Timing side-channel",
            "Phòng thủ": "Constant-time implementation",
        },
        {
            "Mối đe dọa": "Attacker khai thác lỗi tự viết crypto",
            "Liên quan": "Sai edge-case, sai validate, sai randomness",
            "Phòng thủ": "Dùng thư viện trưởng thành, test vector, audit",
        },
    ]

    st.dataframe(
        pd.DataFrame(threat_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 🧪 Checklist rủi ro triển khai")

    col1, col2 = st.columns(2)

    with col1:
        nonce_strategy = st.radio(
            "Cách sinh nonce k",
            [
                "RFC6979-style deterministic nonce",
                "Random nonce từ CSPRNG tốt",
                "Random thường / seed yếu",
                "Cố định hoặc có thể dùng lại k",
            ],
            index=0,
            help="Trong ECDSA, nonce k phải bí mật, không lặp lại và không được đoán được.",
            key="defense_nonce_strategy",
        )

        no_reuse_policy = st.checkbox(
            "Có cơ chế đảm bảo không reuse nonce",
            value=True,
            key="defense_no_reuse_policy",
        )

        test_vectors = st.checkbox(
            "Có test vector / kiểm thử chữ ký",
            value=True,
            key="defense_test_vectors",
        )

    with col2:
        constant_time = st.checkbox(
            "Triển khai constant-time cho phần xử lý bí mật",
            value=False,
            key="defense_constant_time",
        )

        side_channel_review = st.checkbox(
            "Có xem xét side-channel như timing/cache/power",
            value=False,
            key="defense_side_channel",
        )

        library_choice = st.radio(
            "Cách triển khai",
            [
                "Dùng thư viện mật mã trưởng thành",
                "Tự viết để học, không dùng production",
                "Tự viết và định dùng production",
            ],
            index=0,
            key="defense_library_choice",
        )

        deployment_context = st.radio(
            "Mục tiêu sử dụng",
            [
                "Toy demo để học",
                "Prototype nội bộ",
                "Production / ví thật / hệ thống thật",
            ],
            index=0,
            key="defense_deployment_context",
            help="Cùng một lựa chọn kỹ thuật nhưng rủi ro rất khác nhau tùy dùng để học hay dùng trong hệ thật.",
        )

        external_audit = st.checkbox(
            "Có review/audit độc lập nếu dùng production",
            value=False,
            key="defense_external_audit",
        )

        risk_score = 0
        risk_notes = []
        fatal_findings = []
        must_fix = []

        # ---------------- NONCE RISK ----------------
        if nonce_strategy == "RFC6979-style deterministic nonce":
            risk_score += 5
            risk_notes.append("RFC6979-style giúp giảm phụ thuộc vào nguồn random bên ngoài.")
        elif nonce_strategy == "Random nonce từ CSPRNG tốt":
            risk_score += 15
            risk_notes.append("Random nonce có thể ổn nếu CSPRNG thật sự tốt và không bị lệch.")
        elif nonce_strategy == "Random thường / seed yếu":
            risk_score += 45
            risk_notes.append("Random yếu hoặc seed yếu có thể làm nonce bị đoán hoặc có bias.")
            must_fix.append("Thay random thường/seed yếu bằng RFC6979-style hoặc CSPRNG đạt chuẩn.")
            if deployment_context == "Production / ví thật / hệ thống thật":
                fatal_findings.append("Production không được dùng random thường hoặc seed yếu cho nonce ECDSA.")
        elif nonce_strategy == "Cố định hoặc có thể dùng lại k":
            risk_score += 90
            risk_notes.append("Dùng lại nonce là lỗi nghiêm trọng, có thể làm lộ private key.")
            fatal_findings.append("Nonce cố định hoặc có thể bị reuse: private key có thể bị khôi phục.")
            must_fix.append("Bắt buộc sửa nonce generation trước mọi thứ khác.")

        if not no_reuse_policy:
            risk_score += 35
            risk_notes.append("Không có cơ chế chống reuse nonce là rủi ro lớn.")
            must_fix.append("Thêm cơ chế đảm bảo mỗi chữ ký không dùng lại nonce với message khác.")

        # ---------------- IMPLEMENTATION RISK ----------------
        if library_choice == "Dùng thư viện mật mã trưởng thành":
            risk_notes.append("Dùng thư viện trưởng thành là hướng đúng cho hệ thật.")
        elif library_choice == "Tự viết để học, không dùng production":
            risk_score += 10
            risk_notes.append("Toy implementation dùng để học thì ổn, miễn là không dùng cho sản phẩm thật.")
        elif library_choice == "Tự viết và định dùng production":
            risk_score += 75
            risk_notes.append("Tự viết crypto production là rủi ro cực cao nếu không có audit nghiêm túc.")
            fatal_findings.append("Tự viết ECDSA production mà không có audit là lựa chọn nguy hiểm.")
            must_fix.append("Không dùng toy/self-written crypto cho production; chuyển sang thư viện trưởng thành.")

        # Constant-time nên xét cùng library_choice.
        if library_choice == "Dùng thư viện mật mã trưởng thành":
            if not constant_time:
                risk_score += 10
                risk_notes.append(
                    "Nếu dùng thư viện trưởng thành, cần kiểm tra thư viện đó có cam kết constant-time cho phần xử lý bí mật hay không."
                )
                must_fix.append("Kiểm tra tài liệu thư viện về constant-time và side-channel hardening.")
        else:
            if not constant_time:
                risk_score += 25
                risk_notes.append("Tự viết mà không constant-time có thể rò thông tin qua timing side-channel.")
                must_fix.append("Không tự viết scalar multiplication/signing phụ thuộc dữ liệu bí mật theo thời gian chạy.")

        if not side_channel_review:
            risk_score += 15
            risk_notes.append("Không xem xét side-channel khiến hệ thống dễ bị tấn công ngoài mô hình toán học.")
            if deployment_context == "Production / ví thật / hệ thống thật":
                must_fix.append("Production cần review side-channel: timing, cache, power, memory access.")

        if not test_vectors:
            risk_score += 10
            risk_notes.append("Thiếu test vector làm tăng nguy cơ sai implementation.")
            must_fix.append("Thêm test vector chuẩn và test edge-case cho signing/verification.")

        if deployment_context == "Production / ví thật / hệ thống thật":
            risk_score += 15
            risk_notes.append("Production có tiêu chuẩn cao hơn toy demo/prototype.")
            if not external_audit:
                risk_score += 25
                risk_notes.append("Production crypto nên có review/audit độc lập.")
                must_fix.append("Cần review/audit độc lập trước khi dùng trong hệ thật.")

        elif deployment_context == "Prototype nội bộ":
            risk_score += 5
            risk_notes.append("Prototype nội bộ vẫn cần tránh thói quen nguy hiểm, nhất là nonce yếu hoặc self-written crypto.")

        elif deployment_context == "Toy demo để học":
            risk_notes.append("Toy demo để học có thể chấp nhận đơn giản hóa, miễn là ghi rõ không dùng production.")

        risk_score = min(risk_score, 100)

        if fatal_findings:
            with st.expander("🚨 Lỗi chí mạng cần sửa ngay", expanded=True):
                for item in fatal_findings:
                    st.error(item)

        if must_fix:
            with st.expander("🛠️ Việc nên sửa trước", expanded=True):
                for item in must_fix:
                    st.write(f"- {item}")

        # ---------------- RISK GATES ----------------
        if fatal_findings:
            verdict = "🚨 Critical: lỗi chí mạng"
            verdict_msg = "Có lỗi thuộc nhóm một phát có thể làm lộ private key. Phải sửa trước khi bàn đến điểm số."
            risk_score = max(risk_score, 90)
        elif risk_score >= 80:
            verdict = "🚨 Rủi ro cực cao"
            verdict_msg = "Thiết kế này có khả năng làm lộ private key nếu dùng trong hệ thật."
        elif risk_score >= 50:
            verdict = "⚠️ Rủi ro cao"
            verdict_msg = "Cần sửa nghiêm túc trước khi nghĩ đến môi trường thật."
        elif risk_score >= 25:
            verdict = "🟡 Rủi ro trung bình"
            verdict_msg = "Có vài điểm ổn, nhưng vẫn còn lỗ hổng engineering."
        else:
            verdict = "🟢 Rủi ro thấp trong cấu hình này"
            verdict_msg = "Cấu hình nhìn hợp lý hơn, nhưng vẫn cần audit nếu là production."

    col_metric1, col_metric2 = st.columns(2)

    with col_metric1:
        st.metric("Điểm rủi ro minh họa", f"{risk_score}/100")

    with col_metric2:
        st.metric("Đánh giá", verdict)

    if risk_score >= 50:
        st.error(verdict_msg)
    elif risk_score >= 25:
        st.warning(verdict_msg)
    else:
        st.success(verdict_msg)

    if risk_notes:
        with st.expander("🔍 Vì sao app đánh giá như vậy?", expanded=True):
            for note in risk_notes:
                st.write(f"- {note}")

    st.markdown("### Bảng nguyên tắc phòng thủ")

    defense_rows = [
        {
            "Nguyên tắc": "Không reuse nonce k",
            "Nếu làm sai thì sao?": "Hai chữ ký dùng cùng k có thể làm lộ k và private key d.",
            "Liên hệ": "Page 7 — reused nonce attack",
        },
        {
            "Nguyên tắc": "Không để lộ nonce k",
            "Nếu làm sai thì sao?": "Chỉ một chữ ký với known nonce cũng có thể làm lộ d.",
            "Liên hệ": "Page 7 — known nonce attack",
        },
        {
            "Nguyên tắc": "RFC6979-style deterministic nonce",
            "Nếu làm sai thì sao?": "Random yếu hoặc bị bias có thể tạo nonce dễ đoán.",
            "Liên hệ": "Giảm phụ thuộc vào RNG bên ngoài",
        },
        {
            "Nguyên tắc": "Constant-time implementation",
            "Nếu làm sai thì sao?": "Thời gian chạy có thể rò bit bí mật.",
            "Liên hệ": "Timing side-channel",
        },
        {
            "Nguyên tắc": "Side-channel awareness",
            "Nếu làm sai thì sao?": "Cache, power, timing có thể rò một phần nonce/private key.",
            "Liên hệ": "Partial nonce leakage",
        },
        {
            "Nguyên tắc": "Dùng thư viện trưởng thành",
            "Nếu làm sai thì sao?": "Toy crypto dễ sai ở edge-case, validation, timing và randomness.",
            "Liên hệ": "Secure engineering",
        },
    ]

    st.dataframe(
        pd.DataFrame(defense_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "Checklist này không phải security audit thật. "
        "Nó chỉ giúp người học nối Page 7 với thực tế triển khai: ECDSA an toàn không chỉ vì ECDLP khó, "
        "mà còn vì nonce và implementation phải đúng kỷ luật."
    )

def render_shamir_optimization_tab():
    st.markdown("## 2. Shamir's trick: tối ưu bước verify ECDSA")

    st.markdown(
        """
        Trong ECDSA verification, ta cần tính:

        """
    )

    st.latex(r"P = u_1G + u_2Q")

    st.markdown(
        """
        Cách trực tiếp:

        ```text
        tính u1G riêng
        tính u2Q riêng
        cộng hai điểm lại
        ```

        Shamir's trick tối ưu bằng cách xử lý hai phép nhân điểm cùng lúc.
        Mục tiêu là giảm số phép toán điểm trong bước verify.

        **Quan trọng:** đây là tối ưu hiệu năng, không phải cơ chế bảo mật chính.
        """
    )

    st.warning(
        "Shamir's trick không làm ECDSA an toàn hơn trước nonce attack. "
        "Nó chỉ giúp tính u1G + u2Q hiệu quả hơn trong verification."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        d_for_q = int(st.number_input(
            "Private key mô phỏng để tạo Q = dG",
            min_value=1,
            max_value=ORDER_N - 1,
            value=min(5, ORDER_N - 1),
            key="shamir_d_for_q",
        ))

    with col2:
        u1_demo = int(st.number_input(
            "Hệ số u1",
            min_value=1,
            value=13,
            key="shamir_u1",
        ))

    with col3:
        u2_demo = int(st.number_input(
            "Hệ số u2",
            min_value=1,
            value=19,
            key="shamir_u2",
        ))

    Q_demo = ECDSA_PARAMS.curve.scalar_mul(d_for_q, ECDSA_PARAMS.G)

    setup_rows = [
        {
            "Thành phần": "G",
            "Giá trị": point_to_text(ECDSA_PARAMS.G),
            "Ý nghĩa": "Điểm sinh cố định.",
        },
        {
            "Thành phần": "Q = dG",
            "Giá trị": point_to_text(Q_demo),
            "Ý nghĩa": "Public key mô phỏng dùng trong verify.",
        },
        {
            "Thành phần": "u1",
            "Giá trị": u1_demo,
            "Ý nghĩa": "Hệ số phụ thuộc vào hash message trong ECDSA verify.",
        },
        {
            "Thành phần": "u2",
            "Giá trị": u2_demo,
            "Ý nghĩa": "Hệ số phụ thuộc vào chữ ký r trong ECDSA verify.",
        },
    ]

    st.dataframe(
        pd.DataFrame(setup_rows),
        use_container_width=True,
        hide_index=True,
    )

    if st.button("📊 So sánh cách trực tiếp và Shamir's trick", use_container_width=True, key="run_shamir_page8"):
        try:
            ECDSA_PARAMS.curve.reset_counters()
            p_naive = naive_mul_add(
                ECDSA_PARAMS.curve,
                u1_demo,
                ECDSA_PARAMS.G,
                u2_demo,
                Q_demo,
            )
            naive_add = ECDSA_PARAMS.curve.add_count
            naive_double = ECDSA_PARAMS.curve.double_count

            ECDSA_PARAMS.curve.reset_counters()
            p_shamir = shamir_mul(
                ECDSA_PARAMS.curve,
                u1_demo,
                ECDSA_PARAMS.G,
                u2_demo,
                Q_demo,
            )
            shamir_add = ECDSA_PARAMS.curve.add_count
            shamir_double = ECDSA_PARAMS.curve.double_count

        except Exception as exc:
            st.error(f"Lỗi khi chạy so sánh Shamir: {exc}")
            return

        result_rows = [
            {
                "Cách làm": "Trực tiếp",
                "Kết quả P": point_to_text(p_naive),
                "Cộng điểm": naive_add,
                "Nhân đôi điểm": naive_double,
                "Tổng phép toán đếm được": naive_add + naive_double,
            },
            {
                "Cách làm": "Shamir's trick",
                "Kết quả P": point_to_text(p_shamir),
                "Cộng điểm": shamir_add,
                "Nhân đôi điểm": shamir_double,
                "Tổng phép toán đếm được": shamir_add + shamir_double,
            },
        ]

        result_df = pd.DataFrame(result_rows)

        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True,
        )

        chart_rows = [
            {
                "Cách làm": "Trực tiếp",
                "Phép toán": "Cộng điểm",
                "Số lượng": naive_add,
            },
            {
                "Cách làm": "Trực tiếp",
                "Phép toán": "Nhân đôi điểm",
                "Số lượng": naive_double,
            },
            {
                "Cách làm": "Shamir's trick",
                "Phép toán": "Cộng điểm",
                "Số lượng": shamir_add,
            },
            {
                "Cách làm": "Shamir's trick",
                "Phép toán": "Nhân đôi điểm",
                "Số lượng": shamir_double,
            },
        ]

        fig = px.bar(
            pd.DataFrame(chart_rows),
            x="Cách làm",
            y="Số lượng",
            color="Phép toán",
            barmode="group",
            text_auto=True,
            title="So sánh số phép toán điểm",
        )

        fig.update_layout(
            height=520,
            xaxis_title="Cách làm",
            yaxis_title="Số phép toán",
        )

        st.plotly_chart(fig, use_container_width=True)

        if p_naive == p_shamir:
            st.success(
                "Hai cách cho cùng kết quả P. Shamir's trick là tối ưu cách tính, không đổi ý nghĩa toán học."
            )
        else:
            st.error(
                "Hai cách cho kết quả khác nhau. Cần kiểm tra implementation của naive_mul_add hoặc shamir_mul."
            )

        naive_total = naive_add + naive_double
        shamir_total = shamir_add + shamir_double

        if shamir_total < naive_total:
            saved = naive_total - shamir_total
            st.info(f"Trong lượt chạy này, Shamir's trick giảm được {saved} phép toán đếm được.")
        elif shamir_total == naive_total:
            st.info(
                "Trong lượt chạy này, hai cách có tổng phép toán bằng nhau. "
                "Với tham số khác, Shamir's trick có thể thể hiện lợi thế rõ hơn."
            )
        else:
            st.warning(
                "Trong lượt chạy này, Shamir's trick không ít phép toán hơn theo bộ đếm toy. "
                "Điều này có thể xảy ra với tham số nhỏ hoặc implementation demo."
            )

# ============================================================
# PAGE 8
# ============================================================

def demo_nonce_defense_notes():
    st.title("8. Phòng thủ và tối ưu")

    render_page_intro(
        "Muốn dùng ECDSA thật thì cần kỷ luật triển khai gì?",
        "Page 7 cho thấy nonce sai có thể làm lộ private key. Page này nối phần mật mã học với secure engineering và tối ưu verification.",
        "Tab 1 là checklist phòng thủ triển khai ECDSA; Tab 2 là demo Shamir's trick để tối ưu phép tính u1G + u2Q trong verification.",
    )

    st.warning(
        "Page này không biến toy code thành production crypto. "
        "Nó chỉ cho thấy những nguyên tắc engineering cần nhớ khi đi từ công thức ECDSA sang hệ thống thật."
    )

    render_term_notes([
        (
            "Nonce discipline",
            "Kỷ luật quản lý nonce trong ECDSA: nonce k phải không lặp lại, không bị lộ, không dễ đoán và không bị bias."
        ),
        (
            "RFC6979-style",
            "Cách sinh nonce xác định từ private key và message, giúp giảm rủi ro do nguồn random yếu hoặc bị lỗi."
        ),
        (
            "CSPRNG",
            "Cryptographically Secure Pseudo-Random Number Generator: bộ sinh số ngẫu nhiên đủ mạnh cho mật mã. Random thường không đủ an toàn để sinh nonce/khóa."
        ),
        (
            "Threat model",
            "Mô hình mối đe dọa: xác định attacker có thể quan sát gì, đo gì, khai thác gì, ví dụ nhiều chữ ký, timing, cache hoặc lỗi tự viết crypto."
        ),
        (
            "Constant-time",
            "Cách viết code sao cho thời gian chạy không phụ thuộc vào dữ liệu bí mật như private key d hoặc nonce k."
        ),
        (
            "Side-channel",
            "Kênh rò rỉ phụ ngoài output chính, ví dụ thời gian chạy, cache, điện năng, mẫu truy cập bộ nhớ hoặc log/debug."
        ),
        (
            "Partial nonce leakage",
            "Nonce k không bị lộ toàn bộ, nhưng rò một phần qua nhiều chữ ký. Trường hợp này vẫn có thể nguy hiểm, nhất là khi kết hợp với các tấn công nâng cao."
        ),
        (
            "Test vector",
            "Bộ input-output chuẩn dùng để kiểm tra implementation. Ví dụ: private key, message, nonce và chữ ký kỳ vọng."
        ),
        (
            "Security audit",
            "Quá trình review độc lập để tìm lỗi thiết kế, lỗi implementation, lỗi side-channel, lỗi dependency hoặc lỗi cấu hình bảo mật."
        ),
        (
            "Risk gate / Fatal finding",
            "Điều kiện lỗi chí mạng. Nếu gặp lỗi như reuse nonce hoặc tự viết crypto production không audit, app phải báo critical ngay thay vì chỉ cộng điểm nhẹ."
        ),
        (
            "Toy / Prototype / Production",
            "Toy là code để học, prototype là thử nghiệm nội bộ, production là hệ thật. Cùng một lỗi nhưng trong production sẽ nghiêm trọng hơn rất nhiều."
        ),
        (
            "Scalar multiplication",
            "Phép nhân điểm như dG hoặc kG trong ECC. Đây là phép toán lõi và thường cần được triển khai cẩn thận để tránh rò rỉ side-channel."
        ),
        (
            "Thư viện trưởng thành",
            "Thư viện mật mã được dùng rộng rãi, có test, audit, xử lý edge-case và thường có chú ý tới constant-time/side-channel."
        ),
        (
            "Shamir's trick",
            "Kỹ thuật tính đồng thời u1G + u2Q để tối ưu ECDSA verification. Đây là tối ưu hiệu năng, không phải phòng thủ nonce attack."
        ),
    ])

    tab_defense, tab_shamir = st.tabs([
        "🛡️ Phòng thủ triển khai",
        "⚡ Shamir's trick",
    ])

    with tab_defense:
        render_ecdsa_defense_checklist_tab()

    with tab_shamir:
        render_shamir_optimization_tab()

    render_learning_summary(
        "Phòng thủ và tối ưu",
        [
            "Page 7 cho thấy ECDSA có thể lộ private key nếu nonce k bị dùng lại, bị lộ hoặc rò một phần.",
            "Phòng thủ ECDSA cần nonce discipline: không reuse nonce, dùng RFC6979-style hoặc CSPRNG tốt, và không để nonce rò qua side-channel.",
            "Constant-time implementation và side-channel awareness là phần engineering quan trọng, không phải trang trí cho sang.",
            "Toy code chỉ dùng để học; hệ thống thật phải dùng thư viện mật mã trưởng thành và được kiểm chứng.",
            "Shamir's trick tối ưu bước verify bằng cách tính u1G + u2Q hiệu quả hơn.",
            "Shamir's trick là tối ưu hiệu năng, không phải cơ chế phòng thủ nonce attack.",
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
    st.title("9. OpenSSL secp256k1 và kết luận")

    render_page_intro(
        "Toy demo liên hệ công cụ thật như thế nào?",
        "Các page trước dùng toy curve để nhìn rõ toán học. Page này dùng OpenSSL với secp256k1 để đối chiếu luồng ký và kiểm tra chữ ký bằng công cụ thật.",
        "Người dùng sinh key secp256k1, ký nội dung gốc, sửa nội dung để verify fail, rồi đọc lại kết luận toàn bộ đề tài.",
    )

    st.warning(
        "Demo này ký một đoạn text/file bằng OpenSSL secp256k1. "
        "Đây không phải ký giao dịch Bitcoin đầy đủ: không có Bitcoin Script, không có sighash, "
        "không có transaction serialization thật và không có consensus/network."
    )

    render_term_notes([
        (
            "OpenSSL",
            "Công cụ/thư viện mật mã phổ biến, dùng ở đây để chạy ký và kiểm tra chữ ký bằng công cụ thật."
        ),
        (
            "secp256k1",
            "Đường cong elliptic mà Bitcoin truyền thống dùng cho ECDSA."
        ),
        (
            "Private key",
            "Khóa bí mật dùng để ký. Trong demo này là file tạm do OpenSSL sinh ra."
        ),
        (
            "Public key",
            "Khóa công khai dùng để kiểm tra chữ ký."
        ),
        (
            "Signature",
            "Chữ ký số được tạo từ nội dung gốc và private key."
        ),
        (
            "Integrity / tính toàn vẹn",
            "Nếu dữ liệu bị sửa sau khi ký, chữ ký cũ không còn hợp lệ."
        ),
        (
            "Toy demo vs công cụ thật",
            "Toy demo giúp hiểu từng bước toán học; OpenSSL cho thấy cùng ý tưởng ký/verify tồn tại trong công cụ mật mã thật."
        ),
    ])

    init_openssl_lab_state()
    lab = st.session_state.openssl_lab

    openssl_path = get_openssl_path()

    if openssl_path:
        st.success(f"Đã tìm thấy OpenSSL: `{openssl_version(openssl_path)}`")
    else:
        st.error(
            "Không tìm thấy OpenSSL trong PATH. "
            "Page này cần OpenSSL để sinh key, ký và verify bằng công cụ thật."
        )

    st.markdown("## Vai trò của Page 9")

    role_rows = [
        {
            "Vai trò": "Đối chiếu với công cụ thật",
            "Ý nghĩa": "Các page trước dùng toy curve; page này dùng OpenSSL secp256k1 để chạy ký/verify thật trên file/message.",
        },
        {
            "Vai trò": "Kiểm tra tính toàn vẹn",
            "Ý nghĩa": "Giữ nguyên message thì verify pass; sửa message sau khi ký thì verify fail.",
        },
        {
            "Vai trò": "Tổng kết đề tài",
            "Ý nghĩa": "Chốt lại ECC, ECDLP, ECDSA, Bitcoin case study và bài học triển khai an toàn.",
        },
    ]

    st.dataframe(
        pd.DataFrame(role_rows),
        use_container_width=True,
        hide_index=True,
    )

    tab_key, tab_sign, tab_verify, tab_bench, tab_conclusion = st.tabs([
        "1️⃣ Sinh key thật",
        "2️⃣ Ký nội dung",
        "3️⃣ Sửa và verify",
        "4️⃣ Mini benchmark",
        "5️⃣ Kết luận đề tài",
    ])

    # ---------------- TAB 1 ----------------
    with tab_key:
        st.subheader("1. Sinh cặp khóa secp256k1 bằng OpenSSL")

        st.markdown(
            """
            Ở bước này, OpenSSL tạo ra một cặp khóa trên curve `secp256k1`:

            ```text
            private key: dùng để ký
            public key : dùng để verify
            ```

            Khóa nằm trong thư mục tạm của app. Đây không phải ví Bitcoin thật.
            """
        )

        col_action, col_reset = st.columns(2)

        with col_action:
            if st.button("🔑 Sinh cặp khóa secp256k1", use_container_width=True):
                generate_openssl_secp256k1_keys()
                st.rerun()

        with col_reset:
            if st.button("🧹 Reset OpenSSL lab", use_container_width=True):
                reset_openssl_lab_state()
                st.rerun()

        key_status_rows = [
            {
                "Mục": "Đã có key chưa?",
                "Giá trị": lab["keys_generated"],
            },
            {
                "Mục": "Private key file",
                "Giá trị": lab["private_key"],
            },
            {
                "Mục": "Public key file",
                "Giá trị": lab["public_key"],
            },
        ]

        st.dataframe(
            pd.DataFrame(key_status_rows),
            use_container_width=True,
            hide_index=True,
        )

        if lab["keys_generated"]:
            st.success("Đã có key. Sang tab 2 để ký nội dung gốc.")
        else:
            st.info("Bấm sinh key trước. Chưa có key thì chưa ký được.")

    # ---------------- TAB 2 ----------------
    with tab_sign:
        st.subheader("2. Ký nội dung gốc bằng private key")

        st.markdown(
            """
            Chữ ký số không ký một “ý định mơ hồ”, mà ký vào dữ liệu cụ thể.

            Trong tab này:

            ```text
            message gốc + private key secp256k1
            → OpenSSL tạo signature
            ```
            """
        )

        if not lab["keys_generated"]:
            st.info("Chưa có key. Hãy sang tab 1 sinh key trước.")
        else:
            original_message = st.text_area(
                "Nội dung gốc sẽ được ký",
                value=lab["original_message"] or "Alice trả Bob 1 BTC mô phỏng",
                height=130,
                key="openssl_original_message_input",
            )

            if st.button("✍️ Ký nội dung gốc bằng OpenSSL", use_container_width=True):
                if not original_message.strip():
                    st.warning("Nội dung gốc không nên để trống.")
                else:
                    sign_original_message_with_openssl(original_message)
                    st.rerun()

            if lab["message_signed"]:
                st.success("Đã có chữ ký cho nội dung gốc.")
                st.markdown("#### Chữ ký dạng hex, rút gọn")
                st.code(lab["signature_hex"][:200] + "...", language="text")

                signed_rows = [
                    {
                        "Mục": "Nội dung đã ký",
                        "Giá trị": lab["original_message"],
                    },
                    {
                        "Mục": "Signature file",
                        "Giá trị": lab["signature_file"],
                    },
                ]

                st.dataframe(
                    pd.DataFrame(signed_rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Sau khi ký xong, sang tab 3 để kiểm tra nội dung gốc và nội dung bị sửa.")

    # ---------------- TAB 3 ----------------
    with tab_verify:
        st.subheader("3. Sửa nội dung và kiểm tra chữ ký cũ")

        st.markdown(
            """
            Đây là phần quan trọng nhất của Page 9.

            Chữ ký được tạo cho **nội dung gốc**. Sau đó ta dùng **cùng chữ ký cũ** để kiểm tra một nội dung bất kỳ:

            ```text
            nội dung giống gốc  → verify pass
            nội dung bị sửa     → verify fail
            ```

            Đây chính là tính toàn vẹn của chữ ký số.
            """
        )

        if not lab["message_signed"]:
            st.info("Chưa có chữ ký. Hãy sang tab 2 ký nội dung gốc trước.")
        else:
            col_original, col_verify = st.columns(2)

            with col_original:
                st.markdown("#### Nội dung gốc đã ký")
                st.text_area(
                    "Nội dung gốc",
                    value=lab["original_message"],
                    height=150,
                    disabled=True,
                    key="openssl_original_display_final",
                )

            with col_verify:
                st.markdown("#### Nội dung đem đi verify")

                if "openssl_verify_message_next" in st.session_state:
                    st.session_state.openssl_verify_message = st.session_state.pop("openssl_verify_message_next")
                elif "openssl_verify_message" not in st.session_state:
                    st.session_state.openssl_verify_message = lab["original_message"]

                verify_message = st.text_area(
                    "Có thể giữ nguyên hoặc tự sửa",
                    height=150,
                    key="openssl_verify_message",
                )

            col_check, col_tamper, col_restore = st.columns(3)

            with col_check:
                if st.button("✅ Verify nội dung hiện tại", use_container_width=True):
                    verify_message_with_old_signature(verify_message)
                    st.rerun()

            with col_tamper:
                if st.button("🧪 Tạo bản bị sửa mẫu", use_container_width=True):
                    st.session_state.openssl_verify_message_next = lab["original_message"] + " [đã bị sửa]"
                    st.rerun()

            with col_restore:
                if st.button("↩️ Khôi phục giống gốc", use_container_width=True):
                    st.session_state.openssl_verify_message_next = lab["original_message"]
                    st.rerun()

            if lab["last_verify"] is not None:
                result = lab["last_verify"]

                st.divider()
                st.markdown("### Kết quả verify")

                result_rows = [
                    {
                        "Câu hỏi": "Nội dung đem verify có giống nội dung gốc không?",
                        "Kết quả": result["same_as_original"],
                    },
                    {
                        "Câu hỏi": "OpenSSL có chấp nhận chữ ký cũ không?",
                        "Kết quả": result["accepted"],
                    },
                    {
                        "Câu hỏi": "Output từ OpenSSL",
                        "Kết quả": result["output"],
                    },
                ]

                st.dataframe(
                    pd.DataFrame(result_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                if result["accepted"]:
                    st.success(
                        "Verify thành công. Nội dung kiểm tra khớp với chữ ký cũ."
                    )
                else:
                    st.error(
                        "Verify thất bại. Nếu nội dung đã bị sửa, đây là kết quả đúng: chữ ký cũ không còn hợp lệ."
                    )

                st.info(
                    "Liên hệ Page 6: trong Bitcoin case study, nếu attacker sửa số tiền hoặc người nhận sau khi transaction đã ký, "
                    "dữ liệu transaction thay đổi nên chữ ký cũ không còn khớp. Node phải từ chối."
                )

    # ---------------- TAB 4 ----------------
    with tab_bench:
        st.subheader("4. Mini benchmark cho chữ ký secp256k1 hiện tại")

        st.markdown(
            """
            Page 2 đã benchmark để so sánh RSA/DSA/ECDSA.  
            Tab này chỉ đo nhanh thao tác ký và verify trong chính OpenSSL lab hiện tại.

            Kết quả phụ thuộc máy, phiên bản OpenSSL và số lần chạy.
            """
        )

        if not lab["message_signed"]:
            st.info("Cần sinh key và ký nội dung gốc trước khi đo thời gian.")
        else:
            iterations = int(st.slider(
                "Số lần chạy thử",
                min_value=1,
                max_value=100,
                value=10,
                key="openssl_local_benchmark_iterations",
            ))

            if st.button("📊 Đo thời gian ký/verify", use_container_width=True):
                result = benchmark_current_openssl_signature(iterations)

                if result is not None:
                    st.session_state["openssl_local_benchmark_result"] = result

            if "openssl_local_benchmark_result" in st.session_state:
                result = st.session_state["openssl_local_benchmark_result"]

                bench_rows = [
                    {"Chỉ số": "Số lần chạy", "Giá trị": result["iterations"]},
                    {"Chỉ số": "Thời gian ký trung bình (ms/lần)", "Giá trị": f"{result['sign_avg_ms']:.4f}"},
                    {"Chỉ số": "Thời gian verify trung bình (ms/lần)", "Giá trị": f"{result['verify_avg_ms']:.4f}"},
                    {"Chỉ số": "Số lần ký mỗi giây", "Giá trị": f"{result['sign_ops_per_sec']:.2f}"},
                    {"Chỉ số": "Số lần verify mỗi giây", "Giá trị": f"{result['verify_ops_per_sec']:.2f}"},
                ]

                st.dataframe(
                    pd.DataFrame(bench_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                fig_df = pd.DataFrame([
                    {"Phép toán": "Ký", "ms/lần": result["sign_avg_ms"]},
                    {"Phép toán": "Verify", "ms/lần": result["verify_avg_ms"]},
                ])

                fig = px.bar(
                    fig_df,
                    x="Phép toán",
                    y="ms/lần",
                    text_auto=True,
                    title="OpenSSL secp256k1: thời gian ký và verify",
                )

                fig.update_layout(
                    height=480,
                    xaxis_title="Phép toán",
                    yaxis_title="Milliseconds / lần",
                )

                st.plotly_chart(fig, use_container_width=True)

                st.warning(
                    "Đây chỉ là mini benchmark cho lab hiện tại, không thay thế benchmark chuẩn. "
                    "Muốn so sánh RSA/ECDSA nhiều hệ thì xem Page 2."
                )

    # ---------------- TAB 5 ----------------
    with tab_conclusion:
        st.subheader("5. Kết luận toàn bộ đề tài")

        st.markdown(
            """
            Sau khi đi qua toàn bộ app, mạch logic của đề tài nên được hiểu như sau:
            """
        )

        conclusion_rows = [
            {
                "Mảnh ghép": "Public-key cryptography",
                "Kết luận": "Ra đời để giải quyết trao đổi khóa, xác thực và chữ ký số trong hệ thống lớn.",
            },
            {
                "Mảnh ghép": "ECC",
                "Kết luận": "Là một nhánh public-key crypto dựa trên nhóm điểm của đường cong elliptic.",
            },
            {
                "Mảnh ghép": "ECDLP",
                "Kết luận": "Là bài toán khó đứng sau ECC: biết G và Q = dG thì khó tìm lại d.",
            },
            {
                "Mảnh ghép": "ECDSA",
                "Kết luận": "Là chữ ký số dựa trên ECC: private key ký, public key verify.",
            },
            {
                "Mảnh ghép": "Bitcoin",
                "Kết luận": "Là case study thực tế: ECDSA được dùng để chứng minh quyền tiêu UTXO.",
            },
            {
                "Mảnh ghép": "Nonce attack",
                "Kết luận": "ECDLP khó không cứu được hệ thống nếu nonce k bị reuse, bị lộ hoặc rò một phần.",
            },
            {
                "Mảnh ghép": "Secure engineering",
                "Kết luận": "An toàn thật cần nonce discipline, RFC6979-style/CSPRNG tốt, constant-time và thư viện trưởng thành.",
            },
            {
                "Mảnh ghép": "OpenSSL",
                "Kết luận": "Toy demo giúp hiểu toán; OpenSSL cho thấy cùng ý tưởng ký/verify chạy được bằng công cụ thật.",
            },
        ]

        st.dataframe(
            pd.DataFrame(conclusion_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Một câu chốt để thuyết trình")

        st.success(
            "ECC cung cấp nền tảng khóa công khai hiệu quả dựa trên ECDLP; "
            "ECDSA biến nền tảng đó thành cơ chế chữ ký số; "
            "Bitcoin dùng ECDSA như một case study để chứng minh quyền chi tiêu UTXO; "
            "và an toàn thực tế không chỉ đến từ toán học, mà còn đến từ triển khai đúng."
        )

        st.markdown("### Những giới hạn của demo")

        limitation_rows = [
            {
                "Giới hạn": "Toy curve nhỏ",
                "Ý nghĩa": "Các page toy giúp học toán, không đại diện cho độ an toàn thật.",
            },
            {
                "Giới hạn": "Bitcoin case study giản lược",
                "Ý nghĩa": "Có UTXO/signature/public key hash, nhưng không mô phỏng đầy đủ Bitcoin Script, sighash, consensus.",
            },
            {
                "Giới hạn": "OpenSSL ký message/file",
                "Ý nghĩa": "Đối chiếu công cụ thật, nhưng không phải ký một Bitcoin transaction thật.",
            },
            {
                "Giới hạn": "Không demo lattice attack",
                "Ý nghĩa": "Partial nonce leakage chỉ được giải thích ở mức lý thuyết để tránh lệch trọng tâm.",
            },
        ]

        st.dataframe(
            pd.DataFrame(limitation_rows),
            use_container_width=True,
            hide_index=True,
        )

    render_openssl_action_log()

    render_learning_summary(
        "OpenSSL secp256k1 và kết luận",
        [
            "OpenSSL secp256k1 giúp đối chiếu toy demo với công cụ mật mã thật.",
            "Sinh key, ký message và verify message cho thấy ECDSA không chỉ là công thức trên bảng.",
            "Chữ ký chỉ hợp lệ với đúng dữ liệu đã ký; sửa dữ liệu sau khi ký làm verify thất bại.",
            "Không được nhầm ký một message/file bằng OpenSSL với ký giao dịch Bitcoin đầy đủ.",
            "ECC là nền tảng public-key crypto; ECDLP là bài toán khó; ECDSA là ứng dụng chữ ký số; Bitcoin là case study.",
            "An toàn thực tế cần cả toán học đúng lẫn triển khai đúng: nonce discipline, constant-time và thư viện trưởng thành.",
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
        demo_symmetric_to_public_key()
    elif page_id == 2:
        demo_public_key_systems_and_benchmark()
    elif page_id == 3:
        demo_ecc_toy_curve()
    elif page_id == 4:
        demo_ecdlp_explanation()
    elif page_id == 5:
        demo_ecdsa_sign_verify()
    elif page_id == 6:
        demo_interactive_bitcoin_transaction_lab()
    elif page_id == 7:
        demo_reused_nonce_attack()
    elif page_id == 8:
        demo_nonce_defense_notes()
    elif page_id == 9:
        demo_openssl_summary()

    st.divider()
    render_navigation_footer()


if __name__ == "__main__":
    main()
