"""
app/routes/obsidian.py
Obsidian vault — Rclone / Local Filesystem entegrasyonu
Subdomain: obsidian.yigitgulyurt.net.tr
"""

import os
import shutil
from functools import wraps
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, session, current_app, abort
)

bp = Blueprint('obsidian', __name__, subdomain='obsidian')

def obsidian_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        pw = current_app.config.get('OBSIDIAN_PASSWORD', '')
        if not pw or session.get('obsidian_ok') != pw:
            return redirect(url_for('obsidian.login'))
        return f(*args, **kwargs)
    return decorated

def get_vault_path():
    path = current_app.config.get('OBSIDIAN_VAULT_PATH')
    if not path or not os.path.exists(path):
        current_app.logger.error(f"Vault yolu bulunamadı veya ayarlanmadı: {path}")
        return None
    return path

def build_tree(root_path, current_path=''):
    """Yerel dizin yapısını recursive olarak tarar."""
    full_path = os.path.join(root_path, current_path)
    tree = []
    
    try:
        items = os.listdir(full_path)
    except Exception as e:
        current_app.logger.error(f"Dizin listelenirken hata: {str(e)}")
        return []

    # Önce klasörler, sonra dosyalar (alfabetik)
    items.sort(key=lambda x: (not os.path.isdir(os.path.join(full_path, x)), x.lower()))

    for item in items:
        if item.startswith('.'): # Gizli dosyaları (örn: .obsidian) atla
            continue
            
        item_full_path = os.path.join(full_path, item)
        is_dir = os.path.isdir(item_full_path)
        rel_path = os.path.join(current_path, item).replace('\\', '/')
        
        try:
            stats = os.stat(item_full_path)
            modified = datetime.fromtimestamp(stats.st_mtime).isoformat()
        except:
            modified = ""

        node = {
            'id': rel_path, # Template'lerde file_id olarak geçer
            'name': item,
            'path': rel_path,
            'is_folder': is_dir,
            'modified': modified,
            'children': []
        }

        if is_dir:
            node['children'] = build_tree(root_path, rel_path)
        else:
            if not item.endswith('.md'):
                continue
        
        tree.append(node)
    return tree

# ── AUTH ROUTES ───────────────────────────────────────────────

@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        pw = current_app.config.get('OBSIDIAN_PASSWORD', '')
        if request.form.get('password') == pw:
            session['obsidian_ok'] = pw
            session.permanent = True
            return redirect(url_for('obsidian.index'))
        error = True
    return render_template('obsidian/obsidian_login.html', error=error)

@bp.route('/logout')
def logout():
    session.pop('obsidian_ok', None)
    return redirect(url_for('obsidian.login'))

# ── MAIN ROUTES ───────────────────────────────────────────────

@bp.route('/')
@obsidian_auth
def index():
    vault_path = get_vault_path()
    if not vault_path:
        return render_template('obsidian/obsidian_index.html', 
                               tree=[], error='Vault yolu sunucuda bulunamadı. Rclone mount edildiğinden emin olun.')
    
    tree = build_tree(vault_path)
    return render_template('obsidian/obsidian_index.html', tree=tree, error=None)

@bp.route('/edit/<path:file_id>')
@obsidian_auth
def edit(file_id):
    vault_path = get_vault_path()
    full_path = os.path.join(vault_path, file_id)
    
    if not os.path.exists(full_path):
        abort(404)
        
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    stats = os.stat(full_path)
    meta = {
        'id': file_id,
        'name': os.path.basename(file_id),
        'modifiedTime': datetime.fromtimestamp(stats.st_mtime).isoformat()
    }
    
    return render_template('obsidian/obsidian_edit.html', file=meta, content=content)

@bp.route('/new')
@obsidian_auth
def new():
    folder_path = request.args.get('folder_id', '') 
    return render_template('obsidian/obsidian_new.html', 
                           folder_id=folder_path,
                           vault_id='')

# ── API ROUTES ────────────────────────────────────────────────

@bp.route('/api/file/<path:file_id>', methods=['GET'])
@obsidian_auth
def api_get_file(file_id):
    vault_path = get_vault_path()
    full_path = os.path.join(vault_path, file_id)
    if not os.path.exists(full_path):
        return jsonify({'error': 'Dosya bulunamadı'}), 404
        
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'content': content})

@bp.route('/api/file/<path:file_id>', methods=['PUT'])
@obsidian_auth
def api_update_file(file_id):
    vault_path = get_vault_path()
    full_path = os.path.join(vault_path, file_id)
    data = request.get_json()
    content = data.get('content', '')
    
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/file', methods=['POST'])
@obsidian_auth
def api_create_file():
    vault_path = get_vault_path()
    data = request.get_json()
    folder_rel_path = data.get('folder_id', '')
    name = data.get('name', 'Yeni Not')
    content = data.get('content', '')
    
    if not name.endswith('.md'):
        name += '.md'
        
    full_folder_path = os.path.join(vault_path, folder_rel_path)
    os.makedirs(full_folder_path, exist_ok=True)
    
    full_file_path = os.path.join(full_folder_path, name)
    rel_file_path = os.path.join(folder_rel_path, name).replace('\\', '/')
    
    try:
        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'ok': True, 'file': {'id': rel_file_path}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/folder', methods=['POST'])
@obsidian_auth
def api_create_folder():
    vault_path = get_vault_path()
    data = request.get_json()
    parent_rel_path = data.get('parent_id', '')
    name = data.get('name', 'Yeni Klasör')
    
    full_path = os.path.join(vault_path, parent_rel_path, name)
    
    try:
        os.makedirs(full_path, exist_ok=True)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/file/<path:file_id>', methods=['DELETE'])
@obsidian_auth
def api_delete_file(file_id):
    vault_path = get_vault_path()
    full_path = os.path.join(vault_path, file_id)
    
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/tree')
@obsidian_auth
def api_tree():
    vault_path = get_vault_path()
    if not vault_path:
        return jsonify([])
    tree = build_tree(vault_path)
    return jsonify(tree)
