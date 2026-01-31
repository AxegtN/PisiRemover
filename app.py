import streamlit as st
from rembg import remove, new_session
from PIL import Image, ImageDraw
from io import BytesIO
import os
import zipfile
import base64
import gc # RAM temizliği için Çöp Toplayıcı

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    layout="wide",
    page_title="PisiRemover - AI Studio",
    page_icon="🐾",
    initial_sidebar_state="collapsed"
)

# --- 2. YARDIMCI FONKSİYONLAR ---
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

def smart_resize(img, max_size=1024):
    """
    RAM KORUMASI: Resmi orantılı olarak küçültür.
    BiRefNet gibi ağır modellerde RAM patlamasını önler.
    """
    width, height = img.size
    if width > max_size or height > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    return img

# --- 3. CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #050505;
        color: #ffffff;
    }
    .stApp { background-color: #050505; }

    header, footer, #MainMenu {visibility: hidden;}
    .block-container {
        padding-top: 0;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
    }

    .navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 0;
        margin-bottom: 60px;
    }
    .nav-links {
        display: flex;
        gap: 30px;
        align-items: center;
    }
    .nav-item {
        color: #888;
        text-decoration: none;
        font-weight: 600;
        font-size: 14px;
        transition: color 0.3s;
    }
    .nav-item:hover { color: white; }
    .login-button {
        background-color: #1f1f1f;
        padding: 10px 20px;
        border-radius: 20px;
        color: white !important;
        font-weight: 700;
        text-decoration: none;
    }

    .hero-title {
        font-size: 72px;
        font-weight: 900;
        line-height: 1.1;
        margin-bottom: 20px;
        background: linear-gradient(135deg, #ffffff 0%, #a5a5a5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 20px;
        color: #999;
        line-height: 1.6;
        margin-bottom: 40px;
        max-width: 500px;
    }

    [data-testid="stFileUploader"] {
        background-color: #111;
        border: 2px dashed #333;
        border-radius: 16px;
        padding: 40px 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #7dbb42;
        background-color: #161616;
    }
    
    .showcase-card {
        background: linear-gradient(145deg, #111, #0a0a0a);
        border-radius: 30px;
        padding: 20px;
        border: 1px solid #222;
        box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        position: relative;
    }
    .badge {
        position: absolute;
        top: 20px;
        right: 20px;
        background: #7dbb42;
        color: black;
        padding: 5px 15px;
        border-radius: 12px;
        font-weight: 800;
        font-size: 12px;
        z-index: 10;
    }

    .result-container {
        margin-top: 50px;
        padding: 30px;
        background: #0f0f0f;
        border-radius: 24px;
        border: 1px solid #222;
    }

    div[data-testid="stDownloadButton"] button {
        background: #fff !important;
        color: #000 !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        border: none !important;
        padding: 12px 24px !important;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. HEADER ---
logo_data = get_image_base64("logo.png")
logo_html = f'<img src="data:image/png;base64,{logo_data}" height="40">' if logo_data else '<h2 style="margin:0; color:#7dbb42;">Pisi</h2>'

st.markdown(f"""
<div class="navbar">
    <div class="logo">{logo_html}</div>
    <div class="nav-links">
        <a href="#" class="nav-item">Özellikler</a>
        <a href="#" class="nav-item">Fiyatlandırma</a>
        <a href="#" class="login-button">Giriş Yap</a>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 5. HERO BÖLÜMÜ ---
col_text, col_img = st.columns([1.2, 1])

with col_text:
    st.markdown("""
    <div style="margin-top: 20px;">
        <h1 class="hero-title">Arka Planı<br>Saniyeler İçinde Sil.</h1>
        <p class="hero-subtitle">
            Pisi Software yapay zekası ile görsellerinizi otomatik temizleyin. 
            Tasarımcı olmanıza gerek yok, fotoğrafınızı yükleyin ve sonucu görün.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("Fotoğraf yükle veya sürükle", type=["jpg", "png", "webp"], accept_multiple_files=True)

with col_img:
    cat_orig_path = "kedi_orijinal.jpg"
    cat_clean_path = "kedi_temiz.png"
    
    if os.path.exists(cat_orig_path) and os.path.exists(cat_clean_path):
        st.markdown('<div class="showcase-card"><div class="badge">AI DEMO</div>', unsafe_allow_html=True)
        c_before, c_after = st.columns(2)
        with c_before:
            st.image(cat_orig_path, caption="Önce", use_container_width=True)
        with c_after:
            clean_img = Image.open(cat_clean_path)
            checker = create_checkerboard(clean_img.size)
            checker.paste(clean_img, mask=clean_img.split()[3])
            st.image(checker, caption="Sonra", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("💡 Demo görünümü için klasöre 'kedi_orijinal.jpg' ve 'kedi_temiz.png' dosyalarını ekleyin.")

# --- 6. İŞLEM MANTIĞI (RAM KORUMALI) ---
if uploaded_files:
    st.markdown("---")
    
    # Session Cache
    @st.cache_resource
    def get_session(): return new_session("isnet-general-use")
    session = get_session()
    
    processed_images = []

    for file in uploaded_files:
        # RAM KORUMASI 1: Resmi aç
        img = Image.open(file)
        
        # RAM KORUMASI 2: Resmi Akıllı Küçült (Max 1024px)
        # Bu işlem BiRefNet'in RAM kullanımını devasa oranda düşürür
        img = smart_resize(img, max_size=1024)

        with st.spinner(f"AI İşleniyor: {file.name}..."):
            try:
                # Silme İşlemi
                out = remove(img, session=session, alpha_matting=True, alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=10, alpha_matting_erode_size=5)
                
                buf = BytesIO()
                out.save(buf, format="PNG")
                byte_im = buf.getvalue()
                processed_images.append((f"Pisi_{file.name}.png", byte_im))
                
                check = create_checkerboard(out.size)
                check.paste(out, mask=out.split()[3])

                # SONUÇ KARTI
                st.markdown('<div class="result-container">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.image(img, caption="Orijinal", use_container_width=True)
                with col2:
                    st.image(check, caption="PisiRemover Sonucu", use_container_width=True)
                with col3:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    st.download_button("İndir", byte_im, f"Pisi_{file.name}.png", "image/png", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # RAM KORUMASI 3: Çöp Toplama
                del out
                del check
                gc.collect()

            except Exception as e:
                st.error(f"Hata oluştu: {e}")
                st.warning("Eğer hala hata alıyorsanız, daha küçük boyutlu bir resim deneyin.")

    if len(processed_images) > 1:
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as z:
            for name, data in processed_images: z.writestr(name, data)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_c, col_d, col_e = st.columns([1, 2, 1])
        with col_d:

             st.download_button("📦 TÜMÜNÜ ZIP İNDİR", zip_buf.getvalue(), "Pisi_Pack.zip", "application/zip", use_container_width=True)
