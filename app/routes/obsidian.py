"""
app/routes/obsidian.py
Obsidian vault — Google Drive entegrasyonu
Subdomain: obsidian.yigitgulyurt.net.tr
"""

import os, json
from functools import wraps
from flask import (
    Blueprint, render_template, request, jsonify,
    redirect, url_for, session, current_app
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io

bp = Blueprint('obsidian', __name__, subdomain='obsidian')

def obsidian_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        pw = current_app.config.get('OBSIDIAN_PASSWORD', '')
        if not pw or session.get('obsidian_ok') != pw:
            return redirect(url_for('obsidian.login'))
        return f(*args, **kwargs)
    return decorated

SCOPES = ['https://www.googleapis.com/auth/drive']

# Drive'da vault'un klasör adı (root altında arar)
VAULT_FOLDER_NAME = 'yigitgulyurt'
VAULT_PARENT_PATH = ['Obsidian']  # Drive'ım > Obsidian > yigitgulyurt


def get_flow():
    client_config = {
        "web": {
            "client_id":     current_app.config['GOOGLE_CLIENT_ID'],
            "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=current_app.config['GOOGLE_REDIRECT_URI']
    )
    return flow


def get_credentials():
    """Session'dan veya .env token'dan credential yükle."""
    token_path = current_app.config.get('GOOGLE_TOKEN_PATH', 'google_token.json')
    if os.path.exists(token_path):
        with open(token_path) as f:
            token_data = json.load(f)
        creds = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=current_app.config['GOOGLE_CLIENT_ID'],
            client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
            scopes=SCOPES
        )
        return creds
    return None


def save_credentials(creds):
    token_path = current_app.config.get('GOOGLE_TOKEN_PATH', 'google_token.json')
    with open(token_path, 'w') as f:
        json.dump({
            'token':         creds.token,
            'refresh_token': creds.refresh_token,
        }, f)


def get_drive_service():
    creds = get_credentials()
    if not creds:
        return None
    # Token expire olmuşsa refresh et
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        save_credentials(creds)
    return build('drive', 'v3', credentials=creds)


def find_vault_folder(service):
    """Drive'da Obsidian/yigitgulyurt klasörünün ID'sini bulur."""
    # Önce Obsidian klasörünü bul
    q = "name='Obsidian' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = service.files().list(q=q, fields='files(id,name)').execute()
    obsidian_folders = res.get('files', [])
    if not obsidian_folders:
        return None
    obsidian_id = obsidian_folders[0]['id']

    # Sonra içindeki yigitgulyurt klasörünü bul
    q = (f"name='{VAULT_FOLDER_NAME}' and "
         f"'{obsidian_id}' in parents and "
         f"mimeType='application/vnd.google-apps.folder' and trashed=false")
    res = service.files().list(q=q, fields='files(id,name)').execute()
    folders = res.get('files', [])
    return folders[0]['id'] if folders else None


def list_folder(service, folder_id):
    """Klasör içeriğini döner: [{id, name, mimeType, modifiedTime}]"""
    q = f"'{folder_id}' in parents and trashed=false"
    res = service.files().list(
        q=q,
        fields='files(id,name,mimeType,modifiedTime,size)',
        orderBy='folder,name'
    ).execute()
    return res.get('files', [])


def build_tree(service, folder_id, path=''):
    """Recursive vault tree builder."""
    items = list_folder(service, folder_id)
    tree = []
    for item in items:
        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
        node = {
            'id':       item['id'],
            'name':     item['name'],
            'path':     f"{path}/{item['name']}" if path else item['name'],
            'is_folder': is_folder,
            'modified': item.get('modifiedTime', ''),
            'children': []
        }
        if is_folder:
            node['children'] = build_tree(service, item['id'], node['path'])
        else:
            # Sadece markdown dosyalarını göster
            if not item['name'].endswith('.md'):
                continue
        tree.append(node)
    return tree


def get_file_content(service, file_id):
    """Drive'dan dosya içeriğini string olarak çeker."""
    req = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue().decode('utf-8')


def update_file_content(service, file_id, content):
    """Var olan dosyayı günceller."""
    media = MediaIoBaseUpload(
        io.BytesIO(content.encode('utf-8')),
        mimetype='text/markdown'
    )
    service.files().update(fileId=file_id, media_body=media).execute()


def create_file_in_folder(service, folder_id, name, content=''):
    """Klasörde yeni .md dosyası oluşturur."""
    if not name.endswith('.md'):
        name += '.md'
    meta = {'name': name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(
        io.BytesIO(content.encode('utf-8')),
        mimetype='text/markdown'
    )
    file = service.files().create(
        body=meta, media_body=media, fields='id,name'
    ).execute()
    return file


def create_subfolder(service, parent_id, name):
    """Klasör altında yeni klasör oluşturur."""
    meta = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=meta, fields='id,name').execute()
    return folder


def delete_item(service, file_id):
    """Dosyayı çöp kutusuna taşır."""
    service.files().update(fileId=file_id, body={'trashed': True}).execute()


# ── AUTH ROUTES ───────────────────────────────────────────────

@bp.route('/oauth2callback')
def oauth2callback():
    # Nginx arkasında HTTP→HTTPS dönüşümü için
    auth_response = request.url.replace('http://', 'https://')
    flow = get_flow()
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow.fetch_token(authorization_response=auth_response)
    save_credentials(flow.credentials)
    return redirect(url_for('obsidian.index'))


@bp.route('/auth')
@obsidian_auth
def auth():
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['oauth_state'] = state
    return redirect(auth_url)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        pw = current_app.config.get('OBSIDIAN_PASSWORD', '')
        if request.form.get('password') == pw:
            session['obsidian_ok'] = pw
            session.permanent = True
            return redirect(url_for('obsidian.auth'))
        error = True
    return render_template('obsidian/login.html', error=error)

# ── MAIN ROUTES ───────────────────────────────────────────────

@bp.route('/')
@obsidian_auth
def index():
    service = get_drive_service()
    if not service:
        return redirect(url_for('obsidian.auth'))
    vault_id = find_vault_folder(service)
    if not vault_id:
        return render_template('obsidian/index.html',
                               tree=[], error='Vault klasörü bulunamadı.')
    tree = build_tree(service, vault_id)
    return render_template('obsidian/index.html', tree=tree, error=None)


@bp.route('/edit/<file_id>')
@obsidian_auth
def edit(file_id):
    service = get_drive_service()
    if not service:
        return redirect(url_for('obsidian.auth'))
    # Dosya meta
    meta = service.files().get(fileId=file_id, fields='id,name,modifiedTime').execute()
    content = get_file_content(service, file_id)
    return render_template('obsidian/edit.html', file=meta, content=content)


@bp.route('/new')
@obsidian_auth
def new():
    service = get_drive_service()
    if not service:
        return redirect(url_for('obsidian.auth'))
    # folder_id query param'dan alınır
    folder_id = request.args.get('folder_id', '')
    vault_id  = find_vault_folder(service)
    return render_template('obsidian/new.html',
                           folder_id=folder_id or vault_id,
                           vault_id=vault_id)


# ── API ROUTES ────────────────────────────────────────────────

@bp.route('/api/file/<file_id>', methods=['GET'])
@obsidian_auth
def api_get_file(file_id):
    service = get_drive_service()
    content = get_file_content(service, file_id)
    return jsonify({'content': content})


@bp.route('/api/file/<file_id>', methods=['PUT'])
@obsidian_auth
def api_update_file(file_id):
    data = request.get_json()
    content = data.get('content', '')
    service = get_drive_service()
    update_file_content(service, file_id, content)
    return jsonify({'ok': True})


@bp.route('/api/file', methods=['POST'])
@obsidian_auth
def api_create_file():
    data = request.get_json()
    folder_id = data.get('folder_id')
    name      = data.get('name', 'Yeni Not')
    content   = data.get('content', '')
    service   = get_drive_service()
    if not folder_id:
        folder_id = find_vault_folder(service)
    file = create_file_in_folder(service, folder_id, name, content)
    return jsonify({'ok': True, 'file': file})


@bp.route('/api/folder', methods=['POST'])
@obsidian_auth
def api_create_folder():
    data      = request.get_json()
    parent_id = data.get('parent_id')
    name      = data.get('name', 'Yeni Klasör')
    service   = get_drive_service()
    if not parent_id:
        parent_id = find_vault_folder(service)
    folder = create_subfolder(service, parent_id, name)
    return jsonify({'ok': True, 'folder': folder})


@bp.route('/api/file/<file_id>', methods=['DELETE'])
@obsidian_auth
def api_delete_file(file_id):
    service = get_drive_service()
    delete_item(service, file_id)
    return jsonify({'ok': True})


@bp.route('/api/tree')
@obsidian_auth
def api_tree():
    service  = get_drive_service()
    vault_id = find_vault_folder(service)
    tree     = build_tree(service, vault_id)
    return jsonify(tree)