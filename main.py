# ============================================================
# Label Generator — Complete & Fixed Version +111
# ============================================================

import streamlit as st
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm as mm_unit
from reportlab.lib.utils import ImageReader
import base64
import os

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(layout="wide")
st.title("Label Generator")

PX_PER_MM = 96.0 / 25.4  # ~3.7795 px per mm

# ============================================================
# UTILITIES
# ============================================================

def safe_text_height(font, text="A"):
    try:
        bbox = font.getbbox(text)
        return bbox[3] - bbox[1]
    except:
        return font.getsize(text)[1]


def safe_text_width(draw, font, text):
    try:
        return draw.textlength(text, font=font)
    except:
        return draw.textsize(text, font=font)[0]


# ============================================================
# FIXED FONT LOADER
# ============================================================

def load_font(size=16):
    """
    Font loader yang aman.
    Slider font size akan selalu bekerja.
    """
    font_paths = [
        "Roboto-Regular.ttf",
        "./Roboto-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass

    return ImageFont.load_default()


def pil_to_bytes(img: Image.Image, fmt="PNG"):
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


# ============================================================
# BARCODE GENERATORS
# ============================================================

def generate_qr(data: str):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")


def generate_code128(data: str):
    CODE128 = barcode.get_barcode_class("code128")
    c128 = CODE128(data, writer=ImageWriter())
    buffer = io.BytesIO()
    c128.write(buffer)
    buffer.seek(0)
    return Image.open(buffer)


# ============================================================
# PRESETS
# ============================================================

LABEL_PRESETS = {
    "38×100 mm": (38, 100),
    "50×100 mm": (50, 100),
    "32×64 mm": (32, 64),
    "18×50 mm": (18, 50),
    "13×38 mm": (13, 38),
    "8×20 mm": (8, 20),
    "38×75 mm": (38, 75),
    "11×30 mm": (11, 30),
}

PAPER_PRESETS = {
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "4R (102×152 mm)": (102, 152),
    "4R (102×102 mm)": (102, 102),
    "26 × 15 mm": (26, 15),
    "33 × 15 mm": (33, 15),
    "33 × 25 mm": (33, 25),
    "48 × 33 mm": (48, 33),
    "60 × 30 mm": (60, 30),
    "76 × 35 mm": (76, 35),
    "100 × 50 mm": (100, 50),
}


# ============================================================
# TEXT WRAP
# ============================================================

def wrap_text_to_width(draw, font, text, max_width_px):
    words = text.split()
    if not words:
        return []

    lines = []
    current = words[0]

    for w in words[1:]:
        test = current + " " + w
        if safe_text_width(draw, font, test) <= max_width_px:
            current = test
        else:
            lines.append(current)
            current = w

    lines.append(current)
    return lines


# ============================================================
# COMPOSE LABEL IMAGE
# ============================================================

def compose_label_image_wrapped(
    barcode_img,
    description,
    spacing_px=5,
    font_size=14,
    target_barcode_width_px=420,
    bg_color="white",
    position="Bottom"
):

    desc = " ".join(description.split())
    font = load_font(font_size)

    bc = barcode_img.copy().convert("RGB")

    if bc.width > target_barcode_width_px:
        scale = target_barcode_width_px / bc.width
        bc = bc.resize((int(bc.width * scale), int(bc.height * scale)), Image.LANCZOS)

    bw, bh = bc.size

    tmp = Image.new("RGB", (max(bw, 500), 500), "white")
    draw_tmp = ImageDraw.Draw(tmp)

    wrap_width = int(bw * 0.95) if position == "Bottom" else int((bw * 0.7))
    lines = wrap_text_to_width(draw_tmp, font, desc, wrap_width) if desc else []

    line_h = safe_text_height(font)
    desc_h = len(lines) * (line_h + 2)
    desc_w = max((safe_text_width(draw_tmp, font, ln) for ln in lines), default=0)

    pad = 8

    if position == "Bottom":

        canvas_w = int(max(bw, desc_w) + pad * 2)
        canvas_h = int(bh + desc_h + spacing_px + pad * 2)

        out = Image.new("RGB", (canvas_w, canvas_h), bg_color)
        draw = ImageDraw.Draw(out)

        out.paste(bc, (int((canvas_w - bw)/2), pad))

        y = pad + bh + spacing_px

        for ln in lines:
            w_ln = safe_text_width(draw, font, ln)
            x_ln = int((canvas_w - w_ln)/2)
            draw.text((x_ln, y), ln, font=font, fill="black")
            y += line_h + 2

        return out

    else:

        canvas_w = int(bw + spacing_px + desc_w + pad * 2)
        canvas_h = int(max(bh, desc_h) + pad * 2)

        out = Image.new("RGB", (canvas_w, canvas_h), bg_color)
        draw = ImageDraw.Draw(out)

        x_bc = pad
        y_bc = pad + int((canvas_h - pad*2 - bh)/2)

        out.paste(bc, (x_bc, y_bc))

        x_desc = pad + bw + spacing_px
        y_desc = pad + int((canvas_h - pad*2 - desc_h)/2)

        for ln in lines:
            draw.text((x_desc, y_desc), ln, font=font, fill="black")
            y_desc += line_h + 2

        return out


# ============================================================
# UI SIDEBAR
# ============================================================

st.sidebar.header("Controls")

code_input = st.sidebar.text_input("Input Kode:", "")
description_value = st.sidebar.text_area("Description:", "")
barcode_type = st.sidebar.selectbox("Jenis Barcode:", ["Code128","QR"])

with st.sidebar.expander("Description Settings", True):

    desc_position = st.selectbox("Posisi Description", ["Bottom","Right"])
    desc_font_size = st.slider("Font size", 8, 72, 14)
    spacing_barcode_to_description = st.slider("Spacing barcode → desc", -50, 50, 5)


generate_btn = st.sidebar.button("Generate & Compose Label",type ="primary")


# ============================================================
# GENERATE LABEL
# ============================================================

if generate_btn:

    if not code_input.strip():

        st.sidebar.error("Masukkan kode terlebih dahulu!")

    else:

        raw_bc = generate_qr(code_input) if barcode_type=="QR" else generate_code128(code_input)

        composed = compose_label_image_wrapped(
            raw_bc.convert("RGB"),
            description_value,
            spacing_px=spacing_barcode_to_description,
            font_size=desc_font_size,
            position=desc_position
        )

        st.session_state["label_img"] = composed
        st.success("Label berhasil dibuat!")


# ============================================================
# PREVIEW
# ============================================================

col1, col2 = st.columns(2)

with col1:

    st.subheader("Composed Label")

    if "label_img" in st.session_state:
        st.image(pil_to_bytes(st.session_state["label_img"]))
    else:
        st.info("Belum ada label.")


with col2:

    st.subheader("Preview Layout Halaman")

    if "label_img" in st.session_state:
        st.image(pil_to_bytes(st.session_state["label_img"]))
    else:
        st.info("Generate label dulu.")


# ============================================================
# FOOTER
# ============================================================

st.sidebar.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px; margin-top: 50px;'>
        © 2025 Label Generator — Developed by amma.inc
    </div>
    """,
    unsafe_allow_html=True
)
