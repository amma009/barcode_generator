
# ============================================================
# Label Generator — Complete & Fixed Version
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

def load_font(size=16):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except:
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

    # Resize barcode
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

    else:  # RIGHT
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
# AUTO-FIT SIZE CALCULATION
# ============================================================
def compute_label_mm_from_composed(img, paper_mm, margins, spacing_mm, orientation):
    w_mm = img.width / PX_PER_MM + 4
    h_mm = img.height / PX_PER_MM + 4
    if orientation == "Landscape":
        w_mm, h_mm = h_mm, w_mm

    usable_w = paper_mm[0] - margins["left"] - margins["right"]
    usable_h = paper_mm[1] - margins["top"] - margins["bottom"]

    w_mm = min(w_mm, max(5, usable_w - spacing_mm))
    h_mm = min(h_mm, max(5, usable_h - spacing_mm))

    return round(w_mm, 1), round(h_mm, 1)

# ============================================================
# PDF & PREVIEW FUNCTIONS
# ============================================================
def generate_pdf(label_img, label_mm, paper_mm, margins_mm, spacing_mm, padding_mm, label_orientation="Portrait", page_landscape=False):
    lw, lh = label_mm
    if label_orientation=="Landscape": lw, lh = lh, lw
    pw, ph = paper_mm
    if page_landscape: pw, ph = ph, pw

    lw_pt, lh_pt = lw * mm_unit, lh * mm_unit
    pw_pt, ph_pt = pw * mm_unit, ph * mm_unit
    m = {k: margins_mm[k]*mm_unit for k in margins_mm}
    p = {k: padding_mm[k]*mm_unit for k in padding_mm}
    spacing_pt = spacing_mm*mm_unit

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(pw_pt, ph_pt))

    img_buf = io.BytesIO()
    label_img.save(img_buf, "PNG")
    img_buf.seek(0)
    img_reader = ImageReader(img_buf)

    usable_w = pw_pt - m["left"] - m["right"]
    usable_h = ph_pt - m["top"] - m["bottom"]
    cols = max(1, int((usable_w + spacing_pt)//(lw_pt + spacing_pt)))
    rows = max(1, int((usable_h + spacing_pt)//(lh_pt + spacing_pt)))

    start_x = m["left"]
    start_y = ph_pt - m["top"] - lh_pt

    for r in range(rows):
        for c in range(cols):
            x = start_x + c*(lw_pt + spacing_pt)
            y = start_y - r*(lh_pt + spacing_pt)
            pdf.drawImage(
                img_reader,
                x + p["left"],
                y + p["bottom"],
                lw_pt - (p["left"] + p["right"]),
                lh_pt - (p["top"] + p["bottom"]),
                preserveAspectRatio=True,
                anchor="sw"
            )

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf

def generate_pdf_preview(label_img, label_mm, paper_mm, margins_mm, spacing_mm, padding_mm, label_orientation="Portrait", max_px=900, page_landscape=False):
    lw, lh = label_mm
    if label_orientation=="Landscape": lw, lh = lh, lw
    pw, ph = paper_mm
    if page_landscape: pw, ph = ph, pw

    scale = max_px/max(pw, ph)
    scale = min(max(scale, 2), 12)

    def mm_to_px(mm): return int(round(mm*scale))
    pw_px, ph_px = mm_to_px(pw), mm_to_px(ph)
    lw_px, lh_px = mm_to_px(lw), mm_to_px(lh)
    mt, mb, ml, mr = (mm_to_px(margins_mm[k]) for k in ["top","bottom","left","right"])
    pt, pb, pl, pr = (mm_to_px(padding_mm[k]) for k in ["top","bottom","left","right"])
    sp = mm_to_px(spacing_mm)

    preview = Image.new("RGB", (pw_px, ph_px), "white")
    draw = ImageDraw.Draw(preview)

    li = label_img.copy().convert("RGB")
    li.thumbnail((lw_px - pl - pr, lh_px - pt - pb))

    usable_w = pw_px - ml - mr
    usable_h = ph_px - mt - mb
    cols = max(1, (usable_w + sp)//(lw_px + sp))
    rows = max(1, (usable_h + sp)//(lh_px + sp))

    for r in range(rows):
        for c in range(cols):
            x = ml + c*(lw_px + sp)
            y = mt + r*(lh_px + sp)

            draw.rectangle((x, y, x+lw_px, y+lh_px), outline="#666666", width=2)
            ix1, iy1 = x+pl, y+pt
            ix2, iy2 = x+lw_px-pr, y+lh_px-pb
            draw.rectangle((ix1, iy1, ix2, iy2), outline="#cccccc", width=1)

            px = ix1 + ((ix2 - ix1 - li.width)//2)
            py = iy1 + ((iy2 - iy1 - li.height)//2)
            preview.paste(li, (px, py))

    return preview, cols, rows

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

with st.sidebar.expander("Label & Page Options"):
    label_mode = st.radio("Mode ukuran label:", ["Custom","Auto-fit"])
    if label_mode=="Manual":
        preset = st.selectbox("Preset:", list(LABEL_PRESETS.keys()))
        label_mm = LABEL_PRESETS[preset]
    elif label_mode=="Custom":
        w = st.number_input("Label Width (mm)", 1.0, value=38.0)
        h = st.number_input("Label Height (mm)", 1.0, value=100.0)
        label_mm = (w,h)
    else:
        label_mm = (0,0)
    paper_choice = st.selectbox("Ukuran kertas:", list(PAPER_PRESETS.keys()), index=list(PAPER_PRESETS.keys()).index("A4"))
    paper_mm = PAPER_PRESETS[paper_choice]
    label_orientation = st.selectbox("Orientasi Label:", ["Portrait","Landscape"])
    page_landscape = st.checkbox("Halaman Landscape?")

with st.sidebar.expander("Page Margin & Padding"):
    "Setting Jarak Antara Kertas dan Label"
    m_top = st.number_input("Margin Top", value=1.0)
    m_bottom = st.number_input("Margin Bottom", value=1.0)
    m_left = st.number_input("Margin Left", value=1.0)
    m_right = st.number_input("Margin Right", value=1.0)
    "-------------------------------"
    "Setting Jarak Antara Label Dan Isi Label"
    pad_top = st.number_input("Padding Top", value=1.0)
    pad_bottom = st.number_input("Padding Bottom", value=1.0)
    pad_left = st.number_input("Padding Left", value=1.0)
    pad_right = st.number_input("Padding Right", value=1.0)

    "-------------------------------"
    "Setting Jarak Antara Label"
    spacing_mm = st.number_input("Spacing antar label", value=1.0)

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
        margins = {"top": m_top, "bottom": m_bottom, "left": m_left, "right": m_right}
        padding = {"top": pad_top, "bottom": pad_bottom, "left": pad_left, "right": pad_right}

        if label_mode=="Auto-fit":
            label_mm_use = compute_label_mm_from_composed(st.session_state["label_img"], paper_mm, margins, spacing_mm, label_orientation)
            st.caption(f"Auto-fit size: {label_mm_use[0]} × {label_mm_use[1]} mm")
        else:
            label_mm_use = label_mm

        preview_img, cols, rows = generate_pdf_preview(
            st.session_state["label_img"],
            label_mm_use,
            paper_mm,
            margins,
            spacing_mm,
            padding,
            label_orientation,
            max_px=900,
            page_landscape=page_landscape
        )
        st.image(pil_to_bytes(preview_img),
                 caption=f"{cols} kolom × {rows} baris = {cols*rows} label")
    else:
        st.info("Generate label dulu.")

# ============================================================
# GENERATE PDF
# ============================================================
st.sidebar.subheader("Generate PDF")
generate_pdf_btn = st.sidebar.button("Generate PDF", type="primary")

if generate_pdf_btn and "label_img" in st.session_state:
    margins = {"top": m_top, "bottom": m_bottom, "left": m_left, "right": m_right}
    padding = {"top": pad_top, "bottom": pad_bottom, "left": pad_left, "right": pad_right}

    if label_mode=="Auto-fit":
        label_mm_use = compute_label_mm_from_composed(
            st.session_state["label_img"], paper_mm, margins, spacing_mm, label_orientation
        )
    else:
        label_mm_use = label_mm

    pdf_buf = generate_pdf(
        st.session_state["label_img"],
        label_mm_use,
        paper_mm,
        margins,
        spacing_mm,
        padding,
        label_orientation,
        page_landscape
    )

    pdf_bytes = pdf_buf.getvalue()


    # Tombol download PDF
    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=f"{code_input}.pdf",
        mime="application/pdf"
    )





# Tambahkan ini di paling bawah sidebar
st.sidebar.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px; margin-top: 50px;'>
        © 2025 Label Generator — Developed by amma.inc
    </div>
    """,
    unsafe_allow_html=True
)

