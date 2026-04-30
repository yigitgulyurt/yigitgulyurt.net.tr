"""
app/routes/obsidian.py
Obsidian vault — Rclone / Local Filesystem entegrasyonu
Subdomain: obsidian.yigitgulyurt.net.tr
"""

import re
import os
import time
import shutil
from functools import wraps
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, session, current_app, abort, send_from_directory
)
from werkzeug.utils import secure_filename

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
    return os.path.abspath(path)

def safe_join(vault_path, *paths):
    """Güvenli yol birleştirme ve vault dışına çıkış kontrolü."""
    full_path = os.path.abspath(os.path.join(vault_path, *paths))
    if not full_path.startswith(vault_path):
        abort(403)
    return full_path

def update_recent_files(file_id):
    """Son kullanılan dosyalar listesini günceller."""
    recent = session.get('obsidian_recent', [])
    if file_id in recent:
        recent.remove(file_id)
    recent.insert(0, file_id)
    session['obsidian_recent'] = recent[:10] # Son 10 dosya
    session.modified = True

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
        actual_path = current_app.config.get('OBSIDIAN_VAULT_PATH', '/mnt/obsidian')
        error_msg = f'Vault yolu ({actual_path}) sunucuda bulunamadı veya erişilemiyor. Rclone mount ve izinleri kontrol edin.'
        return render_template('obsidian/obsidian_index.html', 
                               tree=[], error=error_msg, recent=[])
    
    tree = build_tree(vault_path)
    recent = session.get('obsidian_recent', [])
    # Recent listesindeki dosyaların hala var olduğunu doğrula
    valid_recent = []
    for r_id in recent:
        if os.path.exists(os.path.join(vault_path, r_id)):
            valid_recent.append({'id': r_id, 'name': os.path.basename(r_id)})
    
    return render_template('obsidian/obsidian_index.html', 
                           tree=tree, 
                           recent=valid_recent,
                           error=None)

@bp.route('/edit/<path:file_id>')
@obsidian_auth
def edit(file_id):
    vault_path = get_vault_path()
    full_path = safe_join(vault_path, file_id)
    
    if not os.path.exists(full_path):
        abort(404)
    
    update_recent_files(file_id)
        
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
    full_path = safe_join(vault_path, file_id)
    if not os.path.exists(full_path):
        return jsonify({'error': 'Dosya bulunamadı'}), 404
    
    update_recent_files(file_id)
        
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'content': content})

@bp.route('/api/file/<path:file_id>', methods=['PUT'])
@obsidian_auth
def api_update_file(file_id):
    vault_path = get_vault_path()
    full_path = safe_join(vault_path, file_id)
    data = request.get_json()
    content = data.get('content', '')
    
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        update_recent_files(file_id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/file', methods=['POST'])
@obsidian_auth
def api_create_file():
    vault_path = get_vault_path()
    data = request.get_json()
    folder_rel_path = data.get('folder_id', '')
    raw_name = data.get('name', 'Yeni Not').strip()
    content = data.get('content', '')
    
    # "folder/note" veya "folder/" mantığı
    if '/' in raw_name:
        parts = raw_name.split('/')
        # Son parça boşsa bu bir klasör oluşturma isteğidir
        is_only_folder = raw_name.endswith('/')
        
        if is_only_folder:
            # Sadece klasör oluştur
            new_folder_rel = os.path.join(folder_rel_path, raw_name.rstrip('/'))
            full_folder_path = os.path.join(vault_path, new_folder_rel)
            os.makedirs(full_folder_path, exist_ok=True)
            return jsonify({'ok': True, 'type': 'folder'})
        else:
            # Klasör(leri) ve dosyayı oluştur
            file_name = parts[-1]
            sub_folders = '/'.join(parts[:-1])
            folder_rel_path = os.path.join(folder_rel_path, sub_folders)
            name = file_name
    else:
        name = raw_name

    if not name.endswith('.md'):
        name += '.md'
        
    full_folder_path = safe_join(vault_path, folder_rel_path)
    os.makedirs(full_folder_path, exist_ok=True)
    
    full_file_path = safe_join(full_folder_path, name)
    rel_file_path = os.path.relpath(full_file_path, vault_path).replace('\\', '/')
    
    try:
        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        update_recent_files(rel_file_path)
        return jsonify({'ok': True, 'file': {'id': rel_file_path}, 'type': 'file'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/folder', methods=['POST'])
@obsidian_auth
def api_create_folder():
    vault_path = get_vault_path()
    data = request.get_json()
    parent_rel_path = data.get('parent_id', '')
    name = data.get('name', 'Yeni Klasör')
    
    full_path = safe_join(vault_path, parent_rel_path, name)
    
    try:
        os.makedirs(full_path, exist_ok=True)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/file/<path:file_id>', methods=['DELETE'])
@obsidian_auth
def api_delete_file(file_id):
    vault_path = get_vault_path()
    full_path = safe_join(vault_path, file_id)
    
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        # Recent listesinden sil
        recent = session.get('obsidian_recent', [])
        if file_id in recent:
            recent.remove(file_id)
            session['obsidian_recent'] = recent
            session.modified = True
            
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/rename', methods=['POST'])
@obsidian_auth
def api_rename():
    vault_path = get_vault_path()
    data = request.get_json()
    old_rel_path = data.get('old_path')
    new_name = data.get('new_name')
    
    if not old_rel_path or not new_name:
        return jsonify({'error': 'Geçersiz parametre'}), 400
        
    old_full_path = safe_join(vault_path, old_rel_path)
    parent_dir = os.path.dirname(old_full_path)
    
    # Eğer dosya ise uzantıyı koru
    if os.path.isfile(old_full_path) and not new_name.endswith('.md'):
        new_name += '.md'
        
    new_full_path = safe_join(parent_dir, new_name)
    
    try:
        os.rename(old_full_path, new_full_path)
        new_rel_path = os.path.relpath(new_full_path, vault_path).replace('\\', '/')
        
        # Recent listesinde güncelle
        recent = session.get('obsidian_recent', [])
        if old_rel_path in recent:
            idx = recent.index(old_rel_path)
            recent[idx] = new_rel_path
            session['obsidian_recent'] = recent
            session.modified = True
            
        return jsonify({'ok': True, 'new_path': new_rel_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/media/<path:filename>')
@obsidian_auth
def serve_media(filename):
    """Vault içindeki resim ve diğer medya dosyalarını sunar."""
    vault_path = get_vault_path()
    if not vault_path:
        abort(404)
    
    # Güvenlik kontrolü: vault dışına çıkılmasını engelle
    full_path = os.path.normpath(os.path.join(vault_path, filename))
    if not full_path.startswith(os.path.normpath(vault_path)):
        abort(403)
        
    if not os.path.exists(full_path):
        # Eğer dosya tam yolda bulunamazsa, vault içinde ismen ara (Obsidian tarzı)
        file_only = os.path.basename(filename).lower()
        for root, dirs, files in os.walk(vault_path):
            # .obsidian klasörünü atla
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.lower() == file_only:
                    return send_from_directory(root, f)
        
        current_app.logger.error(f"Medya dosyası bulunamadı: {filename} (Yol: {full_path})")
        abort(404)
        
    return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path))

# Arama sonuçları için basit bir bellek içi önbellek
_search_cache = {
    'last_scan': 0,
    'files': {} # {rel_path: {'content': '...', 'mtime': ...}}
}

@bp.route('/api/daily-note')
@obsidian_auth
def api_daily_note():
    """Bugünün tarihli notunu bulur veya oluşturur."""
    vault_path = get_vault_path()
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}.md"
    
    # "Daily" klasörü varsa oraya, yoksa root'a
    daily_dir = safe_join(vault_path, "Daily")
    if os.path.isdir(daily_dir):
        rel_path = f"Daily/{filename}"
    else:
        rel_path = filename
        
    full_path = safe_join(vault_path, rel_path)
    if not os.path.exists(full_path):
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(f"# {today}\n\n")
            
    update_recent_files(rel_path)
    return jsonify({'ok': True, 'path': rel_path})

@bp.route('/api/upload', methods=['POST'])
@obsidian_auth
def api_upload():
    """Vault'a dosya yükler."""
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'Dosya seçilmedi'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'ok': False, 'error': 'Dosya adı boş'})
        
    vault_path = get_vault_path()
    filename = secure_filename(file.filename)
    
    # Root'a kaydet (User isteğine göre değişebilir)
    target_path = safe_join(vault_path, filename)
    file.save(target_path)
    
    return jsonify({'ok': True, 'filename': filename})

@bp.route('/api/backlinks/<path:file_id>')
@obsidian_auth
def api_backlinks(file_id):
    """Belirli bir nota link veren diğer notları bulur."""
    vault_path = get_vault_path()
    note_name = os.path.basename(file_id).replace('.md', '')
    
    backlinks = []
    # Arama motorunu kullan (Cache'den faydalan)
    # Cache yoksa veya eskiyse doldur (api_search içindeki mantığı burada da kullanabiliriz)
    # Basitlik için api_search benzeri bir tarama yapalım
    
    search_pattern = f"[[{note_name}]]"
    
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if not file.endswith('.md'): continue
            
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, vault_path).replace('\\', '/')
            if rel_path == file_id: continue # Kendisini atla
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if search_pattern in content:
                        backlinks.append({
                            'id': rel_path,
                            'name': file.replace('.md', '')
                        })
            except:
                continue
                
    return jsonify(backlinks)

@bp.route('/api/graph-data')
@obsidian_auth
def api_graph_data():
    """Graph view için tüm notları ve aralarındaki linkleri döndürür."""
    vault_path = get_vault_path()
    nodes = []
    links = []
    
    # Wiki-link yakalamak için regex
    wiki_regex = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
    
    # Dosya listesi (id -> name mapping için)
    file_map = {} # {note_name: rel_path}
    
    # 1. Tüm notları tara
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if not file.endswith('.md'): continue
            
            rel_path = os.path.relpath(os.path.join(root, file), vault_path).replace('\\', '/')
            name = file.replace('.md', '')
            file_map[name] = rel_path
            nodes.append({'id': rel_path, 'name': name})

    # 2. Linkleri tara
    for node in nodes:
        full_path = os.path.join(vault_path, node['id'])
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = wiki_regex.findall(content)
                for target_name in matches:
                    # Target'ın vault'da var olup olmadığını kontrol et
                    target_name = target_name.strip()
                    if target_name in file_map:
                        links.append({
                            'source': node['id'],
                            'target': file_map[target_name]
                        })
        except:
            continue
            
    return jsonify({'nodes': nodes, 'links': links})

@bp.route('/api/search')
@obsidian_auth
def api_search():
    query = request.args.get('q', '').lower().strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    vault_path = get_vault_path()
    if not vault_path:
        return jsonify([])

    results = []
    MAX_RESULTS = 30
    now = time.time()
    
    # Her 5 dakikada bir dosya listesini tazele (veya ilk çalışmada)
    refresh_cache = (now - _search_cache['last_scan']) > 300
    
    if refresh_cache:
        _search_cache['last_scan'] = now
        # Cache'deki artık dosyaları temizle (isteğe bağlı, şimdilik basit tutalım)

    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if not file.endswith('.md'):
                continue
                
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, vault_path).replace('\\', '/')
            
            # Dosya adında eşleşme (Çok hızlı, disk okuması gerektirmez)
            name_match = query in file.lower()
            
            # İçerik araması
            content_lower = ""
            try:
                stats = os.stat(full_path)
                mtime = stats.st_mtime
                
                # Cache kontrolü
                cached = _search_cache['files'].get(rel_path)
                if cached and cached['mtime'] == mtime:
                    content = cached['content']
                else:
                    # Rclone üzerinden okuma maliyetli olduğu için sadece gerektiğinde oku
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        _search_cache['files'][rel_path] = {
                            'content': content,
                            'mtime': mtime
                        }
                content_lower = content.lower()
            except Exception as e:
                current_app.logger.error(f"Arama hatası ({file}): {str(e)}")
                continue

            if name_match or query in content_lower:
                snippet = ""
                idx = content_lower.find(query)
                if idx != -1:
                    start = max(0, idx - 40)
                    end = min(len(content_lower), idx + 60)
                    snippet = _search_cache['files'][rel_path]['content'][start:end].replace('\n', ' ')
                
                results.append({
                    'id': rel_path,
                    'name': file,
                    'snippet': f"...{snippet}..." if snippet else "",
                    'score': 100 if name_match else 1
                })
                
            if len(results) >= MAX_RESULTS:
                break
        if len(results) >= MAX_RESULTS:
            break
            
    results.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(results)

@bp.route('/api/tree')
@obsidian_auth
def api_tree():
    vault_path = get_vault_path()
    if not vault_path:
        return jsonify([])
    tree = build_tree(vault_path)
    return jsonify(tree)
