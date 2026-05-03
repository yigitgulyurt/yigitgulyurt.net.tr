from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Admin, Project, BlogPost, ContactMessage
from app import db
import re

bp = Blueprint('admin', __name__)

import re

def slugify(text):
    text = text.lower().strip()
    
    # Türkçe karakter dönüşümü
    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u"
    }
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    
    # boşlukları tire yap
    text = re.sub(r'[\s]+', '-', text)
    
    # geçersiz karakterleri temizle
    text = re.sub(r'[^\w\-]', '', text)
    
    return text

# --- Auth ---

@bp.route('/giris', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        user = Admin.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Hatalı kullanıcı adı veya şifre.', 'error')
    return render_template('admin/login.html')

@bp.route('/cikis')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/')
@login_required
def dashboard():
    stats = {
        'projects': Project.query.count(),
        'posts': BlogPost.query.count(),
        'messages': ContactMessage.query.filter_by(read=False).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)

# --- Projects ---

@bp.route('/projeler')
@login_required
def projects():
    projects = Project.query.order_by(Project.order).all()
    return render_template('admin/projects.html', projects=projects)

@bp.route('/projeler/yeni', methods=['GET', 'POST'])
@bp.route('/projeler/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
def project_edit(id=None):
    project = Project.query.get_or_404(id) if id else Project()
    if request.method == 'POST':
        project.title = request.form['title']
        project.slug = request.form.get('slug') or slugify(request.form['title'])
        project.description = request.form.get('description')
        project.tech_stack = request.form.get('tech_stack')
        # Resim yükleme
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'img', 'projects')
            os.makedirs(upload_dir, exist_ok=True)
            image_file.save(os.path.join(upload_dir, filename))
            project.image = filename
        project.content = request.form.get('content')
        project.live_url = request.form.get('live_url')
        project.github_url = request.form.get('github_url')
        project.featured = bool(request.form.get('featured'))
        project.order = int(request.form.get('order') or 0)
        if not id:
            db.session.add(project)
        db.session.commit()
        flash('Proje kaydedildi.', 'success')
        return redirect(url_for('admin.projects'))
    return render_template('admin/project_edit.html', project=project)

@bp.route('/projeler/<int:id>/sil', methods=['POST'])
@login_required
def project_delete(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Proje silindi.', 'success')
    return redirect(url_for('admin.projects'))

# --- Blog ---

@bp.route('/blog')
@login_required
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog.html', posts=posts)

@bp.route('/blog/yeni', methods=['GET', 'POST'])
@bp.route('/blog/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
def post_edit(id=None):
    post = BlogPost.query.get_or_404(id) if id else BlogPost()
    if request.method == 'POST':
        post.title = request.form['title']
        post.slug = request.form.get('slug') or slugify(request.form['title'])
        post.summary = request.form.get('summary')
        post.content = request.form.get('content')
        post.published = bool(request.form.get('published'))
        if not id:
            db.session.add(post)
        db.session.commit()
        flash('Yazı kaydedildi.', 'success')
        return redirect(url_for('admin.blog'))
    return render_template('admin/post_edit.html', post=post)

@bp.route('/blog/<int:id>/sil', methods=['POST'])
@login_required
def post_delete(id):
    post = BlogPost.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash('Yazı silindi.', 'success')
    return redirect(url_for('admin.blog'))

# --- Markdown Preview ---

@bp.route('/preview', methods=['POST'])
@login_required
def preview():
    from flask import jsonify
    import markdown as md
    text = request.form.get('content', '')
    html = md.markdown(text, extensions=['fenced_code', 'tables'])
    return jsonify({'html': html})

# --- Stream Config ---

@bp.route('/yayin', methods=['GET', 'POST'])
@login_required
def stream_config():
    from app.models import StreamConfig
    cfg = StreamConfig.get()
    if request.method == 'POST':
        new_key = request.form.get('stream_key', '').strip()
        if new_key:
            cfg.stream_key = new_key
        cfg.show_section = bool(request.form.get('show_section'))
        cfg.title = request.form.get('title', '').strip() or 'Canlı Yayın'
        cfg.subtitle = request.form.get('subtitle', '').strip()
        db.session.commit()
        flash('Yayın ayarları güncellendi.', 'success')
        return redirect(url_for('admin.stream_config'))
    return render_template('admin/stream_config.html', cfg=cfg)

# --- Stream Viewers ---

@bp.route('/izleyiciler')
@login_required
def stream_viewers():
    import json, time
    viewers = []
    try:
        import redis as redis_lib
        import os
        r = redis_lib.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
        keys = r.keys('yg_viewer:*')
        now = int(time.time())
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
                ttl = r.ttl(key)
                data['since'] = now - data.get('last_seen', now)
                data['ttl'] = ttl
                viewers.append(data)
            except Exception:
                pass
        viewers.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
    except Exception as e:
        viewers = []
    return render_template('admin/stream_viewers.html', viewers=viewers)

# --- Messages ---

@bp.route('/mesajlar')
@login_required
def messages():
    msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=msgs)

@bp.route('/mesajlar/<int:id>')
@login_required
def message_detail(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.read = True
    db.session.commit()
    return render_template('admin/message_detail.html', message=msg)

# --- Og ---

@bp.route('/og')
@login_required
def og():
    return render_template('admin/showcase/og.html')

@bp.route('/og/yigitgulyurt.net.tr')
@login_required
def yigitgulyurt_og():
    return render_template('admin/showcase/yigitgulyurt.html')

@bp.route('/og/cagrivakti.com.tr')
@login_required
def cagrivakti_og():
    return render_template('admin/showcase/cagrivakti.html')
