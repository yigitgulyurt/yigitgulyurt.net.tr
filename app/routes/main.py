from flask import Blueprint, render_template, Response, url_for, current_app, request, jsonify, redirect
from app.models import Project, BlogPost, StreamConfig, QrRedirect
from app import db
from datetime import datetime
import random
import string
import re
from urllib.parse import urlparse, parse_qs

bp = Blueprint('main', __name__)

def generate_id(length=7):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def extract_slug(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Kapsamlı Domain Map
        domain_map = {
            # Video & Stream
            'youtube.com': 'yt', 'youtu.be': 'yt', 'twitch.tv': 'tv', 'vimeo.com': 'vm', 'netflix.com': 'nf',
            # Sosyal Medya
            'twitter.com': 'tw', 'x.com': 'tw', 'instagram.com': 'ig', 'facebook.com': 'fb', 'fb.com': 'fb',
            'tiktok.com': 'tk', 'reddit.com': 'rd', 'linkedin.com': 'ln', 'pinterest.com': 'pin',
            # Müzik
            'spotify.com': 'sp', 'open.spotify.com': 'sp', 'soundcloud.com': 'sc', 'music.apple.com': 'am',
            # Yazılım & Geliştirme
            'github.com': 'gh', 'gitlab.com': 'gl', 'stackoverflow.com': 'so', 'codepen.io': 'cp',
            'medium.com': 'md', 'dev.to': 'dev', 'behance.net': 'be', 'dribbble.com': 'dr',
            # Diğer Popüler
            'amazon.com': 'amz', 'amazon.com.tr': 'amz', 'wikipedia.org': 'wiki', 'discord.com': 'dc',
            'steamcommunity.com': 'st', 'steampowered.com': 'st', 't.me': 'tg', 'telegram.org': 'tg'
        }
        
        short_domain = domain_map.get(domain)
        if not short_domain:
            # Subdomain kontrolü (örn: open.spotify.com -> sp)
            for d, code in domain_map.items():
                if domain.endswith('.' + d):
                    short_domain = code
                    break
        
        if not short_domain:
            short_domain = domain.split('.')[0][:10]
        
        # 1. Query parametrelerini kontrol et
        qs = parse_qs(parsed.query)
        # Önemli parametreler listesi
        param_keys = ['v', 'id', 'p', 'slug', 'article', 'track', 'album', 's', 'post']
        for key in param_keys:
            if key in qs and qs[key]:
                val = qs[key][0]
                if len(val) >= 3:
                    return short_domain, clean_slug(val)
        
        # 2. Path segmentlerini kontrol et
        path_parts = [p for p in parsed.path.split('/') if p]
        if path_parts:
            # Belirleyici anahtar kelimeler (örn: /track/ID, /p/ID, /watch/ID)
            trigger_keywords = [
                'track', 'album', 'playlist', 'u', 'user', 'posts', 'p', 'watch', 
                'video', 'article', 'item', 'product', 'groups', 'community', 'channel'
            ]
            for i, part in enumerate(path_parts[:-1]):
                if part.lower() in trigger_keywords:
                    return short_domain, clean_slug(path_parts[i+1])
            
            # Eğer özel bir tetikleyici yoksa son anlamlı parçayı al
            last_segment = path_parts[-1]
            if '.' in last_segment:
                last_segment = last_segment.rsplit('.', 1)[0]
            
            if len(last_segment) >= 3:
                # Domain ismiyle aynıysa boş dön (örn: twitter.com/)
                if last_segment.lower() in [short_domain.lower(), domain.split('.')[0].lower()]:
                    return short_domain, None
                return short_domain, clean_slug(last_segment)
                
        return short_domain, None
    except Exception:
        pass
    return "link", None

def clean_slug(text):
    text = text.lower()
    # Spotify ID'leri ve benzerleri için alfanumerik karakterleri koru
    text = re.sub(r'[^a-z0-9\-_]', '', text)
    return text[:30] # Spotify ID'leri 22 karakterdir, sınırı biraz artırdık

@bp.route('/')
def index():
    featured_projects = Project.query.filter_by(featured=True).order_by(Project.order).limit(3).all()
    recent_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
    stats = {
        'projects': Project.query.count(),
        'posts': BlogPost.query.filter_by(published=True).count(),
    }

    # Canlı yayın section kontrolü — DB'den
    stream_config = StreamConfig.get()
    show_stream = stream_config.show_section
    stream_live = False
    if show_stream:
        try:
            import requests as req_lib
            key = stream_config.stream_key or current_app.config.get('STREAM_KEY', '')
            r = req_lib.get('http://localhost:9997/v3/paths/list', timeout=1)
            items = r.json().get('items', [])
            path = next((p for p in items if p.get('name') == f'canli/{key}'), None)
            stream_live = bool(path and path.get('ready'))
        except Exception:
            stream_live = False

    return render_template('main/index.html',
                           featured_projects=featured_projects,
                           recent_posts=recent_posts,
                           stats=stats,
                           show_stream=show_stream,
                           stream_live=stream_live,
                           stream_config=stream_config)

@bp.route('/Mustafa-Kemal-Ataturk')
def ataturk():
    return render_template('main/ataturk.html')

@bp.route('/hakkimda')
def about():
    projects = Project.query.order_by(Project.order, Project.created_at.desc()).all()
    return render_template('main/about.html', projects=projects)

@bp.route('/cv')
def cv():
    projects = Project.query.order_by(Project.order, Project.created_at.desc()).all()
    return render_template('main/cv.html', projects=projects)

@bp.route('/sitemap.xml')
def sitemap():
    pages = []
    base = 'https://yigitgulyurt.net.tr'

    static_pages = [
        ('main.ataturk',   '0.8',  'monthly'),
        ('main.index',    '1.0',  'weekly'),
        ('main.about',    '0.8',  'monthly'),
        ('main.cv',       '0.7',  'monthly'),
        ('projects.index','0.9',  'weekly'),
        ('blog.index',    '0.9',  'weekly'),
        ('contact.index', '0.5',  'monthly'),
        ('main.qr_okuyucu', '0.8',  'monthly')
    ]
    for endpoint, priority, changefreq in static_pages:
        pages.append({
            'loc': base + url_for(endpoint),
            'priority': priority,
            'changefreq': changefreq,
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
        })

    for p in Project.query.all():
        pages.append({
            'loc': base + url_for('projects.detail', slug=p.slug),
            'priority': '0.8',
            'changefreq': 'monthly',
            'lastmod': p.created_at.strftime('%Y-%m-%d'),
        })

    for post in BlogPost.query.filter_by(published=True).all():
        pages.append({
            'loc': base + url_for('blog.detail', slug=post.slug),
            'priority': '0.7',
            'changefreq': 'monthly',
            'lastmod': post.updated_at.strftime('%Y-%m-%d'),
        })

    xml = render_template('main/sitemap.xml', pages=pages)
    return Response(xml, mimetype='application/xml')

@bp.route('/api/shorten', methods=['POST'])
def shorten():
    data = request.get_json(silent=True, force=True)
    if not data:
        return jsonify({'error': 'JSON parse edilemedi'}), 400
    
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL gerekli'}), 400
    
    existing = QrRedirect.query.filter_by(url=url).first()
    if existing:
        return jsonify({
            'short_id': existing.id,
            'short_domain': existing.short_domain or 'r'
        })
    
    # URL'den anlamlı parçalar çıkarmaya çalış
    short_domain_val, slug = extract_slug(url)
    
    if slug:
        short_id = slug
        # Eğer bu slug zaten varsa sonuna kısa bir random ekle
        if QrRedirect.query.get(short_id):
            short_id = f"{slug}-{generate_id(3)}"
            while QrRedirect.query.get(short_id):
                short_id = f"{slug}-{generate_id(3)}"
    else:
        short_id = generate_id()
        while QrRedirect.query.get(short_id):
            short_id = generate_id()
    
    redirect_obj = QrRedirect(id=short_id, short_domain=short_domain_val, url=url)
    db.session.add(redirect_obj)
    db.session.commit()
    
    return jsonify({
        'short_id': short_id,
        'short_domain': short_domain_val
    })

@bp.route('/r/<short_id>')
@bp.route('/r/<short_domain>/<short_id>')
def redirect_url(short_id, short_domain=None):
    # short_domain opsiyonel, eski linklerin çalışması için hem tekli hem ikili rotayı destekliyoruz
    obj = QrRedirect.query.get_or_404(short_id)
    obj.hit_count += 1
    db.session.commit()
    return redirect(obj.url)

@bp.route('/qr-okuyucu')
def qr_okuyucu():
    return render_template('qr-reader/qr-reader.html')

@bp.route('/robots.txt')
def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "\n"
        "Sitemap: https://yigitgulyurt.net.tr/sitemap.xml\n"
    )
    return Response(content, mimetype='text/plain')


@bp.route('/og')
def og():
    return render_template('showcase/og.html')

@bp.route('/og/yigitgulyurt.net.tr')
def yigitgulyurt_og():
    return render_template('showcase/yigitgulyurt.html')

@bp.route('/og/cagrivakti.com.tr')
def cagrivakti_og():
    return render_template('showcase/cagrivakti.html')
