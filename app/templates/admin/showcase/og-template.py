import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

sitead = input("Siteyi yaz: ").strip()

# Eğer kullanıcı protokol yazmadıysa ekle
if not sitead.startswith(("http://", "https://")):
    start_url = "https://" + sitead
else:
    start_url = sitead
    
htmladraw = input("Html dosyası adnı yaz: ").strip()

if not htmladraw.endswith(".html"):
    htmlad = htmladraw + ".html"
else:
    htmlad = htmladraw
    
headers = {"User-Agent": "Mozilla/5.0"}


def get_sitemap(url):
    sitemap_url = url.rstrip("/") + "/sitemap.xml"
    r = requests.get(sitemap_url, headers=headers, timeout=10)
    if r.status_code == 200:
        return sitemap_url
    return None


def parse_sitemap(sitemap_url):
    r = requests.get(sitemap_url, headers=headers, timeout=10)
    root = ET.fromstring(r.content)

    urls = []
    for elem in root.iter():
        if "loc" in elem.tag and elem.text:
            urls.append(elem.text)

    return urls


def get_meta(url):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        og = soup.find("meta", property="og:image")
        title = soup.title.text.strip() if soup.title else "No Title"

        og_url = og["content"] if og and og.get("content") else None

        return title, og_url
    except:
        return "Error", None


# ---------------- MAIN ----------------

sitemap = get_sitemap(start_url)
urls = parse_sitemap(sitemap)

data = []

for i, url in enumerate(urls):
    print(f"[{i+1}/{len(urls)}] {url}")

    title, og_img = get_meta(url)

    data.append({
        "url": url,
        "title": title,
        "og": og_img
    })


# ---------------- HTML ----------------

html = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OG Image Dashboard</title>
<link rel="stylesheet" href="https://fonts.yigitgulyurt.net.tr/JetBrainsMonoNerd/JetBrainsMonoNLNerdFont-Regular.ttf">

<style>
:root {
    --bg: #050505;
    --card-bg: #0f0f0f;
    --border: rgba(255, 255, 255, 0.08);
    --primary: #4ade80;
    --text: #eee;
    --text-dim: #888;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'JetBrains Mono', sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 40px 20px;
    line-height: 1.5;
}

header {
    max-width: 1200px;
    margin: 0 auto 40px;
    text-align: center;
}

h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 12px;
    background: linear-gradient(to right, #fff, var(--primary));
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.stats {
    font-size: 0.9rem;
    color: var(--text-dim);
    margin-bottom: 20px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 30px;
    max-width: 1400px;
    margin: 0 auto;
}

.card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
}

.card:hover {
    transform: translateY(-8px);
    border-color: var(--primary);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
}

.card-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 16px;
    color: #fff;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.field {
    margin-bottom: 12px;
}

.label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

.value {
    font-size: 0.9rem;
    color: var(--text);
    word-break: break-all;
}

.value a {
    color: var(--primary);
    text-decoration: none;
}

.value a:hover { text-decoration: underline; }

.img-container {
    margin-top: 20px;
    position: relative;
    aspect-ratio: 1200 / 630;
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border);
}

img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.5s ease;
}

.card:hover img {
    transform: scale(1.02);
}

.badge {
    position: absolute;
    top: 10px;
    right: 10px;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.7rem;
    color: #fff;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

@media (max-width: 600px) {
    .grid { grid-template-columns: 1fr; }
    h1 { font-size: 1.8rem; }
}
</style>
</head>
<body>

<header>
    <h1>OG Image Dashboard</h1>
    <p class="stats">Toplam {len(data)} sayfa incelendi</p>
</header>

<div class="grid">
"""

for item in data:
    html += f"""
    <div class="card">
        <div class="card-title" title="{item['title']}">{item['title']}</div>

        <div class="field">
            <div class="label">🔗 Sayfa Adresi</div>
            <div class="value"><a href="{item['url']}" target="_blank">{item['url']}</a></div>
        </div>

        <div class="field">
            <div class="label">🖼️ OG Görsel Yolu</div>
            <div class="value" style="font-family: monospace; color: var(--text-dim); font-size: 0.8rem;">{item['og']}</div>
        </div>

        <div class="img-container">
            <span class="badge">1200x630</span>
            """
    if item["og"]:
        html += f'<img loading="lazy" src="{item["og"]}" alt="OG Preview"/>'
    else:
        html += '<div style="display:flex; align-items:center; justify-content:center; height:100%; color:#444;">Görsel Yok</div>'
    
    html += """
        </div>
    </div>
    """

html += """
</div>
</body>
</html>
"""


with open(htmlad, "w", encoding="utf-8") as f:
    f.write(html)

print("\nBitti -> "+ sitead +" oluşturuldu")