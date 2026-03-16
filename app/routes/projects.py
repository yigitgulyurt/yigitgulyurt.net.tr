from flask import Blueprint, render_template
from app.models import Project
import markdown

bp = Blueprint('projects', __name__)

@bp.route('/')
def index():
    projects = Project.query.order_by(Project.order, Project.created_at.desc()).all()
    return render_template('projects/index.html', projects=projects)

@bp.route('/<slug>')
def detail(slug):
    project = Project.query.filter_by(slug=slug).first_or_404()
    project.content_html = markdown.markdown(
        project.content or '',
        extensions=['fenced_code', 'tables']
    )
    return render_template('projects/detail.html', project=project)
