from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import ContactMessage
from app import db

bp = Blueprint('contact', __name__)

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            flash('Lütfen zorunlu alanları doldurun.', 'error')
            return render_template('contact/index.html')

        msg = ContactMessage(name=name, email=email, subject=subject, message=message)
        db.session.add(msg)
        db.session.commit()
        flash('Mesajınız alındı, teşekkürler!', 'success')
        return redirect(url_for('contact.index'))

    return render_template('contact/index.html')
