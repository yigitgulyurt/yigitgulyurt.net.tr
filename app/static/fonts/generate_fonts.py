import os
import re

def generate_font_css(fonts_dir, base_url="https://fonts.yigitgulyurt.net.tr"):
    """
    Belirtilen dizindeki font dosyalarını tarar ve her font ailesi için 
    kendi klasöründe ayrı bir CSS dosyası oluşturur.
    """
    # Font ağırlığı haritası
    weight_map = {
        'Thin': '100',
        'ExtraLight': '200',
        'Light': '300',
        'Regular': '400',
        'Medium': '500',
        'SemiBold': '600',
        'Bold': '700',
        'ExtraBold': '800',
        'Black': '900'
    }

    # Font ailesine göre CSS içeriklerini tutacak sözlük
    # { '': ['@font-face...', ...], 'JetBrainsMono': [...] }
    family_css = {}

    # Klasörleri gez
    for root, dirs, files in os.walk(fonts_dir):
        for file in files:
            if file.endswith(('.ttf', '.woff2', '.woff')):
                name_no_ext = os.path.splitext(file)[0]
                
                # Font ailesini tahmin et (Örn: -Bold -> )
                # Önce alt klasör ismine bak, yoksa dosya adından çıkar
                rel_dir = os.path.basename(root)
                if rel_dir and rel_dir != 'fonts':
                    family = rel_dir
                else:
                    family_match = re.match(r'^([^_|-]+)', name_no_ext)
                    family = family_match.group(1) if family_match else "UnknownFont"
                
                if family not in family_css:
                    family_css[family] = ["/* Auto-generated Font CSS for " + family + " */"]
                
                style = "normal"
                if "Italic" in name_no_ext or "italic" in name_no_ext:
                    style = "italic"
                
                weight = "400"
                for key, val in weight_map.items():
                    if key in name_no_ext:
                        weight = val
                        break
                
                # URL yolunu oluştur
                rel_path = os.path.relpath(os.path.join(root, file), fonts_dir).replace("\\", "/")
                full_url = f"{base_url}/{rel_path}"
                
                # Uzantıya göre format belirle
                font_format = "truetype"
                if file.endswith('.woff2'): font_format = "woff2"
                elif file.endswith('.woff'): font_format = "woff"
                
                font_face = f"""
@font-face {{
  font-family: '{family}';
  src: url('{full_url}') format('{font_format}');
  font-weight: {weight};
  font-style: {style};
  font-display: swap;
}}"""
                family_css[family].append(font_face)

    # Her aile için ayrı dosya oluştur
    for family, content in family_css.items():
        # Dosya yolunu belirle: fonts/Family/family.css (küçük harf)
        family_dir = os.path.join(fonts_dir, family)
        if not os.path.exists(family_dir):
            os.makedirs(family_dir)
            
        output_file = os.path.join(family_dir, f"{family.lower()}.css")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        
        print(f"✅ {family} için CSS oluşturuldu: {output_file}")

if __name__ == "__main__":
    # Yapılandırma
    # Not: Script klasörlerin içinde olduğu için yolu dinamik alıyoruz
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Eğer script fonts klasörünün içindeyse, FONTS_PATH burasıdır
    if os.path.basename(current_dir) == 'fonts':
        generate_font_css(current_dir)
    else:
        # Değilse eski sabit yolu dene
        FONTS_PATH = r"c:\Users\Yiğit Gülyurt\Desktop\klasörler\yigitgulyurt.net.tr\app\static\fonts"
        if os.path.exists(FONTS_PATH):
            generate_font_css(FONTS_PATH)
        else:
            print("❌ Hata: Font dizini bulunamadı!")
