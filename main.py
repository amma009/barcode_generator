# ============================================================
# Label Generator — Fixed Version with Printer DPI Support
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

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(layout="wide")
st.title("Label Generator")

# ============================================================
# DPI UTILITIES
# ============================================================
def px_per_mm(dpi: int) -> float:
    return dpi / 25.4

# ============================================================
# UTILITIES
# ============================================================
def safe_text_height(font, text="A"):
    try:
        bbox = font.getbbox(text)
        return bbox[3] - bbox[1]
    except Exception:
        return font.getsize(text)[1]

def safe_text_width(draw, font, text):
    try:
        return draw.textlength(text, font=font)
    except Exception:
        return draw.textsize(text, font=font)[0]

def load_font(size=16):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
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
    dpi,
    spacing_px=5,
    font_size=14,
    target_barcode_width_mm=40,
    bg_color="white",
    position="Bottom"
):
    desc = " ".join(description.split())
    font = load_font(font_size)

    target_barcode_width_px = int(target_barcode_width_mm * px_per_mm(dpi))

    bc = barcode_img.copy().convert("RGB")
    if bc.width > target_barcode_width_px:
        scale = target_barcode_width_px / bc.width
        bc = bc.resize((int(bc.width * scale), int(bc.height * scale)), Image.LANCZOS)

    bw, bh = bc.size

    tmp = Image.new("RGB", (max(bw, 500), 500), "white")
    draw_tmp = ImageDraw.Draw(tmp)

    wrap_width = int(bw * 0.95) if position == "Bottom" else int(bw * 0.7)
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

        out.paste(bc, (int((canvas_w - bw) / 2), pad))
        y = pad + bh + spacing_px
        for ln in lines:
            w_ln = safe_text_width(draw, font, ln)
            x_ln = int((canvas_w - w_ln) / 2)
            draw.text((x_ln, y), ln, font=font, fill="black")
            y += line_h + 2
        return out

    else:
        canvas_w = int(bw + spacing_px + desc_w + pad * 2)
        canvas_h = int(max(bh, desc_h) + pad * 2)
        out = Image.new("RGB", (canvas_w, canvas_h), bg_color)
        draw = ImageDraw.Draw(out)

        x_bc = pad
        y_bc = pad + int((canvas_h - pad * 2 - bh) / 2)
        out.paste(bc, (x_bc, y_bc))

        x_desc = pad + bw + spacing_px
        y_desc = pad + int((canvas_h - pad * 2 - desc_h) / 2)
        for ln in lines:
            draw.text((x_desc, y_desc), ln, font=font, fill="black")
            y_desc += line_h + 2
        return out

# ============================================================
# AUTO-FIT SIZE CALCULATION (DPI AWARE)
# ============================================================
def compute_label_mm_from_composed(img, paper_mm, margins, spacing_mm, orientation, dpi):
    ppm = px_per_mm(dpi)
    w_mm = img.width / ppm + 4
    h_mm = img.height / ppm + 4

    if orientation == "Landscape":
        w_mm, h_mm = h_mm, w_mm

    usable_w = paper_mm[0] - margins["left"] - margins["right"]
    usable_h = paper_mm[1] - margins["top"] - margins["bottom"]

    w_mm = min(w_mm, max(5, usable_w - spacing_mm))
    h_mm = min(h_mm, max(5, usable_h - spacing_mm))

    return round(w_mm, 1), round(h_mm, 1)

# ============================================================
# SIDEBAR UI
# ============================================================
st.sidebar.header("Controls")

printer_dpi = st.sidebar.selectbox("Printer DPI", [203, 300], index=0)

code_input = st.sidebar.text_input("Input Kode:")
description_value = st.sidebar.text_area("Description:")
barcode_type = st.sidebar.selectbox("Jenis Barcode", ["Code128", "QR"])

desc_position = st.sidebar.selectbox("Posisi Description", ["Bottom", "Right"])
desc_font_size = st.sidebar.slider("Font size", 8, 72, 14)
spacing_barcode_to_description = st.sidebar.slider("Spacing barcode → desc", -50, 50, 5)

generate_btn = st.sidebar.button("Generate Label")

# ============================================================
# GENERATE LABEL
# ============================================================
if generate_btn:
    if not code_input.strip():
        st.error("Masukkan kode terlebih dahulu")
    else:
        raw = generate_qr(code_input) if barcode_type == "QR" else generate_code128(code_input)
        composed = compose_label_image_wrapped(
            raw,
            description_value,
            dpi=printer_dpi,
            spacing_px=spacing_barcode_to_description,
            font_size=desc_font_size,
            position=desc_position
        )
        st.session_state["label_img"] = composed

# ============================================================
# PREVIEW
# ============================================================
if "label_img" in st.session_state:
    st.subheader("Composed Label")
    st.image(pil_to_bytes(st.session_state["label_img"]))

st.sidebar.markdown(
    """
    <div style='text-align:center;color:gray;font-size:12px;margin-top:40px;'>
    © 2025 Label Generator — DPI Accurate Printing
    </div>
    """,
    unsafe_allow_html=True,
)
