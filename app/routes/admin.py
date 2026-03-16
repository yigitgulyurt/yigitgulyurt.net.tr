from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Admin, Project, BlogPost, ContactMessage
from app import db
import re

bp = Blueprint('admin', __name__)

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[\s]+', '-', text)
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
