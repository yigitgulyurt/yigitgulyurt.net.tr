from flask import Blueprint, render_template, abort
from app.models import BlogPost
import markdown

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():
    posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).all()
    return render_template('blog/index.html', posts=posts)

@bp.route('/<slug>')
def detail(slug):
    post = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
    post.content_html = markdown.markdown(post.content or '', extensions=['fenced_code', 'tables'])
    return render_template('blog/detail.html', post=post)
