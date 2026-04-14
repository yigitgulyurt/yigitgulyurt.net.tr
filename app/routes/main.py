from flask import Blueprint, render_template, Response, url_for, current_app, request, jsonify, redirect
from app.models import Project, BlogPost, StreamConfig, QrRedirect
from app import db
from datetime import datetime
import random
import string

bp = Blueprint('main', __name__)

def generate_id(length=7):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

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

@bp.route('/ataturk')
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
        ('main.index',    '1.0',  'weekly'),
        ('main.about',    '0.8',  'monthly'),
        ('main.cv',       '0.7',  'monthly'),
        ('projects.index','0.9',  'weekly'),
        ('blog.index',    '0.9',  'weekly'),
        ('contact.index', '0.5',  'monthly'),
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
        return jsonify({'short_id': existing.id})
    
    short_id = generate_id()
    while QrRedirect.query.get(short_id):
        short_id = generate_id()
    
    redirect_obj = QrRedirect(id=short_id, url=url)
    db.session.add(redirect_obj)
    db.session.commit()
    
    return jsonify({'short_id': short_id})

@bp.route('/r/<short_id>')
def redirect_url(short_id):
    obj = QrRedirect.query.get_or_404(short_id)
    obj.hit_count += 1
    db.session.commit()
    return redirect(obj.url)

@bp.route('/qr-okuyucu')
def qr_okuyucu():
    return render_template('main/qr-reader.html')

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