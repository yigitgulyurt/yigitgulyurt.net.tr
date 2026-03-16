from flask import Blueprint, render_template
from app.models import Project, BlogPost

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    featured_projects = Project.query.filter_by(featured=True).order_by(Project.order).limit(3).all()
    recent_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
    stats = {
        'projects': Project.query.count(),
        'posts': BlogPost.query.filter_by(published=True).count(),
    }
    return render_template('main/index.html',
                           featured_projects=featured_projects,
                           recent_posts=recent_posts,
                           stats=stats)

@bp.route('/hakkimda')
def about():
    return render_template('main/about.html')
