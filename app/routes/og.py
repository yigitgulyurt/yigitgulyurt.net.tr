"""
og.py — Dinamik OG Image Üretici
=================================
Kullanım: /og-image?title=...&subtitle=...&theme=...&prompt=...&domain=...

Parametreler:
  title    — Ana başlık metni           (max 80 karakter)
  subtitle — Alt başlık metni           (max 100 karakter)
  theme    — Renk teması                (default|live|ataturk|blog|project)
  prompt   — Sol üstteki terminal komutu (max 60 karakter)
  domain   — Sağ alttaki domain metni  (max 50 karakter)

Örnek:
  /og-image?title=Yiğit+Gülyurt&subtitle=Full-Stack+Developer&theme=default&domain=yigitgulyurt.net.tr
"""

import io
from flask import Blueprint, request, send_file
from PIL import Image, ImageDraw, ImageFont

bp = Blueprint('og', __name__)

# ─────────────────────────────────────────────
# GÖRSEL BOYUTLARI
# ─────────────────────────────────────────────
W = 1200   # genişlik (piksel)
H = 630    # yükseklik (piksel)

# ─────────────────────────────────────────────
# RENK TEMALAR
# Her tema: bg, accent, accent2, text, text2
#   bg       — arka plan rengi
#   accent   — üst çizgi, prompt ve sol vurgu rengi
#   accent2  — domain ve bracket rengi
#   text     — ana başlık rengi
#   text2    — alt başlık rengi
# ─────────────────────────────────────────────
THEMES = {
    'default': {
        'bg':      '#0d0d0d',
        'accent':  '#4ade80',   # yeşil
        'accent2': '#60a5fa',   # mavi
        'text':    '#e2e2e2',
        'text2':   '#666666',
    },
    'live': {
        'bg':      '#0d0d0d',
        'accent':  '#f87171',   # kırmızı
        'accent2': '#60a5fa',   # mavi
        'text':    '#e2e2e2',
        'text2':   '#666666',
    },
    'ataturk': {
        'bg':      '#080808',
        'accent':  '#e30a17',   # Türk kırmızısı
        'accent2': '#c5a059',   # altın
        'text':    '#f0f0f0',
        'text2':   '#777777',
    },
    'blog': {
        'bg':      '#0d0d0d',
        'accent':  '#60a5fa',   # mavi
        'accent2': '#4ade80',   # yeşil
        'text':    '#e2e2e2',
        'text2':   '#666666',
    },
    'project': {
        'bg':      '#0d0d0d',
        'accent':  '#4ade80',   # yeşil
        'accent2': '#a78bfa',   # mor
        'text':    '#e2e2e2',
        'text2':   '#666666',
    },
}

# ─────────────────────────────────────────────
# FONT YOLLARI (Ubuntu/Debian sunucu için)
# Farklı bir sunucuda çalışıyorsa bu yolları güncelle
# ─────────────────────────────────────────────
FONT_BOLD = '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf'
FONT_REG  = '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf'

# ─────────────────────────────────────────────
# DİZAYN SABİTLERİ
# ─────────────────────────────────────────────
PAD         = 64    # sol/sağ kenar boşluğu
MARGIN      = 40    # domain kutusu kenar boşluğu
DOM_PAD_X   = 16    # domain etrafı yatay iç boşluk
DOM_PAD_Y   = 10    # domain etrafı dikey iç boşluk
DOM_FONT_SZ = 20    # domain font boyutu
PROMPT_SZ   = 22    # prompt font boyutu
SUBTITLE_SZ = 26    # alt başlık font boyutu
BRACKET_LW  = 2     # bracket çizgi kalınlığı
TITLE_SIZES = (72, 58, 46, 36, 28)  # başlık için denenen font boyutları

# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────

def _hex(h):
    """#rrggbb → (r, g, b) tuple"""
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _font(path, size):
    """Font yükle, bulamazsa varsayılanı kullan"""
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def _fit_title(d, text, max_width):
    """Başlığı taşırmadan sığacak en büyük font boyutunu bul"""
    for size in TITLE_SIZES:
        f = _font(FONT_BOLD, size)
        if d.textbbox((0, 0), text, font=f)[2] < max_width:
            return f, size
    return _font(FONT_BOLD, TITLE_SIZES[-1]), TITLE_SIZES[-1]

def _draw_bracket(d, x1, y1, x2, y2, color):
    """
    4 köşeli bracket çerçevesi çizer.
    Kol uzunluğu kutu genişliğiyle orantılıdır:
      arm = max(20, min(36, genişlik × 0.18))
    """
    lw  = BRACKET_LW
    arm = max(20, min(36, int((x2 - x1) * 0.18)))

    # Sol üst ⌐
    d.rectangle([x1,        y1,        x1 + arm, y1 + lw], fill=color)
    d.rectangle([x1,        y1,        x1 + lw,  y1 + arm], fill=color)
    # Sağ üst
    d.rectangle([x2 - arm,  y1,        x2,        y1 + lw], fill=color)
    d.rectangle([x2 - lw,   y1,        x2,        y1 + arm], fill=color)
    # Sol alt
    d.rectangle([x1,        y2 - lw,   x1 + arm,  y2], fill=color)
    d.rectangle([x1,        y2 - arm,  x1 + lw,   y2], fill=color)
    # Sağ alt ¬
    d.rectangle([x2 - arm,  y2 - lw,   x2,        y2], fill=color)
    d.rectangle([x2 - lw,   y2 - arm,  x2,        y2], fill=color)

# ─────────────────────────────────────────────
# ANA GÖRSEL ÜRETİCİ
# ─────────────────────────────────────────────

def make_og(title, subtitle, theme, prompt, domain):
    t   = THEMES.get(theme, THEMES['default'])
    img = Image.new('RGB', (W, H), _hex(t['bg']))
    d   = ImageDraw.Draw(img)

    # 1. Üst accent çizgisi
    d.rectangle([0, 0, W, 3], fill=_hex(t['accent']))

    # 2. Prompt (sol üst)
    f_prompt = _font(FONT_REG, PROMPT_SZ)
    d.text((PAD, 48), prompt, font=f_prompt, fill=_hex(t['accent']))

    # 3. Ana başlık (dikey merkez üstü)
    f_title, title_size = _fit_title(d, title, W - PAD * 2)
    title_y = H // 2 - title_size - 16
    d.text((PAD, title_y), title, font=f_title, fill=_hex(t['text']))

    # 4. Alt başlık
    f_sub = _font(FONT_REG, SUBTITLE_SZ)
    d.text((PAD, title_y + title_size + 20), subtitle,
           font=f_sub, fill=_hex(t['text2']))

    # 5. Domain + bracket (sağ alt)
    f_domain = _font(FONT_REG, DOM_FONT_SZ)
    db = d.textbbox((0, 0), domain, font=f_domain)
    dw, dh = db[2] - db[0], db[3] - db[1]

    # Bracket kutu sınırları
    bx1 = W - MARGIN - dw - DOM_PAD_X * 2
    by1 = H - MARGIN - dh - DOM_PAD_Y * 2
    bx2 = W - MARGIN
    by2 = H - MARGIN

    # Domain metni
    d.text((bx1 + DOM_PAD_X, by1 + DOM_PAD_Y),
           domain, font=f_domain, fill=_hex(t['accent2']))

    # Bracket çerçevesi
    _draw_bracket(d, bx1, by1, bx2, by2, _hex(t['accent2']))

    return img

# ─────────────────────────────────────────────
# FLASK ROUTE
# ─────────────────────────────────────────────

@bp.route('/og-image')
def og_image():
    title    = request.args.get('title',    'Yiğit Gülyurt')[:80]
    subtitle = request.args.get('subtitle', '')[:100]
    theme    = request.args.get('theme',    'default')
    prompt   = request.args.get('prompt',   '$ whoami')[:60]
    domain   = request.args.get('domain',   'yigitgulyurt.net.tr')[:50]

    img = make_og(title, subtitle, theme, prompt, domain)
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    buf.seek(0)

    resp = send_file(buf, mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp
