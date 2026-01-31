import streamlit as st
from rembg import remove, new_session
from PIL import Image, ImageDraw
from io import BytesIO
import os
import zipfile
import base64
import gc

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    layout="wide",
    page_title="PisiRemover",
    page_icon="🐾",
    initial_sidebar_state="collapsed"
)

# --- 2. FONKSİYONLAR ---
def create_checkerboard(size, tile_size=20):
    width, height = size
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            if (x // tile_size + y // tile_size) % 2 == 1:
                draw.rectangle([x, y, x + tile_size, y + tile_size], fill=(220, 220, 220))
    return img

def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

# RAM KORUMASI: Resmi küçült
def smart_resize(img, max_size=800):
    width, height = img.size
    if width > max_size or height > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    return img

# --- 3. CSS TASARIMI (Dark & Clean) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #050505; color: #ffffff; }
    .stApp { background-color: #050505; }
    header, footer {visibility: hidden;}
    .block-container { padding-top: 2rem; max-width: 1200px; }
    
    .hero-title {
        font-size: 60px; font-weight: 900;
        background: linear-gradient(to right, #fff, #999);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    
    [data-testid="stFileUploader"] { background-color: #111; border: 1px dashed #444; padding: 40px; border-radius: 20px; }
    div[data-testid="stDownloadButton"] button { background: white !important; color: black !important; border-radius: 12px !important; font-weight: 800 !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 4. HEADER ---
logo_data = get_image_base64("logo.png")
logo_html = f'<img src="data:image/png;base64,{logo_data}" height="40">' if logo_data else '<h2 style="color:#7dbb42;">Pisi</h2>'
st.markdown(f'<div style="display:flex; justify-content:space-between; margin-bottom:40px;"><div>{logo_html}</div></div>', unsafe_allow_html=True)

# --- 5. ANA EKRAN ---
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown('<h1 class="hero-title">Arka Planı Sil.</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#888;">Yapay zeka destekli, hızlı ve ücretsiz.</p>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Fotoğraf yükle", type=["jpg", "png", "webp"], accept_multiple_files=True)

with c2:
    # Demo görseli varsa göster
    if os.path.exists("kedi_temiz.png"):
        st.image("kedi_temiz.png", caption="Örnek Sonuç", use_container_width=True)

# --- 6. İŞLEM (RAM DOSTU MOD) ---
if uploaded_files:
    st.markdown("---")
    # KRİTİK NOKTA: 'u2net' varsayılan modeldir ve hafiftir.
    # İlk açılışta BiRefNet kullanmıyoruz!
    session = new_session("u2net") 
    
    processed_images = []

    for file in uploaded_files:
        img = Image.open(file)
        # Resmi 800px'e küçültüyoruz (RAM patlamasın diye)
        img = smart_resize(img, max_size=800)
        
        with st.spinner("İşleniyor..."):
            try:
                out = remove(img, session=session)
                
                buf = BytesIO()
                out.save(buf, format="PNG")
                byte_im = buf.getvalue()
                processed_images.append((f"Pisi_{file.name}.png", byte_im))
                
                check = create_checkerboard(out.size)
                check.paste(out, mask=out.split()[3])

                colA, colB, colC = st.columns([1, 1, 1])
                with colA: st.image(img, caption="Orijinal", use_container_width=True)
                with colB: st.image(check, caption="Temiz", use_container_width=True)
                with colC: st.download_button("İndir", byte_im, f"Pisi_{file.name}.png", "image/png")
                
                del out, check
                gc.collect() # RAM TEMİZLİĞİ

            except Exception as e:
                st.error(f"Hata: {e}")

    if len(processed_images) > 1:
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as z:
            for name, data in processed_images: z.writestr(name, data)
        st.download_button("📦 HEPSİNİ İNDİR", zip_buf.getvalue(), "Pisi_Pack.zip", "application/zip")
